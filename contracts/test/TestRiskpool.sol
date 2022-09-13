// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/BasicRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract TestRiskpool is BasicRiskpool {

    uint256 public constant SUM_OF_SUM_INSURED_CAP = 10**24;

    constructor(
        bytes32 name,
        uint256 collateralization,
        address erc20Token,
        address wallet,
        address registry
    )
        BasicRiskpool(name, collateralization, SUM_OF_SUM_INSURED_CAP, erc20Token, wallet, registry)
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