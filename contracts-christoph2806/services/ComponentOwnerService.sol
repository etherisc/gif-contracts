// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../modules/ComponentController.sol";
// TODO ComponentOwnerService should not know of the PoolController - if we have a better idea how to build this, it should be changed.  
import "../modules/PoolController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/services/IComponentOwnerService.sol";

contract ComponentOwnerService is 
    IComponentOwnerService,
    CoreController
{
    ComponentController private _component;

    modifier onlyOwnerWithRoleFromComponent(IComponent component) {
        address owner = component.getOwner();
        bytes32 requiredRole = _component.getRequiredRole(component.getType());
        require(_msgSender() == owner, "ERROR:COS-001:NOT_OWNER");
        require(_access.hasRole(requiredRole, owner), "ERROR:COS-002:REQUIRED_ROLE_MISSING");
        _;
    }

    modifier onlyOwnerWithRole(uint256 id) {
        IComponent component = _component.getComponent(id);
        require(address(component) != address(0), "ERROR:COS-003:COMPONENT_ID_INVALID");

        address owner = component.getOwner();
        bytes32 requiredRole = _component.getRequiredRole(_component.getComponentType(id));

        require(_msgSender() == owner, "ERROR:COS-004:NOT_OWNER");
        require(_access.hasRole(requiredRole, owner), "ERROR:COS-005:REQUIRED_ROLE_MISSING");
        _;
    }

    /**
     * @dev This function is called after the contract is initialized and can only be called once. It sets the component controller contract address.
     */
    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    /**
     * @dev Propose a new component to be added to the system.
     * @param component The component to be proposed.
     */
    function propose(IComponent component) 
        external override
        onlyOwnerWithRoleFromComponent(component) 
    {
        _component.propose(component);
    }

    /**
     * @dev Stake function allows the owner to stake a specific id.
     *
     * @param id The id of the stake.
     *
     */
    function stake(uint256 id) 
        external override 
        onlyOwnerWithRole(id) 
    {
        revert("ERROR:COS-006:IMPLEMENATION_MISSING");
    }

    /**
     * @dev Allows the owner to withdraw a specific asset by its ID.
     * @param id The ID of the asset to be withdrawn.
     */
    function withdraw(uint256 id) 
        external override
        onlyOwnerWithRole(id) 
    {
        revert("ERROR:COS-007:IMPLEMENATION_MISSING");
    }
        

    /**
     * @dev Pauses a specific component with the given ID.
     * @param id The ID of the component to be paused.
     */
    function pause(uint256 id) 
        external override
        onlyOwnerWithRole(id) 
    {
        _component.pause(id);
    }

    /**
     * @dev Unpauses a component with the specified ID.
     * @param id The ID of the component to unpause.
     */
    function unpause(uint256 id) 
        external override 
        onlyOwnerWithRole(id) 
    {
        _component.unpause(id);
    }

    /**
     * @dev Archives a component with the given ID from the component owner's inventory.
     * @param id The ID of the component to be archived.
     */
    function archive(uint256 id) 
        external override 
        onlyOwnerWithRole(id) 
    {
        _component.archiveFromComponentOwner(id);
    }
}