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

    /**
     * @dev Constructor function that creates a new instance of the contract.
     * @param _controller The address of the controller contract.
     * @param encoded_initializer The encoded initializer data.
     */
    constructor(address _controller, bytes memory encoded_initializer) 
        ERC1967Proxy(_controller, encoded_initializer) 
    {
        _changeAdmin(msg.sender);
    }

    /**
     * @dev Returns the address of the current implementation contract.
     * @return implementation The address of the current implementation contract.
     */
    function implementation() external view returns (address) {
        return _implementation();
    }

    /**
     * @dev Upgrades the contract to a new implementation and forwards a function call to it.
     * @param newImplementation The address of the new implementation contract.
     * @param data The data payload to be forwarded to the new implementation.
     * @notice This function emits 1 events: 
     * - LogCoreContractUpgraded
     */
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
