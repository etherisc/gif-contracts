// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

// inspired/informed by
// https://soliditydeveloper.com/safe-erc20
// https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/ERC20.sol
// https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/utils/SafeERC20.sol
// https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/utils/Address.sol
// https://github.com/Uniswap/solidity-lib/blob/master/contracts/libraries/TransferHelper.sol
library TransferHelper {

    event LogTransferHelperInputValidation1Failed(bool tokenIsContract, address from, address to);
    event LogTransferHelperInputValidation2Failed(uint256 balance, uint256 allowance);
    event LogTransferHelperCallFailed(bool callSuccess, uint256 returnDataLength, bytes returnData);

    /**
     * @dev Executes a transferFrom function call on an ERC20 token contract, after performing input validation.
     * @param token The ERC20 token contract to transfer from.
     * @param from The address to transfer tokens from.
     * @param to The address to transfer tokens to.
     * @param value The amount of tokens to transfer.
     * @return success A boolean indicating whether the transfer was successful or not.
     *
     * Emits a LogTransferHelperInputValidation1Failed event if the input validation step 1 fails.
     * Emits a LogTransferHelperInputValidation2Failed event if the input validation step 2 fails.
     * Emits a LogTransferHelperCallFailed event if the low-level call to transferFrom fails.
     * @notice This function emits 3 events: 
     * - LogTransferHelperInputValidation1Failed
     * - LogTransferHelperInputValidation2Failed
     * - LogTransferHelperCallFailed
     */
    function unifiedTransferFrom(
        IERC20 token,
        address from,
        address to,
        uint256 value
    )
        internal
        returns(bool success)
    {
        // input validation step 1
        address tokenAddress = address(token);
        bool tokenIsContract = (tokenAddress.code.length > 0);
        if (from == address(0) || to == address (0) || !tokenIsContract) {
            emit LogTransferHelperInputValidation1Failed(tokenIsContract, from, to);
            return false;
        }
        
        // input validation step 2
        uint256 balance = token.balanceOf(from);
        uint256 allowance = token.allowance(from, address(this));
        if (balance < value || allowance < value) {
            emit LogTransferHelperInputValidation2Failed(balance, allowance);
            return false;
        }

        // low-level call to transferFrom
        // bytes4(keccak256(bytes('transferFrom(address,address,uint256)')));
        (bool callSuccess, bytes memory data) = address(token).call(
            abi.encodeWithSelector(
                0x23b872dd, 
                from, 
                to, 
                value));

        success = callSuccess && (false
            || data.length == 0 
            || (data.length == 32 && abi.decode(data, (bool))));

        if (!success) {
            emit LogTransferHelperCallFailed(callSuccess, data.length, data);
        }
    }
}