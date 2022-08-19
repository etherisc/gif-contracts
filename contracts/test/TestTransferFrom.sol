// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/Address.sol";

contract TestTransferFrom {

    // using Address for address;

    // trimmed down version of openzeppelin SafeERC20.safeTransferFrom/_callOptionalReturn
    function unifiedTransferFrom(
        IERC20 token, 
        address from, 
        address to, 
        uint256 amount
    ) 
        external 
        returns(bool success)
    {
        if (token.allowance(from, to) < amount) { 
            return false;
        }

        if (token.balanceOf(from) < amount) {
            return false;
        }

        bytes memory callData = abi.encodeWithSelector(token.transferFrom.selector, from, to, amount);
        return functionCall(address(token), callData);
    }

    event LogTransferFunctionCall(address tokenAddress, bool callSuccess, bytes returnData);

    // adapted from openzeppelin Address.functionCall/functionCallWithValue
    function functionCall(address tokenAddress, bytes memory callData) 
        internal 
        returns(bool success) 
    {
        (bool callSuccess, bytes memory returnData) = tokenAddress.call{value: 0}(callData);
        emit LogTransferFunctionCall(tokenAddress, callSuccess, returnData);
        success = verifyCallResultFromTarget(tokenAddress, callSuccess, returnData);
    }

    event LogTransferCallSuccess(bool callSuccess);
    event LogTransferIsContract(bool addressIsContract);
    event LogTransferReturnDataSuccess(bool success);

    // adapted from openzeppelin Address.verifyCallResultFromTarget
    function verifyCallResultFromTarget(
        address target,
        bool callSuccess,
        bytes memory returnData
    )
        internal 
        returns (bool) 
    {
        emit LogTransferCallSuccess(callSuccess);

        // if (!callSuccess) {
        //     return false;
        // } 

        if (returnData.length == 0) {
            // only check isContract if the call was successful and the return data is empty
            // otherwise we already know that it was a contract
            bool ctrct = isContract(target);
            emit LogTransferIsContract(ctrct);
            return ctrct;
        } 
        
        bool success = abi.decode(returnData, (bool));
        emit LogTransferReturnDataSuccess(success);
        return success;
    }

    // copied from openzeppelin Address.isContract
    function isContract(address account) internal view returns (bool) {
        // This method relies on extcodesize/address.code.length, which returns 0
        // for contracts in construction, since the code is only stored at the end
        // of the constructor execution.

        return account.code.length > 0;
    }

}
