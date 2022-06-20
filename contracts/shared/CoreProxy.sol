// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;


import "@gif-interface/contracts/shared/ICoreProxy.sol";
import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract CoreProxy is ICoreProxy, ERC1967Proxy {

    constructor(address _controller, bytes memory encoded_initializer) 
        ERC1967Proxy(_controller, encoded_initializer) 
    {}

    function implementation() external view returns (address) {
        return _implementation();
    }

    function upgradeToAndCall(address newImplementation, bytes calldata data) 
        external 
        payable 
    {
        address oldImplementation =  _implementation();

        _upgradeToAndCall(newImplementation, data, true);

        emit LogCoreContractUpgraded(
            oldImplementation, 
            newImplementation);
    }    
}
