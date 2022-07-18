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
            "ERROR:CCR-001:NOT_INSTANCE_OPERATOR_SERVICE");
        _;
    }

    function propose(IComponent component) 
        external
        onlyComponentOwnerService 
    {
        // input validation
        require(_componentIdByAddress[address(component)] == 0, "ERROR:CCR-002:COMPONENT_ALREADY_EXISTS");
        require(_componentIdByName[component.getName()] == 0, "ERROR:CCR-003:COMPONENT_NAME_ALREADY_EXISTS");

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
        component.setId(id);
        _changeState(component, ComponentState.Proposed);

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
        IComponent component = getComponent(id);
        _changeState(component, ComponentState.Active);
        emit LogComponentApproved(id);
        
        // inform component about successful approval
        component.approvalCallback();
    }

    function decline(uint256 id) 
        external
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ComponentState.Declined);
        emit LogComponentDeclined(id);
        
        // inform component about decline
        component.declineCallback();
    }

    function suspend(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ComponentState.Suspended);
        emit LogComponentSuspended(id);
        
        // inform component about suspending
        component.suspendCallback();
    }

    function resume(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ComponentState.Active);
        emit LogComponentResumed(id);
        
        // inform component about resuming
        component.resumeCallback();
    }

    function pause(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ComponentState.Paused);
        emit LogComponentPaused(id);
        
        // inform component about pausing
        component.pauseCallback();
    }

    function unpause(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ComponentState.Active);
        emit LogComponentUnpaused(id);
        
        // inform component about unpausing
        component.unpauseCallback();
    }

    function getComponent(uint256 id) public view returns (IComponent component) {
        component = _componentById[id];
        require(address(component) != address(0), "ERROR:CCR-005:INVALID_COMPONENT_ID");
    }

    function getComponentId(address componentAddress) public view returns (uint256 id) {
        require(componentAddress != address(0), "ERROR:CCR-005:COMPONENT_ADDRESS_ZERO");
        id = _componentIdByAddress[componentAddress];
    }

    function components() public view returns (uint256 count) { return _componentCount; }
    function products() public view returns (uint256 count) { return _products.length; }
    function oracles() public view returns (uint256 count) { return _oracles.length; }
    function riskpools() public view returns (uint256 count) { return _riskpools.length; }

    function _changeState(IComponent component, ComponentState newState) internal {
        ComponentState oldState = component.getState();

        _checkStateTransition(oldState, newState);
        component.setState(newState);

        // log entry for successful component state change
        emit LogComponentStateChanged(component.getId(), oldState, newState);
    }

    function _checkStateTransition(ComponentState oldState, ComponentState newState) internal pure {
        if (oldState == ComponentState.Created) {
            require(newState == ComponentState.Proposed, "ERROR:CMP-012:CREATED_INVALID_TRANSITION");
        } else if (oldState == ComponentState.Proposed) {
            require(newState == ComponentState.Active || newState == ComponentState.Declined, "ERROR:CMP-013:PROPOSED_INVALID_TRANSITION");
        } else if (oldState == ComponentState.Declined) {
            revert("ERROR:CMP-014:DECLINED_IS_FINAL_STATE");
        } else if (oldState == ComponentState.Active) {
            require(newState == ComponentState.Paused || newState == ComponentState.Suspended, "ERROR:CMP-015:ACTIVE_INVALID_TRANSITION");
        } else if (oldState == ComponentState.Paused) {
            require(newState == ComponentState.Active, "ERROR:CMP-016:PAUSED_INVALID_TRANSITION");
        } else if (oldState == ComponentState.Suspended) {
            require(newState == ComponentState.Active, "ERROR:CMP-017:SUSPENDED_INVALID_TRANSITION");
        } else {
            revert("ERROR:CMP-018:INITIAL_STATE_NOT_HANDLED");
        }
    }
}
