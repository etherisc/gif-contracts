// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract TestCoinAlternativeImplementation is ERC20 {

    string public constant NAME = "Test Alternative Coin";
    string public constant SYMBOL = "TAC";

    uint256 public constant INITIAL_SUPPLY = 10**24;

    /**
     * @dev Constructor function that creates a new ERC20 token with the given name and symbol, and mints the initial supply to the sender.
     */
    constructor()
        ERC20(NAME, SYMBOL)
    {
        _mint(
            _msgSender(),
            INITIAL_SUPPLY
        );
    }

    // inspired by ZRX transfer implementation
    // see https://soliditydeveloper.com/safe-erc20
    /**
     * @dev Transfer tokens from one address to another.
     * @param _from The address from which to transfer the tokens.
     * @param _to The address to which to transfer the tokens.
     * @param _value The amount of tokens to transfer.
     * @return A boolean value indicating whether the transfer was successful or not.
     *
     * Requirements:
     * - The sender must have a balance of at least `_value`.
     * - The sender must have allowance for `_spender`'s tokens of at least `_value`.
     * - The balance of `_to` must not be less than the sum of the balance and `_value`.
     * - Neither `_from` nor `_to` can be the zero address.
     */
    function transferFrom(address _from, address _to, uint _value)
        public virtual override returns (bool) 
    {
        if (balanceOf(_from) >= _value                      // check sufficient balance
            && allowance(_from, msg.sender) >= _value       // check sufficient allowance
            && balanceOf(_to) + _value >= balanceOf(_to)   // check overflow
            && _from != address(0)                           // sender not zero address
            && _to != address(0))                            // recipient not zero address
        {
            return super.transferFrom(_from, _to, _value); // should never fail now
        } else { 
            return false; 
        }
    }
}
