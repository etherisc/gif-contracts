// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/TransferHelper.sol";

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract TestTransferFrom {

    event LogTransferHelperInputValidation1Failed(bool tokenIsContract, address from, address to);
    event LogTransferHelperInputValidation2Failed(uint256 balance, uint256 allowance);
    event LogTransferHelperCallFailed(bool callSuccess, uint256 returnDataLength, bytes returnData);

    /**
     * @dev Transfers tokens from a specified address to another specified address using the TransferHelper library.
     * @param token The address of the ERC20 token to transfer.
     * @param from The address from which to transfer tokens.
     * @param to The address to which to transfer tokens.
     * @param amount The amount of tokens to transfer.
     * @return Returns a boolean indicating whether the transfer was successful or not.
     */
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
