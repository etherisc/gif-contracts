// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/BundleController.sol";
import "../modules/ComponentController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "@etherisc/gif-interface/contracts/services/IRiskpoolService.sol";

contract RiskpoolService is
    IRiskpoolService, 
    CoreController
{
    bytes32 public constant RISKPOOL_NAME = "Riskpool";

    ComponentController private _component;
    BundleController private _bundle;
    TreasuryModule private _treasury;

    modifier onlyRiskpool() {
        IComponent component = IComponent(_msgSender());
        require(
            component.isRiskpool(),
            "ERROR:RPS-001:SENDER_NOT_RISKPOOL"
        );
        _;
    }

    modifier onlyOwningRiskpool(uint256 bundleId) {
        IComponent component = IComponent(_msgSender());
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            component.isRiskpool() && component.getId() == bundle.riskpoolId,
            "ERROR:RPS-002:NOT_OWNING_RISKPOOL"
        );
        _;
    }


    function _afterInitialize() 
        internal override 
        onlyInitializing 
    {
        _bundle = BundleController(_getContractAddress("Bundle"));
        _component = ComponentController(_getContractAddress("Component"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));
    }


    function createBundle(
        address owner, 
        bytes calldata filter, 
        uint256 initialCapital
    ) 
        external override
        onlyRiskpool
        returns(uint256 bundleId)
    {
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        bundleId = _bundle.create(owner, riskpoolId, filter, 0);

        (bool success, uint256 netCapital) = _treasury.processCapital(bundleId, initialCapital);

        if (success) {
            _bundle.fund(bundleId, netCapital);
        }
    }


    function fundBundle(uint256 bundleId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId)  
    {
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(bundle.state != IBundle.BundleState.Closed, "ERROR:RPS-003:BUNDLE_CLOSED");

        (bool success, uint256 netAmount) = _treasury.processCapital(bundleId, amount);
        if (success) {
            _bundle.fund(bundleId, netAmount);
        }
    }


    function defundBundle(uint256 bundleId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId)  
    {
        (bool success, uint256 netAmount) = _treasury.processWithdrawl(bundleId, amount);
        if (success) {
            _bundle.defund(bundleId, netAmount);
        }
    }


    function lockBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId)  
    {
        _bundle.lock(bundleId);
    }


    function unlockBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId)  
    {
        _bundle.unlock(bundleId);
    }


    function closeBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId)  
    {
        _bundle.close(bundleId);
    }

    
    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 collateralAmount) 
        external override
        onlyOwningRiskpool(bundleId)  
    {
        _bundle.collateralizePolicy(bundleId, processId, collateralAmount);
    }


    function increaseBundleBalance(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId)  
    {        
        _bundle.increaseBalance(bundleId, processId, amount);
    }


    function decreaseBundleBalance(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId)  
    {
        revert("NOT_IMPLEMENTED_YET:decreaseBundleBalance(...)");
    }

    function releasePolicy(uint256 bundleId, bytes32 processId)
        external override
        onlyRiskpool
        returns(uint256 collateralAmount)
    {
        // TODO refactor reqruire below into modifier onlyAssociatedRiskpool
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            riskpoolId == bundle.riskpoolId,
            "ERROR:RPS-003:NOT_ASSOCIATED_RISKPOOL"
        );

        collateralAmount = _bundle.releasePolicy(bundleId, processId);
    }
}
