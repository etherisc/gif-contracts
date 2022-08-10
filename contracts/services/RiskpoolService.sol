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
    PoolController private _pool;
    TreasuryModule private _treasury;

    modifier onlyProposedRiskpool() {
        uint256 componentId = _component.getComponentId(_msgSender());
        require(
            _component.getComponentType(componentId) == IComponent.ComponentType.Riskpool,
            "ERROR:RPS-001:SENDER_NOT_RISKPOOL"
        );
        require(
            _component.getComponentState(componentId) == IComponent.ComponentState.Proposed,
            "ERROR:RPS-002:RISKPOOL_NOT_PROPOSED"
        );
        _;
    }

    modifier onlyActiveRiskpool() {
        uint256 componentId = _component.getComponentId(_msgSender());
        require(
            _component.getComponentType(componentId) == IComponent.ComponentType.Riskpool,
            "ERROR:RPS-001:SENDER_NOT_RISKPOOL"
        );
        require(
            _component.getComponentState(componentId) == IComponent.ComponentState.Active,
            "ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"
        );
        _;
    }

    modifier onlyOwningRiskpool(uint256 bundleId, bool mustBeActive) {
        uint256 componentId = _component.getComponentId(_msgSender());
        bool isRiskpool = _component.getComponentType(componentId) == IComponent.ComponentType.Riskpool;
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            isRiskpool && componentId == bundle.riskpoolId,
            "ERROR:RPS-002:NOT_OWNING_RISKPOOL"
        );
        if (mustBeActive) {
            require(
                _component.getComponentState(componentId) == IComponent.ComponentState.Active,
                "ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"
            );
        }
        _;
    }


    function _afterInitialize() 
        internal override 
        onlyInitializing 
    {
        _bundle = BundleController(_getContractAddress("Bundle"));
        _component = ComponentController(_getContractAddress("Component"));
        _pool = PoolController(_getContractAddress("Pool"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));
    }


    function registerRiskpool(
        address wallet,
        address erc20Token,
        uint256 collateralizationLevel, 
        uint256 sumOfSumInsuredCap
    )
        external override
        onlyProposedRiskpool
    {
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        _pool.registerRiskpool(
            riskpoolId, 
            wallet,
            erc20Token,
            collateralizationLevel, 
            sumOfSumInsuredCap
        );
    }

    function createBundle(
        address owner, 
        bytes calldata filter, 
        uint256 initialCapital
    ) 
        external override
        onlyActiveRiskpool
        returns(uint256 bundleId)
    {
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        bundleId = _bundle.create(owner, riskpoolId, filter, 0);

        (bool success, uint256 fee, uint256 netCapital) = _treasury.processCapital(bundleId, initialCapital);

        if (success) {
            _bundle.fund(bundleId, netCapital);
        }
    }


    function fundBundle(uint256 bundleId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
        returns(bool success, uint256 netAmount)
    {
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(bundle.state != IBundle.BundleState.Closed, "ERROR:RPS-003:BUNDLE_CLOSED");

        uint256 feeAmount;
        (success, feeAmount, netAmount) = _treasury.processCapital(bundleId, amount);
        if (success) {
            _bundle.fund(bundleId, netAmount);
        }
    }


    function defundBundle(uint256 bundleId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
        returns(bool success, uint256 netAmount)
    {
        uint256 feeAmount;
        (success, feeAmount, netAmount) = _treasury.processWithdrawal(bundleId, amount);
        require(success, "ERROR:RPS-004:BUNDLE_DEFUNDING_FAILED");
        require(netAmount == amount, "UUPS");

        if (success) {
            _bundle.defund(bundleId, amount);
        }
    }


    function lockBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)
    {
        _bundle.lock(bundleId);
    }


    function unlockBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        _bundle.unlock(bundleId);
    }


    function closeBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        _bundle.close(bundleId);
    }

    function burnBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        // ensure bundle is closed
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(bundle.state == IBundle.BundleState.Closed, "ERROR:RPS-004:BUNDLE_NOT_CLOSED");

        // withdraw remaining balance
        (bool success, uint256 feeAmount, uint256 netAmount) = _treasury.processWithdrawal(bundleId, bundle.balance);
        require(success, "ERROR:RPS-005:WITHDRAWAL_FAILED");

        if (success) {
            _bundle.defund(bundleId, bundle.balance);
            _bundle.burn(bundleId);
        }
    }
    
    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 collateralAmount) 
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        _bundle.collateralizePolicy(bundleId, processId, collateralAmount);
    }

    function releasePolicy(uint256 bundleId, bytes32 processId)
        external override
        onlyOwningRiskpool(bundleId, false)  
        returns(uint256 collateralAmount)
    {
        collateralAmount = _bundle.releasePolicy(bundleId, processId);
    }


    // TODO remove from interface, delete, test, remove
    function increaseBundleBalance(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
    {        
        _bundle.increaseBalance(bundleId, processId, amount);
    }

    // TODO remove from interface, delete, test, remove
    function decreaseBundleBalance(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
    {
        _bundle.decreaseBalance(bundleId, processId, amount);
    }
}
