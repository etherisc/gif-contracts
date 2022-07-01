// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract DummyCoin is ERC20 {

    string public constant NAME = "Dummy";
    string public constant SYMBOL = "DMY";

    uint256 public constant INITIAL_SUPPLY = 10**20;

    constructor()
        ERC20(NAME, SYMBOL)
    {
        _mint(
            _msgSender(),
            INITIAL_SUPPLY
        );
    }
}