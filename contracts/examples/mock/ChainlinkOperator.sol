// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "@openzeppelin/contracts/access/Ownable.sol";

contract ChainlinkOperator is 
    Ownable
{

    struct Commitment {
        bytes31 paramsHash;
        uint8 dataVersion;
    }

    uint256 public constant getExpiryTime = 5 minutes;
    uint256 private constant MAXIMUM_DATA_VERSION = 256;
    uint256 private constant MINIMUM_CONSUMER_GAS_LIMIT = 400000;

    event AuthorizedSendersChanged(address[] senders, address changedBy);

    event OracleRequest(
        bytes32 indexed specId,
        address requester,
        bytes32 requestId,
        uint256 payment,
        address callbackAddr,
        bytes4 callbackFunctionId,
        uint256 cancelExpiration,
        uint256 dataVersion,
        bytes data
    );

    event CancelOracleRequest(bytes32 indexed requestId);

    event OracleResponse(bytes32 indexed requestId);

    // contract variables
    mapping(address => bool) private s_authorizedSenders;
    address[] private s_authorizedSenderList;

    mapping(bytes32 => Commitment) private s_commitments;

    /**
    * @notice prevents non-authorized addresses from calling this method
    */
    modifier validateAuthorizedSenderSetter() {
        require(_canSetAuthorizedSenders(), "Cannot set authorized senders");
        _;
    }

    constructor() Ownable() { }

    /**
    * @notice Sets the fulfillment permission for a given node. Use `true` to allow, `false` to disallow.
    * @param senders The addresses of the authorized Chainlink node
    */
    function setAuthorizedSenders(address[] calldata senders)
        external 
        validateAuthorizedSenderSetter 
    {
        require(senders.length > 0, "Must have at least 1 authorized sender");
        // Set previous authorized senders to false
        uint256 authorizedSendersLength = s_authorizedSenderList.length;
        for (uint256 i = 0; i < authorizedSendersLength; i++) {
            s_authorizedSenders[s_authorizedSenderList[i]] = false;
        }
        // Set new to true
        for (uint256 i = 0; i < senders.length; i++) {
            s_authorizedSenders[senders[i]] = true;
        }
        // Replace list
        s_authorizedSenderList = senders;
        emit AuthorizedSendersChanged(senders, msg.sender);
    }


    function getAuthorizedSenders()
        external 
        view
        returns(address [] memory)
    {
        return s_authorizedSenderList;
    }

    /**
    * @notice Called when LINK is sent to the contract via `transferAndCall`
    * @dev The data payload's first 2 words will be overwritten by the `sender` and `amount`
    * values to ensure correctness. Calls oracleRequest.
    * @param sender Address of the sender
    * @param amount Amount of LINK sent (specified in wei)
    * @param data Payload of the transaction
    */
    function onTokenTransfer(
        address sender,
        uint256 amount,
        bytes memory data
    )
        public 
        // validateFromLINK 
        // permittedFunctionsForLINK(data) 
    {
        assembly {
            // solhint-disable-next-line avoid-low-level-calls
            mstore(add(data, 36), sender) // ensure correct sender is passed
            // solhint-disable-next-line avoid-low-level-calls
            mstore(add(data, 68), amount) // ensure correct amount is passed
        }
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = address(this).delegatecall(data); // calls oracleRequest
        require(success, "Unable to create request");
    }


    /**
    * @notice Creates the Chainlink request. This is a backwards compatible API
    * with the Oracle.sol contract, but the behavior changes because
    * callbackAddress is assumed to be the same as the request sender.
    * @param callbackAddress The consumer of the request
    * @param payment The amount of payment given (specified in wei)
    * @param specId The Job Specification ID
    * @param callbackAddress The address the oracle data will be sent to
    * @param callbackFunctionId The callback function ID for the response
    * @param nonce The nonce sent by the requester
    * @param dataVersion The specified data version
    * @param data The extra request parameters
    */
    function oracleRequest(
        address sender,
        uint256 payment,
        bytes32 specId,
        address callbackAddress,
        bytes4 callbackFunctionId,
        uint256 nonce,
        uint256 dataVersion,
        bytes calldata data
    )
        external 
        // override 
        // validateFromLINK 
    {
        (bytes32 requestId, uint256 expiration) = _verifyAndProcessOracleRequest(
            sender,
            payment,
            callbackAddress,
            callbackFunctionId,
            nonce,
            dataVersion
        );
        emit OracleRequest(specId, sender, requestId, payment, sender, callbackFunctionId, expiration, dataVersion, data);
    }


    /**
    * @notice Called by the Chainlink node to fulfill requests with multi-word support
    * @dev Given params must hash back to the commitment stored from `oracleRequest`.
    * Will call the callback address' callback function without bubbling up error
    * checking in a `require` so that the node can get paid.
    * @param requestId The fulfillment request ID that must match the requester's
    * @param payment The payment amount that will be released for the oracle (specified in wei)
    * @param callbackAddress The callback address to call for fulfillment
    * @param callbackFunctionId The callback function ID to use for fulfillment
    * @param expiration The expiration that the node should respond by before the requester can cancel
    * @param data The data to return to the consuming contract
    * @return Status if the external call was successful
    */
    function fulfillOracleRequest2(
        bytes32 requestId,
        uint256 payment,
        address callbackAddress,
        bytes4 callbackFunctionId,
        uint256 expiration,
        bytes calldata data
    )
        external
        // override
        // validateAuthorizedSender
        // validateRequestId(requestId)
        // validateCallbackAddress(callbackAddress)
        // validateMultiWordResponseId(requestId, data)
        returns (bool)
    {
        _verifyOracleRequestAndProcessPayment(requestId, payment, callbackAddress, callbackFunctionId, expiration, 2);

        emit OracleResponse(requestId);
        require(gasleft() >= MINIMUM_CONSUMER_GAS_LIMIT, "Must provide consumer enough gas");

        // All updates to the oracle's fulfillment should come before calling the
        // callback(addr+functionId) as it is untrusted.
        // See: https://solidity.readthedocs.io/en/develop/security-considerations.html#use-the-checks-effects-interactions-pattern
        (bool success, ) = callbackAddress.call(abi.encodePacked(callbackFunctionId, data)); // solhint-disable-line avoid-low-level-calls
        return success;
    }


    /**
    * @notice Verify the Oracle Request and record necessary information
    * @param sender The sender of the request
    * @param payment The amount of payment given (specified in wei)
    * @param callbackAddress The callback address for the response
    * @param callbackFunctionId The callback function ID for the response
    * @param nonce The nonce sent by the requester
    */
    function _verifyAndProcessOracleRequest(
        address sender,
        uint256 payment,
        address callbackAddress,
        bytes4 callbackFunctionId,
        uint256 nonce,
        uint256 dataVersion
    ) 
        private 
        // validateNotToLINK(callbackAddress) 
        returns (bytes32 requestId, uint256 expiration) 
    {
        requestId = keccak256(abi.encodePacked(sender, nonce));
        require(s_commitments[requestId].paramsHash == 0, "Must use a unique ID");
        // solhint-disable-next-line not-rely-on-time
        // expiration = block.timestamp.add(getExpiryTime);
        expiration = block.timestamp + getExpiryTime;
        bytes31 paramsHash = _buildParamsHash(payment, callbackAddress, callbackFunctionId, expiration);
        s_commitments[requestId] = Commitment(paramsHash, _safeCastToUint8(dataVersion));
        // s_tokensInEscrow = s_tokensInEscrow.add(payment);
        return (requestId, expiration);
    }


    /**
    * @notice Verify the Oracle request and unlock escrowed payment
    * @param requestId The fulfillment request ID that must match the requester's
    * @param payment The payment amount that will be released for the oracle (specified in wei)
    * @param callbackAddress The callback address to call for fulfillment
    * @param callbackFunctionId The callback function ID to use for fulfillment
    * @param expiration The expiration that the node should respond by before the requester can cancel
    */
    function _verifyOracleRequestAndProcessPayment(
        bytes32 requestId,
        uint256 payment,
        address callbackAddress,
        bytes4 callbackFunctionId,
        uint256 expiration,
        uint256 dataVersion
    )
        internal
    {
        bytes31 paramsHash = _buildParamsHash(payment, callbackAddress, callbackFunctionId, expiration);
        require(s_commitments[requestId].paramsHash == paramsHash, "Params do not match request ID");
        require(s_commitments[requestId].dataVersion <= _safeCastToUint8(dataVersion), "Data versions must match");
        // s_tokensInEscrow = s_tokensInEscrow.sub(payment);
        delete s_commitments[requestId];
    }


    /**
    * @notice Build the bytes31 hash from the payment, callback and expiration.
    * @param payment The payment amount that will be released for the oracle (specified in wei)
    * @param callbackAddress The callback address to call for fulfillment
    * @param callbackFunctionId The callback function ID to use for fulfillment
    * @param expiration The expiration that the node should respond by before the requester can cancel
    * @return hash bytes31
    */
    function _buildParamsHash(
        uint256 payment,
        address callbackAddress,
        bytes4 callbackFunctionId,
        uint256 expiration
    ) internal pure returns (bytes31) {
        return bytes31(keccak256(abi.encodePacked(payment, callbackAddress, callbackFunctionId, expiration)));
    }


    /**
    * @notice Safely cast uint256 to uint8
    * @param number uint256
    * @return uint8 number
    */
    function _safeCastToUint8(uint256 number) internal pure returns (uint8) {
        require(number < MAXIMUM_DATA_VERSION, "number too big to cast");
        return uint8(number);
    }

    /**
    * @notice concrete implementation of AuthorizedReceiver
    * @return bool of whether sender is authorized
    */
    function _canSetAuthorizedSenders() internal view returns (bool) {
        return owner() == msg.sender;
    }

}
