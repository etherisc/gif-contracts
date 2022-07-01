// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/WithRegistry.sol";
// import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/ILicense.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";
import "@gif-interface/contracts/modules/IQuery.sol";

/*
 * PolicyFlowDefault is a delegate of ProductService.sol.
 * Access Control is maintained:
 * 1) by checking condition in ProductService.sol
 * 2) by modifiers "onlyPolicyFlow" in StakeController.sol
 * For all functions here, msg.sender is = address of ProductService.sol which is registered in the Registry.
 * (if not, it reverts in StakeController.sol)
 */

contract PolicyFlowDefault is 
    WithRegistry 
    // CoreController
{
    bytes32 public constant NAME = "PolicyFlowDefault";

    modifier onlyActivePolicy(bytes32 _bpKey) {
        IPolicy policy = getPolicyContract();
        require(
            policy.getPolicy(_bpKey).state == IPolicy.PolicyState.Active,
            "ERROR:PFD-001:POLICY_NOT_ACTIVE"
        );
        _;
    }

    // solhint-disable-next-line no-empty-blocks
    constructor(address _registry) 
        WithRegistry(_registry) 
    { }

    function newApplication(
        bytes32 _bpKey,
        bytes calldata _data 
    )
        external 
    {
        ILicense license = getLicenseContract();
        uint256 productId = license.getProductId(msg.sender);

        IPolicy policy = getPolicyContract();
        policy.createPolicyFlow(productId, _bpKey);
        policy.createApplication(_bpKey, _data);
    }

    function underwrite(bytes32 processId) external {
        IPolicy policy = getPolicyContract();
        IPolicy.Application application = policy.getApplication(_bpKey);
        require(
            policy.getApplication(processId).state ==
                IPolicy.ApplicationState.Applied,
            "ERROR:PFD-002:INVALID_APPLICATION_STATE"
        );

        // TODO check sum insured can be covered by risk pool
        // 1 get set of nft covering this policy
        // 2 get free capacity per covering nft
        // 3 ensure total free capacity >= sum insure
        // 4 lock capacity in participating nft according to allocated capacity fraction per nft
        // 5 inform that cpacity is available
        // 6 continue here (steps 1-6 to be handled pool internally)

        IRiskpool riskpool = getRiskpoolContract();
        bool isSecured = riskpool.securePolicy(processId);
        require(isSecured, "ERROR:PFD-003:RISK_CAPITAL_UNAVAILABLE");

        // make sure premium amount is available
        // TODO move this to treasury
        require(
            _token.allowance(policyHolder, address(this)) >= premium, 
            "ERROR:TI-3:PREMIUM_NOT_COVERED"
        );

        // check how to distribute premium
        IPricing pricing = getPricingContract();
        (uint256 feeAmount, uint256 capitalAmount) = pricing.getPremiumSplit(processId);

        ITreasury treasury = getContract();
        bool isTransferred = treasury.transferPremium(processId, feeAmount, capitalAmount);
        require(isTransferred, "ERROR:PFD-003:PREMIUM_TRANSFER_FAILED");

        // final step create policy after successful underwriting
        policy.setApplicationState(processId, IPolicy.ApplicationState.Underwritten);
        policy.createPolicy(processId);
    }

    function decline(bytes32 _bpKey) external {
        IPolicy policy = getPolicyContract();
        require(
            policy.getApplication(_bpKey).state ==
                IPolicy.ApplicationState.Applied,
            "ERROR:PFD-004:INVALID_APPLICATION_STATE"
        );

        policy.setApplicationState(_bpKey, IPolicy.ApplicationState.Declined);
    }

    function newClaim(bytes32 _bpKey, bytes calldata _data)
        external
        onlyActivePolicy(_bpKey)
        returns (uint256 _claimId)
    {
        _claimId = getPolicyContract().createClaim(_bpKey, _data);
    }

    function confirmClaim(
        bytes32 _bpKey,
        uint256 _claimId,
        bytes calldata _data
    ) external returns (uint256 _payoutId) {
        IPolicy policy = getPolicyContract();
        require(
            policy.getClaim(_bpKey, _claimId).state ==
            IPolicy.ClaimState.Applied,
            "ERROR:PFD-010:INVALID_CLAIM_STATE"
        );

        policy.setClaimState(_bpKey, _claimId, IPolicy.ClaimState.Confirmed);

        _payoutId = policy.createPayout(_bpKey, _claimId, _data);
    }

    function declineClaim(bytes32 _bpKey, uint256 _claimId) external {
        IPolicy policy = getPolicyContract();
        require(
            policy.getClaim(_bpKey, _claimId).state ==
            IPolicy.ClaimState.Applied,
            "ERROR:PFD-011:INVALID_CLAIM_STATE"
        );

        policy.setClaimState(_bpKey, _claimId, IPolicy.ClaimState.Declined);
    }

    function expire(bytes32 _bpKey) 
        external
        onlyActivePolicy(_bpKey)
    {
        IPolicy policy = getPolicyContract();
        policy.setPolicyState(_bpKey, IPolicy.PolicyState.Expired);
    }

    function payout(
        bytes32 _bpKey,
        uint256 _payoutId,
        bool _complete,
        bytes calldata _data
    ) external {
        getPolicyContract().payOut(_bpKey, _payoutId, _complete, _data);
    }

    function request(
        bytes32 _bpKey,
        bytes calldata _input,
        string calldata _callbackMethodName,
        address _callbackContractAddress,
        uint256 _responsibleOracleId
    ) 
        external 
        returns (uint256 _requestId) 
    {
        _requestId = getQueryContract().request(
            _bpKey,
            _input,
            _callbackMethodName,
            _callbackContractAddress,
            _responsibleOracleId
        );
    }

    function getApplicationData(bytes32 _bpKey)
        external
        view
        returns (bytes memory _data)
    {
        IPolicy policy = getPolicyContract();
        return policy.getApplication(_bpKey).data;
    }

    function getClaimData(bytes32 _bpKey, uint256 _claimId)
        external
        view
        returns (bytes memory _data)
    {
        IPolicy policy = getPolicyContract();
        return policy.getClaim(_bpKey, _claimId).data;
    }

    function getPayoutData(bytes32 _bpKey, uint256 _payoutId)
        external
        view
        returns (bytes memory _data)
    {
        IPolicy policy = getPolicyContract();
        return policy.getPayout(_bpKey, _payoutId).data;
    }

    function getLicenseContract() internal view returns (ILicense) {
        return ILicense(getContractFromRegistry("License"));
    }

    function getPolicyContract() internal view returns (IPolicy) {
        return IPolicy(getContractFromRegistry("Policy"));
    }

    function getQueryContract() internal view returns (IQuery) {
        return IQuery(getContractFromRegistry("Query"));
    }

    // function getContractFromRegistry(bytes32 moduleName) internal view returns(address) {
    //     return _getContractAddress(moduleName);
    // }
}
