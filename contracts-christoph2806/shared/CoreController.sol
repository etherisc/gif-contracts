// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/modules/IAccess.sol";
import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/utils/Context.sol";

contract CoreController is
    Context,
    Initializable 
{
    IRegistry internal _registry;
    IAccess internal _access;

    /**
     * @dev Constructor function that disables initializers.
     */
    constructor () {
        _disableInitializers();
    }

    modifier onlyInstanceOperator() {
        require(
            _registry.ensureSender(_msgSender(), "InstanceOperatorService"),
            "ERROR:CRC-001:NOT_INSTANCE_OPERATOR");
        _;
    }

    modifier onlyPolicyFlow(bytes32 module) {
        // Allow only from delegator
        require(
            address(this) == _getContractAddress(module),
            "ERROR:CRC-002:NOT_ON_STORAGE"
        );

        // Allow only ProductService (it delegates to PolicyFlow)
        require(
            _msgSender() == _getContractAddress("ProductService"),
            "ERROR:CRC-003:NOT_PRODUCT_SERVICE"
        );
        _;
    }

    /**
     * @dev Initializes the contract with the provided registry address.
     * @param registry The address of the registry contract.
     */
    function initialize(address registry) public initializer {
        _registry = IRegistry(registry);
        if (_getName() != "Access") { _access = IAccess(_getContractAddress("Access")); }
        
        _afterInitialize();
    }

    /**
     * @dev Returns the name of the contract.
     * @return name The name of the contract as a bytes32 value.
     */
    function _getName() internal virtual pure returns(bytes32) { return ""; }

    /**
     * @dev This function is called after the contract is initialized and can be used to perform additional setup.
     * @notice This function should only be called internally by the contract during initialization.
     */
    function _afterInitialize() internal virtual onlyInitializing {}

    /**
     * @dev Returns the address of a registered contract by its name.
     * @param contractName The name of the contract to retrieve.
     * @return contractAddress The address of the requested contract.
     */
    function _getContractAddress(bytes32 contractName) internal view returns (address contractAddress) { 
        contractAddress = _registry.getContract(contractName);
        require(
            contractAddress != address(0),
            "ERROR:CRC-004:CONTRACT_NOT_REGISTERED"
        );
    }
}
