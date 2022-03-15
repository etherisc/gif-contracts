// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

contract BaseModuleController {
    address public delegator;

    function _assignStorage(address _storage) internal {
        delegator = _storage;
    }
}
