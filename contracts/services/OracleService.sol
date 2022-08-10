// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/services/IOracleService.sol";


contract OracleService is 
    IOracleService, 
    CoreController
{
    IQuery private _query;

    function _afterInitialize() internal override onlyInitializing {
        _query = IQuery(_getContractAddress("Query"));
    }

    function respond(uint256 _requestId, bytes calldata _data) external override {
        _query.respond(_requestId, _msgSender(), _data);
    }
}
