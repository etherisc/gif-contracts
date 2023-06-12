// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

contract TestRegistryCompromisedController {

    bytes32 public constant POLICY = bytes32("Policy");
    bytes32 public constant QUERY = bytes32("Query");

    mapping(bytes32 => address) public contracts;

    /**
     * @dev Returns the address of a registered contract.
     * @param contractName The name of the contract to retrieve.
     * @return moduleAddress The address of the requested contract.
     */
    function getContract(bytes32 contractName)
        external
        view
        returns (address moduleAddress)
    {
        moduleAddress = contracts[contractName];
    }

    /**
     * @dev Upgrades the Policy Manager contract to version 2.
     * @param compromisedPolicyModuleAddress The new address of the compromised policy module.
     * @param originalQueryModuleAddress The new address of the original query module.
     */
    function upgradeToV2(
        address compromisedPolicyModuleAddress, 
        address originalQueryModuleAddress
    ) 
        public 
    { 
        contracts[POLICY] = compromisedPolicyModuleAddress;
        contracts[QUERY] = originalQueryModuleAddress;
    }
}
