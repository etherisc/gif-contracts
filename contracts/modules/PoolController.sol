// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "./ComponentController.sol";
import "./PolicyController.sol";
import "./BundleController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IPool.sol";
import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IRiskpool.sol";


import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

/**
The smart contract manages riskpools, their registration, funding, defunding, collateralization, and other related operations.

- The contract implements the IPool interface and extends the CoreController contract.
- It imports other contracts such as ComponentController, PolicyController, BundleController, and CoreController.
- It uses the EnumerableSet library from OpenZeppelin for managing sets of bundle IDs.
- The contract defines constants for full collateralization level, collateralization level cap, and default maximum number of active bundles.
- It maintains mappings to store riskpool information, riskpool IDs for products, maximum number of active bundles for riskpools, and active bundle IDs for riskpools.
- The contract has a private array to store riskpool IDs.
- It has references to other contracts: ComponentController, PolicyController, and BundleController.
- The contract defines modifiers for access control to specific functions.

Functions:
- `_afterInitialize()`: Called after contract initialization to set addresses of other contracts.
- `registerRiskpool()`: Allows the registration of a new riskpool with the specified parameters. It emits an event upon successful registration.
- `setRiskpoolForProduct()`: Sets the riskpool ID for a given product ID.
- `fund()`: Adds funds to a specific riskpool.
- `defund()`: Allows the Riskpool service to defund a riskpool by a specified amount.
- `underwrite()`: Collateralizes a policy application by calculating the required collateral amount and asking the responsible riskpool to secure the application. It emits events related to collateralization process success or failure.
- `calculateCollateral()`: Calculates the required collateral amount for a given riskpool and sum insured amount.
- `processPremium()`: Processes the premium payment for a policy by calling the corresponding function in the riskpool contract.
- `processPayout()`: Processes a payout for a policy in the Pool. It verifies the availability of sufficient capital, locked capital, and balance in the riskpool before processing the payout.
- `release()`: Releases a policy's collateral from the riskpool.

Overall, the PoolController contract provides functionality to manage riskpools, register riskpools, collateralize policies, process premium payments, process payouts, and release collaterals. It acts as an intermediary between the PolicyController, ComponentController, and BundleController contracts to coordinate these operations.
 */

