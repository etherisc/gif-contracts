// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract RiskpoolToken is
    ERC20
{
    string public constant NAME = "GIF Riskpool Token";
    string public constant SYMBOL = "RPT";

    /**
     * @dev Constructor function that sets the name and symbol of the ERC20 token.
     */
    constructor() 
        ERC20(NAME, SYMBOL)
    {

    }
}
