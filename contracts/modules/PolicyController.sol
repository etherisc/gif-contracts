// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";

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

    bytes32[] public processIds;

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
        processIds.push(processId);

        emit LogNewMetadata(owner, processId, productId, PolicyFlowState.Started);
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

        emit LogNewApplication(processId, premiumAmount, sumInsuredAmount);
    }

    function setApplicationState(bytes32 processId, ApplicationState state)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-012:APPLICATION_DOES_NOT_EXIST");

        application.state = state;
        application.updatedAt = block.timestamp;

        emit LogApplicationStateChanged(processId, state);
    }

    /* Policy */
    function createPolicy(bytes32 processId) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[processId];
        require(meta.createdAt > 0, "ERROR:POC-020:METADATA_DOES_NOT_EXIST");

        Policy storage policy = policies[processId];
        require(policy.createdAt == 0, "ERROR:POC-021:POLICY_ALREADY_EXISTS");

        policy.state = PolicyState.Active;
        policy.createdAt = block.timestamp;
        policy.updatedAt = block.timestamp;

        meta.updatedAt = block.timestamp;

        emit LogNewPolicy(processId);
    }

    function setPolicyState(bytes32 processId, PolicyState state)
        external override
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-022:POLICY_DOES_NOT_EXIST");

        policy.state = state;
        policy.updatedAt = block.timestamp;

        emit LogPolicyStateChanged(processId, state);
    }

    /* Claim */
    function createClaim(bytes32 processId, bytes calldata data)
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
        claim.data = data;
        claim.createdAt = block.timestamp;
        claim.updatedAt = block.timestamp;

        policy.claimsCount += 1;
        policy.updatedAt = block.timestamp;

        emit LogNewClaim(processId, claimId, ClaimState.Applied);
    }

    function setClaimState(
        bytes32 processId,
        uint256 claimId,
        ClaimState state
    ) 
        external override 
        onlyPolicyFlow("Policy") 
    {
        Claim storage claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-033:CLAIM_DOES_NOT_EXIST");

        claim.state = state;
        claim.updatedAt = block.timestamp;

        emit LogClaimStateChanged(processId, claimId, state);
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
        policy.updatedAt = block.timestamp;

        emit LogNewPayout(processId, claimId, payoutId, PayoutState.Expected);
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
        Policy memory policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-043:POLICY_DOES_NOT_EXIST");

        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-044:PAYOUT_DOES_NOT_EXIST");
        require(payout.state == PayoutState.Expected, "ERROR:POC-045:PAYOUT_ALREADY_COMPLETED");

        payout.data = data;
        payout.updatedAt = block.timestamp;

        if (isComplete) {
            payout.state = PayoutState.PaidOut;
            emit LogPayoutCompleted(processId, payoutId, payout.state);
        } else {
            emit LogPayoutProcessed(processId, payoutId, payout.state);
        }
    }

    function setPayoutState(
        bytes32 processId,
        uint256 payoutId,
        PayoutState state
    ) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Payout storage payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-046:PAYOUT_DOES_NOT_EXIST");

        payout.state = state;
        payout.updatedAt = block.timestamp;

        emit LogPayoutStateChanged(processId, payoutId, state);
    }

    function getMetadata(bytes32 processId)
        public override
        view
        returns (IPolicy.Metadata memory _metadata)
    {
        _metadata = metadata[processId];
        require(_metadata.createdAt > 0,  "ERROR:POC-050:METADATA_DOES_NOT_EXIST");
    }

    function getApplication(bytes32 processId)
        public override
        view
        returns (IPolicy.Application memory application)
    {
        application = applications[processId];
        require(application.createdAt > 0, "ERROR:POC-051:APPLICATION_DOES_NOT_EXIST");        
    }

    function getPolicy(bytes32 processId)
        public override
        view
        returns (IPolicy.Policy memory policy)
    {
        policy = policies[processId];
        require(policy.createdAt > 0, "ERROR:POC-052:POLICY_DOES_NOT_EXIST");        
    }

    function getClaim(bytes32 processId, uint256 claimId)
        public override
        view
        returns (IPolicy.Claim memory claim)
    {
        claim = claims[processId][claimId];
        require(claim.createdAt > 0, "ERROR:POC-053:CLAIM_DOES_NOT_EXIST");        
    }

    function getPayout(bytes32 processId, uint256 payoutId)
        public override
        view
        returns (IPolicy.Payout memory payout)
    {
        payout = payouts[processId][payoutId];
        require(payout.createdAt > 0, "ERROR:POC-054:PAYOUT_DOES_NOT_EXIST");        
    }

    function getProcessIdCount() external override view returns (uint256) {
        return processIds.length;
    }
}