contract PoolController is
    IPool,
    CoreController
{

    using EnumerableSet for EnumerableSet.UintSet;

    // used for representation of collateralization
    // collateralization between 0 and 1 (1=100%) 
    // value might be larger when overcollateralization
    uint256 public constant FULL_COLLATERALIZATION_LEVEL = 10**18;

    // upper limit for overcollateralization at 200% 
    uint256 public constant COLLATERALIZATION_LEVEL_CAP = 2 * FULL_COLLATERALIZATION_LEVEL;

    uint256 public constant DEFAULT_MAX_NUMBER_OF_ACTIVE_BUNDLES = 1;

    mapping(bytes32 /* processId */ => uint256 /* collateralAmount*/ ) private _collateralAmount;

    mapping(uint256 /* productId */ => uint256 /* riskpoolId */) private _riskpoolIdForProductId;

    mapping(uint256 /* riskpoolId */ => IPool.Pool)  private _riskpools;

    mapping(uint256 /* riskpoolId */ => uint256 /* maxmimumNumberOfActiveBundles */) private _maxmimumNumberOfActiveBundlesForRiskpoolId;

    mapping(uint256 /* riskpoolId */ => EnumerableSet.UintSet /* active bundle id set */) private _activeBundleIdsForRiskpoolId;
    
    uint256 [] private _riskpoolIds;

    ComponentController private _component;
    PolicyController private _policy;
    BundleController private _bundle;

    modifier onlyInstanceOperatorService() {
        require(
            _msgSender() == _getContractAddress("InstanceOperatorService"),
            "ERROR:POL-001:NOT_INSTANCE_OPERATOR"
        );
        _;
    }

    modifier onlyRiskpoolService() {
        require(
            _msgSender() == _getContractAddress("RiskpoolService"),
            "ERROR:POL-002:NOT_RISKPOOL_SERVICE"
        );
        _;
    }

    modifier onlyActivePool(uint256 riskpoolId) {
        require(
            _component.getComponentState(riskpoolId) == IComponent.ComponentState.Active, 
            "ERROR:POL-003:RISKPOOL_NOT_ACTIVE"
        );
        _;
    }

    modifier onlyActivePoolForProcess(bytes32 processId) {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        require(
            _component.getComponentState(riskpoolId) == IComponent.ComponentState.Active, 
            "ERROR:POL-004:RISKPOOL_NOT_ACTIVE"
        );
        _;
    }

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
        _policy = PolicyController(_getContractAddress("Policy"));
        _bundle = BundleController(_getContractAddress("Bundle"));
    }


    function registerRiskpool(
        uint256 riskpoolId, 
        address wallet,
        address erc20Token,
        uint256 collateralizationLevel, 
        uint256 sumOfSumInsuredCap
    )
        external override
        onlyRiskpoolService
    {
        IPool.Pool storage pool = _riskpools[riskpoolId];
        _riskpoolIds.push(riskpoolId);
        _maxmimumNumberOfActiveBundlesForRiskpoolId[riskpoolId] = DEFAULT_MAX_NUMBER_OF_ACTIVE_BUNDLES;
        
        require(pool.createdAt == 0, "ERROR:POL-005:RISKPOOL_ALREADY_REGISTERED");

        require(wallet != address(0), "ERROR:POL-006:WALLET_ADDRESS_ZERO");
        require(erc20Token != address(0), "ERROR:POL-007:ERC20_ADDRESS_ZERO");
        require(collateralizationLevel <= COLLATERALIZATION_LEVEL_CAP, "ERROR:POL-008:COLLATERALIZATION_lEVEl_TOO_HIGH");
        require(sumOfSumInsuredCap > 0, "ERROR:POL-009:SUM_OF_SUM_INSURED_CAP_ZERO");

        pool.id = riskpoolId; 
        pool.wallet = wallet; 
        pool.erc20Token = erc20Token; 
        pool.collateralizationLevel = collateralizationLevel;
        pool.sumOfSumInsuredCap = sumOfSumInsuredCap;

        pool.sumOfSumInsuredAtRisk = 0;
        pool.capital = 0;
        pool.lockedCapital = 0;
        pool.balance = 0;

        pool.createdAt = block.timestamp;
        pool.updatedAt = block.timestamp;

        emit LogRiskpoolRegistered(riskpoolId, wallet, erc20Token, collateralizationLevel, sumOfSumInsuredCap);
    }

    function setRiskpoolForProduct(uint256 productId, uint256 riskpoolId) 
        external override
        onlyInstanceOperatorService
    {
        require(_component.isProduct(productId), "ERROR:POL-010:NOT_PRODUCT");
        require(_component.isRiskpool(riskpoolId), "ERROR:POL-011:NOT_RISKPOOL");
        require(_riskpoolIdForProductId[productId] == 0, "ERROR:POL-012:RISKPOOL_ALREADY_SET");
        
        _riskpoolIdForProductId[productId] = riskpoolId;
    }

    function fund(uint256 riskpoolId, uint256 amount) 
        external
        onlyRiskpoolService
        onlyActivePool(riskpoolId)
    {
        IPool.Pool storage pool = _riskpools[riskpoolId];
        pool.capital += amount;
        pool.balance += amount;
        pool.updatedAt = block.timestamp;
    }

    function defund(uint256 riskpoolId, uint256 amount) 
        external
        onlyRiskpoolService
        onlyActivePool(riskpoolId)
    {
        IPool.Pool storage pool = _riskpools[riskpoolId];

        if (pool.capital >= amount) { pool.capital -= amount; }
        else                        { pool.capital = 0; }

        pool.balance -= amount;
        pool.updatedAt = block.timestamp;
    }

    function underwrite(bytes32 processId) 
        external override 
        onlyPolicyFlow("Pool")
        onlyActivePoolForProcess(processId)
        returns(bool success)
    {
        // check that application is in applied state
        IPolicy.Application memory application = _policy.getApplication(processId);
        require(
            application.state == IPolicy.ApplicationState.Applied,
            "ERROR:POL-020:APPLICATION_STATE_INVALID"
        );

        // determine riskpool responsible for application
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];

        // calculate required collateral amount
        uint256 sumInsuredAmount = application.sumInsuredAmount;
        uint256 collateralAmount = calculateCollateral(riskpoolId, sumInsuredAmount);
        _collateralAmount[processId] = collateralAmount;

        emit LogRiskpoolRequiredCollateral(processId, sumInsuredAmount, collateralAmount);

        // check that riskpool stays inside sum insured cap when underwriting this application 
        IPool.Pool storage pool = _riskpools[riskpoolId];
        require(
            pool.sumOfSumInsuredCap >= pool.sumOfSumInsuredAtRisk + sumInsuredAmount,
            "ERROR:POL-022:RISKPOOL_SUM_INSURED_CAP_EXCEEDED"
        );

        // ask riskpool to secure application
        IRiskpool riskpool = _getRiskpoolComponent(metadata);
        success = riskpool.collateralizePolicy(processId, collateralAmount);

        if (success) {
            pool.sumOfSumInsuredAtRisk += sumInsuredAmount;
            pool.lockedCapital += collateralAmount;
            pool.updatedAt = block.timestamp;

            emit LogRiskpoolCollateralizationSucceeded(riskpoolId, processId, sumInsuredAmount);
        } else {
            emit LogRiskpoolCollateralizationFailed(riskpoolId, processId, sumInsuredAmount);
        }
    }


    function calculateCollateral(uint256 riskpoolId, uint256 sumInsuredAmount) 
        public
        view 
        returns (uint256 collateralAmount) 
    {
        uint256 collateralization = getRiskpool(riskpoolId).collateralizationLevel;

        // fully collateralized case
        if (collateralization == FULL_COLLATERALIZATION_LEVEL) {
            collateralAmount = sumInsuredAmount;
        // over or under collateralized case
        } else if (collateralization > 0) {
            collateralAmount = (collateralization * sumInsuredAmount) / FULL_COLLATERALIZATION_LEVEL;
        }
        // collateralization == 0, eg complete risk coverd by re insurance outside gif
        else {
            collateralAmount = 0;
        }
    }


    function processPremium(bytes32 processId, uint256 amount) 
        external override
        onlyPolicyFlow("Pool")
        onlyActivePoolForProcess(processId)
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpoolComponent(metadata);
        riskpool.processPolicyPremium(processId, amount);

        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        IPool.Pool storage pool = _riskpools[riskpoolId];
        pool.balance += amount;
        pool.updatedAt = block.timestamp;
    }


    function processPayout(bytes32 processId, uint256 amount) 
        external override
        onlyPolicyFlow("Pool")
        onlyActivePoolForProcess(processId)
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        IPool.Pool storage pool = _riskpools[riskpoolId];
        require(pool.createdAt > 0, "ERROR:POL-026:RISKPOOL_ID_INVALID");
        require(pool.capital >= amount, "ERROR:POL-027:CAPITAL_TOO_LOW");
        require(pool.lockedCapital >= amount, "ERROR:POL-028:LOCKED_CAPITAL_TOO_LOW");
        require(pool.balance >= amount, "ERROR:POL-029:BALANCE_TOO_LOW");

        pool.capital -= amount;
        pool.lockedCapital -= amount;
        pool.balance -= amount;
        pool.updatedAt = block.timestamp; // solhint-disable-line

        IRiskpool riskpool = _getRiskpoolComponent(metadata);
        riskpool.processPolicyPayout(processId, amount);
    }


    function release(bytes32 processId) 
        external override
        onlyPolicyFlow("Pool")
    {
        IPolicy.Policy memory policy = _policy.getPolicy(processId);
        require(
            policy.state == IPolicy.PolicyState.Closed,
            "ERROR:POL-025:POLICY_STATE_INVALID"
        );

        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpoolComponent(metadata);
        riskpool.releasePolicy(processId);

        IPolicy.Application memory application = _policy.getApplication(processId);

        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        IPool.Pool storage pool = _riskpools[riskpoolId];
        uint256 remainingCollateralAmount = _collateralAmount[processId] - policy.payoutAmount;

        pool.sumOfSumInsuredAtRisk -= application.sumInsuredAmount;
        pool.lockedCapital -= remainingCollateralAmount;
        pool.updatedAt = block.timestamp; // solhint-disable-line

        // free memory
        delete _collateralAmount[processId];
        emit LogRiskpoolCollateralReleased(riskpoolId, processId, remainingCollateralAmount);
    }

    function setMaximumNumberOfActiveBundles(uint256 riskpoolId, uint256 maxNumberOfActiveBundles)
        external 
        onlyRiskpoolService
    {
        require(maxNumberOfActiveBundles > 0, "ERROR:POL-032:MAX_NUMBER_OF_ACTIVE_BUNDLES_INVALID");
        _maxmimumNumberOfActiveBundlesForRiskpoolId[riskpoolId] = maxNumberOfActiveBundles;
    }

    function getMaximumNumberOfActiveBundles(uint256 riskpoolId) public view returns(uint256 maximumNumberOfActiveBundles) {
        return _maxmimumNumberOfActiveBundlesForRiskpoolId[riskpoolId];
    }
    
    function riskpools() external view returns(uint256 idx) { return _riskpoolIds.length; }


    function getRiskpool(uint256 riskpoolId) public view returns(IPool.Pool memory riskPool) {
        riskPool = _riskpools[riskpoolId];
        require(riskPool.createdAt > 0, "ERROR:POL-040:RISKPOOL_NOT_REGISTERED");
    }

    function getRiskPoolForProduct(uint256 productId) external view returns (uint256 riskpoolId) {
        return _riskpoolIdForProductId[productId];
    }

    function activeBundles(uint256 riskpoolId) external view returns(uint256 numberOfActiveBundles) {
        return EnumerableSet.length(_activeBundleIdsForRiskpoolId[riskpoolId]);
    }

    function getActiveBundleId(uint256 riskpoolId, uint256 bundleIdx) external view returns(uint256 bundleId) {
        require(
            bundleIdx < EnumerableSet.length(_activeBundleIdsForRiskpoolId[riskpoolId]),
            "ERROR:POL-041:BUNDLE_IDX_TOO_LARGE"
        );

        return EnumerableSet.at(_activeBundleIdsForRiskpoolId[riskpoolId], bundleIdx);
    }

    function addBundleIdToActiveSet(uint256 riskpoolId, uint256 bundleId) 
        external
        onlyRiskpoolService
    {
        require(
            !EnumerableSet.contains(_activeBundleIdsForRiskpoolId[riskpoolId], bundleId), 
            "ERROR:POL-042:BUNDLE_ID_ALREADY_IN_SET"
        );
        require(
            EnumerableSet.length(_activeBundleIdsForRiskpoolId[riskpoolId]) < _maxmimumNumberOfActiveBundlesForRiskpoolId[riskpoolId], 
            "ERROR:POL-043:MAXIMUM_NUMBER_OF_ACTIVE_BUNDLES_REACHED"
        );

        EnumerableSet.add(_activeBundleIdsForRiskpoolId[riskpoolId], bundleId);
    }

    function removeBundleIdFromActiveSet(uint256 riskpoolId, uint256 bundleId) 
        external
        onlyRiskpoolService
    {
        require(
            EnumerableSet.contains(_activeBundleIdsForRiskpoolId[riskpoolId], bundleId), 
            "ERROR:POL-044:BUNDLE_ID_NOT_IN_SET"
        );

        EnumerableSet.remove(_activeBundleIdsForRiskpoolId[riskpoolId], bundleId);
    }

    function getFullCollateralizationLevel() external pure returns (uint256) {
        return FULL_COLLATERALIZATION_LEVEL;
    }

    function _getRiskpoolComponent(IPolicy.Metadata memory metadata) internal view returns (IRiskpool riskpool) {
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        require(riskpoolId > 0, "ERROR:POL-045:RISKPOOL_DOES_NOT_EXIST");

        riskpool = _getRiskpoolForId(riskpoolId);
    }

    function _getRiskpoolForId(uint256 riskpoolId) internal view returns (IRiskpool riskpool) {
        require(_component.isRiskpool(riskpoolId), "ERROR:POL-046:COMPONENT_NOT_RISKPOOL");
        
        IComponent cmp = _component.getComponent(riskpoolId);
        riskpool = IRiskpool(address(cmp));
    }
}
