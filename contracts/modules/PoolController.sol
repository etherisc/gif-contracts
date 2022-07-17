// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "./PolicyController.sol";
import "../shared/CoreController.sol";

import "@gif-interface/contracts/modules/IPool.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/components/IRiskpool.sol";


contract PoolController is
    IPool,
    CoreController
{
    mapping(uint256 => uint256) private _riskpoolIdForProductId;
    uint256 [] private _riskpools;

    ComponentController private _component;
    PolicyController private _policy;

    modifier onlyInstanceOperatorService() {
        require(
            _msgSender() == _getContractAddress("InstanceOperatorService"),
            "ERROR:POL-001:NOT_INSTANCE_OPERATOR"
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
        
        _riskpools.push(riskpoolId);
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
            riskpool.getState() == ComponentState.Active, 
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

    
    function riskpools() external view returns(uint256 idx) { return _riskpools.length; }

    function getRiskpoolId(uint256 idx) 
        external view 
        returns(uint256) 
    { 
        require(idx < _riskpools.length, "ERROR:POL-008:INDEX_TOO_LARGE");
        return _riskpools[idx]; 
    }

    function getRiskPoolForProduct(uint256 productId) external view returns (uint256 riskpoolId) {
        return _riskpoolIdForProductId[productId];
    }

    function _getRiskpool(IPolicy.Metadata memory metadata) internal view returns (IRiskpool riskpool) {
        uint256 riskpoolId = _riskpoolIdForProductId[metadata.productId];
        require(riskpoolId > 0, "ERROR:POL-009:RISKPOOL_DOES_NOT_EXIST");

        riskpool = _getRiskpoolForId(riskpoolId);
    }

    function _getRiskpoolForId(uint256 riskpoolId) internal view returns (IRiskpool riskpool) {
        IComponent cmp = _component.getComponent(riskpoolId);
        require(cmp.isRiskpool(), "ERROR:POL-010:COMPONENT_NOT_RISKPOOL");
        
        riskpool = IRiskpool(address(cmp));
    }
}
