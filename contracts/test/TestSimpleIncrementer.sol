// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

// Simple smart contract that increments a counter. This is used to create a fast transaction. 
contract TestSimpleIncrementer {

    uint256 public counter;

    function increment() external {
        counter++;
    }
    
}
