// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/registry/IRegistry.sol";
import "../modules/access/IAccess.sol";
import "../modules/ComponentController.sol";
import "../test/IComponent.sol";
import "./IComponentOwnerService.sol";
import "@openzeppelin/contracts/utils/Context.sol";

contract ComponentOwnerService is 
    Context,
    IComponentOwnerService
{
    // TODO figure out if we should keep the pattern that core contracts have a name
    bytes32 public constant NAME = "ComponentOwnerService";

    event LogCosDebug (
        address componentOwnerAddress,
        bytes32 requiredRole
    );

    IRegistry private _registry;
    IAccess private _access;
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


    constructor(IRegistry registry) {
        require(address(registry) != address(0), "ERROR:COS-006:REGISTRY_ADDRESS_ZERO");

        _registry = registry;
        _access = _getAccess();
        _componentController = _getComponentController();
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

    function _getAccess() internal view returns (IAccess) {
        return IAccess(_registry.getContract("Access"));
    }


    function _getComponentController() internal view returns (ComponentController) {
        return ComponentController(_registry.getContract("Component"));
    }
}