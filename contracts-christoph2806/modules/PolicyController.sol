// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";
import "./ComponentController.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract PolicyController is 
    IPolicy, 
    CoreController
{
    // bytes32 public constant NAME = "PolicyController";

    // Metadata
    mapping(bytes32 /* processId */ => Metadata) public metadata;

    // Applications
    mapping(bytes32 /* processId */ => Application) public applications;

    // Policies
    mapping(bytes32 /* processId */ => Policy) public policies;

    // Claims
    mapping(bytes32 /* processId */ => mapping(uint256 /* claimId */ => Claim)) public claims;

    // Payouts
    mapping(bytes32 /* processId */ => mapping(uint256 /* payoutId */ => Payout)) public payouts;
    mapping(bytes32 /* processId */ => uint256) public payoutCount;

    // counter for assigned processIds, used to ensure unique processIds
    uint256 private _assigendProcessIds;

    ComponentController private _component;

    /**
     * @dev Internal function that sets the _component variable to the address of the ComponentController contract.
     *
     */
    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    /* Metadata */
    /**
     * @dev Creates a new policy flow for a given owner and product.
     * @param owner The address of the owner of the policy flow.
     * @param productId The ID of the product associated with the policy flow.
     * @param data Additional data associated with the policy flow.
     * @return processId The ID of the newly created policy flow.
     * @notice This function emits 1 events: 
     * - LogMetadataCreated
     */
    function createPolicyFlow(
        address owner,
        uint256 productId,
        bytes calldata data
    )
        external override
        onlyPolicyFlow("Policy")
        returns(bytes32 processId)
    {
        require(owner != address(0), "ERROR:POL-001:INVALID_OWNER");

        require(_component.isProduct(productId), "ERROR:POL-002:INVALID_PRODUCT");
        require(_component.getComponentState(productId) == IComponent.ComponentState.Active, "ERROR:POL-003:PRODUCT_NOT_ACTIVE");
        
        processId = _generateNextProcessId();
        Metadata storage meta = metadata[processId];
        require(meta.createdAt == 0, "ERROR:POC-004:METADATA_ALREADY_EXISTS");

        meta.owner = owner;
        meta.productId = productId;
        meta.state = PolicyFlowState.Started;
        meta.data = data;
        meta.createdAt = block.timestamp; // solhint-disable-line
        meta.updatedAt = block.timestamp; // solhint-disable-line

        emit LogMetadataCreated(owner, processId, productId, PolicyFlowState.Started);
    }

    /* Application */
    /**
     * @dev Creates a new insurance application for a given process ID.
     * @param processId The unique process ID associated with the insurance application.
     * @param premiumAmount The amount of premium to be paid for the insurance.
     * @param sumInsuredAmount The amount of coverage provided by the insurance.
     * @param data Additional data associated with the insurance application.
     *
     * Emits a LogApplicationCreated event with the process ID, premium amount, and sum insured amount.
     *
     * Requirements:
     * - The metadata for the process ID must exist.
     * - An application for the process ID must not already exist.
     * - The premium amount must be greater than zero.
     * - The sum insured amount must be greater than the premium amount.
     * - Only the PolicyFlow contract can call this function.
     * @notice This function emits 2 events: 
     * - LogApplicationCreated
     * - LogMetadataStateChanged
     */
    function createApplication(
        bytes32 processId, 
        uint256 premiumAmount,
        uint256 sumInsuredAmount,
        bytes calldata data
    )
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-010:METADATA_DOES_NOT_EXIST");

        Application storage application = applications[processId];
        require(application.createdAt == 0, "ERROR:POC-011:APPLICATION_ALREADY_EXISTS");

        require(premiumAmount > 0, "ERROR:POC-012:PREMIUM_AMOUNT_ZERO");
        require(sumInsuredAmount > premiumAmount, "ERROR:POC-013:SUM_INSURED_AMOUNT_TOO_SMALL");

        application.state = ApplicationState.Applied;
        application.premiumAmount = premiumAmount;
        application.sumInsuredAmount = sumInsuredAmount;
        application.data = data;
        application.createdAt = block.timestamp; // solhint-disable-line
        application.updatedAt = block.timestamp; // solhint-disable-line

        meta.state = PolicyFlowState.Active;
        meta.updatedAt = block.timestamp; // solhint-disable-line
        emit LogMetadataStateChanged(processId, meta.state);

        emit LogApplicationCreated(processId, premiumAmount, sumInsuredAmount);
    }

    /**
     * @dev Collects premium for a policy.
     * @param processId The unique identifier of the policy.
     * @param amount The amount of premium to be collected.
     *
     * Requirements:
     * - The policy must exist.
     * - The amount to be collected must not exceed the expected premium amount.
     *
     * Emits a {LogPremiumCollected} event.
     * @notice This function emits 1 events: 
     * - LogPremiumCollected
     */
    function collectPremium(bytes32 processId, uint256 amount) 
        external override
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-110:POLICY_DOES_NOT_EXIST");
        require(policy.premiumPaidAmount + amount <= policy.premiumExpectedAmount, "ERROR:POC-111:AMOUNT_TOO_BIG");

        policy.premiumPaidAmount += amount;
        policy.updatedAt = block.timestamp; // solhint-disable-line
    
        emit LogPremiumCollected(processId, amount);
    }
    
    /**
     * @dev Revokes an application with the given process ID.
     * @param processId The process ID of the application to be revoked.
     * @notice This function emits 2 events: 
     * - LogApplicationRevoked
     * - LogMetadataStateChanged
     */
    function revokeApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-014:METADATA_DOES_NOT_EXIST");

        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-015:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-016:APPLICATION_STATE_INVALID");

        application.state = ApplicationState.Revoked;
        application.updatedAt = block.timestamp; // solhint-disable-line

        meta.state = PolicyFlowState.Finished;
        meta.updatedAt = block.timestamp; // solhint-disable-line
        emit LogMetadataStateChanged(processId, meta.state);

        emit LogApplicationRevoked(processId);
    }

    /**
     * @dev Changes the state of an application to underwritten.
     * @param processId The unique ID of the application process.
     *
     * Emits a LogApplicationUnderwritten event.
     * @notice This function emits 1 events: 
     * - LogApplicationUnderwritten
     */
    function underwriteApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-017:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-018:APPLICATION_STATE_INVALID");

        application.state = ApplicationState.Underwritten;
        application.updatedAt = block.timestamp; // solhint-disable-line

        emit LogApplicationUnderwritten(processId);
    }

    /**
     * @dev Declines an application for a policy flow.
     * @param processId The unique identifier of the policy flow process.
     *
     *
     * Emits a LogMetadataStateChanged event with the updated metadata state.
     * Emits a LogApplicationDeclined event with the declined application's process ID.
     *
     * Requirements:
     * - The function can only be called by a "Policy" policy flow.
     * - The metadata for the given process ID must exist.
     * - The application for the given process ID must exist and be in the "Applied" state.
     *
     * Effects:
     * - Updates the state of the application to "Declined".
     * - Updates the state of the metadata to "Finished".
     * - Updates the updatedAt timestamps for both the application and metadata.
     * @notice This function emits 2 events: 
     * - LogApplicationDeclined
     * - LogMetadataStateChanged
     */
    function declineApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-019:METADATA_DOES_NOT_EXIST");

        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-020:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-021:APPLICATION_STATE_INVALID");

        application.state = ApplicationState.Declined;
        application.updatedAt = block.timestamp; // solhint-disable-line

        meta.state = PolicyFlowState.Finished;
        meta.updatedAt = block.timestamp; // solhint-disable-line
        emit LogMetadataStateChanged(processId, meta.state);

        emit LogApplicationDeclined(processId);
    }

    /* Policy */
    /**
     * @dev Creates a new policy for a given application process ID.
     * @param processId The ID of the application process.
     *
     *
     * Emits a `LogPolicyCreated` event.
     *
     * Requirements:
     * - The caller must have the 'Policy' role.
     * - The application must exist and be in the 'Underwritten' state.
     * - The policy must not already exist for the given process ID.
     * @notice This function emits 1 events: 
     * - LogPolicyCreated
     */
    function createPolicy(bytes32 processId) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Application memory application = applications[processId];
        require(application.createdAt > 0 && application.state == ApplicationState.Underwritten, "ERROR:POC-022:APPLICATION_ACCESS_INVALID");

        Policy storage policy = policies[processId];
        require(policy.createdAt == 0, "ERROR:POC-023:POLICY_ALREADY_EXISTS");

        policy.state = PolicyState.Active;
        policy.premiumExpectedAmount = application.premiumAmount;
        policy.payoutMaxAmount = application.sumInsuredAmount;
        policy.createdAt = block.timestamp; // solhint-disable-line
        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogPolicyCreated(processId);
    }

    /**
     * @dev This function adjusts the premium and sum insured amount of an insurance policy application.
     * @param processId The unique identifier of the insurance policy application.
     * @param expectedPremiumAmount The expected premium amount for the insurance policy.
     * @param sumInsuredAmount The sum insured amount for the insurance policy.
     *
     * @notice This function emits 3 events: 
     * - LogApplicationPremiumAdjusted
     * - LogPolicyPremiumAdjusted
     * - LogApplicationSumInsuredAdjusted
     */
    function adjustPremiumSumInsured(
        bytes32 processId, 
        uint256 expectedPremiumAmount,
        uint256 sumInsuredAmount
    )
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(
            application.createdAt > 0 
            && application.state == ApplicationState.Underwritten, 
            "ERROR:POC-024:APPLICATION_ACCESS_INVALID");

        require(
            sumInsuredAmount <= application.sumInsuredAmount, 
            "ERROR:POC-026:APPLICATION_SUM_INSURED_INCREASE_INVALID");

        Policy storage policy = policies[processId];
        require(
            policy.createdAt > 0 
            && policy.state == IPolicy.PolicyState.Active, 
            "ERROR:POC-027:POLICY_ACCESS_INVALID");
        
        require(
            expectedPremiumAmount > 0 
            && expectedPremiumAmount >= policy.premiumPaidAmount
            && expectedPremiumAmount < sumInsuredAmount, 
            "ERROR:POC-025:APPLICATION_PREMIUM_INVALID");

        if (sumInsuredAmount != application.sumInsuredAmount) {
            emit LogApplicationSumInsuredAdjusted(processId, application.sumInsuredAmount, sumInsuredAmount);
            application.sumInsuredAmount = sumInsuredAmount;
            application.updatedAt = block.timestamp; // solhint-disable-line

            policy.payoutMaxAmount = sumInsuredAmount;
            policy.updatedAt = block.timestamp; // solhint-disable-line
        }

        if (expectedPremiumAmount != application.premiumAmount) {
            emit LogApplicationPremiumAdjusted(processId, application.premiumAmount, expectedPremiumAmount);
            application.premiumAmount = expectedPremiumAmount;
            application.updatedAt = block.timestamp; // solhint-disable-line

            emit LogPolicyPremiumAdjusted(processId, policy.premiumExpectedAmount, expectedPremiumAmount);
            policy.premiumExpectedAmount = expectedPremiumAmount;
            policy.updatedAt = block.timestamp; // solhint-disable-line
        }
    }

    /**
     * @dev This function expires a policy with the given process ID.
     *
     * @param processId The process ID of the policy to be expired.
     *
     * @notice This function emits 1 events: 
     * - LogPolicyExpired
     */
    function expirePolicy(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-028:POLICY_DOES_NOT_EXIST");
        require(policy.state == PolicyState.Active, "ERROR:POC-029:APPLICATION_STATE_INVALID");

        policy.state = PolicyState.Expired;
        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogPolicyExpired(processId);
    }

    /**
     * @dev Closes a policy that has expired and has no open claims.
     * @param processId The unique identifier of the policy.
     *
     *
     * Emits a LogMetadataStateChanged event with the updated metadata state.
     * Emits a LogPolicyClosed event with the unique identifier of the closed policy.
     *
     * Requirements:
     * - The metadata for the given processId must exist.
     * - The policy for the given processId must exist.
     * - The state of the policy must be 'Expired'.
     * - The policy must have no open claims.
     * @notice This function emits 2 events: 
     * - LogMetadataStateChanged
     * - LogPolicyClosed
     */
    function closePolicy(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-030:METADATA_DOES_NOT_EXIST");

        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-031:POLICY_DOES_NOT_EXIST");
        require(policy.state == PolicyState.Expired, "ERROR:POC-032:POLICY_STATE_INVALID");
        require(policy.openClaimsCount == 0, "ERROR:POC-033:POLICY_HAS_OPEN_CLAIMS");

        policy.state = PolicyState.Closed;
        policy.updatedAt = block.timestamp; // solhint-disable-line

        meta.state = PolicyFlowState.Finished;
        meta.updatedAt = block.timestamp; // solhint-disable-line
        emit LogMetadataStateChanged(processId, meta.state);

        emit LogPolicyClosed(processId);
    }

    /* Claim */
    /**
     * @dev Creates a new claim for a given policy.
     * @param processId The ID of the policy.
     * @param claimAmount The amount of the claim.
     * @param data Additional data related to the claim.
     * @return claimId The ID of the newly created claim.
     *
     * Emits a LogClaimCreated event.
     *
     * Requirements:
     * - The caller must be authorized to create claims for the policy.
     * - The policy must exist and be in an active state.
     * - The sum of the payout amount and the claim amount must not exceed the maximum payout amount.
     * - The claim must not already exist.
     *
     * Note: The function allows claims with amount 0 to be created, which can be useful for parametric insurance.
     * @notice This function emits 1 events: 
     * - LogClaimCreated
     */
    function createClaim(
        bytes32 processId, 
        uint256 claimAmount,
        bytes calldata data
    )
        external override
        onlyPolicyFlow("Policy")
        returns (uint256 claimId)
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-040:POLICY_DOES_NOT_EXIST");
        require(policy.state == IPolicy.PolicyState.Active, "ERROR:POC-041:POLICY_NOT_ACTIVE");
        // no validation of claimAmount > 0 here to explicitly allow claims with amount 0. This can be useful for parametric insurance 
        // to have proof that the claim calculation was executed without entitlement to payment.
        require(policy.payoutAmount + claimAmount <= policy.payoutMaxAmount, "ERROR:POC-042:CLAIM_AMOUNT_EXCEEDS_MAX_PAYOUT");

        claimId = policy.claimsCount;
        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt == 0, "ERROR:POC-043:CLAIM_ALREADY_EXISTS");

        claim.state = ClaimState.Applied;
        claim.claimAmount = claimAmount;
        claim.data = data;
        claim.createdAt = block.timestamp; // solhint-disable-line
        claim.updatedAt = block.timestamp; // solhint-disable-line

        policy.claimsCount++;
        policy.openClaimsCount++;
        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogClaimCreated(processId, claimId, claimAmount);
    }

    /**
     * @dev Confirms a claim for a policy, updating the claim state to Confirmed and setting the confirmed amount.
     * @param processId The ID of the policy the claim belongs to.
     * @param claimId The ID of the claim to confirm.
     * @param confirmedAmount The amount to confirm for the claim.
     *
     * Requirements:
     * - Only the Policy contract can call this function.
     * - The policy must exist.
     * - The policy must have at least one open claim.
     * - The sum of the policy's payout amount and the confirmed amount must not exceed the policy's maximum payout amount.
     * - The claim must exist.
     * - The claim state must be Applied.
     *
     * Emits a LogClaimConfirmed event with the process ID, claim ID, and confirmed amount.
     * @notice This function emits 1 events: 
     * - LogClaimConfirmed
     */
    function confirmClaim(
        bytes32 processId,
        uint256 claimId,
        uint256 confirmedAmount
    ) 
        external override
        onlyPolicyFlow("Policy") 
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-050:POLICY_DOES_NOT_EXIST");
        require(policy.openClaimsCount > 0, "ERROR:POC-051:POLICY_WITHOUT_OPEN_CLAIMS");
        // no validation of claimAmount > 0 here as is it possible to have claims with amount 0 (see createClaim()). 
        require(policy.payoutAmount + confirmedAmount <= policy.payoutMaxAmount, "ERROR:POC-052:PAYOUT_MAX_AMOUNT_EXCEEDED");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-053:CLAIM_DOES_NOT_EXIST");
        require(claim.state == ClaimState.Applied, "ERROR:POC-054:CLAIM_STATE_INVALID");

        claim.state = ClaimState.Confirmed;
        claim.claimAmount = confirmedAmount;
        claim.updatedAt = block.timestamp; // solhint-disable-line

        policy.payoutAmount += confirmedAmount;
        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogClaimConfirmed(processId, claimId, confirmedAmount);
    }

    /**
     * @dev This function allows the Policy contract to decline a claim.
     * @param processId The ID of the process to which the policy belongs.
     * @param claimId The ID of the claim to be declined.
     *
     * Emits a LogClaimDeclined event.
     * @notice This function emits 1 events: 
     * - LogClaimDeclined
     */
    function declineClaim(bytes32 processId, uint256 claimId)
        external override
        onlyPolicyFlow("Policy") 
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-060:POLICY_DOES_NOT_EXIST");
        require(policy.openClaimsCount > 0, "ERROR:POC-061:POLICY_WITHOUT_OPEN_CLAIMS");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-062:CLAIM_DOES_NOT_EXIST");
        require(claim.state == ClaimState.Applied, "ERROR:POC-063:CLAIM_STATE_INVALID");

        claim.state = ClaimState.Declined;
        claim.updatedAt = block.timestamp; // solhint-disable-line

        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogClaimDeclined(processId, claimId);
    }

    /**
     * @dev Closes a claim for a given policy.
     * @param processId The ID of the policy process.
     * @param claimId The ID of the claim to be closed.
     *
     * @notice This function emits 1 events: 
     * - LogClaimClosed
     */
    function closeClaim(bytes32 processId, uint256 claimId)
        external override
        onlyPolicyFlow("Policy") 
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-070:POLICY_DOES_NOT_EXIST");
        require(policy.openClaimsCount > 0, "ERROR:POC-071:POLICY_WITHOUT_OPEN_CLAIMS");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-072:CLAIM_DOES_NOT_EXIST");
        require(
            claim.state == ClaimState.Confirmed 
            || claim.state == ClaimState.Declined, 
            "ERROR:POC-073:CLAIM_STATE_INVALID");

        require(
            (claim.state == ClaimState.Confirmed && claim.claimAmount == claim.paidAmount) 
            || (claim.state == ClaimState.Declined), 
            "ERROR:POC-074:CLAIM_WITH_UNPAID_PAYOUTS"
        );

        claim.state = ClaimState.Closed;
        claim.updatedAt = block.timestamp; // solhint-disable-line

        policy.openClaimsCount--;
        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogClaimClosed(processId, claimId);
    }

    /* Payout */
    /**
     * @dev Creates a new payout for a confirmed claim in a policy.
     * @param processId The ID of the policy.
     * @param claimId The ID of the claim associated with the payout.
     * @param payoutAmount The amount of the payout.
     * @param data Additional data related to the payout.
     * @return payoutId The ID of the newly created payout.
     *
     * Emits a LogPayoutCreated event with the processId, claimId, payoutId, and payoutAmount.
     *
     * Requirements:
     * - The caller must have the onlyPolicyFlow modifier with "Policy" as the argument.
     * - The policy with the given processId must exist.
     * - The claim with the given claimId must exist and be in the Confirmed state.
     * - The payoutAmount must be greater than zero.
     * - The sum of the paidAmount of the claim and the payoutAmount must not exceed the claimAmount of the claim.
     * - A payout with the given processId and payoutId must not already exist.
     * @notice This function emits 1 events: 
     * - LogPayoutCreated
     */
    function createPayout(
        bytes32 processId,
        uint256 claimId,
        uint256 payoutAmount,
        bytes calldata data
    )
        external override 
        onlyPolicyFlow("Policy") 
        returns (uint256 payoutId)
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-080:POLICY_DOES_NOT_EXIST");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-081:CLAIM_DOES_NOT_EXIST");
        require(claim.state == IPolicy.ClaimState.Confirmed, "ERROR:POC-082:CLAIM_NOT_CONFIRMED");
        require(payoutAmount > 0, "ERROR:POC-083:PAYOUT_AMOUNT_ZERO_INVALID");
        require(
            claim.paidAmount + payoutAmount <= claim.claimAmount,
            "ERROR:POC-084:PAYOUT_AMOUNT_TOO_BIG"
        );

        payoutId = payoutCount[processId];
        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt == 0, "ERROR:POC-085:PAYOUT_ALREADY_EXISTS");

        payout.claimId = claimId;
        payout.amount = payoutAmount;
        payout.data = data;
        payout.state = PayoutState.Expected;
        payout.createdAt = block.timestamp; // solhint-disable-line
        payout.updatedAt = block.timestamp; // solhint-disable-line

        payoutCount[processId]++;
        policy.updatedAt = block.timestamp; // solhint-disable-line

        emit LogPayoutCreated(processId, claimId, payoutId, payoutAmount);
    }

    /**
     * @dev Processes a payout for a policy and claim.
     * @param processId The ID of the policy to process the payout for.
     * @param payoutId The ID of the payout to process.
     *
     * Emits a LogPayoutProcessed event.
     * If the claim is fully paid, emits a LogClaimClosed event.
     *
     * Requirements:
     * - The caller must have the onlyPolicyFlow modifier with the "Policy" role.
     * - The policy with the given processId must exist.
     * - The policy with the given processId must have at least one open claim.
     * - The payout with the given payoutId must exist.
     * - The payout with the given payoutId must be in the Expected state.
     *
     * Effects:
     * - Changes the state of the payout to PaidOut.
     * - Updates the updatedAt timestamp of the payout.
     * - Increases the paidAmount of the claim associated with the payout.
     * - Updates the updatedAt timestamp of the claim.
     * - If the claim is fully paid, changes the state of the claim to Closed.
     * - Decreases the openClaimsCount of the policy associated with the claim.
     * - Updates the updatedAt timestamp of the policy.
     * @notice This function emits 2 events: 
     * - LogClaimClosed
     * - LogPayoutProcessed
     */
    function processPayout(
        bytes32 processId,
        uint256 payoutId
    )
        external override 
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-090:POLICY_DOES_NOT_EXIST");
        require(policy.openClaimsCount > 0, "ERROR:POC-091:POLICY_WITHOUT_OPEN_CLAIMS");

        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-092:PAYOUT_DOES_NOT_EXIST");
        require(payout.state == PayoutState.Expected, "ERROR:POC-093:PAYOUT_ALREADY_PAIDOUT");

        payout.state = IPolicy.PayoutState.PaidOut;
        payout.updatedAt = block.timestamp; // solhint-disable-line

        emit LogPayoutProcessed(processId, payoutId);

        Claim storage claim = claims[processId][payout.claimId];
        claim.paidAmount += payout.amount;
        claim.updatedAt = block.timestamp; // solhint-disable-line

        // check if claim can be closed
        if (claim.claimAmount == claim.paidAmount) {
            claim.state = IPolicy.ClaimState.Closed;

            policy.openClaimsCount -= 1;
            policy.updatedAt = block.timestamp; // solhint-disable-line

            emit LogClaimClosed(processId, payout.claimId);
        }
    }

    /**
     * @dev Returns the metadata for the given process ID.
     * @param processId The ID of the process to retrieve metadata for.
     * @return _metadata The metadata information for the given process ID.
     *
     * Requirements:
     * - The metadata for the given process ID must exist.
     */
    function getMetadata(bytes32 processId)
        public
        view
        returns (IPolicy.Metadata memory _metadata)
    {
        _metadata = metadata[processId];
        require(_metadata.createdAt > 0,  "ERROR:POC-100:METADATA_DOES_NOT_EXIST");
    }

    /**
     * @dev Returns the application associated with the provided process ID.
     * @param processId The ID of the process for which to retrieve the application.
     * @return application The application associated with the provided process ID.
     */
    function getApplication(bytes32 processId)
        public
        view
        returns (IPolicy.Application memory application)
    {
        application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-101:APPLICATION_DOES_NOT_EXIST");        
    }

    /**
     * @dev Returns the number of claims associated with a given process ID.
     * @param processId The ID of the process for which to retrieve the number of claims.
     * @return numberOfClaims The number of claims associated with the given process ID.
     */
    function getNumberOfClaims(bytes32 processId) external view returns(uint256 numberOfClaims) {
        numberOfClaims = getPolicy(processId).claimsCount;
    }
    
    /**
     * @dev Returns the number of payouts for a given process ID.
     * @param processId The ID of the process.
     * @return numberOfPayouts The number of payouts for the given process ID.
     */
    function getNumberOfPayouts(bytes32 processId) external view returns(uint256 numberOfPayouts) {
        numberOfPayouts = payoutCount[processId];
    }

    /**
     * @dev Returns the policy associated with the given process ID.
     * @param processId The ID of the process for which to retrieve the policy.
     * @return policy The policy object associated with the given process ID.
     */
    function getPolicy(bytes32 processId)
        public
        view
        returns (IPolicy.Policy memory policy)
    {
        policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-102:POLICY_DOES_NOT_EXIST");        
    }

    /**
     * @dev Returns the claim with the given ID for the specified process.
     * @param processId The ID of the process.
     * @param claimId The ID of the claim.
     * @return claim The claim object with the given ID.
     * @notice This function can only be called in read-only mode.
     * @notice Throws an error if the claim with the given ID does not exist.
     */
    function getClaim(bytes32 processId, uint256 claimId)
        public
        view
        returns (IPolicy.Claim memory claim)
    {
        claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-103:CLAIM_DOES_NOT_EXIST");        
    }

    /**
     * @dev Retrieves a specific payout from a process.
     * @param processId The ID of the process.
     * @param payoutId The ID of the payout to retrieve.
     * @return payout The payout object with the specified ID.
     * @notice Throws an error if the payout does not exist.
     */
    function getPayout(bytes32 processId, uint256 payoutId)
        public
        view
        returns (IPolicy.Payout memory payout)
    {
        payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-104:PAYOUT_DOES_NOT_EXIST");        
    }

    /**
     * @dev Returns the number of process IDs that have been assigned.
     * @return _assigendProcessIds The number of process IDs that have been assigned.
     */
    function processIds() external view returns (uint256) {
        return _assigendProcessIds;
    }

    /**
     * @dev Generates a unique process ID for the next process.
     * @return processId The generated process ID.
     */
    function _generateNextProcessId() private returns(bytes32 processId) {
        _assigendProcessIds++;

        processId = keccak256(
            abi.encodePacked(
                block.chainid, 
                address(_registry),
                _assigendProcessIds
            )
        );
    } 
}
