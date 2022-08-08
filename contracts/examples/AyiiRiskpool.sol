// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@etherisc/gif-interface/contracts/components/BasicRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract AyiiRiskpool is BasicRiskpool {

    constructor(
        bytes32 name,
        uint256 collateralization,
        address wallet,
        address registry
    )
        BasicRiskpool(name, collateralization, wallet, registry)
    { }

    // trivial implementation that matches every application
    function bundleMatchesApplication(
        IBundle.Bundle memory bundle, 
        IPolicy.Application memory application
    ) 
        public override
        pure
        returns(bool isMatching) 
    {
        isMatching = true;
    }

}