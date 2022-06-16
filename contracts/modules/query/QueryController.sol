// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./QueryStorageModel.sol";
import "./IQueryController.sol";
import "../access/IAccess.sol";
import "../ComponentController.sol";
import "../../shared/ModuleController.sol";
import "@gif-interface/contracts/IOracle.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract QueryController is IQueryController, QueryStorageModel, ModuleController {
    bytes32 public constant NAME = "QueryController";



    modifier isResponsibleOracle(uint256 _requestId, address _responder) {
        // TODO cleanup/refactor, 
        // add getOracle to componentcontroller? 
        // that could then do require and conversion to ioracle internally
        OracleRequest memory oraclReq = oracleRequests[_requestId];
        uint256 respOraclId = oraclReq.responsibleOracleId;

        IComponent cmp = component().getComponent(respOraclId);
        require(cmp.getType() == 2, "ERROR:QUC-00y:COMPONENT_NOT_ORACLE");
        IOracle oracle = IOracle(address(cmp));

        require(
            // oracles[oracleRequests[_requestId].responsibleOracleId]
            //     .oracleContract == _responder,
            address(oracle) == _responder,
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
        Ownable oracle = Ownable(_oracleContract);
        bytes32 opRole = access().oracleProviderRole();
        address opAddress = oracle.owner();

        // check that oracle provider has the permission to propolse
        require(
            access().hasRole(opRole, opAddress), 
            "ERROR:QUC-002:ORACLE_PROVIDER_ROLE_MISSING"
        );

        // check that the oracle has not yet been proposed in the past
        require(
            oracleIdByAddress[_oracleContract] == 0,
            "ERROR:QUC-003:ORACLE_ALREADY_EXISTS"
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
        Ownable oracle = Ownable(_newOracleContract);

        // check that oracle provider has the permission to propose
        require(
            access().hasRole(
                access().oracleProviderRole(), 
                oracle.owner()), 
            "ERROR:QUC-004:ORACLE_PROVIDER_ROLE_MISSING");

        // check that the oracle has not yet been proposed in the past
        require(
            oracleIdByAddress[_newOracleContract] == 0,
            "ERROR:QUC-005:ORACLE_ALREADY_EXISTS"
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

        // TODO cleanup/refactor, 
        // add getOracle to componentcontroller? 
        // that could then do require and conversion to ioracle internally
        IComponent cmp = component().getComponent(_responsibleOracleId);
        require(cmp.getType() == 2, "ERROR:QUC-00x:COMPONENT_NOT_ORACLE");
        IOracle oracle = IOracle(address(cmp));

        // IOracle(oracles[_responsibleOracleId].oracleContract).request(
        oracle.request(
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
    ) 
        external override 
        onlyOracleService 
        isResponsibleOracle(_requestId, _responder) 
    {
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

    /* Lookup */
    function component() internal view returns (ComponentController) {
        return ComponentController(registry.getContract("Component"));
    }

    function access() internal view returns (IAccess) {
        return IAccess(registry.getContract("Access"));
    }
}
