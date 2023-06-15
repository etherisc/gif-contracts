// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "./strings.sol";

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@etherisc/gif-interface/contracts/components/Oracle.sol";

contract AyiiOracle is 
    Oracle, ChainlinkClient 
{
    using strings for bytes32;
    using Chainlink for Chainlink.Request;

    mapping(bytes32 /* Chainlink request ID */ => uint256 /* GIF request ID */) public gifRequests;
    bytes32 public jobId;
    uint256 public payment;

    event LogAyiiRequest(uint256 requestId, bytes32 chainlinkRequestId);
    
    event LogAyiiFulfill(
        uint256 requestId, 
        bytes32 chainlinkRequestId, 
        bytes32 projectId,
        bytes32 uaiId,
        bytes32 cropId,
        uint256 aaay
    );

    /**
     * @dev Constructor function for the ChainlinkOracle contract.
     * @param _name The name of the oracle contract.
     * @param _registry The address of the oracle registry contract.
     * @param _chainLinkToken The address of the Chainlink token contract.
     * @param _chainLinkOperator The address of the Chainlink oracle operator.
     * @param _jobId The ID of the Chainlink job to be used.
     * @param _payment The payment amount to be sent to the Chainlink oracle operator.
     */
    constructor(
        bytes32 _name,
        address _registry,
        address _chainLinkToken,
        address _chainLinkOperator,
        bytes32 _jobId,
        uint256 _payment
    )
        Oracle(_name, _registry)
    {
        updateRequestDetails(
            _chainLinkToken, 
            _chainLinkOperator, 
            _jobId, 
            _payment);
    }

    /**
     * @dev Update request details for Chainlink oracle job.
     * @param _chainLinkToken The address of the Chainlink token contract.
     * @param _chainLinkOperator The address of the Chainlink oracle operator.
     * @param _jobId The job ID for the Chainlink oracle job.
     * @param _payment The payment amount for the Chainlink oracle job.
     */
    function updateRequestDetails(
        address _chainLinkToken,
        address _chainLinkOperator,
        bytes32 _jobId,
        uint256 _payment
    ) 
        public 
        onlyOwner 
    {
        if (_chainLinkToken != address(0)) { setChainlinkToken(_chainLinkToken); }
        if (_chainLinkOperator != address(0)) { setChainlinkOracle(_chainLinkOperator); }
        
        jobId = _jobId;
        payment = _payment;
    }

    /**
     * @dev Sends a Chainlink request to retrieve data for a specific GIF request.
     * @param gifRequestId The ID of the GIF request.
     * @param input The encoded input data containing the project ID, UAI ID, and crop ID.
     *             The input must be in the following format: abi.encode([bytes32 projectId, bytes32 uaiId, bytes32 cropId]).
     * @notice This function emits 1 events: 
     * - LogAyiiRequest
     */
    function request(uint256 gifRequestId, bytes calldata input)
        external override
        onlyQuery
    {
        Chainlink.Request memory request_ = buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );

        (
            bytes32 projectId, 
            bytes32 uaiId, 
            bytes32 cropId
        ) = abi.decode(input, (bytes32, bytes32, bytes32));

        request_.add("projectId", projectId.toB32String());
        request_.add("uaiId", uaiId.toB32String());
        request_.add("cropId", cropId.toB32String());

        bytes32 chainlinkRequestId = sendChainlinkRequest(request_, payment);

        gifRequests[chainlinkRequestId] = gifRequestId;
        emit LogAyiiRequest(gifRequestId, chainlinkRequestId);
    }

    /**
     * @dev This function is used to fulfill a Chainlink request for the given parameters.
     * @param chainlinkRequestId The ID of the Chainlink request to fulfill.
     * @param projectId The ID of the project.
     * @param uaiId The ID of the UAI.
     * @param cropId The ID of the crop.
     * @param aaay The amount of AAAY.
     * @notice This function emits 1 events: 
     * - LogAyiiFulfill
     */
    function fulfill(
        bytes32 chainlinkRequestId, 
        bytes32 projectId, 
        bytes32 uaiId, 
        bytes32 cropId, 
        uint256 aaay
    )
        public recordChainlinkFulfillment(chainlinkRequestId) 
    {
        uint256 gifRequest = gifRequests[chainlinkRequestId];
        bytes memory data =  abi.encode(projectId, uaiId, cropId, aaay);        
        _respond(gifRequest, data);

        delete gifRequests[chainlinkRequestId];
        emit LogAyiiFulfill(gifRequest, chainlinkRequestId, projectId, uaiId, cropId, aaay);
    }

    /**
     * @dev Cancels a Chainlink request.
     * @param requestId The ID of the request to cancel.
     */
    function cancel(uint256 requestId)
        external override
        onlyOwner
    {
        // TODO mid/low priority
        // cancelChainlinkRequest(_requestId, _payment, _callbackFunctionId, _expiration);
    }

    // only used for testing of chainlink operator
    /**
     * @dev Encodes the parameters required for a Chainlink request fulfillment.
     * @param chainlinkRequestId The ID of the Chainlink request.
     * @param projectId The ID of the project.
     * @param uaiId The ID of the UAI.
     * @param cropId The ID of the crop.
     * @param aaay The value of aaay.
     * @return parameterData The encoded parameter data.
     */
    function encodeFulfillParameters(
        bytes32 chainlinkRequestId, 
        bytes32 projectId, 
        bytes32 uaiId, 
        bytes32 cropId, 
        uint256 aaay
    ) 
        external
        pure
        returns(bytes memory parameterData)
    {
        return abi.encode(
            chainlinkRequestId, 
            projectId, 
            uaiId, 
            cropId, 
            aaay
        );
    }

    /**
     * @dev Returns the Chainlink Job ID associated with this contract.
     * @return chainlinkJobId The Chainlink Job ID as a bytes32 variable.
     */
    function getChainlinkJobId() external view returns(bytes32 chainlinkJobId) {
        return jobId;
    }

    /**
     * @dev Returns the payment amount for a Chainlink oracle request.
     * @return paymentAmount The payment amount in uint256.
     */
    function getChainlinkPayment() external view returns(uint256 paymentAmount) {
        return payment;
    }

    /**
     * @dev Returns the address of the Chainlink token.
     * @return linkTokenAddress The address of the Chainlink token.
     */
    function getChainlinkToken() external view returns(address linkTokenAddress) {
        return chainlinkTokenAddress();
    }

    /**
     * @dev Returns the address of the Chainlink operator.
     * @return operator The address of the Chainlink operator.
     */
    function getChainlinkOperator() external view returns(address operator) {
        return chainlinkOracleAddress();
    }
}

