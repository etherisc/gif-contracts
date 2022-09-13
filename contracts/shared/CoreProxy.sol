// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;


import "@etherisc/gif-interface/contracts/shared/ICoreProxy.sol";
import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract CoreProxy is 
    ICoreProxy, 
    ERC1967Proxy
{

    modifier onlyAdmin() {
        require(
            msg.sender == _getAdmin(),
            "ERROR:CRP-001:NOT_ADMIN");
        _;
    }

    constructor(address _controller, bytes memory encoded_initializer) 
        ERC1967Proxy(_controller, encoded_initializer) 
    {
        _changeAdmin(msg.sender);
    }

    function implementation() external view returns (address) {
        return _implementation();
    }

    function upgradeToAndCall(address newImplementation, bytes calldata data) 
        external
        payable
        onlyAdmin
    {
        address oldImplementation =  _implementation();

        _upgradeToAndCall(newImplementation, data, true);

        emit LogCoreContractUpgraded(
            oldImplementation, 
            newImplementation);
    }    
}
