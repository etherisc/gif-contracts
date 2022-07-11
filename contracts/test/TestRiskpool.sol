// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./BasicRiskpool.sol";

import "@gif-interface/contracts/modules/IBundle.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";

contract TestRiskpool is BasicRiskpool {

    constructor(
        bytes32 name,
        uint256 collateralization,
        address wallet,
        address registry
    )
        BasicRiskpool(name, collateralization, wallet, registry)
    { }

    // default/trivial implementation that matches every application
    function bundleMatchesApplication(
        IBundle.Bundle memory bundle, 
        IPolicy.Application memory application
    ) 
        public override
        view
        returns(bool isMatching) 
    {
        isMatching = true;
    }
}