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

    /**
     * @dev Internal function that sets the `_component` variable to the `ComponentController` contract address.
     *
     */
    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    /* Oracle Request */
    // request only works for active oracles
    // function call _getOracle reverts if oracle is not active
    // as a result all request call on oracles that are not active will revert
    /**
     * @dev Creates a new oracle request for a given process with the specified input data and callback information.
     * @param processId The ID of the process.
     * @param input The input data for the request.
     * @param callbackMethodName The name of the callback method to be called upon completion of the request.
     * @param callbackContractAddress The address of the contract to be called upon completion of the request.
     * @param responsibleOracleId The ID of the oracle responsible for handling the request.
     * @return requestId The ID of the newly created oracle request.
     * @notice This function emits 1 events: 
     * - LogOracleRequested
     */
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
    /**
     * @dev Responds to an oracle request with the given requestId, responder address, and data.
     * @param requestId The ID of the oracle request.
     * @param responder The address of the oracle responder.
     * @param data The data to be sent to the oracle contract.
     * @notice This function emits 1 events: 
     * - LogOracleResponded
     */
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

    /**
     * @dev Cancels an oracle request.
     * @param requestId The ID of the oracle request to be canceled.
     * @notice This function emits 1 events: 
     * - LogOracleCanceled
     */
    function cancel(uint256 requestId) 
        external override 
        onlyPolicyFlow("Query") 
    {
        OracleRequest storage oracleRequest = _oracleRequests[requestId];
        require(oracleRequest.createdAt > 0, "ERROR:QUC-030:REQUEST_ID_INVALID");
        delete _oracleRequests[requestId];
        emit LogOracleCanceled(requestId);
    }


    /**
     * @dev Returns the process ID associated with a given request ID.
     * @param requestId The ID of the request to retrieve the process ID for.
     * @return processId The process ID associated with the given request ID.
     */
    function getProcessId(uint256 requestId)
        external
        view
        returns(bytes32 processId)
    {
        OracleRequest memory oracleRequest = _oracleRequests[requestId];
        require(oracleRequest.createdAt > 0, "ERROR:QUC-040:REQUEST_ID_INVALID");
        return oracleRequest.processId;
    }


    /**
     * @dev Returns the number of oracle requests made.
     * @return _count The number of oracle requests made.
     */
    function getOracleRequestCount() public view returns (uint256 _count) {
        return _oracleRequests.length;
    }

    /**
     * @dev Returns the Oracle component with the specified ID.
     * @param id The ID of the Oracle component to retrieve.
     * @return oracle The Oracle component retrieved.
     *
     * Throws a 'COMPONENT_NOT_ORACLE' error if the component with the specified ID is not an Oracle component.
     * Throws an 'ORACLE_NOT_ACTIVE' error if the retrieved Oracle component is not in an active state.
     */
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
