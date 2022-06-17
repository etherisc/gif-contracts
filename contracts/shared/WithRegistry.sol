// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./AccessModifiers.sol";
import "@gif-interface/contracts/modules/IRegistry.sol";

contract WithRegistry is AccessModifiers {
    IRegistry public registry;

    constructor(address _registry) {
        registry = IRegistry(_registry);
    }

    function assignRegistry(address _registry) external onlyInstanceOperator {
        registry = IRegistry(_registry);
    }

    function getContractFromRegistry(bytes32 _contractName)
        public
        override
        view
        returns (address _addr)
    {
        _addr = registry.getContract(_contractName);
    }

    function getContractInReleaseFromRegistry(bytes32 _release, bytes32 _contractName)
        internal
        view
        returns (address _addr)
    {
        _addr = registry.getContractInRelease(_release, _contractName);
    }

    function getReleaseFromRegistry() internal view returns (bytes32 _release) {
        _release = registry.getRelease();
    }
}
