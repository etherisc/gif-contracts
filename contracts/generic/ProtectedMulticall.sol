// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

/// @title Multicall - Aggregate results from multiple read-only function calls
/// @author Michael Elliot <mike@makerdao.com>
/// @author Joshua Levine <joshua@makerdao.com>
/// @author Nick Johnson <arachnid@notdot.net>
/// @notice added onlyOwner so we can restrict access to this contract
contract ProtectedMulticall {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "ProtectedMulticall: only owner");
        _;
    }
    struct Call {
        address target;
        bytes callData;
    }

    constructor() {
        owner = msg.sender;
    }
    function aggregate(
        Call[] calldata calls
    )
        public
        onlyOwner
        returns (uint256 blockNumber, bytes[] memory returnData)
    {
        blockNumber = block.number;
        returnData = new bytes[](calls.length);
        for (uint256 i = 0; i < calls.length; i++) {
            (bool success, bytes memory ret) = calls[i].target.call(
                calls[i].callData
            );
            require(success);
            returnData[i] = ret;
        }
    }
}
