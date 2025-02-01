// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

// new: Implementation with Chainlink Functions.

import "./strings.sol";
import "./AyiiClf.sol";
import "@etherisc/gif-interface/contracts/components/Oracle.sol";

/// @title AyiiOracle
/// @notice This contract is the implementation of the Oracle contract that uses the Chainlink DON network.
/// @custom:security
/// - We assume the security of the Chainlink DON network and the AyiiClfConsumer contract.
/// - The contract owner should be the `oracleProvider` account.
/// - We assume that the owner of this contract is trustworthy,
///   as they can set the address of the AyiiClfConsumer contract anytime.
/// - The contract is automatically registered in the registry
///   when deployed by inheriting the Oracle contract.
/// - Only the contract owner can set the address of the AyiiClfConsumer contract.
/// - The request function can only be called by the GIF framework, i.e. the Query module.
/// - The fulfillClfRequest function can only be called by the AyiiClfConsumer contract,
///   which in turn can only be called by the Chainlink DON framework.
/// @custom:deployment
/// - The contract is deployed by the `oracleProvider` account.
/// - Deployment sequence:
///   The contract must be deployed before the deployment of the product contract,
///   because the product contract deployment requires the address of the oracle contract.
/// - The address of the AyiiClfConsumer contract must be set after deployment, this
///   can be done anytime after deployment, but before the first request is sent.

contract AyiiOracle is Oracle {
    using strings for bytes32;

    AyiiClf public ayiiClf;
    modifier onlyAyiiClf() {
        require(
            _msgSender() == address(ayiiClf),
            "ERROR:AYII-001:ACCESS_DENIED"
        );
        _;
    }

    /// @dev Mapping of Chainlink request IDs to GIF request IDs.
    mapping(bytes32 /* Chainlink request ID */ => uint256 /* GIF request ID */)
        public gifRequests;

    event LogAyiiRequest(uint256 requestId, bytes32 chainlinkRequestId);

    event LogAyiiFulfill(
        uint256 requestId,
        bytes32 chainlinkRequestId,
        bytes response
    );

    event LogAyiiFulfillError(
        uint256 requestId,
        bytes32 chainlinkRequestId,
        bytes err
    );

    constructor(bytes32 _name, address _registry) Oracle(_name, _registry) {
        // NOOP
    }

    /// @dev Here we set the address of the AyiiClfConsumer contract.
    /// The AyiiClfConsumer contract is the one that will send the request to the Chainlink DON network.
    /// AyiiClfConsumer is maintained in a separate repository because it uses the 0.8.19 version of Solidity
    /// which is incompatible with this repo, which uses the 0.8.2 version of Solidity.
    /// @param _ayiiClf The address of the AyiiClfConsumer contract.

    function setClfGateWay(address _ayiiClf) external onlyOwner {
        ayiiClf = AyiiClf(_ayiiClf);
    }

    /// @dev This function is called by the GIF framework and sends a request to the Chainlink DON network.
    /// @param gifRequestId The ID of the request.
    /// @param input The input data for the request.
    /// input data is abi encoded (bytes32, bytes32, bytes32) where:
    /// - the first bytes32 is the projectId e.g. "1234"
    /// - the second bytes32 is the uaiId e.g. "134"
    /// - the third bytes32 is the cropId e.g. "Greengrams"
    /// The abi encoding is already done in the product contract so we don't need to do it here.
    function request(
        uint256 gifRequestId,
        bytes calldata input
    ) external override onlyQuery {
        require(
            address(ayiiClf) != address(0),
            "ERROR:AYII-002:GATEWAY_NOT_SET"
        );
        bytes32 chainlinkRequestId = ayiiClf.sendClfRequest(input);

        gifRequests[chainlinkRequestId] = gifRequestId;
        emit LogAyiiRequest(gifRequestId, chainlinkRequestId);
    }

    /// @dev This function is called by the AyiiClfConsumer contract when it receives a response from the Chainlink DON network.
    /// @param requestId The chainlink functions request ID of the request.
    /// @param response The response from the Chainlink DON network.
    /// @param err The error message if the request failed.
    /// @notice Either response or err will be filled.
    /// In case of an error, the error message will be logged and the function will return so the request can be retried.
    /// In this case, the request has to be cancelled in the product with the cancelOracleRequest function.
    function fulfillClfRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) external onlyAyiiClf {
        uint256 gifRequest = gifRequests[requestId];
        if (gifRequest == 0) {
            revert("ERROR:AYII-003:UNEXPECTED_REQUEST_ID");
        }
        if (err.length > 0) {
            // don't revert so we can log the error
            emit LogAyiiFulfillError(gifRequest, requestId, err);
            return;
        }
        _respond(gifRequest, response);

        delete gifRequests[requestId];
        emit LogAyiiFulfill(gifRequest, requestId, response);
    }

    /// @dev This function needs to exist due to the interface, but it is not used.
    /// not implemented / no implementation needed
    /// to cancel a request on our side, use product.cancelOracleRequest(policyId)
    /// to cancel a request on the Chainlink side, use functions.chainlink.com
    /// Chainlink functions request run in a timeout after 5 minutes, so no need to cancel them;
    /// the timeout needs to be confirmed in the Functions web interface.

    // solhint-disable-next-line no-empty-blocks
    function cancel(uint256 requestId) external override onlyQuery {}
}
