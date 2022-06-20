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

    // TODO remove once deleted from interface
    function assignController(address _storage, address _controller)
        external override
        onlyOwner
    {
        // IModuleStorage(_storage).assignController(_controller);
    }

    // TODO remove once deleted from interface
    function assignStorage(address _controller, address _storage)
        external override
        onlyOwner
    {
        // IModuleController(_controller).assignStorage(_storage);
    }

    /* License */
    function approveProduct(uint256 _productId)
        external override 
        onlyOwner 
    {
        address [] memory tokens = new address[](0);
        uint256 [] memory amounts = new uint256[](0);
        
        _component.approve(_productId, tokens, amounts);
    }

    function disapproveProduct(uint256 _productId) 
        external override 
        onlyOwner 
    {
        _component.decline(_productId);
    }

    function pauseProduct(uint256 _productId) 
        external override 
        onlyOwner 
    {
        // TODO implementation needed
    }

    /* Access */
    function productOwnerRole() public view returns(bytes32) {
        return _access.productOwnerRole();
    }

    function oracleProviderRole() public view returns(bytes32) {
        return _access.oracleProviderRole();
    }

    function riskpoolKeeperRole() public view returns(bytes32) {
        return _access.riskpoolKeeperRole();
    }

    // TODO add to interface IInstanceOperatorService
    function hasRole(bytes32 _role, address _address)
        public view 
        returns(bool)
    {
        return _access.hasRole(_role, _address);
    }

    // TODO update interface and rename to addRole
    function createRole(bytes32 _role) 
        external override
        onlyOwner 
    {
        _access.addRole(_role);
    }

    // TODO update interface and rename to grantRole and switch argument order
    function addRoleToAccount(address _address, bytes32 _role)
        external override
        onlyOwner
    {
        _access.grantRole(_role, _address);
    }

    // TODO add implementation in accesscontroller
    function cleanRolesForAccount(address _address) 
        external override 
        onlyOwner 
    {
    }

    /* Registry */
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

    function register(bytes32 _contractName, address _contractAddress)
        external override
        onlyOwner
    {
        _registry.register(_contractName, _contractAddress);
    }

    function deregisterInRelease(bytes32 _release, bytes32 _contractName)
        external override
        onlyOwner
    {
        _registry.deregisterInRelease(_release, _contractName);
    }

    function deregister(bytes32 _contractName) 
        external override 
        onlyOwner 
    {
        _registry.deregister(_contractName);
    }

    function prepareRelease(bytes32 _newRelease) 
        external override 
        onlyOwner 
    {
        _registry.prepareRelease(_newRelease);
    }

    /* Query */
    function approveOracle(uint256 _oracleId)
        external override 
        onlyOwner
    {
        address [] memory tokens = new address[](0);
        uint256 [] memory amounts = new uint256[](0);
        
        _component.approve(_oracleId, tokens, amounts);
    }

    // TODO align with component neutral workflows
    function disapproveOracle(uint256 _oracleId) 
        external override 
        onlyOwner 
    {
        _component.decline(_oracleId);
    }

    /* Inventory */
    function products() external override view returns(uint256) {
        return _component.products();
    }

    function oracles() external override view returns(uint256) {
        return _component.oracles();
    }
}
