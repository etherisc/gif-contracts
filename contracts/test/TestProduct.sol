// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@gif-interface/contracts/Product.sol";


contract TestProduct is Product {

    bytes32 public constant POLICY_FLOW = "PolicyFlowDefault";
    string public constant ORACLE_CALLBACK_METHOD_NAME = "oracleCallback";

    bytes32 private _testOracleType;
    uint256 private _testOracleId;
    uint256 private _policies;
    uint256 private _claims;

    mapping(bytes32 => address) private _policyIdToAddress;
    mapping(bytes32 => uint256) private _policyIdToClaimId;
    mapping(bytes32 => uint256) private _policyIdToPayoutId;

    constructor(
        address gifProductService,
        bytes32 productName,
        bytes32 oracleType,
        uint256 oracleId
    )
        Product(gifProductService, productName, POLICY_FLOW)
    {
        _testOracleType = oracleType;
        _testOracleId = oracleId;
    }

    function applyForPolicy() external payable returns (bytes32 policyId) {
        address payable policyHolder = payable(msg.sender);
        uint256 premium = msg.value;

        // Validate input parameters
        require(premium >= 0, "ERROR:TI-1:INVALID_PREMIUM");

        // Create and underwrite new application
        policyId = keccak256(abi.encode(policyHolder, _policies));
        _newApplication(policyId, abi.encode(premium, policyHolder));
        _underwrite(policyId);

        // Book keeping
        _policyIdToAddress[policyId] = policyHolder;
        _policies += 1;
    }

    function submitClaim(bytes32 policyId) external {
        // validations 
        // ensure claim is made by policy holder
        require(_policyIdToAddress[policyId] == msg.sender, "ERROR:TI-2:INVALID_POLICY_OR_HOLDER");
        // TODO ensure policy is in active state

        // increase claims counter
        // the oracle business logic will use this counter value 
        // to determine if the claim is linke to a loss event or not
        _claims += 1;

        // Request response to greeting via oracle call
        uint256 requestId = _request(
            policyId,
            abi.encode(_claims),
            ORACLE_CALLBACK_METHOD_NAME,
            _testOracleType,
            _testOracleId
        );
    }

    function oracleCallback(
        uint256 requestId, 
        bytes32 policyId, 
        bytes calldata response
    )
        external
        onlyOracle
    {
        // get oracle response data
        (bool isLossEvent) = abi.decode(response, (bool));

        // claim handling if there is a loss
        if (isLossEvent) {
            // get policy data for oracle response
            (uint256 premium, address payable policyHolder) = abi.decode(
                _getApplicationData(policyId), (uint256, address));

            // GIF claims and payout handling
            uint256 payoutAmount = 2 * premium;
            uint256 claimId = _newClaim(policyId, abi.encode(payoutAmount));
            uint256 payoutId = _confirmClaim(policyId, claimId, abi.encode(payoutAmount));
            _payout(policyId, payoutId, true, abi.encode(payoutAmount));

            _policyIdToClaimId[policyId] = claimId;
            _policyIdToPayoutId[policyId] = payoutId;

            // actual transfer of funds for payout of claim
            policyHolder.transfer(payoutAmount);
        }
        
        // policy only covers a single claims event
        _expire(policyId);
    }

    function getClaimId(bytes32 policyId) external view returns (uint256) { return _policyIdToClaimId[policyId]; }
    function getPayoutId(bytes32 policyId) external view returns (uint256) { return _policyIdToPayoutId[policyId]; }
    function policies() external view returns (uint256) { return _policies; }
    function claims() external view returns (uint256) { return _claims; }
}