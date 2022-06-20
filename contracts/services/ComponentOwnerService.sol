// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ComponentController.sol";
import "../shared/CoreController.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/services/IComponentOwnerService.sol";

contract ComponentOwnerService is 
    IComponentOwnerService,
    CoreController
{
    ComponentController private _componentController;

    modifier onlyOwnerWithRoleFromComponent(IComponent component) {
        address owner = component.getOwner();
        bytes32 requiredRole = component.getRequiredRole();
        require(_access.hasRole(requiredRole, owner), "ERROR:COS-002:REQUIRED_ROLE_MISSING");
        require(_msgSender() == owner, "ERROR:COS-001:NOT_OWNER");
        _;
    }

    modifier onlyOwnerWithRole(uint256 id) {
        IComponent component = _componentController.getComponent(id);
        require(address(component) != address(0), "ERROR:COS-003:COMPONENT_ID_INVALID");

        address owner = component.getOwner();
        bytes32 requiredRole = component.getRequiredRole();

        require(_msgSender() == owner, "ERROR:COS-004:NOT_OWNER");
        require(_access.hasRole(requiredRole, owner), "ERROR:COS-005:REQUIRED_ROLE_MISSING");
        _;
    }

    function _afterInitialize() internal override onlyInitializing {
        _componentController = ComponentController(_getContractAddress("Component"));
    }

    function propose(IComponent component) 
        external 
        onlyOwnerWithRoleFromComponent(component) 
    {
        _componentController.propose(component);
    }

    function stake(
        uint256 id, 
        address [] calldata tokens, 
        uint256 [] calldata amounts
    ) 
        external 
        onlyOwnerWithRole(id)
    { }

    function withdraw(
        uint256 id, 
        address [] calldata tokens, 
        uint256 [] calldata amounts
    ) 
        external
        onlyOwnerWithRole(id)
    { }
        

    function pause(uint256 id) external onlyOwnerWithRole(id) {
        _componentController.pause(id);
    }

    function unpause(uint256 id) external onlyOwnerWithRole(id) {
        _componentController.unpause(id);
    }

    function getComponentId(address componentAddress) external returns(uint256 id) {
        _componentController.getComponentId(componentAddress);
    }
}