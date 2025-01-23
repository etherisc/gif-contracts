// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

// NEU: mit Chainlink Funktion

import "./strings.sol";
import "./AyiiClf.sol";

// import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@etherisc/gif-interface/contracts/components/Oracle.sol";

contract AyiiOracle is Oracle {
    using strings for bytes32;

    AyiiClf public ayiiClf;
    modifier onlyAyiiClf() {
        require(
            _msgSender() == address(ayiiClf),
            "ERROR:AYII-001:ACCESS_DENIED"
        );
        _;
    }

    mapping(bytes32 /* Chainlink request ID */ => uint256 /* GIF request ID */)
        public gifRequests;

    event LogAyiiRequest(uint256 requestId, bytes32 chainlinkRequestId);

    event LogAyiiFulfill(
        uint256 requestId,
        bytes32 chainlinkRequestId,
        bytes response
    );

    constructor(bytes32 _name, address _registry) Oracle(_name, _registry) {
        // NOOP
    }

    function setClfGateWay(address _ayiiClf) external onlyOwner {
        ayiiClf = AyiiClf(_ayiiClf);
    }

    function request(
        uint256 gifRequestId,
        bytes calldata input
    ) external override onlyQuery {
        require(
            address(ayiiClf) != address(0),
            "ERROR:AYII-002:GATEWAY_NOT_SET"
        );
        bytes32 chainlinkRequestId = ayiiClf.sendClfRequest(input);

        gifRequests[chainlinkRequestId] = gifRequestId;
        emit LogAyiiRequest(gifRequestId, chainlinkRequestId);
    }

    function fulfillClfRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) external onlyAyiiClf {
        uint256 gifRequest = gifRequests[requestId];
        if (gifRequest == 0) {
            revert("ERROR:AYII-003:UNEXPECTED_REQUEST_ID");
        }
        _respond(gifRequest, response);

        delete gifRequests[requestId];
        emit LogAyiiFulfill(gifRequest, requestId, response);
    }

    function cancel(uint256 requestId) external override onlyQuery {
        // not implemented
    }
}
