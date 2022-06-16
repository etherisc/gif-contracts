// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

// TODO cleanup
// import "../modules/access/IAccess.sol";
import "../modules/registry/IRegistry.sol";

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

    modifier onlyInstanceOwner() {
        require(
            _registry.ensureSender(msg.sender, "InstanceOwner"),
            "ERROR:CRC-001:NOT_INSTANCE_OWNER");
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

    function _getContractAddress(bytes32 contractName) internal returns (address) { 
        return _registry.getContract(contractName);
    }
}
