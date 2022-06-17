// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/registry/IRegistry.sol";
import "../modules/access/IAccess.sol";
import "../modules/ComponentController.sol";

import "@openzeppelin/contracts/utils/Context.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";

contract CoreController is
    Context,
    Initializable 
{
    IRegistry internal _registry;

    constructor () {
        _disableInitializers();
    }

    modifier onlyInstanceOperator() {
        require(
            _registry.ensureSender(msg.sender, "InstanceOperatorService"),
            "ERROR:CRC-001:NOT_INSTANCE_OPERATOR");
        _;
    }

    modifier onlyPolicyFlow(bytes32 _module) {
        // Allow only from delegator
        require(
            address(this) == _getContractAddress(_module),
            "ERROR:CRC-002:NOT_ON_STORAGE"
        );

        // Allow only ProductService (it delegates to PolicyFlow)
        require(
            msg.sender == _getContractAddress("ProductService"),
            "ERROR:CRC-003:NOT_PRODUCT_SERVICE"
        );
        _;
    }

    modifier onlyOracleService() {
        require(
            msg.sender == _getContractAddress("OracleService"),
            "ERROR:CRC-004:NOT_ORACLE_SERVICE"
        );
        _;
    }

    modifier onlyInstanceOwner() {
        require(
            _registry.ensureSender(msg.sender, "InstanceOwner"),
            "ERROR:CRC-005:NOT_INSTANCE_OWNER");
        _;
    }

    function initialize(address registry) public initializer {
        _setupRegistry(registry);
        _afterInitialize();
    }

    function _setupRegistry(address registry) internal onlyInitializing {
        _registry = IRegistry(registry);
    }

    function _afterInitialize() internal virtual onlyInitializing {}

    /* Lookup */
    function _component() internal view returns (ComponentController) {
        return ComponentController(_getContractAddress("Component"));
    }

    function _access() internal view returns (IAccess) {
        return IAccess(_getContractAddress("Access"));
    }

    function _getContractAddress(bytes32 contractName) internal view returns (address) { 
        return _registry.getContract(contractName);
    }
}
