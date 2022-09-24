// SPDX-License-Identifier: MIT

/*
 * Deployed at 0xF64f1Dbf36b36B52138054C76496A97d38280671 on Avax Mainnet.
 * Parameters: Chainlink Token on Avax Mainnet = 0x5947BB275c521040051D82396192181b413227A3
 * Chainlink Operator (Etherisc) on Avax Mainnet = 0x7178a8Cad2fa94ff308c5dD5Aba4dbe3393D3c47
 * 
 */

pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "./strings.sol";

contract AyiiOracle is ChainlinkClient 
{
    using strings for bytes32;
    using Chainlink for Chainlink.Request;

    uint256 public payment;

    event LogAyiiRequest(bytes32 chainlinkRequestId);
    
    event LogAyiiFulfill(
        bytes32 chainlinkRequestId, 
        bytes32 projectId,
        bytes32 uaiId,
        bytes32 cropId,
        uint256 aaay
    );


    function updateRequestDetails(
        address _chainLinkToken,
        address _chainLinkOperator
    ) 
        public 
    {
        if (_chainLinkToken != address(0)) { setChainlinkToken(_chainLinkToken); }
        if (_chainLinkOperator != address(0)) { setChainlinkOracle(_chainLinkOperator); }
        
        payment = 0;
    }

    function request(bytes32 jobId, bytes32 projectId, bytes32 uaiId, bytes32 cropId)
        external
    {
        Chainlink.Request memory request_ = buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );

        request_.add("projectId", projectId.toB32String());
        request_.add("uaiId", uaiId.toB32String());
        request_.add("cropId", cropId.toB32String());

        bytes32 chainlinkRequestId = sendChainlinkRequest(request_, payment);

        emit LogAyiiRequest(chainlinkRequestId);
    }

    function fulfill(
        bytes32 chainlinkRequestId, 
        bytes32 projectId, 
        bytes32 uaiId, 
        bytes32 cropId, 
        uint256 aaay
    )
        public recordChainlinkFulfillment(chainlinkRequestId) 
    {
        emit LogAyiiFulfill(chainlinkRequestId, projectId, uaiId, cropId, aaay);
    }

}

