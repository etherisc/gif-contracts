// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/services/IOracleService.sol";


contract OracleService is 
    IOracleService, 
    CoreController
{
    IQuery private _query;

    /**
     * @dev Sets the `_query` variable to an instance of the `IQuery` contract.
     */
    function _afterInitialize() internal override onlyInitializing {
        _query = IQuery(_getContractAddress("Query"));
    }

    /**
     * @dev Allows a registered oracle to respond to a data request.
     * @param _requestId The ID of the data request.
     * @param _data The data requested by the smart contract.
     */
    function respond(uint256 _requestId, bytes calldata _data) external override {
        // function below enforces msg.sender to be a registered oracle
        _query.respond(_requestId, _msgSender(), _data);
    }
}
