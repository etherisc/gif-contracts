// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/IClaims.sol";
import "../shared/WithRegistry.sol";
// import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/ILicense.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/modules/IRegistry.sol";
import "@gif-interface/contracts/modules/IUnderwriting.sol";

// import "@gif-interface/contracts/modules/IClaims.sol";
// import "@gif-interface/contracts/modules/IRiskpool.sol";

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
        bytes32 processId,
        uint256 premiumAmount,
        uint256 sumInsuredAmount,
        bytes calldata metaData, 
        bytes calldata applicationData 
    )
        external 
    {
        ILicense license = getLicenseContract();
        uint256 productId = license.getProductId(msg.sender);

        IPolicy policy = getPolicyContract();
        policy.createPolicyFlow(processId, metaData);
        policy.createApplication(
            productId, 
            processId, 
            premiumAmount, 
            sumInsuredAmount, 
            applicationData);
    }

    function underwrite(bytes32 processId) external {
        IUnderwriting underwriting = getUnderwritingContract();
        bool success = underwriting.underwrite(processId);
        require(success, "ERROR:PFD-002:UNDERWRITING_FAILED");

        IPolicy policy = getPolicyContract();
        policy.createPolicy(processId);
    }

    function decline(bytes32 processId) external {
        IPolicy policy = getPolicyContract();
        require(
            policy.getApplication(processId).state ==
                IPolicy.ApplicationState.Applied,
            "ERROR:PFD-004:INVALID_APPLICATION_STATE"
        );

        policy.setApplicationState(processId, IPolicy.ApplicationState.Declined);
    }

    function newClaim(bytes32 processId, bytes calldata data)
        external
        onlyActivePolicy(processId)
        returns (uint256 claimId)
    {
        claimId = getPolicyContract().createClaim(processId, data);
    }

    function confirmClaim(
        bytes32 processId,
        uint256 claimId,
        uint256 payoutAmount,
        bytes calldata data
    ) external returns (uint256 _payoutId) {
        IPolicy policy = getPolicyContract();
        require(
            policy.getClaim(processId, claimId).state ==
            IPolicy.ClaimState.Applied,
            "ERROR:PFD-010:INVALID_CLAIM_STATE"
        );

        policy.setClaimState(processId, claimId, IPolicy.ClaimState.Confirmed);

        _payoutId = policy.createPayout(processId, claimId, payoutAmount, data);
    }

    function declineClaim(bytes32 processId, uint256 _claimId) external {
        IPolicy policy = getPolicyContract();
        require(
            policy.getClaim(processId, _claimId).state ==
            IPolicy.ClaimState.Applied,
            "ERROR:PFD-011:INVALID_CLAIM_STATE"
        );

        policy.setClaimState(processId, _claimId, IPolicy.ClaimState.Declined);
    }

    function expire(bytes32 processId) 
        external
        onlyActivePolicy(processId)
    {
        IPolicy policy = getPolicyContract();
        policy.setPolicyState(processId, IPolicy.PolicyState.Expired);
    }

    function processPayout(
        bytes32 processId,
        uint256 payoutId,
        bool isComplete,
        bytes calldata data
    ) external {
        getPolicyContract().processPayout(processId, payoutId, isComplete, data);
    }

    function request(
        bytes32 processId,
        bytes calldata _input,
        string calldata _callbackMethodName,
        address _callbackContractAddress,
        uint256 _responsibleOracleId
    ) 
        external 
        returns (uint256 _requestId) 
    {
        _requestId = getQueryContract().request(
            processId,
            _input,
            _callbackMethodName,
            _callbackContractAddress,
            _responsibleOracleId
        );
    }

    function getApplicationData(bytes32 processId)
        external
        view
        returns (bytes memory)
    {
        IPolicy policy = getPolicyContract();
        return policy.getApplication(processId).data;
    }

    function getClaimData(bytes32 processId, uint256 claimId)
        external
        view
        returns (bytes memory)
    {
        IPolicy policy = getPolicyContract();
        return policy.getClaim(processId, claimId).data;
    }

    function getPayoutData(bytes32 processId, uint256 payoutId)
        external
        view
        returns (bytes memory)
    {
        IPolicy policy = getPolicyContract();
        return policy.getPayout(processId, payoutId).data;
    }

    function getLicenseContract() internal view returns (ILicense) {
        return ILicense(getContractFromRegistry("License"));
    }

    function getUnderwritingContract() internal view returns (IUnderwriting) {
        return IUnderwriting(getContractFromRegistry("Underwriting"));
    }

    function getPolicyContract() internal view returns (IPolicy) {
        return IPolicy(getContractFromRegistry("Policy"));
    }

    function getQueryContract() internal view returns (IQuery) {
        return IQuery(getContractFromRegistry("Query"));
    }

    function getClaimsContract() internal view returns (IClaims) {
        return IClaims(getContractFromRegistry("Claims"));
    }

    // function getContractFromRegistry(bytes32 moduleName) internal view returns(address) {
    //     return _getContractAddress(moduleName);
    // }
}
