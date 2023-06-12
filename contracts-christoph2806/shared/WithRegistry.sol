// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";

contract WithRegistry {

/*
 *  We can consider the registry address as immutable here as it contains the
 *  root data structure for the whole GIF Instance.
 *  We can therefore ensure that a policy flow cannot overwrite the address
 *  neither by chance nor by intention.
 */
    IRegistry public immutable registry;

    modifier onlyInstanceOperator() {
        require(
            msg.sender == getContractFromRegistry("InstanceOperatorService"),
            "ERROR:ACM-001:NOT_INSTANCE_OPERATOR"
        );
        _;
    }

    modifier onlyOracleService() {
        require(
            msg.sender == getContractFromRegistry("OracleService"),
            "ERROR:ACM-004:NOT_ORACLE_SERVICE"
        );
        _;
    }

    modifier onlyOracleOwner() {
        require(
            msg.sender == getContractFromRegistry("OracleOwnerService"),
            "ERROR:ACM-005:NOT_ORACLE_OWNER"
        );
        _;
    }

    modifier onlyProductOwner() {
        require(
            msg.sender == getContractFromRegistry("ProductOwnerService"),
            "ERROR:ACM-006:NOT_PRODUCT_OWNER"
        );
        _;
    }

    /**
     * @dev Constructor function that sets the address of the registry contract.
     * @param _registry The address of the registry contract.
     */
    constructor(address _registry) {
        registry = IRegistry(_registry);
    }

    /**
     * @dev Returns the address of a contract registered in the registry by its name.
     *
     * @param _contractName The name of the contract to retrieve.
     *
     * @return _addr The address of the contract.
     */
    function getContractFromRegistry(bytes32 _contractName)
        public
        // override
        view
        returns (address _addr)
    {
        _addr = registry.getContract(_contractName);
    }

    /**
     * @dev Returns the address of a contract with a given name in a specific release of the registry.
     * @param _release The release version of the registry where the contract is stored.
     * @param _contractName The name of the contract to retrieve.
     * @return _addr The address of the contract in the given release.
     */
    function getContractInReleaseFromRegistry(bytes32 _release, bytes32 _contractName)
        internal
        view
        returns (address _addr)
    {
        _addr = registry.getContractInRelease(_release, _contractName);
    }

    /**
     * @dev Returns the current release identifier from the registry.
     * @return _release The release identifier as a bytes32 value.
     */
    function getReleaseFromRegistry() internal view returns (bytes32 _release) {
        _release = registry.getRelease();
    }
}
