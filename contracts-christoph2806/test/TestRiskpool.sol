// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/BasicRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract TestRiskpool is BasicRiskpool {

    uint256 public constant SUM_OF_SUM_INSURED_CAP = 10**24;

    /**
     * @dev Constructor function for the Riskpool contract.
     * @param name The name of the Riskpool.
     * @param collateralization The collateralization ratio for the Riskpool.
     * @param erc20Token The address of the ERC20 token used for collateral.
     * @param wallet The address of the wallet that holds the collateral.
     * @param registry The address of the registry contract.
     */
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
    /**
     * @dev This function checks if a given bundle matches a given application.
     * @param bundle The bundle to check.
     * @param application The application to check against.
     * @return isMatching A boolean indicating whether the bundle matches the application.
     */
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