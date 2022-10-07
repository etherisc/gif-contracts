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

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    function propose(IComponent component) 
        external override
        onlyOwnerWithRoleFromComponent(component) 
    {
        _component.propose(component);
    }

    function stake(uint256 id) 
        external override 
        onlyOwnerWithRole(id) 
    {
        revert("ERROR:COS-006:IMPLEMENATION_MISSING");
    }

    function withdraw(uint256 id) 
        external override
        onlyOwnerWithRole(id) 
    {
        revert("ERROR:COS-007:IMPLEMENATION_MISSING");
    }
        

    function pause(uint256 id) 
        external override
        onlyOwnerWithRole(id) 
    {
        _component.pause(id);
    }

    function unpause(uint256 id) 
        external override 
        onlyOwnerWithRole(id) 
    {
        _component.unpause(id);
    }

    function archive(uint256 id) 
        external override 
        onlyOwnerWithRole(id) 
    {
        _component.archiveFromComponentOwner(id);
    }
}