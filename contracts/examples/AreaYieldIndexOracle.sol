// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";

import "@etherisc/gif-interface/contracts/components/Oracle.sol";

contract ZAreaYieldIndexOracle is 
    // Ownable, Oracle, ChainlinkClient // mzi ownable is through oracle -> component
    Oracle, ChainlinkClient 
{
    using Chainlink for Chainlink.Request;

    mapping(bytes32 /* Chainlink request ID */ => uint256 /* GIF request ID */) public gifRequests;
    bytes32 public jobId;
    uint256 public payment;

    event LogAYIRequest(uint256 indexed requestId, bytes32 indexed chainlinkRequestId);
    event LogAYIFulfill(uint256 indexed requestId, bytes32 indexed chainlinkRequestId, bytes data);

    constructor(
        bytes32 _name,
        address _registry,
        address _linkToken,
        address _chainLinkOracle,
        bytes32 _jobId,
        uint256 _payment
    )
        Oracle(_name, _registry)
    {
        if (_linkToken == address(0)) {
            setPublicChainlinkToken();
        } else {
            setChainlinkToken(_linkToken);
        }

        setChainlinkOracle(_chainLinkOracle);
        jobId = _jobId;
        payment = _payment;
    }

    function request(uint256 _gifRequestId, bytes calldata _input)
        external
        override
        onlyQuery
    {
        Chainlink.Request memory req = buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );
        req.addBytes("UAI", _input);

        bytes32 chainlinkRequestId = sendChainlinkRequest(req, payment);
        gifRequests[chainlinkRequestId] = _gifRequestId;
        emit LogAYIRequest(_gifRequestId, chainlinkRequestId);
    }

    function fulfill(bytes32 _chainlinkRequestId, bytes memory _data)
        public // recordChainlinkFulfillment(_chainlinkRequestId) /* temporarily disabled to support a workaround for the `trigger resolution` test case. */
    {
        uint256 gifRequest = gifRequests[_chainlinkRequestId];
        _respond(gifRequest, _data);
        delete gifRequests[_chainlinkRequestId];
        emit LogAYIFulfill(gifRequest, _chainlinkRequestId, _data);
    }

    // function _updateRequestDetails(
    //     address _oracle,
    //     bytes32 _jobId,
    //     uint256 _payment
    // ) private {
    //     setChainlinkOracle(_oracle);
    //     jobId = _jobId;
    //     payment = _payment;
    // }

    function cancelRequest(
        bytes32 _requestId,
        uint256 _payment,
        bytes4 _callbackFunctionId,
        uint256 _expiration
    )
        public
        onlyOwner()
    {
        cancelChainlinkRequest(_requestId, _payment, _callbackFunctionId, _expiration);
    }

    function getChainlinkOperator() external view returns(address operator) {
        operator = chainlinkOracleAddress();
    }
}

