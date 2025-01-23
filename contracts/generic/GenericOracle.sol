// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/Oracle.sol";

contract GenericOracle is Oracle {
    constructor(bytes32 _name, address _registry) Oracle(_name, _registry) {
        // not implemented
    }

    function request(
        uint256 gifRequestId,
        bytes calldata input
    ) external override {
        // not implemented
    }

    function cancel(uint256 requestId) external override {
        // not implemented
    }
}
