// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract PolicyController is 
    IPolicy, 
    CoreController
{
    // bytes32 public constant NAME = "PolicyController";

    // Metadata
    mapping(bytes32 => Metadata) public metadata;

    // Applications
    mapping(bytes32 => Application) public applications;

    // Policies
    mapping(bytes32 => Policy) public policies;

    // Claims
    mapping(bytes32 => mapping(uint256 => Claim)) public claims;

    // Payouts
    mapping(bytes32 => mapping(uint256 => Payout)) public payouts;

    bytes32[] private _processIds;

    /* Metadata */
    function createPolicyFlow(
        address owner,
        bytes32 processId, 
        uint256 productId,
        bytes calldata data
    )
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt == 0, "ERROR:POC-001:METADATA_ALREADY_EXISTS");

        meta.owner = owner;
        meta.productId = productId;
        meta.state = PolicyFlowState.Started;
        meta.data = data;
        meta.createdAt = block.timestamp;
        meta.updatedAt = block.timestamp;
        _processIds.push(processId);

        emit LogMetadataCreated(owner, processId, productId, PolicyFlowState.Started);
    }

    function setPolicyFlowState(
        bytes32 processId, 
        PolicyFlowState state
    )
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-002:METADATA_DOES_NOT_EXIST");

        meta.state = state;
        meta.updatedAt = block.timestamp;

        emit LogMetadataStateChanged(processId, state);
    }

    /* Application */
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

        application.state = ApplicationState.Applied;
        application.premiumAmount = premiumAmount;
        application.sumInsuredAmount = sumInsuredAmount;
        application.data = data;
        application.createdAt = block.timestamp;
        application.updatedAt = block.timestamp;

        meta.updatedAt = block.timestamp;

        emit LogApplicationCreated(processId, premiumAmount, sumInsuredAmount);
    }

    function collectPremium(bytes32 processId, uint256 amount) 
        external override
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-012:POLICY_DOES_NOT_EXIST");
        require(policy.premiumPaidAmount + amount <= policy.premiumExpectedAmount, "ERROR:POC-013:AMOUNT_TOO_BIG");

        policy.premiumPaidAmount += amount;
        policy.updatedAt = block.timestamp;
    
        emit LogPremiumCollected(processId, amount);
    }

    function revokeApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-014:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-015:INVALID_APPLICATION_STATE");

        application.state = ApplicationState.Revoked;
        application.updatedAt = block.timestamp;

        emit LogApplicationRevoked(processId);
    }

    function underwriteApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-016:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-017:INVALID_APPLICATION_STATE");

        application.state = ApplicationState.Underwritten;
        application.updatedAt = block.timestamp;

        emit LogApplicationUnderwritten(processId);
    }

    function declineApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-018:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-019:INVALID_APPLICATION_STATE");

        application.state = ApplicationState.Declined;
        application.updatedAt = block.timestamp;

        emit LogApplicationDeclined(processId);
    }

    /* Policy */
    function createPolicy(bytes32 processId) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Application memory application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-021:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Underwritten, "ERROR:POC-022:APPLICATION_NOT_UNDERWRITTEN");

        Policy storage policy = policies[processId];
        require(policy.createdAt == 0, "ERROR:POC-023:POLICY_ALREADY_EXISTS");

        policy.state = PolicyState.Active;
        policy.premiumExpectedAmount = application.premiumAmount;
        policy.createdAt = block.timestamp;
        policy.updatedAt = block.timestamp;

        emit LogPolicyCreated(processId);
    }

    function expirePolicy(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-024:POLICY_DOES_NOT_EXIST");
        require(policy.state == PolicyState.Active, "ERROR:POC-025:INVALID_APPLICATION_STATE");

        policy.state = PolicyState.Expired;
        policy.updatedAt = block.timestamp;

        emit LogPolicyExpired(processId);
    }

    function closePolicy(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-026:POLICY_DOES_NOT_EXIST");
        require(policy.state == PolicyState.Expired, "ERROR:POC-027:INVALID_APPLICATION_STATE");

        // TODO add requires to ensure there are no open claims or payments

        policy.state = PolicyState.Closed;
        policy.updatedAt = block.timestamp;

        emit LogPolicyClosed(processId);
    }

    /* Claim */
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
        require(policy.createdAt > 0, "ERROR:POC-030:POLICY_DOES_NOT_EXIST");
        require(policy.state == IPolicy.PolicyState.Active, "ERROR:POC-031:POLICY_NOT_ACTIVE");

        claimId = policy.claimsCount;
        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt == 0, "ERROR:POC-032:CLAIM_ALREADY_EXISTS");

        claim.state = ClaimState.Applied;
        claim.claimAmount = claimAmount;
        claim.data = data;
        claim.createdAt = block.timestamp;
        claim.updatedAt = block.timestamp;

        policy.claimsCount += 1;
        policy.openClaimsCount += 1;
        policy.updatedAt = block.timestamp;

        emit LogClaimCreated(processId, claimId);
    }

    function confirmClaim(bytes32 processId, uint256 claimId) 
        external override
        onlyPolicyFlow("Policy") 
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-033:POLICY_DOES_NOT_EXIST");
        require(policy.openClaimsCount > 0, "ERROR:POC-034:NO_OPEN_CLAIMS");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-035:CLAIM_DOES_NOT_EXIST");
        require(claim.state == ClaimState.Applied, "ERROR:POC-036:INVALID_CLAIM_STATE");

        claim.state = ClaimState.Confirmed;
        claim.updatedAt = block.timestamp;

        policy.openClaimsCount -= 1;
        policy.updatedAt = block.timestamp;

        emit LogClaimConfirmed(processId, claimId);
    }

    function declineClaim(bytes32 processId, uint256 claimId)
        external override
        onlyPolicyFlow("Policy") 
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-033:POLICY_DOES_NOT_EXIST");
        require(policy.openClaimsCount > 0, "ERROR:POC-034:NO_OPEN_CLAIMS");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-035:CLAIM_DOES_NOT_EXIST");
        require(claim.state == ClaimState.Applied, "ERROR:POC-036:INVALID_CLAIM_STATE");

        claim.state = ClaimState.Declined;
        claim.updatedAt = block.timestamp;

        policy.openClaimsCount -= 1;
        policy.updatedAt = block.timestamp;

        emit LogClaimDeclined(processId, claimId);
    }

    /* Payout */
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
        require(policy.createdAt > 0, "ERROR:POC-040:POLICY_DOES_NOT_EXIST");

        Claim memory claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-041:CLAIM_DOES_NOT_EXIST");

        payoutId = policy.payoutsCount;
        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt == 0, "ERROR:POC-042:PAYOUT_ALREADY_EXISTS");

        payout.claimId = claimId;
        payout.payoutAmount = payoutAmount;
        payout.data = data;
        payout.state = PayoutState.Expected;
        payout.createdAt = block.timestamp;
        payout.updatedAt = block.timestamp;

        policy.payoutsCount += 1;
        policy.openPayoutsCount += 1;
        policy.updatedAt = block.timestamp;

        emit LogPayoutCreated(processId, claimId, payoutId);
    }

    function processPayout(
        bytes32 processId,
        uint256 payoutId,
        bool isComplete,
        bytes calldata data
    )
        external override 
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-043:POLICY_DOES_NOT_EXIST");
        require(policy.openPayoutsCount > 0, "ERROR:POC-044:NO_OPEN_PAYOUTS");

        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-045:PAYOUT_DOES_NOT_EXIST");
        require(payout.state == PayoutState.Expected, "ERROR:POC-046:PAYOUT_ALREADY_COMPLETED");

        payout.data = data;
        payout.updatedAt = block.timestamp;

        if (isComplete) {
            payout.state = PayoutState.PaidOut;

            policy.openPayoutsCount -= 1;
            policy.updatedAt = block.timestamp;

            emit LogPayoutCompleted(processId, payoutId);
        } else {
            emit LogPayoutProcessed(processId, payoutId);
        }
    }

    function getMetadata(bytes32 processId)
        public
        view
        returns (IPolicy.Metadata memory _metadata)
    {
        _metadata = metadata[processId];
        require(_metadata.createdAt > 0,  "ERROR:POC-050:METADATA_DOES_NOT_EXIST");
    }

    function getApplication(bytes32 processId)
        public
        view
        returns (IPolicy.Application memory application)
    {
        application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-051:APPLICATION_DOES_NOT_EXIST");        
    }

    function getPolicy(bytes32 processId)
        public
        view
        returns (IPolicy.Policy memory policy)
    {
        policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-052:POLICY_DOES_NOT_EXIST");        
    }

    function getClaim(bytes32 processId, uint256 claimId)
        public
        view
        returns (IPolicy.Claim memory claim)
    {
        claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-053:CLAIM_DOES_NOT_EXIST");        
    }

    function getPayout(bytes32 processId, uint256 payoutId)
        public
        view
        returns (IPolicy.Payout memory payout)
    {
        payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-054:PAYOUT_DOES_NOT_EXIST");        
    }

    function processIds() external view returns (uint256) {
        return _processIds.length;
    }
}
