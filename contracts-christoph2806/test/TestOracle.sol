// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/Oracle.sol";

contract TestOracle is Oracle {

    /**
     * @dev Constructor function for creating an Oracle contract.
     * @param oracleName The name of the Oracle contract.
     * @param registry The address of the registry contract.
     */
    constructor(
        bytes32 oracleName,
        address registry
    )
        Oracle(oracleName, registry)
    { }

    /**
     * @dev Requests data from the oracle contract.
     * @param requestId The unique identifier of the request.
     * @param input The input data to be decoded by the oracle.
     *             It is a tuple containing a uint256 counter and a bool immediateResponse.
     *
     * This function decodes the input data and calls the _oracleCalculation function
     * to obtain data from the oracle given the request data (counter).
     * If immediateResponse is true, the function responds with the result obtained from the oracle.
     * Otherwise, the response is handled outside the function in a separate asynchronous transaction.
     * The response is sent back to the contract through the respond function.
     */
    function request(uint256 requestId, bytes calldata input) external override onlyQuery {
        // decode oracle input data
        (uint256 counter, bool immediateResponse) = abi.decode(input, (uint256, bool));

        if (immediateResponse) {
            // obtain data from oracle given the request data (counter)
            // for off chain oracles this happens outside the request
            // call in a separate asynchronous transaction
            bool isLossEvent = _oracleCalculation(counter);
            respond(requestId, isLossEvent);
        }
    }

    /**
     * @dev Cancels a Chainlink request.
     * @param requestId The ID of the Chainlink request to be cancelled.
     */
    function cancel(uint256 requestId)
        external override
        onlyOwner
    {
        // TODO mid/low priority
        // cancelChainlinkRequest(_requestId, _payment, _callbackFunctionId, _expiration);
    }

    // usually called by off-chain oracle (and not internally) 
    // in which case the function modifier should be changed 
    // to external
    /**
     * @dev Responds to an oracle request with a boolean value indicating whether a loss event occurred.
     * @param requestId The ID of the oracle request being responded to.
     * @param isLossEvent A boolean value indicating whether a loss event occurred.
     */
    function respond(uint256 requestId, bool isLossEvent) 
        public
    {
        // encode data obtained from oracle
        bytes memory output = abi.encode(bool(isLossEvent));

        // trigger inherited response handling
        _respond(requestId, output);
    }

    // dummy implementation
    // "real" oracles will get the output from some off-chain
    // component providing the outcome of the business logic
    /**
     * @dev Performs an oracle calculation to determine if a loss event occurred.
     * @param counter The counter value used in the calculation.
     * @return isLossEvent A boolean indicating if a loss event occurred.
     */
    function _oracleCalculation(uint256 counter) internal returns (bool isLossEvent) {
        isLossEvent = (counter % 2 == 1);
    }    
}