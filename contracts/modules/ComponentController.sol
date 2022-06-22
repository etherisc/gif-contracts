// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/modules/IComponentEvents.sol";

contract ComponentController is
    IComponentEvents,
    CoreController 
 {
    uint16 public constant CREATED_STATE = 0;
    uint16 public constant PROPOSED_STATE = 1;
    uint16 public constant DECLINED_STATE = 2;
    uint16 public constant ACTIVE_STATE = 3;
    uint16 public constant PAUSED_STATE = 4;
    uint16 public constant SUSPENDED_STATE = 5;

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

    function propose(IComponent component) external onlyComponentOwnerService {
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
        _changeState(component, PROPOSED_STATE);

        // update controller book keeping
        _componentById[id] = component;
        _componentIdByName[component.getName()] = id;
        _componentIdByAddress[address(component)] = id;

        // type specific book keeping
        if (component.isProduct()) { _products.push(id); }
        else if (component.isOracle()) { _oracles.push(id); }
        else if (component.isRiskpool()) { _riskpools.push(id); }
    }

    function approve(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ACTIVE_STATE);
        emit LogComponentApproved(id);
        
        // inform component about successful approval
        component.approvalCallback();
    }

    function decline(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, DECLINED_STATE);
        emit LogComponentDeclined(id);
        
        // inform component about decline
        component.declineCallback();
    }

    function suspend(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, SUSPENDED_STATE);
        emit LogComponentSuspended(id);
        
        // TODO add func to IComponent inform component about suspending
        // component.suspendCallback();
    }

    function resume(uint256 id) 
        external 
        onlyInstanceOperatorService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ACTIVE_STATE);
        emit LogComponentResumed(id);
        
        // TODO add func to IComponent inform component about resuming
        // component.resumeCallback();
    }

    function pause(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        IComponent component = getComponent(id);
        _changeState(component, PAUSED_STATE);
        emit LogComponentPaused(id);
    }

    function unpause(uint256 id) 
        external 
        onlyComponentOwnerService 
    {
        IComponent component = getComponent(id);
        _changeState(component, ACTIVE_STATE);
        emit LogComponentUnpaused(id);
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

    function _changeState(IComponent component, uint16 newState) internal {
        uint16 oldState = component.getState();

        _checkStateTransition(oldState, newState);
        component.setState(newState);

        // log entry for successful component state change
        emit LogComponentStateChanged(component.getId(), oldState, newState);
    }

    function _checkStateTransition(uint16 oldState, uint16 newState) internal pure {
        require(oldState <= 5, "ERROR:CMP-010:INVALID_INITIAL_STATE");
        require(newState <= 5, "ERROR:CMP-011:INVALID_TARGET_STATE");

        if (oldState == CREATED_STATE) {
            require(newState == PROPOSED_STATE, "ERROR:CMP-012:CREATED_INVALID_TRANSITION");
        } else if (oldState == PROPOSED_STATE) {
            require(newState == ACTIVE_STATE || newState == DECLINED_STATE, "ERROR:CMP-013:PROPOSED_INVALID_TRANSITION");
        } else if (oldState == DECLINED_STATE) {
            revert("ERROR:CMP-014:DECLINED_IS_FINAL_STATE");
        } else if (oldState == ACTIVE_STATE) {
            require(newState == PAUSED_STATE || newState == SUSPENDED_STATE, "ERROR:CMP-015:ACTIVE_INVALID_TRANSITION");
        } else if (oldState == PAUSED_STATE) {
            require(newState == ACTIVE_STATE, "ERROR:CMP-016:PAUSED_INVALID_TRANSITION");
        } else if (oldState == SUSPENDED_STATE) {
            require(newState == ACTIVE_STATE, "ERROR:CMP-017:SUSPENDED_INVALID_TRANSITION");
        } else {
            revert("ERROR:CMP-018:INITIAL_STATE_NOT_HANDLED");
        }
    }
}
