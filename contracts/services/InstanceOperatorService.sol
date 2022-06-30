// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ComponentController.sol";
import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/services/IInstanceOperatorService.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract InstanceOperatorService is 
    IInstanceOperatorService, 
    CoreController, 
    Ownable 
{
    ComponentController private _component;

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
        _transferOwnership(_msgSender());
    }

    /* registry */
    function prepareRelease(bytes32 _newRelease) 
        external override 
        onlyOwner 
    {
        _registry.prepareRelease(_newRelease);
    }

    function register(bytes32 _contractName, address _contractAddress)
        external override
        onlyOwner
    {
        _registry.register(_contractName, _contractAddress);
    }

    function deregister(bytes32 _contractName) 
        external override 
        onlyOwner 
    {
        _registry.deregister(_contractName);
    }

    function registerInRelease(
        bytes32 _release,
        bytes32 _contractName,
        address _contractAddress
    ) 
        external override 
        onlyOwner 
    {
        _registry.registerInRelease(_release, _contractName, _contractAddress);
    }

    function deregisterInRelease(bytes32 _release, bytes32 _contractName)
        external override
        onlyOwner
    {
        _registry.deregisterInRelease(_release, _contractName);
    }

    /* access */
    function createRole(bytes32 _role) 
        external override
        onlyOwner 
    {
        _access.addRole(_role);
    }

    function grantRole(bytes32 role, address principal)
        external override
        onlyOwner
    {
        _access.grantRole(role, principal);
    }

    function revokeRole(bytes32 role, address principal) 
        external override 
        onlyOwner 
    {
        _access.revokeRole(role, principal);
    }

    /* component */
    function approve(uint256 id)
        external override 
        onlyOwner 
    {
        _component.approve(id);
    }

    function decline(uint256 id) 
        external override 
        onlyOwner 
    {
        _component.decline(id);
    }

    function suspend(uint256 id) 
        external override 
        onlyOwner 
    {
        _component.suspend(id);
    }

    function resume(uint256 id) 
        external override 
        onlyOwner 
    {
        _component.resume(id);
    }

    // service staking
    // TODO implement setDefaultStaking staking
    function setDefaultStaking(
        uint16 componentType, 
        bytes calldata data
    )
        external override
        onlyOwner
    {
        revert("ERROR:IOS-001:IMPLEMENATION_MISSING");
    }

    // TODO implement adjustStakingRequirements staking
    function adjustStakingRequirements(
        uint256 id, 
        bytes calldata data
    )
        external override
        onlyOwner
    {
        revert("ERROR:IOS-002:IMPLEMENATION_MISSING");
    }
}
