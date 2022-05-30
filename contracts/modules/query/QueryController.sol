// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./QueryStorageModel.sol";
import "./IQueryController.sol";
import "../../shared/ModuleController.sol";
import "@gif-interface/contracts/IOracle.sol";

contract QueryController is IQueryController, QueryStorageModel, ModuleController {
    bytes32 public constant NAME = "QueryController";

    modifier isResponsibleOracle(uint256 _requestId, address _responder) {
        require(
            oracles[oracleRequests[_requestId].responsibleOracleId]
                .oracleContract == _responder,
            "ERROR:QUC-001:NOT_RESPONSIBLE_ORACLE"
        );
        _;
    }

    constructor(address _registry) WithRegistry(_registry) {}

    function proposeOracle(bytes32 _name, address _oracleContract)
        external
        override
        onlyOracleOwner
        returns (uint256 _oracleId)
    {
        require(
            oracleIdByAddress[_oracleContract] == 0,
            "ERROR:QUC-008:ORACLE_ALREADY_EXISTS"
        );

        oracleCount += 1;
        _oracleId = oracleCount;

        oracles[_oracleId] = Oracle(
            _name,
            _oracleContract,
            OracleState.Proposed
        );
        oracleIdByAddress[_oracleContract] = _oracleId;

        emit LogOracleProposed(_oracleId, _name, _oracleContract);
    }

    function updateOracleContract(address _newOracleContract, uint256 _oracleId)
        external
        override
        onlyOracleOwner
    {
        require(
            oracleIdByAddress[_newOracleContract] == 0,
            "ERROR:QUC-009:ORACLE_ALREADY_EXISTS"
        );

        address prevContract = oracles[_oracleId].oracleContract;

        oracleIdByAddress[oracles[_oracleId].oracleContract] = 0;
        oracles[_oracleId].oracleContract = _newOracleContract;
        oracleIdByAddress[_newOracleContract] = _oracleId;

        emit LogOracleContractUpdated(
            _oracleId,
            prevContract,
            _newOracleContract
        );
    }

    function setOracleState(uint256 _oracleId, OracleState _state) internal {
        require(
            oracles[_oracleId].oracleContract != address(0),
            "ERROR:QUC-011:ORACLE_DOES_NOT_EXIST"
        );
        oracles[_oracleId].state = _state;
        emit LogOracleSetState(_oracleId, _state);
    }

    function approveOracle(uint256 _oracleId) external override onlyInstanceOperator {
        setOracleState(_oracleId, OracleState.Approved);
    }

    function pauseOracle(uint256 _oracleId) external override onlyInstanceOperator {
        setOracleState(_oracleId, OracleState.Paused);
    }

    function disapproveOracle(uint256 _oracleId) external override onlyInstanceOperator {
        setOracleState(_oracleId, OracleState.Proposed);
    }

    /* Oracle Request */
    // 1->1
    function request(
        bytes32 _bpKey,
        bytes calldata _input,
        string calldata _callbackMethodName,
        address _callbackContractAddress,
        uint256 _responsibleOracleId
    ) 
        external 
        override 
        onlyPolicyFlow("Query") 
        returns (uint256 _requestId) 
    {
        // todo: validate

        _requestId = oracleRequests.length;
        oracleRequests.push();

        // todo: get token from product

        OracleRequest storage req = oracleRequests[_requestId];
        req.bpKey = _bpKey;
        req.data = _input;
        req.callbackMethodName = _callbackMethodName;
        req.callbackContractAddress = _callbackContractAddress;
        req.responsibleOracleId = _responsibleOracleId;
        req.createdAt = block.timestamp;

        IOracle(oracles[_responsibleOracleId].oracleContract).request(
            _requestId,
            _input
        );

        emit LogOracleRequested(_bpKey, _requestId, _responsibleOracleId);
    }

    /* Oracle Response */
    function respond(
        uint256 _requestId,
        address _responder,
        bytes calldata _data
    ) external override onlyOracleService isResponsibleOracle(_requestId, _responder) {
        OracleRequest storage req = oracleRequests[_requestId];

        (bool status, ) =
            req.callbackContractAddress.call(
                abi.encodeWithSignature(
                    string(
                        abi.encodePacked(
                            req.callbackMethodName,
                            "(uint256,bytes32,bytes)"
                        )
                    ),
                    _requestId,
                    req.bpKey,
                    _data
                )
            );

        // todo: send reward

        emit LogOracleResponded(req.bpKey, _requestId, _responder, status);
    }

    function getOracleRequestCount() public view returns (uint256 _count) {
        return oracleRequests.length;
    }

    function getOracleCount() external override view returns (uint256) {
        return oracleCount;
    }

}
