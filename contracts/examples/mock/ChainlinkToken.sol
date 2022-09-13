// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

abstract contract ERC677Receiver {
    function onTokenTransfer (address _sender, uint _value, bytes calldata _data) public virtual;
}

contract ChainlinkToken is ERC20 {
    constructor(address owner, uint256 supply) ERC20("Chainlink Dummy Token", "CDT"){
        _mint(owner, supply);
    }

    function transferAndCall(address _to, uint _value, bytes calldata _data) public returns (bool success){
        super.transfer(_to, _value);
        //  Transfer(msg.sender, _to, _value, _data);
        if (isContract(_to)) {
            contractFallback(_to, _value, _data);
        }
        return true;
    }

    function contractFallback(address _to, uint _value, bytes calldata _data) private {
        ERC677Receiver receiver = ERC677Receiver(_to);
        receiver.onTokenTransfer(msg.sender, _value, _data);
    }

    function isContract(address _addr) private view returns (bool hasCode) {
        uint length;
        assembly { length := extcodesize(_addr) }
        return length > 0;
    }
}
