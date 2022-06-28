// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@gif-interface/contracts/components/Product.sol";

contract TestProduct is 
    Product 
{
    bytes32 public constant POLICY_FLOW = "PolicyFlowDefault";
    string public constant ORACLE_CALLBACK_METHOD_NAME = "oracleCallback";

    uint256 private _testOracleId;
    uint256 private _policies;
    uint256 private _claims;

    mapping(bytes32 => address) private _policyIdToAddress;
    mapping(bytes32 => uint256) private _policyIdToClaimId;
    mapping(bytes32 => uint256) private _policyIdToPayoutId;

    event LogTestProductFundingReceived(address sender, uint256 amount);
    event LogTestOracleCallbackReceived(uint256 requestId, bytes32 policyId, bytes response);

    modifier onlyPolicyHolder(bytes32 policyId) {
        require(
            _msgSender() == _policyIdToAddress[policyId], 
            "ERROR:TI-2:INVALID_POLICY_OR_HOLDER"
        );
        _;
    }

    constructor(
        bytes32 productName,
        address registry,
        uint256 oracleId
    )
        Product(productName, POLICY_FLOW, registry)
    {
        _testOracleId = oracleId;
    }

    receive() external payable {
        emit LogTestProductFundingReceived(_msgSender(), msg.value);
    }

    function applyForPolicy() external payable returns (bytes32 policyId) {
        address payable policyHolder = payable(_msgSender());
        uint256 premium = msg.value;

        // Validate input parameters
        require(premium >= 0, "ERROR:TI-1:INVALID_PREMIUM");

        // Create and underwrite new application
        policyId = keccak256(abi.encode(policyHolder, _policies));
        // policyId = keccak256(abi.encode(policyHolder, block.timestamp));
        _newApplication(policyId, abi.encode(premium, policyHolder));
        _underwrite(policyId);

        // Book keeping
        _policyIdToAddress[policyId] = policyHolder;
        _policies += 1;
    }

    function expire(bytes32 policyId) 
        external
        onlyOwner
    {
        _expire(policyId);
    }

    function submitClaim(bytes32 policyId, uint256 payoutAmount) 
        external
        onlyPolicyHolder(policyId)
    {

        // increase claims counter
        // the oracle business logic will use this counter value 
        // to determine if the claim is linke to a loss event or not
        _claims += 1;
        
        // claim application
        bytes memory claimsData = abi.encode(payoutAmount);
        uint256 claimId = _newClaim(policyId, claimsData);
        _policyIdToClaimId[policyId] = claimId;

        // Request response to greeting via oracle call
        bytes memory queryData = abi.encode(_claims);
        uint256 requestId = _request(
            policyId,
            queryData,
            ORACLE_CALLBACK_METHOD_NAME,
            _testOracleId
        );
    }

    function oracleCallback(
        uint256 requestId, 
        bytes32 policyId, 
        bytes calldata responseData
    )
        external
        onlyOracle
    {
        emit LogTestOracleCallbackReceived(requestId, policyId, responseData);

        // get oracle response data
        (bool isLossEvent) = abi.decode(responseData, (bool));
        uint256 claimId = _policyIdToClaimId[policyId];

        // claim handling if there is a loss
        if (isLossEvent) {
            // get policy and claims data for oracle response
            (uint256 premium, address payable policyHolder) = abi.decode(
                _getApplicationData(policyId), (uint256, address));

            (uint256 payoutAmount) = abi.decode(
                _getClaimData(policyId, claimId), (uint256));

            // specify payout data
            bytes memory payoutData = abi.encode(payoutAmount);
            uint256 payoutId = _confirmClaim(policyId, claimId, payoutData);
            _policyIdToPayoutId[policyId] = payoutId;

            // create payout record
            bool fullPayout = true;
            _payout(policyId, payoutId, fullPayout, payoutData);

            // actual transfer of funds for payout of claim
            // failing requires not visible when called via .call in querycontroller
            policyHolder.transfer(payoutAmount);
        } else {
            _declineClaim(policyId, claimId);
        }
    }

    function getClaimId(bytes32 policyId) external view returns (uint256) { return _policyIdToClaimId[policyId]; }
    function getPayoutId(bytes32 policyId) external view returns (uint256) { return _policyIdToPayoutId[policyId]; }
    function policies() external view returns (uint256) { return _policies; }
    function claims() external view returns (uint256) { return _claims; }
}