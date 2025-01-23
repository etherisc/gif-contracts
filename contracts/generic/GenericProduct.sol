// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/Product.sol";

contract GenericProduct is Product {
    bytes32 public constant POLICY_FLOW = "";

    constructor(
        bytes32 productName,
        address registry,
        address token,
        uint256 riskpoolId,
        address insurer
    ) Product(productName, token, POLICY_FLOW, riskpoolId, registry) {}
}
