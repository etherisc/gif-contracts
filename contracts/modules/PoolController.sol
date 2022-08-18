// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "./PolicyController.sol";
import "./BundleController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IPool.sol";
import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IRiskpool.sol";


contract PoolController is
    IPool,
    CoreController
{

    // used for representation of collateralization
    // collateralization between 0 and 1 (1=100%) 
    // value might be larger when overcollateralization
    uint256 public constant FULL_COLLATERALIZATION_LEVEL = 10**18;

    // upper limit for overcollateralization at 200% 
    uint256 public constant COLLATERALIZATION_LEVEL_CAP = 2 * FULL_COLLATERALIZATION_LEVEL;

    mapping(bytes32 /* processId */ => uint256 /* collateralAmount*/ ) private _collateralAmount;

    mapping(uint256 /* productId */ => uint256 /* riskpoolId */) private _riskpoolIdForProductId;

    mapping(uint256 /* riskpoolId */ => IPool.Pool)  private _riskpools;

    mapping(uint256 /* riskpoolId */ => uint256 /* maxmimumNumberOfActiveBundles */) private _maxmimumNumberOfActiveBundlesForRiskpoolId;
    
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

    modifier onlyTreasury() {
        require(
            _msgSender() == _getContractAddress("Treasury"),
            "ERROR:POL-003:NOT_TREASURY"
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
        
        require(pool.createdAt == 0, "ERROR:POL-004:RISKPOOL_ALREADY_REGISTERED");

        require(wallet != address(0), "ERROR:POL-005:WALLET_ADDRESS_ZERO");
        require(erc20Token != address(0), "ERROR:POL-006:ERC20_ADDRESS_ZERO");
        require(collateralizationLevel <= COLLATERALIZATION_LEVEL_CAP, "ERROR:POL-007:COLLATERALIZATION_lEVEl_TOO_HIGH");
        require(sumOfSumInsuredCap > 0, "ERROR:POL-008:SUM_OF_SUM_INSURED_CAP_ZERO");

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
        IComponent product = _component.getComponent(productId);
        IComponent riskpool = _component.getComponent(riskpoolId);

        require(product.isProduct(), "ERROR:POL-010:NOT_PRODUCT");
        require(riskpool.isRiskpool(), "ERROR:POL-011:NOT_RISKPOOL");
        require(_riskpoolIdForProductId[productId] == 0, "ERROR:POL-012:RISKPOOL_ALREADY_SET");
        
        _riskpoolIdForProductId[productId] = riskpoolId;
    }

    function fund(uint256 riskpoolId, uint256 amount) 
        external
        onlyRiskpoolService
    {
        IPool.Pool storage pool = _riskpools[riskpoolId];
        pool.capital += amount;
        pool.balance += amount;
        pool.updatedAt = block.timestamp;
    }

    function defund(uint256 riskpoolId, uint256 amount) 
        external
        onlyRiskpoolService
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
        require(
            _component.getComponentState(riskpoolId) == IComponent.ComponentState.Active, 
            "ERROR:POL-021:RISKPOOL_NOT_ACTIVE"
        );

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

        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        IPolicy.Application memory application = _policy.getApplication(processId);
        IPool.Pool storage pool = _riskpools[riskpoolId];
        uint256 collateralAmount = _collateralAmount[processId];

        pool.sumOfSumInsuredAtRisk -= application.sumInsuredAmount;
        pool.lockedCapital -= collateralAmount;
        pool.updatedAt = block.timestamp;

        // free memory
        delete _collateralAmount[processId];
        emit LogRiskpoolCollateralReleased(riskpoolId, processId, collateralAmount);
    }


    function increaseBalance(bytes32 processId, uint256 amount) 
        external override
        onlyPolicyFlow("Pool")
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpoolComponent(metadata);
        riskpool.increaseBalance(processId, amount);

        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        IPool.Pool storage pool = _riskpools[riskpoolId];
        pool.balance += amount;
        pool.updatedAt = block.timestamp;
    }


    function decreaseBalance(bytes32 processId, uint256 amount) 
        external override
        onlyPolicyFlow("Pool")
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpoolComponent(metadata);
        riskpool.decreaseBalance(processId, amount);

        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        IPool.Pool storage pool = _riskpools[riskpoolId];
        pool.balance -= amount;
        pool.updatedAt = block.timestamp;
    }

    function isArchivingAllowed(uint256 riskpoolId) external view returns (bool) {
        require(
            _component.getComponentState(riskpoolId) == IComponent.ComponentState.Paused
            || _component.getComponentState(riskpoolId) == IComponent.ComponentState.Suspended, 
            "ERROR:POL-030:TRANSITION_TO_ARCHIVED_STATE_INVALID"
            );
        require(
            _bundle.unburntBundles(riskpoolId) == 0, 
            "ERROR:POL-031:RISKPOOL_HAS_UNBURNT_BUNDLES"
            );
    }

    function setMaximumNumberOfActiveBundles(uint256 riskpoolId, uint256 maxNumberOfActiveBundles)
        external 
        onlyRiskpoolService
    {
        require(maxNumberOfActiveBundles >= _bundle.unburntBundles(riskpoolId), "ERROR:POL-015:TOO_MANY_ACTIVE_BUNDLES");
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

    function getFullCollateralizationLevel() external view returns (uint256) {
        return FULL_COLLATERALIZATION_LEVEL;
    }

    function _getRiskpoolComponent(IPolicy.Metadata memory metadata) internal view returns (IRiskpool riskpool) {
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        require(riskpoolId > 0, "ERROR:POL-042:RISKPOOL_DOES_NOT_EXIST");

        riskpool = _getRiskpoolForId(riskpoolId);
    }

    function _getRiskpoolForId(uint256 riskpoolId) internal view returns (IRiskpool riskpool) {
        IComponent cmp = _component.getComponent(riskpoolId);
        require(cmp.isRiskpool(), "ERROR:POL-043:COMPONENT_NOT_RISKPOOL");
        
        riskpool = IRiskpool(address(cmp));
    }
}
