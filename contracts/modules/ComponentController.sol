// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";
import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IOracle.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/components/IRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IComponentEvents.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

/**
The smart contract provides functionality to manage and control components in a system.
The contract defines several mappings and sets to store information about components, such as their addresses, IDs, states, and types.
It also includes modifiers to restrict access to certain functions based on the caller's role.

Functions:
- `propose()`: Allows the owner service of a component to propose a new component to the system. It verifies that the component and its name do not already exist and emits an event indicating the successful proposal.
- `_persistComponent()`: Persists a new component into the system by assigning it an ID and updating the necessary mappings and sets.
- `exists()`: Checks if a component with the given ID exists in the system.
- `approve()`: Approves a component with the given ID, changing its state to "Active" and emitting an event. If the component is a product, it sets the policy flow in the `_policyFlowByProductId` mapping.
- `decline()`: Changes the state of a component with the given ID to "Declined" and emits an event. It also calls the `declineCallback` function of the component.
- `suspend()`: Suspends a component with the given ID by changing its state to "Suspended" and emitting an event. It also calls the `suspendCallback` function of the component.
- `resume()`: Resumes a component with the given ID by changing its state to "Active" and emitting an event. It also calls the `resumeCallback` function of the component.
- `pause()`: Pauses a component with the given ID by changing its state to "Paused" and emitting an event. It also calls the `pauseCallback` function of the component.
- `unpause()`: Unpauses a component with the given ID by changing its state to "Active" and emitting an event. It also calls the `unpauseCallback` function of the component.
- `archiveFromComponentOwner()`: Archives a component with the given ID by changing its state to "Archived" and emitting an event. It also calls the `archiveCallback` function of the component.
- `archiveFromInstanceOperator()`: Archives a component instance with the given ID by changing its state to "Archived" and emitting an event. It also calls the `archiveCallback` function of the component.
- `getComponent()`: Retrieves the component with the given ID.
- `getComponentId()`: Retrieves the ID of a registered component given its address.
- `getComponentType()`: Retrieves the component type of a given component ID.
- `getComponentState()`: Retrieves the state of the component with the given ID.
- `getOracleId()`: Retrieves the oracle ID at the specified index.
- `getRiskpoolId()`: Retrieves the risk pool ID at the specified index.
- `getProductId()`: Retrieves the product ID at the specified index.
- `getRequiredRole()`: Retrieves the required role for a given component type.
- `components()`: Returns the number of components currently stored in the contract.
- `products()`: Returns the number of products in the `_products` set.
- `oracles()`: Returns the number of oracles registered in the `_oracles` set.
- `riskpools()`: Returns the number of risk pools in the set.

The contract also includes various modifiers (`onlyComponentOwnerService` and `onlyInstanceOperatorService`) to ensure that only authorized callers can access certain functions.

The contract imports several Solidity files from external dependencies and uses the `EnumerableSet` library from the OpenZeppelin library for set operations.
 */

