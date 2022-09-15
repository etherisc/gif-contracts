// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

contract TestRegistryCompromisedController {

    bytes32 public constant POLICY = bytes32("Policy");
    bytes32 public constant QUERY = bytes32("Query");

    mapping(bytes32 => address) public contracts;

    function getContract(bytes32 contractName)
        external
        view
        returns (address moduleAddress)
    {
        moduleAddress = contracts[contractName];
    }

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
