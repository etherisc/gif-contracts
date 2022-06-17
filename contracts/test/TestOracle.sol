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

    function _calculateResponseData(bytes calldata requestData)
        internal 
        override 
        returns (bytes memory responseData)
    {
        // decode oracle input data
        (uint256 input_value) = abi.decode(requestData, (uint256));

        // this is just for dummy testing
        // real oracle implementations would make the oracle call here
        // either to some chainlink data feed or some off-chain
        // component providing the outcome of the business logic
        bool isLossEvent = (input_value % 2 == 1);

        // encode oracle output data
        responseData = abi.encode(bool(isLossEvent));
    }
}