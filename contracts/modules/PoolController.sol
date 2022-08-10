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

    mapping(uint256 /* productId */ => uint256 /* riskpoolId */) private _riskpoolIdForProductId;

    mapping(uint256 /* riskpoolId */ => IPool.Pool)  private _riskpools;
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
            "ERROR:POL-002:NOT_TREASURY"
        );
        _;
    }

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
        _policy = PolicyController(_getContractAddress("Policy"));
        _bundle = BundleController(_getContractAddress("Bundle"));
    }


    // // TODO remove with next iteration fo gif-interface
    // event LogRiskpoolRegistered(
    //     uint256 riskpoolId, 
    //     address wallet,
    //     address erc20Token, 
    //     uint256 collateralizationLevel, 
    //     uint256 sumOfSumInsuredCap
    // );
    
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
        require(pool.createdAt == 0, "ERROR:POL-003:RISKPOOL_ALREADY_REGISTERED");

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
        
        _riskpoolIds.push(riskpoolId);
        _riskpoolIdForProductId[productId] = riskpoolId;
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
            "ERROR:POL-020:INVALID_APPLICATION_STATE"
        );

        // determine riskpool responsible for application
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpool(metadata);
        require(
            _component.getComponentState(riskpool.getId()) == IComponent.ComponentState.Active, 
            "ERROR:POL-021:RISKPOOL_NOT_ACTIVE"
        );

        // ask riskpool to secure application
        success = riskpool.collateralizePolicy(processId);
        uint256 riskpoolId = riskpool.getId();
        uint256 sumInsured = application.sumInsuredAmount;

        if (success) {
            emit LogRiskpoolCollateralizationSucceeded(riskpoolId, processId, sumInsured);
        } else {
            emit LogRiskpoolCollateralizationFailed(riskpoolId, processId, sumInsured);
        }
    }


    function release(bytes32 processId) 
        external override
        onlyPolicyFlow("Pool")
    {
        // check that policy is in aciive state
        IPolicy.Policy memory policy = _policy.getPolicy(processId);
        require(
            policy.state == IPolicy.PolicyState.Closed,
            "ERROR:POL-007:INVALID_POLICY_STATE"
        );

        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpool(metadata);
        riskpool.releasePolicy(processId);
    }


    function increaseBalance(bytes32 processId, uint256 amount) 
        external override
        onlyPolicyFlow("Pool")
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpool(metadata);
        riskpool.increaseBalance(processId, amount);
    }


    function decreaseBalance(bytes32 processId, uint256 amount) 
        external override
        onlyPolicyFlow("Pool")
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IRiskpool riskpool = _getRiskpool(metadata);
        riskpool.decreaseBalance(processId, amount);
    }

    function isArchivingAllowed(uint256 id) external view returns (bool) {
        IRiskpool riskpool = _getRiskpoolForId(id);
        uint256 riskpoolId = riskpool.getId();
        require(
            _component.getComponentState(riskpoolId) == IComponent.ComponentState.Paused
            || _component.getComponentState(riskpoolId) == IComponent.ComponentState.Suspended, 
            "ERROR:POL-010:TRANSITION_TO_ARCHIVED_STATE_INVALID"
            );
        require(
            _bundle.unburntBundles(riskpoolId) == 0, 
            "ERROR:POL-011:RISKPOOL_HAS_UNBURNT_BUNDLES"
            );
    }
    
    function riskpools() external view returns(uint256 idx) { return _riskpoolIds.length; }


    function getRiskpool(uint256 riskpoolId) external view returns(IPool.Pool memory riskPool) {
        revert("TO_BE_IMPLEMENTED");
    }


    function getRiskpoolId(uint256 idx) 
        external view 
        returns(uint256) 
    { 
        require(idx < _riskpoolIds.length, "ERROR:POL-020:INDEX_TOO_LARGE");
        return _riskpoolIds[idx]; 
    }

    function getRiskPoolForProduct(uint256 productId) external view returns (uint256 riskpoolId) {
        return _riskpoolIdForProductId[productId];
    }

    function getFullCollateralizationLevel() external view returns (uint256) {
        return FULL_COLLATERALIZATION_LEVEL;
    }

    function _getRiskpool(IPolicy.Metadata memory metadata) internal view returns (IRiskpool riskpool) {
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        require(riskpoolId > 0, "ERROR:POL-021:RISKPOOL_DOES_NOT_EXIST");

        riskpool = _getRiskpoolForId(riskpoolId);
    }

    function _getRiskpoolForId(uint256 riskpoolId) internal view returns (IRiskpool riskpool) {
        IComponent cmp = _component.getComponent(riskpoolId);
        require(cmp.isRiskpool(), "ERROR:POL-022:COMPONENT_NOT_RISKPOOL");
        
        riskpool = IRiskpool(address(cmp));
    }
}
