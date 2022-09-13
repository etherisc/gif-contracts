// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/TransferHelper.sol";

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract TestTransferFrom {

    event LogTransferHelperInputValidation1Failed(bool tokenIsContract, address from, address to);
    event LogTransferHelperInputValidation2Failed(uint256 balance, uint256 allowance);
    event LogTransferHelperCallFailed(bool callSuccess, uint256 returnDataLength, bytes returnData);

    function unifiedTransferFrom(
        IERC20 token, 
        address from, 
        address to, 
        uint256 amount
    ) 
        external 
        returns(bool)
    {
        return TransferHelper.unifiedTransferFrom(token, from, to, amount);
    }

}
