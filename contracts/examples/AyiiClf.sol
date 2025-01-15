// SPDX-License-Identifier: MIT

pragma solidity 0.8.2;

interface AyiiClf {
    function _sendRequest(
        bytes calldata input
    ) external returns (bytes32 requestId);
}
