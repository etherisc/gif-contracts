// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

abstract contract ERC677Receiver {
    /**
     * @dev This function is called when tokens are transferred to this contract.
     * @param _sender The address of the sender.
     * @param _value The amount of tokens being transferred.
     * @param _data Additional data with no specified format.
     */
    function onTokenTransfer (address _sender, uint _value, bytes calldata _data) public virtual;
}

contract ChainlinkToken is ERC20 {
    /**
     * @dev Constructor function to initialize the Chainlink Dummy Token with the given owner and supply.
     * @param owner The address of the owner of the token.
     * @param supply The initial supply of the token.
     */
    constructor(address owner, uint256 supply) ERC20("Chainlink Dummy Token", "CDT"){
        _mint(owner, supply);
    }

    /**
     * @dev Transfers tokens to a specified address and calls the recipient's function.
     * @param _to The address of the recipient.
     * @param _value The amount of tokens to send.
     * @param _data Additional data to send to the recipient's function.
     * @return success Returns true if the transfer was successful.
     */
    function transferAndCall(address _to, uint _value, bytes calldata _data) public returns (bool success){
        super.transfer(_to, _value);
        //  Transfer(msg.sender, _to, _value, _data);
        if (isContract(_to)) {
            contractFallback(_to, _value, _data);
        }
        return true;
    }

    /**
     * @dev Executes a contract fallback function.
     * @param _to The address of the contract to execute the fallback function on.
     * @param _value The amount of tokens being transferred.
     * @param _data Additional data to be passed to the fallback function.
     */
    function contractFallback(address _to, uint _value, bytes calldata _data) private {
        ERC677Receiver receiver = ERC677Receiver(_to);
        receiver.onTokenTransfer(msg.sender, _value, _data);
    }

    /**
     * @dev Checks if the given address contains code.
     * @param _addr The address to check.
     * @return hasCode A boolean indicating whether the address contains code or not.
     */
    function isContract(address _addr) private view returns (bool hasCode) {
        uint length;
        assembly { length := extcodesize(_addr) }
        return length > 0;
    }
}
