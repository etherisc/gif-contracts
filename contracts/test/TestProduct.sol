// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

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
    uint256 private _testOracleId;
    uint256 private _testRiskpoolId;

    bytes32 [] private _applications;
    bytes32 [] private _policies;
    uint256 private _claims;

    mapping(bytes32 => uint256) private _policyIdToClaimId;
    mapping(bytes32 => uint256) private _policyIdToPayoutId;

    event LogTestProductFundingReceived(address sender, uint256 amount);
    event LogTestOracleCallbackReceived(uint256 requestId, bytes32 policyId, bytes response);

    /**
     * @dev Constructor function for creating a new instance of the Product contract.
     * @param productName The name of the product.
     * @param tokenAddress The address of the token used for the product.
     * @param capitalOwner The address of the capital owner.
     * @param oracleId The ID of the oracle used for the product.
     * @param riskpoolId The ID of the riskpool used for the product.
     * @param registryAddress The address of the registry contract.
     */
    constructor(
        bytes32 productName,
        address tokenAddress,
        address capitalOwner,
        uint256 oracleId,
        uint256 riskpoolId,
        address registryAddress
    )
        Product(productName, tokenAddress, POLICY_FLOW, riskpoolId, registryAddress)
    {
        require(tokenAddress != address(0), "ERROR:TI-2:TOKEN_ADDRESS_ZERO");
        _capitalOwner = capitalOwner;
        _testOracleId = oracleId;
        _testRiskpoolId = riskpoolId;
    }

    /**
     * @dev Allows a policy holder to apply for a new insurance policy by submitting an application with the specified premium, sum insured, metadata and application data.
     * @param premium The amount of premium to be paid by the policy holder.
     * @param sumInsured The sum insured for the new policy.
     * @param metaData Additional metadata associated with the application.
     * @param applicationData Additional application data.
     * @return processId The unique identifier of the new policy application process.
     */
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

        processId = _newApplication(
            policyHolder,
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

    /**
     * @dev Creates a new insurance application and underwrites it if possible.
     * @param policyHolder The address of the policy holder.
     * @param premium The amount of premium paid by the policy holder.
     * @param sumInsured The amount of coverage requested by the policy holder.
     * @param metaData Additional metadata associated with the application.
     * @param applicationData The application data submitted by the policy holder.
     * @return processId The identifier of the new insurance application.
     */
    function applyForPolicy(
        address payable policyHolder,
        uint256 premium, 
        uint256 sumInsured,
        bytes calldata metaData,
        bytes calldata applicationData
    ) 
        external 
        payable 
        returns (bytes32 processId) 
    {
        processId = _newApplication(
            policyHolder,
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


    /**
     * @dev Creates a new insurance application.
     * @param premium The amount of premium to be paid for the insurance policy.
     * @param sumInsured The amount of coverage for the insurance policy.
     * @param metaData Metadata to be associated with the application.
     * @param applicationData Additional data related to the application.
     * @return processId The unique identifier for the new application process.
     */
    function newAppliation(
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

        processId = _newApplication(
            policyHolder,
            premium, 
            sumInsured,
            metaData,
            applicationData);

        _applications.push(processId);
    }


    /**
     * @dev Revokes a process identified by its processId. Only the policy holder can revoke a process.
     * @param processId The unique identifier of the process to be revoked.
     */
    function revoke(bytes32 processId) external onlyPolicyHolder(processId) { 
        _revoke(processId);
    }

    /**
     * @dev Declines a specific process by its ID.
     * @param processId The ID of the process to be declined.
     */
    function decline(bytes32 processId) external onlyOwner { 
        _decline(processId);
    }

    /**
     * @dev Underwrites a policy for a given process ID.
     * @param processId The ID of the process to underwrite a policy for. 
     */
    function underwrite(bytes32 processId) external onlyOwner { 
        bool success = _underwrite(processId);
        if (success) {
            _policies.push(processId);
        }
    }

    /**
     * @dev Collects the premium for a specific policy.
     * @param policyId The ID of the policy for which the premium will be collected.
     * @return success A boolean indicating whether the premium collection was successful.
     * @return fee The amount of fee collected by the insurer.
     * @return netPremium The net amount of premium collected by the insurer after deducting the fee.
     */
    function collectPremium(bytes32 policyId) 
        external onlyOwner
        returns(bool success, uint256 fee, uint256 netPremium)
    {
        (success, fee, netPremium) = _collectPremium(policyId);
    }

    /**
     * @dev Collects the premium for a specific policy.
     * @param policyId The unique identifier of the policy.
     * @param amount The amount of the premium to be collected.
     * @return success A boolean indicating whether the premium collection was successful.
     * @return fee The fee charged for collecting the premium.
     * @return netPremium The net amount of premium collected after deducting the fee.
     */
    function collectPremium(bytes32 policyId, uint256 amount) 
        external onlyOwner
        returns(bool success, uint256 fee, uint256 netPremium)
    {
        (success, fee, netPremium) = _collectPremium(policyId, amount);
    }

    /**
     * @dev Adjusts the premium and sum insured amounts for a given process ID.
     * @param processId The ID of the process to adjust.
     * @param expectedPremiumAmount The expected premium amount for the process.
     * @param sumInsuredAmount The sum insured amount for the process.
     */
    function adjustPremiumSumInsured(
        bytes32 processId,
        uint256 expectedPremiumAmount,
        uint256 sumInsuredAmount
    )
        external
    {
        _adjustPremiumSumInsured(processId, expectedPremiumAmount, sumInsuredAmount);
    }

    /**
     * @dev Expire a policy by its ID.
     * @param policyId The ID of the policy to expire.
     */
    function expire(bytes32 policyId) external onlyOwner {
        _expire(policyId);
    }

    /**
     * @dev Closes a policy with the given ID.
     * @param policyId The ID of the policy to be closed.
     */
    function close(bytes32 policyId) external onlyOwner {
        _close(policyId);
    }

    /**
     * @dev Allows a policy holder to submit a claim for a specific policy.
     * @param policyId The ID of the policy for which the claim is being submitted.
     * @param claimAmount The amount of the claim being submitted.
     * @return claimId The ID of the submitted claim.
     *
     * Increases the claims counter and creates a new claim application.
     * The oracle business logic will use the claims counter value to determine if the claim is linked to a loss event or not.
     * The function also requests a response to the greeting via oracle call.
     */
    function submitClaim(bytes32 policyId, uint256 claimAmount) 
        external
        onlyPolicyHolder(policyId)
        returns(uint256 claimId)
    {

        // increase claims counter
        // the oracle business logic will use this counter value 
        // to determine if the claim is linked to a loss event or not
        _claims++;
        
        // claim application
        claimId = _newClaim(policyId, claimAmount, "");
        _policyIdToClaimId[policyId] = claimId;

        // Request response to greeting via oracle call
        bool immediateResponse = true;
        bytes memory queryData = abi.encode(_claims, immediateResponse);
        _request(
            policyId,
            queryData,
            ORACLE_CALLBACK_METHOD_NAME,
            _testOracleId
        );
    }

    /**
     * @dev Allows a policy holder to submit a claim without the need for an oracle.
     * @param policyId The ID of the policy for which the claim is being submitted.
     * @param claimAmount The amount being claimed by the policy holder.
     * @return claimId The ID of the claim created.
     */
    function submitClaimNoOracle(bytes32 policyId, uint256 claimAmount) 
        external
        onlyPolicyHolder(policyId)
        returns(uint256 claimId)
    {

        // increase claims counter
        // the oracle business logic will use this counter value 
        // to determine if the claim is linked to a loss event or not
        _claims++;
        
        // claim application
        claimId = _newClaim(policyId, claimAmount, "");
        _policyIdToClaimId[policyId] = claimId;
    }
    
    /**
     * @dev Submits a claim for a specific policy with a deferred response from the oracle.
     * Increases the claims counter and creates a new claim application.
     * Then, requests a response from the oracle via an external call with encoded query data.
     * @param policyId The ID of the policy the claim is being made against.
     * @param claimAmount The amount of the claim being made.
     * @return claimId The ID of the newly created claim.
     * @return requestId The ID of the oracle request made to retrieve the response.
     */
    function submitClaimWithDeferredResponse(bytes32 policyId, uint256 claimAmount) 
        external
        onlyPolicyHolder(policyId)
        returns(uint256 claimId, uint256 requestId)
    {

        // increase claims counter
        // the oracle business logic will use this counter value 
        // to determine if the claim is linked to a loss event or not
        _claims++;
        
        // claim application
        claimId = _newClaim(policyId, claimAmount, "");
        _policyIdToClaimId[policyId] = claimId;

        // Request response to greeting via oracle call
        bool immediateResponse = false;
        bytes memory queryData = abi.encode(_claims, immediateResponse);
        requestId = _request(
            policyId,
            queryData,
            ORACLE_CALLBACK_METHOD_NAME,
            _testOracleId
        );
    }

    /**
     * @dev Confirms the amount to be paid out for a specific claim.
     * @param policyId The ID of the policy the claim belongs to.
     * @param claimId The ID of the claim to be confirmed.
     * @param confirmedAmount The amount to be paid out for the claim.
     */
    function confirmClaim(
        bytes32 policyId, 
        uint256 claimId, 
        uint256 confirmedAmount
    ) 
        external
        onlyOwner
    {
        _confirmClaim(policyId, claimId, confirmedAmount);
    }

    /**
     * @dev Allows the owner of the contract to decline a claim.
     * @param policyId The ID of the policy related to the claim.
     * @param claimId The ID of the claim to be declined.
     */
    function declineClaim(
        bytes32 policyId, 
        uint256 claimId
    ) 
        external
        onlyOwner
    {
        _declineClaim(policyId, claimId);
    }

    /**
     * @dev Closes a specific claim for a given policy.
     * @param policyId The ID of the policy the claim belongs to.
     * @param claimId The ID of the claim to be closed.
     */
    function closeClaim(
        bytes32 policyId, 
        uint256 claimId
    ) 
        external
        onlyOwner
    {
        _closeClaim(policyId, claimId);
    }

    /**
     * @dev Creates a new payout for a specific policy and claim.
     * @param policyId The ID of the policy associated with the payout.
     * @param claimId The ID of the claim associated with the payout.
     * @param payoutAmount The amount of the payout to be created.
     * @return payoutId The ID of the newly created payout.
     */
    function createPayout(
        bytes32 policyId, 
        uint256 claimId, 
        uint256 payoutAmount
    ) 
        external
        onlyOwner
        returns(uint256 payoutId)
    {
        payoutId = _newPayout(
            policyId, 
            claimId, 
            payoutAmount, 
            abi.encode(0));
            
        _processPayout(policyId, payoutId);
    }

    /**
     * @dev Creates a new payout for a claim under a policy.
     * @param policyId The ID of the policy.
     * @param claimId The ID of the claim.
     * @param payoutAmount The amount to be paid out for the claim.
     * @return payoutId The ID of the newly created payout.
     */
    function newPayout(
        bytes32 policyId, 
        uint256 claimId, 
        uint256 payoutAmount
    ) 
        external
        onlyOwner
        returns(uint256 payoutId)
    {
        payoutId = _newPayout(
            policyId, 
            claimId, 
            payoutAmount, 
            abi.encode(0));
    }

    /**
     * @dev Processes a payout for a specific policy.
     * @param policyId The ID of the policy to process the payout for.
     * @param payoutId The ID of the payout to process.
     */
    function processPayout(
        bytes32 policyId, 
        uint256 payoutId
    ) 
        external
        onlyOwner
    {
        _processPayout(policyId, payoutId);
    }

    /**
     * @dev This function is called by the oracle to provide the response data for a specified policy ID and request ID.
     * @param requestId The ID of the request made by the oracle.
     * @param policyId The ID of the policy associated with the oracle request.
     * @param responseData The response data provided by the oracle.
     *
     * Emits a LogTestOracleCallbackReceived event with the provided request ID, policy ID, and response data.
     *
     * Decodes the response data to obtain the isLossEvent boolean value and the claim ID associated with the policy ID.
     *
     * If the event is a loss event, retrieves the policy and claim information, confirms the claim, creates a payout record, and processes the payout.
     *
     * If the event is not a loss event, declines the claim.
     * @notice This function emits 1 events: 
     * - LogTestOracleCallbackReceived
     */
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
            _getApplication(policyId);

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

    /**
     * @dev Returns the claim ID associated with a given policy ID.
     * @param policyId The policy ID for which the claim ID is requested.
     * @return The claim ID associated with the given policy ID.
     */
    function getClaimId(bytes32 policyId) external view returns (uint256) { return _policyIdToClaimId[policyId]; }
    /**
     * @dev Returns the payout ID associated with a given policy ID.
     * @param policyId The ID of the policy.
     * @return The payout ID associated with the given policy ID.
     */
    function getPayoutId(bytes32 policyId) external view returns (uint256) { return _policyIdToPayoutId[policyId]; }
    /**
     * @dev Returns the number of applications that have been submitted.
     * @return The number of applications as a uint256 value.
     */
    function applications() external view returns (uint256) { return _applications.length; }
    /**
     * @dev Returns the number of policies in the _policies array.
     * @return The length of the _policies array.
     */
    function policies() external view returns (uint256) { return _policies.length; }
    /**
     * @dev Returns the number of claims made by users.
     * @return _claims The total number of claims made by users.
     */
    function claims() external view returns (uint256) { return _claims; }
}