// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract RiskpoolToken is
    ERC20
{
    string public constant NAME = "GIF Riskpool Token";
    string public constant SYMBOL = "RPT";

    constructor() 
        ERC20(NAME, SYMBOL)
    {

    }
}
