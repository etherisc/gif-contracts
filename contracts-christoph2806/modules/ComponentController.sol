// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";
import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IOracle.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/components/IRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IComponentEvents.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

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

    /**
     * @dev Proposes a new component to the system.
     * @param component The component to be proposed.
     *
     * Emits a LogComponentProposed event with the name, type, address and id of the proposed component.
     * Calls the proposalCallback function of the proposed component to inform it about the successful proposal.
     *
     * Requirements:
     * - The caller must be the owner service of the component.
     * - The component must not already exist in the system.
     * - The component name must not already exist in the system.
     * @notice This function emits 1 events: 
     * - LogComponentProposed
     */
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

    /**
     * @dev Persists a new component into the system.
     * @param component The component to be persisted.
     * @return id The id of the newly persisted component.
     *
     * - Fetches the next component id.
     * - Updates component state to Proposed.
     * - Sets the id of the component.
     * - Updates controller book keeping with the new component id.
     * - Updates type specific book keeping.
     */
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

    /**
     * @dev Checks if a component with the given ID exists.
     * @param id The ID of the component to check.
     * @return True if a component with the given ID exists, false otherwise.
     */
    function exists(uint256 id) public view returns(bool) {
        IComponent component = _componentById[id];
        return (address(component) != address(0));
    }

    /**
     * @dev Approves a component with the given id.
     * @param id The id of the component to be approved.
     *
     * Emits a LogComponentApproved event and informs the component about the successful approval by calling the approvalCallback function.
     * If the component is a product, sets the policy flow in the _policyFlowByProductId mapping.
     * @notice This function emits 1 events: 
     * - LogComponentApproved
     */
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

    /**
     * @dev Changes the state of a component with the given ID to "Declined" and emits a LogComponentDeclined event.
     *      Calls the declineCallback function of the component with the given ID.
     *
     * @param id The ID of the component to decline.
     * @notice This function emits 1 events: 
     * - LogComponentDeclined
     */
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

    /**
     * @dev Suspends a component with the given ID.
     *
     * @param id The ID of the component to suspend.
     *
     * @notice This function emits 1 events: 
     * - LogComponentSuspended
     */
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

    /**
     * @dev Resumes a component by changing its state to Active and emitting an event.
     *      It also calls the resumeCallback() function of the component to inform it about the resuming.
     *
     * @param id The ID of the component to be resumed.
     * @notice This function emits 1 events: 
     * - LogComponentResumed
     */
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

    /**
     * @dev Pauses the component with the given ID.
     * @param id The ID of the component to be paused.
     * @notice This function emits 1 events: 
     * - LogComponentPaused
     */
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

    /**
     * @dev Unpauses a component with the given id.
     *
     * @param id The id of the component to unpause.
     *
     * @notice This function emits 1 events: 
     * - LogComponentUnpaused
     */
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

    /**
     * @dev Archives a component with the given ID, changing its state to "Archived" and emitting a LogComponentArchived event.
     *      Also calls the archiveCallback function of the component with the given ID, informing it about the archiving.
     *
     * @param id The ID of the component to be archived.
     * @notice This function emits 1 events: 
     * - LogComponentArchived
     */
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

    /**
     * @dev Archives a component instance with the given ID.
     * @param id The ID of the component instance to be archived.
     *
     * @notice This function emits 1 events: 
     * - LogComponentArchived
     */
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

    /**
     * @dev Returns the component with the given ID.
     * @param id The ID of the component to retrieve.
     * @return component The component with the given ID.
     */
    function getComponent(uint256 id) public view returns (IComponent component) {
        component = _componentById[id];
        require(address(component) != address(0), "ERROR:CCR-005:INVALID_COMPONENT_ID");
    }

    /**
     * @dev Returns the ID of a registered component given its address.
     * @param componentAddress The address of the component.
     * @return id The ID of the component.
     */
    function getComponentId(address componentAddress) public view returns (uint256 id) {
        require(componentAddress != address(0), "ERROR:CCR-006:COMPONENT_ADDRESS_ZERO");
        id = _componentIdByAddress[componentAddress];

        require(id > 0, "ERROR:CCR-007:COMPONENT_UNKNOWN");
    }

    /**
     * @dev Returns the component type of a given component ID.
     * @param id The ID of the component.
     * @return componentType The type of the component (Product, Oracle or Riskpool).
     * @notice If the component ID is not found, reverts with an error message.
     */
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

    /**
     * @dev Returns the state of the component with the given ID.
     * @param id The ID of the component.
     * @return componentState The state of the component.
     */
    function getComponentState(uint256 id) public view returns (IComponent.ComponentState componentState) {
        return _componentState[id];
    }

    /**
     * @dev Returns the oracle ID at the given index.
     * @param idx The index of the oracle ID to retrieve.
     * @return oracleId The oracle ID at the given index.
     */
    function getOracleId(uint256 idx) public view returns (uint256 oracleId) {
        return EnumerableSet.at(_oracles, idx);
    }

    /**
     * @dev Returns the riskpool ID at the specified index.
     * @param idx The index of the riskpool ID to retrieve.
     * @return riskpoolId The ID of the riskpool at the specified index.
     */
    function getRiskpoolId(uint256 idx) public view returns (uint256 riskpoolId) {
        return EnumerableSet.at(_riskpools, idx);
    }

    /**
     * @dev Returns the product ID at the given index in the _products set.
     * @param idx The index of the product ID to retrieve.
     * @return productId The product ID at the given index.
     */
    function getProductId(uint256 idx) public view returns (uint256 productId) {
        return EnumerableSet.at(_products, idx);
    }

    /**
     * @dev Returns the required role for a given component type.
     * @param componentType The type of component for which to retrieve the required role.
     * @return The required role as a bytes32 value.
     *
     * Requirements:
     * - The component type must be a valid value from the IComponent.ComponentType enum.
     * - If the component type is not recognized, the function reverts with an error message.
     */
    function getRequiredRole(IComponent.ComponentType componentType) external view returns (bytes32) {
        if (componentType == IComponent.ComponentType.Product) { return _access.getProductOwnerRole(); }
        else if (componentType == IComponent.ComponentType.Oracle) { return _access.getOracleProviderRole(); }
        else if (componentType == IComponent.ComponentType.Riskpool) { return _access.getRiskpoolKeeperRole(); }
        else { revert("ERROR:CCR-010:COMPONENT_TYPE_UNKNOWN"); }
    }

    /**
     * @dev Returns the number of components currently stored in the contract.
     * @return count The number of components stored.
     */
    function components() public view returns (uint256 count) { return _componentCount; }
    /**
     * @dev Returns the number of products in the set '_products'.
     * @return count The number of products in the set '_products'.
     */
    function products() public view returns (uint256 count) { return EnumerableSet.length(_products); }
    /**
     * @dev Returns the number of oracles registered in the _oracles set.
     * @return count The number of oracles registered in the _oracles set.
     */
    function oracles() public view returns (uint256 count) { return EnumerableSet.length(_oracles); }
    /**
     * @dev Returns the number of risk pools in the EnumerableSet.
     * @return count The number of risk pools in the EnumerableSet.
     */
    function riskpools() public view returns (uint256 count) { return EnumerableSet.length(_riskpools); }

    /**
     * @dev Check if a product exists in the set of products.
     * @param id The ID of the product to check.
     * @return Returns true if the product exists in the set, false otherwise.
     */
    function isProduct(uint256 id) public view returns (bool) { return EnumerableSet.contains(_products, id); }

    /**
     * @dev Checks if an oracle with a given ID exists.
     * @param id The ID of the oracle to check.
     * @return A boolean indicating whether the oracle exists or not.
     */
    function isOracle(uint256 id) public view returns (bool) { return EnumerableSet.contains(_oracles, id); }

    /**
     * @dev Checks if a given ID is a riskpool.
     * @param id The ID to check.
     * @return A boolean value indicating if the given ID is a riskpool.
     */
    function isRiskpool(uint256 id) public view returns (bool) { return EnumerableSet.contains(_riskpools, id); }

    /**
     * @dev Returns the address of the policy flow for a given product ID.
     * @param productId The ID of the product to retrieve the policy flow for.
     * @return _policyFlow The address of the policy flow for the given product ID.
     */
    function getPolicyFlow(uint256 productId) public view returns (address _policyFlow) {
        require(isProduct(productId), "ERROR:CCR-011:UNKNOWN_PRODUCT_ID");
        _policyFlow = _policyFlowByProductId[productId];
    }

    /**
     * @dev Changes the state of a component.
     * @param componentId The ID of the component to change the state of.
     * @param newState The new state to set for the component.
     *
     * Emits a LogComponentStateChanged event upon successful state change.
     * @notice This function emits 1 events: 
     * - LogComponentStateChanged
     */
    function _changeState(uint256 componentId, IComponent.ComponentState newState) internal {
        IComponent.ComponentState oldState = _componentState[componentId];

        _checkStateTransition(oldState, newState);
        _componentState[componentId] = newState;

        // log entry for successful component state change
        emit LogComponentStateChanged(componentId, oldState, newState);
    }

    /**
     * @dev Checks if the state transition is valid.
     * @param oldState The current state of the component.
     * @param newState The state to which the component will transition.
     *
     *
     * @dev Throws an error if the newState is the same as the oldState.
     * @dev Throws an error if the transition from Created state is not to Proposed state.
     * @dev Throws an error if the transition from Proposed state is not to Active or Declined state.
     * @dev Throws an error if the transition from Declined state is attempted.
     * @dev Throws an error if the transition from Active state is not to Paused or Suspended state.
     * @dev Throws an error if the transition from Paused state is not to Active or Archived state.
     * @dev Throws an error if the transition from Suspended state is not to Active or Archived state.
     * @dev Throws an error if the initial state is not handled.
     */
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