contract ComponentController is
    IComponentEvents,
    CoreController 
 {
    using EnumerableSet for EnumerableSet.UintSet;

    mapping(uint256 => IComponent) private _componentById;
    mapping(bytes32 => uint256) private _componentIdByName;
    mapping(address => uint256) private _componentIdByAddress;

    mapping(uint256 => IComponent.ComponentState) private _componentState;

    EnumerableSet.UintSet private _products;
    EnumerableSet.UintSet private _oracles;
    EnumerableSet.UintSet private _riskpools;
    uint256 private _componentCount;

    mapping(uint256 /* product id */ => address /* policy flow address */) private _policyFlowByProductId;

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
        component.setId(id);

        // update controller book keeping
        _componentById[id] = component;
        _componentIdByName[component.getName()] = id;
        _componentIdByAddress[address(component)] = id;

        // type specific book keeping
        if (component.isProduct()) { EnumerableSet.add(_products, id); }
        else if (component.isOracle()) { EnumerableSet.add(_oracles, id); }
        else if (component.isRiskpool()) { EnumerableSet.add(_riskpools, id); }
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
        IComponent component = getComponent(id);

        if (isProduct(id)) {
            _policyFlowByProductId[id] = IProduct(address(component)).getPolicyFlow();
        }

        emit LogComponentApproved(id);
        
        // inform component about successful approval
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
        if (EnumerableSet.contains(_products, id)) {
            return IComponent.ComponentType.Product;
        } else if (EnumerableSet.contains(_oracles, id)) {
            return IComponent.ComponentType.Oracle;
        } else if (EnumerableSet.contains(_riskpools, id)) {
            return IComponent.ComponentType.Riskpool;
        } else {
            revert("ERROR:CCR-008:INVALID_COMPONENT_ID");
        }
    }

    function getComponentState(uint256 id) public view returns (IComponent.ComponentState componentState) {
        return _componentState[id];
    }

    function getOracleId(uint256 idx) public view returns (uint256 oracleId) {
        return EnumerableSet.at(_oracles, idx);
    }

    function getRiskpoolId(uint256 idx) public view returns (uint256 riskpoolId) {
        return EnumerableSet.at(_riskpools, idx);
    }

    function getProductId(uint256 idx) public view returns (uint256 productId) {
        return EnumerableSet.at(_products, idx);
    }

    function getRequiredRole(IComponent.ComponentType componentType) external view returns (bytes32) {
        if (componentType == IComponent.ComponentType.Product) { return _access.getProductOwnerRole(); }
        else if (componentType == IComponent.ComponentType.Oracle) { return _access.getOracleProviderRole(); }
        else if (componentType == IComponent.ComponentType.Riskpool) { return _access.getRiskpoolKeeperRole(); }
        else { revert("ERROR:CCR-010:COMPONENT_TYPE_UNKNOWN"); }
    }

    function components() public view returns (uint256 count) { return _componentCount; }
    function products() public view returns (uint256 count) { return EnumerableSet.length(_products); }
    function oracles() public view returns (uint256 count) { return EnumerableSet.length(_oracles); }
    function riskpools() public view returns (uint256 count) { return EnumerableSet.length(_riskpools); }

    function isProduct(uint256 id) public view returns (bool) { return EnumerableSet.contains(_products, id); }

    function isOracle(uint256 id) public view returns (bool) { return EnumerableSet.contains(_oracles, id); }

    function isRiskpool(uint256 id) public view returns (bool) { return EnumerableSet.contains(_riskpools, id); }

    function getPolicyFlow(uint256 productId) public view returns (address _policyFlow) {
        require(isProduct(productId), "ERROR:CCR-011:UNKNOWN_PRODUCT_ID");
        _policyFlow = _policyFlowByProductId[productId];
    }

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
        require(newState != oldState, 
            "ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL");
        
        if (oldState == IComponent.ComponentState.Created) {
            require(newState == IComponent.ComponentState.Proposed, 
                "ERROR:CCR-021:CREATED_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Proposed) {
            require(newState == IComponent.ComponentState.Active 
                || newState == IComponent.ComponentState.Declined, 
                "ERROR:CCR-22:PROPOSED_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Declined) {
            revert("ERROR:CCR-023:DECLINED_IS_FINAL_STATE");
        } else if (oldState == IComponent.ComponentState.Active) {
            require(newState == IComponent.ComponentState.Paused 
                || newState == IComponent.ComponentState.Suspended, 
                "ERROR:CCR-024:ACTIVE_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Paused) {
            require(newState == IComponent.ComponentState.Active
                || newState == IComponent.ComponentState.Archived, 
                "ERROR:CCR-025:PAUSED_INVALID_TRANSITION");
        } else if (oldState == IComponent.ComponentState.Suspended) {
            require(newState == IComponent.ComponentState.Active
                || newState == IComponent.ComponentState.Archived, 
                "ERROR:CCR-026:SUSPENDED_INVALID_TRANSITION");
        } else {
            revert("ERROR:CCR-027:INITIAL_STATE_NOT_HANDLED");
        }
    }
}
