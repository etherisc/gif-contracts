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
    mapping(bytes32 /* processId */ => Metadata) public metadata;

    // Applications
    mapping(bytes32 /* processId */ => Application) public applications;

    // Policies
    mapping(bytes32 /* processId */ => Policy) public policies;

    // TODO decide for current data structure or alternative
    // alternative mapping(bytes32 => Claim []) 
    // Claims
    mapping(bytes32 /* processId */ => mapping(uint256 /* claimId */ => Claim)) public claims;

    // TODO decide for current data structure or alternative
    // alternative mapping(bytes32 => Payout []) 
    // Payouts
    mapping(bytes32 /* processId */ => mapping(uint256 /* payoutId */ => Payout)) public payouts;
    mapping(bytes32 /* processId */ => uint256) public payoutCount;

    // counter for assigned processIds, used to ensure unique processIds
    uint256 private _assigendProcessIds;

    /* Metadata */
    function createPolicyFlow(
        address owner,
        uint256 productId,
        bytes calldata data
    )
        external override
        onlyPolicyFlow("Policy")
        returns(bytes32 processId)
    {
        processId = _generateNextProcessId();
        Metadata storage meta = metadata[processId];
        require(meta.createdAt == 0, "ERROR:POC-001:METADATA_ALREADY_EXISTS");

        meta.owner = owner;
        meta.productId = productId;
        meta.state = PolicyFlowState.Started;
        meta.data = data;
        meta.createdAt = block.timestamp;
        meta.updatedAt = block.timestamp;

        emit LogMetadataCreated(owner, processId, productId, PolicyFlowState.Started);
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

        meta.state = PolicyFlowState.Active;
        meta.updatedAt = block.timestamp;
        emit LogMetadataStateChanged(processId, meta.state);

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
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-014:METADATA_DOES_NOT_EXIST");

        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-015:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-016:APPLICATION_STATE_INVALID");

        application.state = ApplicationState.Revoked;
        application.updatedAt = block.timestamp;

        meta.state = PolicyFlowState.Finished;
        meta.updatedAt = block.timestamp;
        emit LogMetadataStateChanged(processId, meta.state);

        emit LogApplicationRevoked(processId);
    }

    function underwriteApplication(bytes32 processId)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-017:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Applied, "ERROR:POC-018:APPLICATION_STATE_INVALID");

        application.state = ApplicationState.Underwritten;
        application.updatedAt = block.timestamp;

        emit LogApplicationUnderwritten(processId);
    }

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
        application.updatedAt = block.timestamp;

        meta.state = PolicyFlowState.Finished;
        meta.updatedAt = block.timestamp;
        emit LogMetadataStateChanged(processId, meta.state);

        emit LogApplicationDeclined(processId);
    }

    /* Policy */
    function createPolicy(bytes32 processId) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Application memory application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-022:APPLICATION_DOES_NOT_EXIST");
        require(application.state == ApplicationState.Underwritten, "ERROR:POC-023:APPLICATION_NOT_UNDERWRITTEN");

        Policy storage policy = policies[processId];
        require(policy.createdAt == 0, "ERROR:POC-024:POLICY_ALREADY_EXISTS");

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
        require(policy.createdAt > 0, "ERROR:POC-025:POLICY_DOES_NOT_EXIST");
        require(policy.state == PolicyState.Active, "ERROR:POC-026:APPLICATION_STATE_INVALID");

        policy.state = PolicyState.Expired;
        policy.updatedAt = block.timestamp;

        emit LogPolicyExpired(processId);
    }

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
        policy.updatedAt = block.timestamp;

        meta.state = PolicyFlowState.Finished;
        meta.updatedAt = block.timestamp;
        emit LogMetadataStateChanged(processId, meta.state);

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
        require(policy.createdAt > 0, "ERROR:POC-040:POLICY_DOES_NOT_EXIST");
        require(policy.state == IPolicy.PolicyState.Active, "ERROR:POC-041:POLICY_NOT_ACTIVE");

        claimId = policy.claimsCount;
        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt == 0, "ERROR:POC-042:CLAIM_ALREADY_EXISTS");

        claim.state = ClaimState.Applied;
        claim.claimAmount = claimAmount;
        claim.data = data;
        claim.createdAt = block.timestamp;
        claim.updatedAt = block.timestamp;

        policy.claimsCount++;
        policy.openClaimsCount++;
        policy.updatedAt = block.timestamp;

        emit LogClaimCreated(processId, claimId, claimAmount);
    }

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

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-052:CLAIM_DOES_NOT_EXIST");
        require(claim.state == ClaimState.Applied, "ERROR:POC-053:CLAIM_STATE_INVALID");

        claim.state = ClaimState.Confirmed;
        claim.claimAmount = confirmedAmount;
        claim.updatedAt = block.timestamp;

        policy.updatedAt = block.timestamp;

        emit LogClaimConfirmed(processId, claimId, confirmedAmount);
    }

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
        claim.updatedAt = block.timestamp;

        policy.updatedAt = block.timestamp;

        emit LogClaimDeclined(processId, claimId);
    }

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
            claim.claimAmount == claim.paidAmount, 
            "ERROR:POC-074:CLAIM_WITH_UNPAID_PAYOUTS"
        );

        claim.state = ClaimState.Closed;
        claim.updatedAt = block.timestamp;

        policy.openClaimsCount -= 1;
        policy.updatedAt = block.timestamp;

        emit LogClaimClosed(processId, claimId);
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
        require(policy.createdAt > 0, "ERROR:POC-080:POLICY_DOES_NOT_EXIST");

        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-081:CLAIM_DOES_NOT_EXIST");
        require(claim.state == IPolicy.ClaimState.Confirmed, "ERROR:POC-082:CLAIM_NOT_CONFIRMED");
        require(payoutAmount > 0, "ERROR:POC-083:PAYOUT_AMOUNT_ZERO_INVALID");
        require(
            claim.payoutsAmount + payoutAmount <= claim.claimAmount,
            "ERROR:POC-084:PAYOUT_AMOUNT_TOO_BIG"
        );

        payoutId = payoutCount[processId];
        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt == 0, "ERROR:POC-085:PAYOUT_ALREADY_EXISTS");

        payout.claimId = claimId;
        payout.amount = payoutAmount;
        payout.data = data;
        payout.state = PayoutState.Expected;
        payout.createdAt = block.timestamp;
        payout.updatedAt = block.timestamp;

        claim.payoutsAmount += payoutAmount;
        claim.updatedAt = block.timestamp;

        payoutCount[processId]++;
        policy.updatedAt = block.timestamp;

        emit LogPayoutCreated(processId, claimId, payoutId, payoutAmount);
    }

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
        payout.updatedAt = block.timestamp;

        emit LogPayoutProcessed(processId, payoutId);

        Claim storage claim = claims[processId][payout.claimId];
        claim.paidAmount += payout.amount;
        claim.updatedAt = block.timestamp;

        // check if claim can be closed
        if (claim.claimAmount == claim.paidAmount) {
            claim.state = IPolicy.ClaimState.Closed;

            policy.openClaimsCount -= 1;
            policy.updatedAt = block.timestamp;

            emit LogClaimClosed(processId, payout.claimId);
        }
    }

    function getMetadata(bytes32 processId)
        public
        view
        returns (IPolicy.Metadata memory _metadata)
    {
        _metadata = metadata[processId];
        require(_metadata.createdAt > 0,  "ERROR:POC-100:METADATA_DOES_NOT_EXIST");
    }

    function getApplication(bytes32 processId)
        public
        view
        returns (IPolicy.Application memory application)
    {
        application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-101:APPLICATION_DOES_NOT_EXIST");        
    }

    function getNumberOfClaims(bytes32 processId) external view returns(uint256 numberOfClaims) {
        numberOfClaims = getPolicy(processId).claimsCount;
    }
    
    function getNumberOfPayouts(bytes32 processId) external view returns(uint256 numberOfPayouts) {
        numberOfPayouts = payoutCount[processId];
    }

    function getPolicy(bytes32 processId)
        public
        view
        returns (IPolicy.Policy memory policy)
    {
        policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-102:POLICY_DOES_NOT_EXIST");        
    }

    function getClaim(bytes32 processId, uint256 claimId)
        public
        view
        returns (IPolicy.Claim memory claim)
    {
        claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-103:CLAIM_DOES_NOT_EXIST");        
    }

    function getPayout(bytes32 processId, uint256 payoutId)
        public
        view
        returns (IPolicy.Payout memory payout)
    {
        payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-104:PAYOUT_DOES_NOT_EXIST");        
    }

    function processIds() external view returns (uint256) {
        return _assigendProcessIds;
    }

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
