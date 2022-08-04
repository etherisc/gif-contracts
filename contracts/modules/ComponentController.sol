// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/modules/IComponentEvents.sol";

contract ComponentController is
    IComponentEvents,
    CoreController 
 {
    mapping(uint256 => IComponent) private _componentById;
    mapping(bytes32 => uint256) private _componentIdByName;
    mapping(address => uint256) private _componentIdByAddress;

    mapping(uint256 => IComponent.ComponentType) private _componentType;
    mapping(uint256 => IComponent.ComponentState) private _componentState;

    uint256 [] private _products;
    uint256 [] private _oracles;
    uint256 [] private _riskpools;
    uint256 private _componentCount;

    modifier onlyComponentOwnerService() {
        require(
             _msgSender() == _getContractAddress("ComponentOwnerService"),
            "ERROR:CCR-001:NOT_COMPONENT_OWNER_SERVICE");
        _;
    }

    modifier onlyInstanceOperatorService() {
        require(
             _msgSender() == _getContractAddress("InstanceOperatorService"),
            "ERROR:CCR-002:NOT_INSTANCE_OPERATOR_SERVICE");
        _;
    }

    function propose(IComponent component) 
        external
        onlyComponentOwnerService 
    {
        // input validation
        require(_componentIdByAddress[address(component)] == 0, "ERROR:CCR-003:COMPONENT_ALREADY_EXISTS");
        require(_componentIdByName[component.getName()] == 0, "ERROR:CCR-004:COMPONENT_NAME_ALREADY_EXISTS");

        // assigning id and persisting component
        uint256 id = _persistComponent(component);

        // log entry for successful proposal
        emit LogComponentProposed(
            component.getName(),
            component.getType(),
            address(component),
            id);
        
        // inform component about successful proposal
        component.proposalCallback();
    }

    function _persistComponent(IComponent component) 
        internal
        returns(uint256 id)
    {
        // fetch next component id
        _componentCount++;
        id = _componentCount;

        // update component state
        _changeState(id, IComponent.ComponentState.Proposed);
        _componentType[id] = component.getType();
        component.setId(id);

        // update controller book keeping
        _componentById[id] = component;
        _componentIdByName[component.getName()] = id;
        _componentIdByAddress[address(component)] = id;

        // type specific book keeping
        if (component.isProduct()) { _products.push(id); }
        else if (component.isOracle()) { _oracles.push(id); }
        else if (component.isRiskpool()) { _riskpools.push(id); }
    }

    function exists(uint256 id) public view returns(bool) {
        IComponent component = _componentById[id];
        return (address(component) != address(0));
    }

    function approve(uint256 id) 
        external
        onlyInstanceOperatorService 
    {
        _changeState(id, IComponent.ComponentState.Active);
        emit LogComponentApproved(id);
        
        // inform component about successful approval
        IComponent component = getComponent(id);
        component.approvalCallback();
    }

    function decline(uint256 id) 
        external
        onlyInstanceOperatorService 
    {
        _changeState(id, IComponent.ComponentState.Declined);
        emit LogComponentDeclined(id);
        
        // inform component about decline
        IComponent component = getComponent(id);
        component.declineCallback();
    }

    function suspend(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        _changeState(id, IComponent.ComponentState.Suspended);
        emit LogComponentSuspended(id);
        
        // inform component about suspending
        IComponent component = getComponent(id);
        component.suspendCallback();
    }

    function resume(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        _changeState(id, IComponent.ComponentState.Active);
        emit LogComponentResumed(id);
        
        // inform component about resuming
        IComponent component = getComponent(id);
        component.resumeCallback();
    }

    function pause(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        _changeState(id, IComponent.ComponentState.Paused);
        emit LogComponentPaused(id);
        
        // inform component about pausing
        IComponent component = getComponent(id);
        component.pauseCallback();
    }

    function unpause(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        _changeState(id, IComponent.ComponentState.Active);
        emit LogComponentUnpaused(id);
        
        // inform component about unpausing
        IComponent component = getComponent(id);
        component.unpauseCallback();
    }

    function archiveFromComponentOwner(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        _changeState(id, IComponent.ComponentState.Archived);
        emit LogComponentArchived(id);
        
        // inform component about archiving
        IComponent component = getComponent(id);
        component.archiveCallback();
    }

    function archiveFromInstanceOperator(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        _changeState(id, IComponent.ComponentState.Archived);
        emit LogComponentArchived(id);
        
        // inform component about archiving
        IComponent component = getComponent(id);
        component.archiveCallback();
    }

    function getComponent(uint256 id) public view returns (IComponent component) {
        component = _componentById[id];
        require(address(component) != address(0), "ERROR:CCR-005:INVALID_COMPONENT_ID");
    }

    function getComponentId(address componentAddress) public view returns (uint256 id) {
        require(componentAddress != address(0), "ERROR:CCR-006:COMPONENT_ADDRESS_ZERO");
        id = _componentIdByAddress[componentAddress];

        require(id > 0, "ERROR:CCR-007:COMPONENT_UNKNOWN");
    }

    function getComponentType(uint256 id) public view returns (IComponent.ComponentType componentType) {
        return _componentType[id];
    }

    function getComponentState(uint256 id) public view returns (IComponent.ComponentState componentState) {
        return _componentState[id];
    }

    function components() public view returns (uint256 count) { return _componentCount; }
    function products() public view returns (uint256 count) { return _products.length; }
    function oracles() public view returns (uint256 count) { return _oracles.length; }
    function riskpools() public view returns (uint256 count) { return _riskpools.length; }

    function _changeState(uint256 componentId, IComponent.ComponentState newState) internal {
        IComponent.ComponentState oldState = _componentState[componentId];

        _checkStateTransition(oldState, newState);
        _componentState[componentId] = newState;

        // log entry for successful component state change
        emit LogComponentStateChanged(componentId, oldState, newState);
    }

    function _checkStateTransition(
        IComponent.ComponentState oldState, 
        IComponent.ComponentState newState
    ) 
        internal 
        pure 
    {
        if (oldState == IComponent.ComponentState.Created) {
            require(newState == IComponent.ComponentState.Proposed, "ERROR:CMP-012:CREATED_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Proposed) {
            require(newState == IComponent.ComponentState.Active 
                || newState == IComponent.ComponentState.Declined, "ERROR:CMP-013:PROPOSED_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Declined) {
            revert("ERROR:CMP-014:DECLINED_IS_FINAL_STATE");
        } else if (oldState == IComponent.ComponentState.Active) {
            require(newState == IComponent.ComponentState.Paused 
                || newState == IComponent.ComponentState.Suspended, "ERROR:CMP-015:ACTIVE_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Paused) {
            require(newState == IComponent.ComponentState.Active, "ERROR:CMP-016:PAUSED_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Suspended) {
            require(newState == IComponent.ComponentState.Active, "ERROR:CMP-017:SUSPENDED_INVALID_TRANSITION");
        } else {
            revert("ERROR:CMP-018:INITIAL_STATE_NOT_HANDLED");
        }
    }
}
