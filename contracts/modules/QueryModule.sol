// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "./ComponentController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IOracle.sol";
import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceService.sol";

/**
 * @dev The smart contract implements the "IQuery" interface and extends the "CoreController" contract.
 * The contract imports several external contracts from the "etherisc/gif-interface" repository, including "IComponent.sol", "IOracle.sol", "IQuery.sol", and "IInstanceService.sol".
 * It also imports two local contracts, "ComponentController.sol" and "CoreController.sol".
 * 
 * The contract defines a private variable `_component` of type "ComponentController" and an array `_oracleRequests` of type "OracleRequest[]".
 * 
 * The contract includes two modifiers:
 * 1. `onlyOracleService`: It requires that the caller must be the contract with the address specified by the "OracleService" contract address stored in the CoreController.
 * 2. `onlyResponsibleOracle`: It checks if the oracle specified by the `responder` address is responsible for the given `requestId`.
 * 
 * The contract provides the following functions:
 * - `_afterInitialize()`: Sets the `_component` variable to the address of the "ComponentController" contract. It is called after contract initialization and only during the initialization phase.
 * - `request()`: Allows the creation of a new oracle request with the specified parameters. It requires the caller to have the "Query" policy flow. The function validates the callback contract address to ensure it corresponds to a product. It creates a new oracle request in the `_oracleRequests` array, initializes its fields, and calls the `request()` function on the responsible oracle. It emits a `LogOracleRequested` event.
 * - `respond()`: Enables an oracle to respond to a specific oracle request. The caller must be the contract specified by the "OracleService" address. The function verifies that the responding oracle is responsible for the given request and then calls the callback method on the callback contract. It emits a `LogOracleResponded` event.
 * - `cancel()`: Cancels an oracle request with the given `requestId`. The caller must have the "Query" policy flow. It removes the request from the `_oracleRequests` array and emits a `LogOracleCanceled` event.
 * - `getProcessId()`: Returns the process ID associated with a given `requestId`.
 * - `getOracleRequestCount()`: Returns the number of oracle requests made.
 * - `_getOracle()`: Retrieves the Oracle component with the specified ID. It checks if the component is an Oracle component and if it is in an active state. If the checks pass, it returns the Oracle component.
 * 
 * The contract emits the following events:
 * 1. `LogOracleRequested`: Indicates the creation of a new oracle request and includes the process ID, request ID, and responsible oracle ID.
 * 2. `LogOracleResponded`: Indicates the response to an oracle request and includes the process ID, request ID, responder address, and success status.
 * 3. `LogOracleCanceled`: Indicates the cancellation of an oracle request and includes the request ID.
 */


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
