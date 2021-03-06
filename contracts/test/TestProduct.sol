// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";
import "@etherisc/gif-interface/contracts/services/IProductService.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceService.sol";
import "@etherisc/gif-interface/contracts/components/Product.sol";

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract TestProduct is 
    Product 
{
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";
    string public constant ORACLE_CALLBACK_METHOD_NAME = "oracleCallback";

    address private _capitalOwner;
    address private _feeOwner;
    uint256 private _testOracleId;
    uint256 private _testRiskpoolId;

    bytes32 [] private _applications;
    bytes32 [] private _policies;
    uint256 private _claims;

    mapping(bytes32 => uint256) private _policyIdToClaimId;
    mapping(bytes32 => uint256) private _policyIdToPayoutId;

    event LogTestProductFundingReceived(address sender, uint256 amount);
    event LogTestOracleCallbackReceived(uint256 requestId, bytes32 policyId, bytes response);

    constructor(
        bytes32 productName,
        address tokenAddress,
        address capitalOwner,
        address feeOwner, // TODO feeOwner not product specific, move to instance
        uint256 oracleId,
        uint256 riskpoolId,
        address registryAddress
    )
        Product(productName, tokenAddress, POLICY_FLOW, riskpoolId, registryAddress)
    {
        require(tokenAddress != address(0), "ERROR:TI-2:TOKEN_ADDRESS_ZERO");
        _capitalOwner = capitalOwner;
        _feeOwner = feeOwner;
        _testOracleId = oracleId;
        _testRiskpoolId = riskpoolId;
    }

    function applyForPolicy(
        uint256 premium, 
        uint256 sumInsured,
        bytes calldata metaData,
        bytes calldata applicationData
    ) 
        external 
        payable 
        returns (bytes32 processId) 
    {
        address payable policyHolder = payable(_msgSender());

        // Create and underwrite new application
        processId = keccak256(abi.encode(policyHolder, _policies));

        _newApplication(
            policyHolder,
            processId, 
            premium, 
            sumInsured,
            metaData,
            applicationData);

        _applications.push(processId);

        bool success = _underwrite(processId);
        if (success) {
            _policies.push(processId);
        }
    }

    function collectPremium(bytes32 policyId) 
        external 
        returns(bool success, uint256 fee, uint256 netPremium)
    {
        (success, fee, netPremium) = _collectPremium(policyId);
    }

    function collectPremium(bytes32 policyId, uint256 amount) 
        external 
        returns(bool success, uint256 fee, uint256 netPremium)
    {
        (success, fee, netPremium) = _collectPremium(policyId, amount);
    }

    function expire(bytes32 policyId) external onlyOwner {
        _expire(policyId);
    }

    function close(bytes32 policyId) external onlyOwner {
        _close(policyId);
    }

    function submitClaim(bytes32 policyId, uint256 claimAmount) 
        external
        onlyPolicyHolder(policyId)
    {

        // increase claims counter
        // the oracle business logic will use this counter value 
        // to determine if the claim is linked to a loss event or not
        _claims += 1;
        
        // claim application
        uint256 claimId = _newClaim(policyId, claimAmount, "");
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
            // get policy and claims info for oracle response
            IPolicy.Application memory application 
                = _getApplication(policyId);

            IPolicy.Claim memory claim 
                = _getClaim(policyId, claimId);

            // specify payout data
            uint256 confirmedAmount = claim.claimAmount;
            _confirmClaim(policyId, claimId, confirmedAmount);

            // create payout record
            uint256 payoutAmount = confirmedAmount;
            bytes memory payoutData = abi.encode(0);
            uint256 payoutId = _newPayout(policyId, claimId, payoutAmount, payoutData);
            _policyIdToPayoutId[policyId] = payoutId;

            _processPayout(policyId, payoutId);

            // TODO refactor to payout using erc-20 token
            // actual transfer of funds for payout of claim
            // failing requires not visible when called via .call in querycontroller
            // policyHolder.transfer(payoutAmount);
        } else {
            _declineClaim(policyId, claimId);
        }
    }

    function getClaimId(bytes32 policyId) external view returns (uint256) { return _policyIdToClaimId[policyId]; }
    function getPayoutId(bytes32 policyId) external view returns (uint256) { return _policyIdToPayoutId[policyId]; }
    function applications() external view returns (uint256) { return _applications.length; }
    function policies() external view returns (uint256) { return _policies.length; }
    function claims() external view returns (uint256) { return _claims; }
}