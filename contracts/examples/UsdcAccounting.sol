// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/draft-ERC20Permit.sol";

contract UsdcAccounting is ERC20Permit {

    string public constant NAME = "USD Coin - Accounting Token";
    string public constant SYMBOL = "USDC-AT";
    uint8 public constant DECIMALS = 6;
    uint256 public constant INITIAL_SUPPLY = 10**24;

    constructor()
        ERC20(NAME, SYMBOL)
        ERC20Permit(NAME)
    {
        _mint(
            _msgSender(),
            INITIAL_SUPPLY
        );
    }

    function decimals() public view virtual override returns (uint8) {
        return DECIMALS;
    }
}
