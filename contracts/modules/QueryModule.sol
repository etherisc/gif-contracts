// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "./ComponentController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IOracle.sol";
import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceService.sol";


contract QueryModule is 
    IQuery, 
    CoreController
{
    ComponentController private _component;
    OracleRequest[] private _oracleRequests;

    modifier onlyOracleService() {
        require(
            _msgSender() == _getContractAddress("OracleService"),
            "ERROR:CRC-001:NOT_ORACLE_SERVICE"
        );
        _;
    }

    modifier onlyResponsibleOracle(uint256 requestId, address responder) {
        OracleRequest memory oracleRequest = _oracleRequests[requestId];

        require(
            oracleRequest.createdAt > 0,
            "ERROR:QUC-002:REQUEST_ID_INVALID"
        );

        uint256 oracleId = oracleRequest.responsibleOracleId;
        address oracleAddress = address(_getOracle(oracleId));
        require(
            oracleAddress == responder,
            "ERROR:QUC-003:ORACLE_NOT_RESPONSIBLE"
        );
        _;
    }

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    /* Oracle Request */
    // request only works for active oracles
    // function call _getOracle reverts if oracle is not active
    // as a result all request call on oracles that are not active will revert
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
        uint256 componentId = _component.getComponentId(callbackContractAddress);
        require(
            _component.isProduct(componentId),
            "ERROR:QUC-010:CALLBACK_ADDRESS_IS_NOT_PRODUCT"
        );
        
        requestId = _oracleRequests.length;
        _oracleRequests.push();

        // TODO: get token from product

        OracleRequest storage req = _oracleRequests[requestId];
        req.processId = processId;
        req.data = input;
        req.callbackMethodName = callbackMethodName;
        req.callbackContractAddress = callbackContractAddress;
        req.responsibleOracleId = responsibleOracleId;
        req.createdAt = block.timestamp; // solhint-disable-line

        _getOracle(responsibleOracleId).request(
            requestId,
            input
        );

        emit LogOracleRequested(processId, requestId, responsibleOracleId);
    }

    /* Oracle Response */
    // respond only works for active oracles
    // modifier onlyResponsibleOracle contains a function call to _getOracle 
    // which reverts if oracle is not active
    // as a result, all response calls by oracles that are not active will revert
    function respond(
        uint256 requestId,
        address responder,
        bytes calldata data
    ) 
        external override 
        onlyOracleService 
        onlyResponsibleOracle(requestId, responder) 
    {
        OracleRequest storage req = _oracleRequests[requestId];
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

        require(success, "ERROR:QUC-020:PRODUCT_CALLBACK_UNSUCCESSFUL");
        delete _oracleRequests[requestId];

        // TODO implement reward payment

        emit LogOracleResponded(processId, requestId, responder, success);
    }

    function cancel(uint256 requestId) 
        external override 
        onlyPolicyFlow("Query") 
    {
        OracleRequest storage oracleRequest = _oracleRequests[requestId];
        require(oracleRequest.createdAt > 0, "ERROR:QUC-030:REQUEST_ID_INVALID");
        delete _oracleRequests[requestId];
        emit LogOracleCanceled(requestId);
    }


    function getProcessId(uint256 requestId)
        external
        view
        returns(bytes32 processId)
    {
        OracleRequest memory oracleRequest = _oracleRequests[requestId];
        require(oracleRequest.createdAt > 0, "ERROR:QUC-040:REQUEST_ID_INVALID");
        return oracleRequest.processId;
    }


    function getOracleRequestCount() public view returns (uint256 _count) {
        return _oracleRequests.length;
    }

    function _getOracle(uint256 id) internal view returns (IOracle oracle) {
        IComponent cmp = _component.getComponent(id);
        oracle = IOracle(address(cmp));

        require(
            _component.getComponentType(id) == IComponent.ComponentType.Oracle, 
            "ERROR:QUC-041:COMPONENT_NOT_ORACLE"
        );

        require(
            _component.getComponentState(id) == IComponent.ComponentState.Active, 
            "ERROR:QUC-042:ORACLE_NOT_ACTIVE"
        );
    }
}
