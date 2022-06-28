// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@gif-interface/contracts/components/Oracle.sol";

contract TestOracle is Oracle {

    constructor(
        bytes32 oracleName,
        address registry
    )
        Oracle(oracleName, registry)
    { }

    function request(uint256 requestId, bytes calldata input) external override onlyQuery {
        // decode oracle input data
        (uint256 counter) = abi.decode(input, (uint256));

        // obtain data from oracle given the request data (counter)
        // for off chain oracles this happens outside the request
        // call in a separate asynchronous transaction
        bool isLossEvent = _oracleCalculation(counter);
        respond(requestId, isLossEvent);
    }

    // usually called by off-chain oracle (and not internally) 
    // in which case the function modifier should be changed 
    // to external
    function respond(uint256 requestId, bool isLossEvent) 
        internal
    {
        // encode data obtained from oracle
        bytes memory output = abi.encode(bool(isLossEvent));

        // trigger inherited response handling
        _respond(requestId, output);
    }

    // dummy implementation
    // "real" oracles will get the output from some off-chain
    // component providing the outcome of the business logic
    function _oracleCalculation(uint256 counter) internal returns (bool isLossEvent) {
        isLossEvent = (counter % 2 == 1);
    }    
}