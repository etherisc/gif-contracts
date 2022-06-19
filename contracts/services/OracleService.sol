// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/WithRegistry.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/services/IOracleService.sol";
import "@openzeppelin/contracts/utils/Context.sol";


contract OracleService is 
    IOracleService, 
    WithRegistry, 
    Context
{
    bytes32 public constant NAME = "OracleService";

    // solhint-disable-next-line no-empty-blocks
    constructor(address _registry) WithRegistry(_registry) {}

    function respond(uint256 _requestId, bytes calldata _data) external override {
        // todo: oracle contract should be approved
        _query().respond(_requestId, msg.sender, _data);
    }

    function _query() internal view returns (IQuery) {
        return IQuery(registry.getContract("Query"));
    }
}
