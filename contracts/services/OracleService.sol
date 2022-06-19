// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/services/IOracleService.sol";


contract OracleService is 
    IOracleService, 
    CoreController
{
    bytes32 public constant NAME = "OracleService";

    function respond(uint256 _requestId, bytes calldata _data) external override {
        // todo: oracle contract should be approved
        _query().respond(_requestId, _msgSender(), _data);
    }

    function _query() internal view returns (IQuery) {
        address queryAddress = _getContractAddress("Query");
        return IQuery(queryAddress);
    }
}
