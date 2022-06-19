// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ILicense.sol";
import "../modules/ComponentController.sol";
import "../shared/WithRegistry.sol";
import "../shared/IModuleController.sol";
import "../shared/IModuleStorage.sol";
import "@gif-interface/contracts/modules/IAccess.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/services/IInstanceOperatorService.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract InstanceOperatorService is 
    IInstanceOperatorService, 
    WithRegistry, 
    Ownable 
{
    bytes32 public constant NAME = "InstanceOperatorService";

    // solhint-disable-next-line no-empty-blocks
    constructor(address _registry) WithRegistry(_registry) {}

    function assignController(address _storage, address _controller)
        external override
        onlyOwner
    {
        IModuleStorage(_storage).assignController(_controller);
    }

    function assignStorage(address _controller, address _storage)
        external override
        onlyOwner
    {
        IModuleController(_controller).assignStorage(_storage);
    }

    /* License */
    function approveProduct(uint256 _productId)
        external override 
        onlyOwner 
    {
        address [] memory tokens = new address[](0);
        uint256 [] memory amounts = new uint256[](0);
        
        component().approve(_productId, tokens, amounts);
    }

    function disapproveProduct(uint256 _productId) 
        external override 
        onlyOwner 
    {
        component().decline(_productId);
    }

    function pauseProduct(uint256 _productId) 
        external override 
        onlyOwner 
    {
        // TODO implementation needed
    }

    /* Access */
    function productOwnerRole() public view returns(bytes32) {
        return access().productOwnerRole();
    }

    function oracleProviderRole() public view returns(bytes32) {
        return access().oracleProviderRole();
    }

    function riskpoolKeeperRole() public view returns(bytes32) {
        return access().riskpoolKeeperRole();
    }

    // TODO add to interface IInstanceOperatorService
    function hasRole(bytes32 _role, address _address)
        public view 
        returns(bool)
    {
        return access().hasRole(_role, _address);
    }

    // TODO update interface and rename to addRole
    function createRole(bytes32 _role) 
        external override
        onlyOwner 
    {
        access().addRole(_role);
    }

    // TODO update interface and rename to grantRole and switch argument order
    function addRoleToAccount(address _address, bytes32 _role)
        external override
        onlyOwner
    {
        access().grantRole(_role, _address);
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
        registry.registerInRelease(_release, _contractName, _contractAddress);
    }

    function register(bytes32 _contractName, address _contractAddress)
        external override
        onlyOwner
    {
        registry.register(_contractName, _contractAddress);
    }

    function deregisterInRelease(bytes32 _release, bytes32 _contractName)
        external override
        onlyOwner
    {
        registry.deregisterInRelease(_release, _contractName);
    }

    function deregister(bytes32 _contractName) 
        external override 
        onlyOwner 
    {
        registry.deregister(_contractName);
    }

    function prepareRelease(bytes32 _newRelease) 
        external override 
        onlyOwner 
    {
        registry.prepareRelease(_newRelease);
    }

    /* Query */
    function approveOracle(uint256 _oracleId)
        external override 
        onlyOwner
    {
        address [] memory tokens = new address[](0);
        uint256 [] memory amounts = new uint256[](0);
        
        component().approve(_oracleId, tokens, amounts);
    }

    // TODO align with component neutral workflows
    function disapproveOracle(uint256 _oracleId) 
        external override 
        onlyOwner 
    {
        component().decline(_oracleId);
    }

    /* Inventory */
    function products() external override view returns(uint256) {
        return component().products();
    }

    function oracles() external override view returns(uint256) {
        return component().oracles();
    }

    /* Lookup */
    function access() internal view returns (IAccess) {
        return IAccess(registry.getContract("Access"));
    }

    function component() internal view returns (ComponentController) {
        return ComponentController(registry.getContract("Component"));
    }

    function license() internal view returns (ILicense) {
        return ILicense(registry.getContract("License"));
    }

    function query() internal view returns (IQuery) {
        return IQuery(registry.getContract("Query"));
    }
}
