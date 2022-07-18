// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IOracle.sol";
import "@etherisc/gif-interface/contracts/modules/IQuery.sol";


contract QueryController is 
    IQuery, 
    CoreController
{
    OracleRequest[] public oracleRequests;

    modifier onlyOracleService() {
        require(
            _msgSender() == _getContractAddress("OracleService"),
            "ERROR:CRC-001:NOT_ORACLE_SERVICE"
        );
        _;
    }

    modifier onlyResponsibleOracle(uint256 requestId, address responder) {
        OracleRequest memory oracleRequest = oracleRequests[requestId];

        require(
            oracleRequest.createdAt > 0,
            "ERROR:QUC-002:INVALID_REQUEST_ID"
        );

        uint256 oracleId = oracleRequest.responsibleOracleId;
        address oracleAddress = address(_getOracle(oracleId));
        require(
            oracleAddress == responder,
            "ERROR:QUC-003:NOT_RESPONSIBLE_ORACLE"
        );
        _;
    }

    /* Oracle Request */
    // 1->1
    function request(
        bytes32 processId,
        bytes calldata input,
        string calldata callbackMethodName,
        address callbackContractAddress,
        uint256 responsibleOracleId
    ) 
        external 
        override 
        onlyPolicyFlow("Query") 
        returns (uint256 requestId) 
    {
        // TODO: validate

        requestId = oracleRequests.length;
        oracleRequests.push();

        // TODO: get token from product

        OracleRequest storage req = oracleRequests[requestId];
        req.processId = processId;
        req.data = input;
        req.callbackMethodName = callbackMethodName;
        req.callbackContractAddress = callbackContractAddress;
        req.responsibleOracleId = responsibleOracleId;
        req.createdAt = block.timestamp;

        _getOracle(responsibleOracleId).request(
            requestId,
            input
        );

        emit LogOracleRequested(processId, requestId, responsibleOracleId);
    }

    /* Oracle Response */
    function respond(
        uint256 requestId,
        address responder,
        bytes calldata data
    ) 
        external override 
        onlyOracleService 
        onlyResponsibleOracle(requestId, responder) 
    {
        OracleRequest storage req = oracleRequests[requestId];
        string memory functionSignature = string(
            abi.encodePacked(
                req.callbackMethodName,
                "(uint256,bytes32,bytes)"
            ));
        bytes32 processId = req.processId;

        (bool success, ) =
            req.callbackContractAddress.call(
                abi.encodeWithSignature(
                    functionSignature,
                    requestId,
                    processId,
                    data
                )
            );

        require(success, "ERROR:QUC-004:UNSUCCESSFUL_PRODUCT_CALLBACK");
        delete oracleRequests[requestId];

        // TODO implement reward payment

        emit LogOracleResponded(processId, requestId, responder, success);
    }

    function getOracleRequestCount() public view returns (uint256 _count) {
        return oracleRequests.length;
    }

    function _getOracle(uint256 id) internal view returns (IOracle oracle) {
        IComponent cmp = _component().getComponent(id);
        require(cmp.isOracle(), "ERROR:QUC-005:COMPONENT_NOT_ORACLE");
        oracle = IOracle(address(cmp));
    }

    function _component() internal view returns (ComponentController) {
        return ComponentController(_getContractAddress("Component"));
    }
}
