// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ComponentController.sol";
import "../shared/CoreController.sol";
import "../services/InstanceOperatorService.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/modules/IRegistry.sol";
import "@gif-interface/contracts/services/IComponentOwnerService.sol";
import "@gif-interface/contracts/services/IInstanceService.sol";
import "@gif-interface/contracts/services/IInstanceOperatorService.sol";
import "@gif-interface/contracts/services/IOracleService.sol";
import "@gif-interface/contracts/services/IProductService.sol";

contract InstanceService is 
    IInstanceService, 
    CoreController
{
    bytes32 public constant COMPONENT_NAME = "Component";
    bytes32 public constant COMPONENT_OWNER_SERVICE_NAME = "ComponentOwnerService";
    bytes32 public constant INSTANCE_OPERATOR_SERVICE_NAME = "InstanceOperatorService";
    bytes32 public constant ORACLE_SERVICE_NAME = "OracleService";
    bytes32 public constant PRODUCT_SERVICE_NAME = "ProductService";

    /* registry */
    function getComponentOwnerService() external override view returns(IComponentOwnerService service) {
        return IComponentOwnerService(_getContractAddress(COMPONENT_OWNER_SERVICE_NAME));
    }

    function getInstanceOperatorService() external override view returns(IInstanceOperatorService service) {
        return IInstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
    }

    function getOracleService() external override view returns(IOracleService service) {
        return IOracleService(_getContractAddress(ORACLE_SERVICE_NAME));
    }

    function getProductService() external override view returns(IProductService service) {
        return IProductService(_getContractAddress(PRODUCT_SERVICE_NAME));
    }

    function getOwner() external view returns(address) {
        InstanceOperatorService ios = InstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
        return ios.owner();
    }

    function getRegistry() external view returns(IRegistry service) {
        return _registry;
    }

    /* access */
    function productOwnerRole() external override view returns(bytes32) {
        return _access.productOwnerRole();
    }

    function oracleProviderRole() external override view returns(bytes32) {
        return _access.oracleProviderRole();
    }

    function riskpoolKeeperRole() external override view returns(bytes32) {
        return _access.riskpoolKeeperRole();
    }

    function hasRole(bytes32 role, address principal)
        external override view 
        returns(bool)
    {
        return _access.hasRole(role, principal);
    }

    /* component */
    function products() external override view returns(uint256) {
        return _component().products();
    }

    function oracles() external override view returns(uint256) {
        return _component().oracles();
    }

    function riskPools() external override view returns(uint256) {
        return _component().riskpools();
    }

    function getComponent(uint256 id) external override view returns(IComponent) {
        return _component().getComponent(id);
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

    function _component() internal view returns(ComponentController) {
        return ComponentController(_getContractAddress(COMPONENT_NAME));
    }
}
