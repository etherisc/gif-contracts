// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/access/AccessControl.sol";

import "./BasicRiskpool2.sol";
import "@etherisc/gif-interface/contracts/components/BasicRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract AyiiRiskpool is 
    BasicRiskpool,
    AccessControl
{
    // 0x5614e11ca6d7673c9c8dcec913465d676494aad1151bb2c1cf40b9d99be4d935
    bytes32 public constant INVESTOR_ROLE = keccak256("INVESTOR");

    // restricts the maximal sum of sum insured that are secured by gthe riskpool
    uint256 public constant SUM_OF_SUM_INSURED_CAP = 10**24;

    constructor(
        bytes32 name,
        uint256 collateralization,
        address erc20Token,
        address wallet,
        address registry
    )
        BasicRiskpool(name, collateralization, SUM_OF_SUM_INSURED_CAP, erc20Token, wallet, registry)
    {

        _setupRole(DEFAULT_ADMIN_ROLE, _msgSender());
    }


    function grantInvestorRole(address investor)
        external
        onlyOwner
    {
        _setupRole(INVESTOR_ROLE, investor);
    }


    function createBundle(bytes memory filter, uint256 initialAmount) 
        public override
        onlyRole(INVESTOR_ROLE)
        returns(uint256 bundleId)
    {
        bundleId = super.createBundle(filter, initialAmount);
    }


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