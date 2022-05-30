// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@gif-interface/contracts/Oracle.sol";


contract TestOracle is Oracle {

    constructor(
        address gifOracleService,
        address gifOracleOwnerService,
        bytes32 oracleName
    )
        Oracle(gifOracleService, gifOracleOwnerService, oracleName)
    { }

    function request(uint256 requestId, bytes calldata input) external override onlyQuery {
        // decode oracle input data
        (uint256 input_value) = abi.decode(input, (uint256));

        // obtain and encode oracle output data
        bool isLossEvent = _businessLogic(input_value);
        bytes memory output = abi.encode(bool(isLossEvent));

        // trigger inherited response handling
        _respond(requestId, output);
    }

    // this is just for dummy testing
    // real oracle implementations will get the output from some off-chain
    // component providing the outcome of the business logic
    function _businessLogic(uint256 value) internal returns (bool isLossEvent) {
        isLossEvent = (value % 2 == 1);
    }
}