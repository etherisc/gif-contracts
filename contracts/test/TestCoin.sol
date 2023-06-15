// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract TestCoin is ERC20 {

    string public constant NAME = "Test Dummy";
    string public constant SYMBOL = "TDY";

    uint256 public constant INITIAL_SUPPLY = 10**24;

    /**
     * @dev Constructor function that initializes the ERC20 token with a given name, symbol, and initial supply.
     */
    constructor()
        ERC20(NAME, SYMBOL)
    {
        _mint(
            _msgSender(),
            INITIAL_SUPPLY
        );
    }
}

contract TestCoinX is ERC20 {

    string public constant NAME = "Test Dummy X";
    string public constant SYMBOL = "TDX";

    uint256 public constant INITIAL_SUPPLY = 10**24;

    /**
     * @dev Constructor function that creates a new instance of the ERC20 token with the given name and symbol. It also mints the initial supply and assigns it to the deployer's address.
     */
    constructor()
        ERC20(NAME, SYMBOL)
    {
        _mint(
            _msgSender(),
            INITIAL_SUPPLY
        );
    }
}
