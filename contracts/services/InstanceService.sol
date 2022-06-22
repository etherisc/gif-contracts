// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ComponentController.sol";
import "../shared/CoreController.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/services/IComponentOwnerService.sol";
import "@gif-interface/contracts/services/IInstanceService.sol";
import "@gif-interface/contracts/services/IInstanceOperatorService.sol";
import "@gif-interface/contracts/services/IOracleService.sol";
import "@gif-interface/contracts/services/IProductService.sol";

contract InstanceService is 
    IInstanceService, 
    CoreController
{
    ComponentController private _component;

    IComponentOwnerService private _componentOwnerService;
    IInstanceOperatorService private _instanceOperatorService;
    IOracleService private _oracleService;
    IProductService private _productService;

    function _afterInitialize() internal override onlyInitializing {
        _componentOwnerService = IComponentOwnerService(_getContractAddress("ComponentOwnerService"));
        _instanceOperatorService = IInstanceOperatorService(_getContractAddress("InstanceOperatorService"));
        _oracleService = IOracleService(_getContractAddress("OracleService"));
        _productService = IProductService(_getContractAddress("ProductService"));
        _component = ComponentController(_getContractAddress("Component"));
    }

    /* registry */
    function getComponentOwnerService() external view returns(IComponentOwnerService service) {
        return _componentOwnerService;
    }

    function getInstanceOperatorService() external view returns(IInstanceOperatorService service) {
        return _instanceOperatorService;
    }

    function getOracleService() external view returns(IOracleService service) {
        return _oracleService;
    }

    function getProductService() external view returns(IProductService service) {
        return _productService;
    }


    /* access */
    function productOwnerRole() public view returns(bytes32) {
        return _access.productOwnerRole();
    }

    function oracleProviderRole() public view returns(bytes32) {
        return _access.oracleProviderRole();
    }

    function riskpoolKeeperRole() public view returns(bytes32) {
        return _access.riskpoolKeeperRole();
    }

    function hasRole(bytes32 role, address principal)
        public view 
        returns(bool)
    {
        return _access.hasRole(role, principal);
    }

    /* component */
    function products() external override view returns(uint256) {
        return _component.products();
    }

    function oracles() external override view returns(uint256) {
        return _component.oracles();
    }

    function riskPools() external override view returns(uint256) {
        return _component.riskpools();
    }

    function getComponent(uint256 id) external override view returns(IComponent) {
        return _component.getComponent(id);
    }

    // service staking
    function getStakingRequirements(uint256 id) 
        external override 
        view 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-001:IMPLEMENATION_MISSING");
    }

    function getStakedAssets(uint256 id)
        external override 
        view 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-002:IMPLEMENATION_MISSING");
    }
}
