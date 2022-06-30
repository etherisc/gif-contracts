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

    bytes32[] public bpKeys;

    /* Metadata */
    function createPolicyFlow(uint256 _productId, bytes32 _bpKey)
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[_bpKey];
        require(meta.createdAt == 0, "ERROR:POC-001:METADATA_ALREADY_EXISTS");

        meta.productId = _productId;
        meta.state = PolicyFlowState.Started;
        meta.createdAt = block.timestamp;
        meta.updatedAt = block.timestamp;
        bpKeys.push(_bpKey);

        emit LogNewMetadata(_productId, _bpKey, PolicyFlowState.Started);
    }

    function setPolicyFlowState(bytes32 _bpKey, PolicyFlowState _state)
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[_bpKey];
        require(meta.createdAt > 0, "ERROR:POC-002:METADATA_DOES_NOT_EXIST");

        meta.state = _state;
        meta.updatedAt = block.timestamp;

        emit LogMetadataStateChanged(_bpKey, _state);
    }

    /* Application */
    function createApplication(bytes32 _bpKey, bytes calldata _data)
        external override
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[_bpKey];
        require(meta.createdAt > 0, "ERROR:POC-010:METADATA_DOES_NOT_EXIST");

        Application storage application = applications[_bpKey];
        require(application.createdAt == 0, "ERROR:POC-011:APPLICATION_ALREADY_EXISTS");

        application.state = ApplicationState.Applied;
        application.data = _data;
        application.createdAt = block.timestamp;
        application.updatedAt = block.timestamp;

        assert(meta.createdAt > 0);
        assert(meta.hasApplication == false);

        meta.hasApplication = true;
        meta.updatedAt = block.timestamp;

        emit LogNewApplication(meta.productId, _bpKey);
    }

    function setApplicationState(bytes32 _bpKey, ApplicationState _state)
        external override
        onlyPolicyFlow("Policy")
    {
        Application storage application = applications[_bpKey];
        require(application.createdAt > 0, "ERROR:POC-012:APPLICATION_DOES_NOT_EXIST");

        application.state = _state;
        application.updatedAt = block.timestamp;

        emit LogApplicationStateChanged(_bpKey, _state);
    }

    /* Policy */
    function createPolicy(bytes32 _bpKey) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Metadata storage meta = metadata[_bpKey];
        require(meta.createdAt > 0, "ERROR:POC-020:METADATA_DOES_NOT_EXIST");
        require(meta.hasPolicy == false, "ERROR:POC-021:POLICY_ALREADY_EXISTS");

        Policy storage policy = policies[_bpKey];
        require(policy.createdAt == 0, "ERROR:POC-022:POLICY_ALREADY_EXISTS_FOR_BPKEY");

        policy.state = PolicyState.Active;
        policy.createdAt = block.timestamp;
        policy.updatedAt = block.timestamp;

        meta.hasPolicy = true;
        meta.updatedAt = block.timestamp;

        emit LogNewPolicy(_bpKey);
    }

    function setPolicyState(bytes32 _bpKey, PolicyState _state)
        external override
        onlyPolicyFlow("Policy")
    {
        Policy storage policy = policies[_bpKey];
        require(policy.createdAt > 0, "ERROR:POC-023:POLICY_DOES_NOT_EXIST");

        policy.state = _state;
        policy.updatedAt = block.timestamp;

        emit LogPolicyStateChanged(_bpKey, _state);
    }

    /* Claim */
    function createClaim(bytes32 _bpKey, bytes calldata _data)
        external override
        onlyPolicyFlow("Policy")
        returns (uint256 _claimId)
    {
        Metadata storage meta = metadata[_bpKey];
        require(meta.createdAt > 0, "ERROR:POC-030:METADATA_DOES_NOT_EXIST");

        Policy memory policy = policies[_bpKey];
        require(policy.createdAt > 0, "ERROR:POC-031:POLICY_DOES_NOT_EXIST");
        require(policy.state == IPolicy.PolicyState.Active, "ERROR:POC-032:POLICY_NOT_ACTIVE");

        _claimId = meta.claimsCount;
        Claim storage claim = claims[_bpKey][_claimId];
        require(claim.createdAt == 0, "ERROR:POC-033:CLAIM_ALREADY_EXISTS");

        meta.claimsCount += 1;
        meta.updatedAt = block.timestamp;

        claim.state = ClaimState.Applied;
        claim.data = _data;
        claim.createdAt = block.timestamp;
        claim.updatedAt = block.timestamp;

        emit LogNewClaim(_bpKey, _claimId, ClaimState.Applied);
    }

    function setClaimState(
        bytes32 _bpKey,
        uint256 _claimId,
        ClaimState _state
    ) 
        external override 
        onlyPolicyFlow("Policy") 
    {
        Claim storage claim = claims[_bpKey][_claimId];
        require(claim.createdAt > 0, "ERROR:POC-034:CLAIM_DOES_NOT_EXIST");

        claim.state = _state;
        claim.updatedAt = block.timestamp;

        emit LogClaimStateChanged(_bpKey, _claimId, _state);
    }

    /* Payout */
    function createPayout(
        bytes32 _bpKey,
        uint256 _claimId,
        bytes calldata _data
    )
        external override 
        onlyPolicyFlow("Policy") 
        returns (uint256 _payoutId)
    {
        Metadata storage meta = metadata[_bpKey];
        require(meta.createdAt > 0, "ERROR:POC-040:METADATA_DOES_NOT_EXIST");

        Claim memory claim = claims[_bpKey][_claimId];
        require(claim.createdAt > 0, "ERROR:POC-041:CLAIM_DOES_NOT_EXIST");

        _payoutId = meta.payoutsCount;
        Payout storage payout = payouts[_bpKey][_payoutId];
        require(payout.createdAt == 0, "ERROR:POC-042:PAYOUT_ALREADY_EXISTS");

        meta.payoutsCount += 1;
        meta.updatedAt = block.timestamp;

        payout.claimId = _claimId;
        payout.data = _data;
        payout.state = PayoutState.Expected;
        payout.createdAt = block.timestamp;
        payout.updatedAt = block.timestamp;

        emit LogNewPayout(_bpKey, _claimId, _payoutId, PayoutState.Expected);
    }

    function payOut(
        bytes32 _bpKey,
        uint256 _payoutId,
        bool _fullPayout,
        bytes calldata _data
    )
        external override 
        onlyPolicyFlow("Policy")
    {
        Metadata memory meta = metadata[_bpKey];
        require(meta.createdAt > 0, "ERROR:POC-043:METADATA_DOES_NOT_EXIST");

        Payout storage payout = payouts[_bpKey][_payoutId];
        require(payout.createdAt > 0, "ERROR:POC-044:PAYOUT_DOES_NOT_EXIST");
        require(payout.state == PayoutState.Expected, "ERROR:POC-045:PAYOUT_ALREADY_COMPLETED");

        payout.data = _data;
        payout.updatedAt = block.timestamp;

        if (_fullPayout) {
            payout.state = PayoutState.PaidOut;
            emit LogPayoutCompleted(_bpKey, _payoutId, payout.state);
        } else {
            emit LogPartialPayout(_bpKey, _payoutId, payout.state);
        }
    }

    function setPayoutState(
        bytes32 _bpKey,
        uint256 _payoutId,
        PayoutState _state
    ) 
        external override 
        onlyPolicyFlow("Policy")
    {
        Payout storage payout = payouts[_bpKey][_payoutId];
        require(payout.createdAt > 0, "ERROR:POC-046:PAYOUT_DOES_NOT_EXIST");

        payout.state = _state;
        payout.updatedAt = block.timestamp;

        emit LogPayoutStateChanged(_bpKey, _payoutId, _state);
    }

    function getMetadata(bytes32 _bpKey)
        public override
        view
        returns (IPolicy.Metadata memory _metadata)
    {
        _metadata = metadata[_bpKey];
        require(_metadata.createdAt > 0,  "ERROR:POC-050:METADATA_DOES_NOT_EXIST");
    }

    function getApplication(bytes32 _bpKey)
        public override
        view
        returns (IPolicy.Application memory _application)
    {
        _application = applications[_bpKey];
        require(_application.createdAt > 0, "ERROR:POC-051:APPLICATION_DOES_NOT_EXIST");        
    }

    function getPolicy(bytes32 _bpKey)
        public override
        view
        returns (IPolicy.Policy memory _policy)
    {
        _policy = policies[_bpKey];
        require(_policy.createdAt > 0, "ERROR:POC-052:POLICY_DOES_NOT_EXIST");        
    }

    function getClaim(bytes32 _bpKey, uint256 _claimId)
        public override
        view
        returns (IPolicy.Claim memory _claim)
    {
        _claim = claims[_bpKey][_claimId];
        require(_claim.createdAt > 0, "ERROR:POC-053:CLAIM_DOES_NOT_EXIST");        
    }

    function getPayout(bytes32 _bpKey, uint256 _payoutId)
        public override
        view
        returns (IPolicy.Payout memory _payout)
    {
        _payout = payouts[_bpKey][_payoutId];
        require(_payout.createdAt > 0, "ERROR:POC-054:PAYOUT_DOES_NOT_EXIST");        
    }

    function getBpKeyCount() external override view returns (uint256 _count) {
        return bpKeys.length;
    }
}
