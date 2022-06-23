// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "../shared/CoreController.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/components/IOracle.sol";
import "@gif-interface/contracts/modules/IQuery.sol";


contract QueryController is 
    IQuery, 
    CoreController
{
    // bytes32 public constant NAME = "QueryController";

    OracleRequest[] public oracleRequests;

    modifier onlyOracleService() {
        require(
            _msgSender() == _getContractAddress("OracleService"),
            "ERROR:CRC-004:NOT_ORACLE_SERVICE"
        );
        _;
    }

    modifier onlyResponsibleOracle(uint256 requestId, address responder) {
        OracleRequest memory oracleRequest = oracleRequests[requestId];
        uint256 oracleId = oracleRequest.responsibleOracleId;

        require(
            address(_getOracle(oracleId)) == responder,
            "ERROR:QUC-001:NOT_RESPONSIBLE_ORACLE"
        );
        _;
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

        _getOracle(_responsibleOracleId).request(
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
        onlyResponsibleOracle(_requestId, _responder) 
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

    function _getOracle(uint256 id) internal view returns (IOracle oracle) {
        IComponent cmp = _component().getComponent(id);
        require(cmp.isOracle(), "ERROR:QUC-002:COMPONENT_NOT_ORACLE");
        oracle = IOracle(address(cmp));
    }

    function _component() internal view returns (ComponentController) {
        return ComponentController(_getContractAddress("Component"));
    }
}
