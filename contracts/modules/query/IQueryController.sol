// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./IQuery.sol";

interface IQueryController {

    function proposeOracle(bytes32 _name, address _oracleContract)
        external
        returns (uint256 _oracleId);

    function updateOracleContract(address _newOracleContract, uint256 _oracleId)
        external;

    function approveOracle(uint256 _oracleId) external;
    function pauseOracle(uint256 _oracleId) external;

    function disapproveOracle(uint256 _oracleId) external;

    function request(
        bytes32 _bpKey,
        bytes calldata _input,
        string calldata _callbackMethodName,
        address _callbackContractAddress,
        uint256 _responsibleOracleId
    ) external returns (uint256 _requestId);

    function respond(
        uint256 _requestId,
        address _responder,
        bytes calldata _data
    ) external;

    function getOracleCount() 
        external 
        view 
        returns (uint256 _oracles);
}
