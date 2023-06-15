// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

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
            "ERROR:RPS-003:SENDER_NOT_RISKPOOL"
        );
        require(
            _component.getComponentState(componentId) == IComponent.ComponentState.Active,
            "ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"
        );
        _;
    }

    modifier onlyOwningRiskpool(uint256 bundleId, bool mustBeActive) {
        uint256 componentId = _component.getComponentId(_msgSender());
        bool isRiskpool = _component.getComponentType(componentId) == IComponent.ComponentType.Riskpool;
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            isRiskpool,
            "ERROR:RPS-005:SENDER_NOT_RISKPOOL"
        );
        require(
            componentId == bundle.riskpoolId,
            "ERROR:RPS-006:BUNDLE_RISKPOOL_MISMATCH"
        );
        if (mustBeActive) {
            require(
                _component.getComponentState(componentId) == IComponent.ComponentState.Active,
                "ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"
            );
        }
        _;
    }

    modifier onlyOwningRiskpoolId(uint256 riskpoolId, bool mustBeActive) {
        uint256 componentId = _component.getComponentId(_msgSender());
        bool isRiskpool = _component.getComponentType(componentId) == IComponent.ComponentType.Riskpool;
        require(
            isRiskpool && componentId == riskpoolId,
            "ERROR:RPS-008:SENDER_NOT_OWNING_RISKPOOL"
        );
        if (mustBeActive) {
            require(
                _component.getComponentState(componentId) == IComponent.ComponentState.Active,
                "ERROR:RPS-009:RISKPOOL_NOT_ACTIVE"
            );
        }
        _;
    }


    /**
     * @dev Sets the addresses of the BundleController, ComponentController, PoolController, and TreasuryModule contracts.
     *
     *
     */
    function _afterInitialize() 
        internal override 
        onlyInitializing 
    {
        _bundle = BundleController(_getContractAddress("Bundle"));
        _component = ComponentController(_getContractAddress("Component"));
        _pool = PoolController(_getContractAddress("Pool"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));
    }


    /**
     * @dev Registers a new risk pool with the given parameters.
     * @param wallet The address of the wallet that will hold the collateral for the risk pool.
     * @param erc20Token The address of the ERC20 token that will be used as collateral.
     * @param collateralizationLevel The percentage of collateral required for the risk pool.
     * @param sumOfSumInsuredCap The maximum sum of all insured amounts for the risk pool.
     */
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

    /**
     * @dev Creates a new bundle with the given parameters and adds it to the active set of the riskpool.
     * @param owner The address of the owner of the bundle.
     * @param filter The filter applied to the bundle.
     * @param initialCapital The initial capital of the bundle.
     * @return bundleId The ID of the newly created bundle.
     */
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
        
        _pool.addBundleIdToActiveSet(riskpoolId, bundleId);

        (uint256 fee, uint256 netCapital) = _treasury.processCapital(bundleId, initialCapital);

        _bundle.fund(bundleId, netCapital);
        _pool.fund(riskpoolId, netCapital);
    }


    /**
     * @dev This function allows a user to fund a bundle with a specified amount.
     * @param bundleId The ID of the bundle to be funded.
     * @param amount The amount of tokens to be funded.
     * @return netAmount The net amount of tokens that were funded after deducting fees.
     */
    function fundBundle(uint256 bundleId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
        returns( uint256 netAmount)
    {
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            bundle.state != IBundle.BundleState.Closed
            && bundle.state != IBundle.BundleState.Burned, 
            "ERROR:RPS-010:BUNDLE_CLOSED_OR_BURNED"
        );

        uint256 feeAmount;
        (feeAmount, netAmount) = _treasury.processCapital(bundleId, amount);

        _bundle.fund(bundleId, netAmount);
        _pool.fund(bundle.riskpoolId, netAmount);
    }


    /**
     * @dev Defunds a bundle by withdrawing a specified amount of tokens from it.
     * @param bundleId The ID of the bundle to be defunded.
     * @param amount The amount of tokens to be withdrawn from the bundle.
     * @return netAmount The net amount of tokens withdrawn from the bundle after deducting any fees.
     */
    function defundBundle(uint256 bundleId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
        returns(uint256 netAmount)
    {
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            bundle.state != IBundle.BundleState.Burned, 
            "ERROR:RPS-011:BUNDLE_BURNED"
        );

        uint256 feeAmount;
        (feeAmount, netAmount) = _treasury.processWithdrawal(bundleId, amount);
        require(netAmount == amount, "ERROR:RPS-013:UNEXPECTED_FEE_SUBTRACTION");

        _bundle.defund(bundleId, amount);
        _pool.defund(bundle.riskpoolId, netAmount);
    }


    /**
     * @dev Locks a bundle, preventing it from being traded or redeemed.
     * @param bundleId The ID of the bundle to be locked.
     */
    function lockBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)
    {
            uint256 riskpoolId = _component.getComponentId(_msgSender());
        _pool.removeBundleIdFromActiveSet(riskpoolId, bundleId);
        _bundle.lock(bundleId);
    }


    /**
     * @dev Unlocks a bundle for trading by adding its ID to the active set of a risk pool and unlocking the bundle.
     * @param bundleId The ID of the bundle to be unlocked.
     */
    function unlockBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        _pool.addBundleIdToActiveSet(riskpoolId, bundleId);
        _bundle.unlock(bundleId);
    }


    /**
     * @dev Closes a bundle and removes it from the active set of the owning riskpool.
     * @param bundleId The ID of the bundle to be closed.
     */
    function closeBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        uint256 riskpoolId = _component.getComponentId(_msgSender());

        if (_bundle.getState(bundleId) == IBundle.BundleState.Active) {
            _pool.removeBundleIdFromActiveSet(riskpoolId, bundleId);
        }

        _bundle.close(bundleId);
    }

    /**
     * @dev Burns a closed bundle, withdrawing its remaining balance and defunding it from the riskpool and the pool.
     * @param bundleId The ID of the bundle to burn.
     */
    function burnBundle(uint256 bundleId)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        // ensure bundle is closed
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(bundle.state == IBundle.BundleState.Closed, "ERROR:RPS-020:BUNDLE_NOT_CLOSED");

        // withdraw remaining balance
        (uint256 feeAmount, uint256 netAmount) = _treasury.processWithdrawal(bundleId, bundle.balance);
    
        _bundle.defund(bundleId, netAmount);
        _pool.defund(bundle.riskpoolId, netAmount);

        _bundle.burn(bundleId);
    }
    
    /**
     * @dev Collateralizes a policy by locking a specified amount of collateral for a given bundle and process ID.
     * @param bundleId The ID of the bundle to which the policy belongs.
     * @param processId The ID of the process associated with the policy.
     * @param collateralAmount The amount of collateral to be locked for the policy.
     */
    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 collateralAmount) 
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        _bundle.collateralizePolicy(bundleId, processId, collateralAmount);
    }

    /**
     * @dev Processes a premium payment for a specific bundle.
     * @param bundleId The ID of the bundle for which the premium is being paid.
     * @param processId The ID of the premium payment process.
     * @param amount The amount of the premium payment in wei.
     */
    function processPremium(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)
    {        
        _bundle.processPremium(bundleId, processId, amount);
    }

    /**
     * @dev Processes a payout for a specific bundle.
     * @param bundleId The ID of the bundle for which to process the payout.
     * @param processId The ID of the payout process.
     * @param amount The amount to be paid out.
     */
    function processPayout(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyOwningRiskpool(bundleId, true)  
    {
        _bundle.processPayout(bundleId, processId, amount);
    }

    /**
     * @dev Releases a policy for a given bundle and process ID.
     * @param bundleId The ID of the bundle containing the policy to be released.
     * @param processId The ID of the process associated with the policy to be released.
     * @return collateralAmount The amount of collateral released for the policy.
     */
    function releasePolicy(uint256 bundleId, bytes32 processId)
        external override
        onlyOwningRiskpool(bundleId, false)  
        returns(uint256 collateralAmount)
    {
        collateralAmount = _bundle.releasePolicy(bundleId, processId);
    }

    /**
     * @dev Sets the maximum number of active bundles for a given riskpool.
     * @param riskpoolId The ID of the riskpool.
     * @param maxNumberOfActiveBundles The maximum number of active bundles to be set.
     */
    function setMaximumNumberOfActiveBundles(uint256 riskpoolId, uint256 maxNumberOfActiveBundles)
        external override
        onlyOwningRiskpoolId(riskpoolId, true)
    {
        _pool.setMaximumNumberOfActiveBundles(riskpoolId, maxNumberOfActiveBundles);
    }   
}
