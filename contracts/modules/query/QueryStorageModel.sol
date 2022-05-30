// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./IQuery.sol";

contract QueryStorageModel is IQuery {

    // Oracles
    mapping(uint256 => Oracle) public oracles;
    mapping(address => uint256) public oracleIdByAddress;
    uint256 public oracleCount;

    // Requests
    OracleRequest[] public oracleRequests;
}
