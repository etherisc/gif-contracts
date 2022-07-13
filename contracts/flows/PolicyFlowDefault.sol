// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/PoolController.sol";
import "../modules/PolicyController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/WithRegistry.sol";
// import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/ILicense.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";
import "@gif-interface/contracts/modules/IQuery.sol";
import "@gif-interface/contracts/modules/IRegistry.sol";
import "@gif-interface/contracts/modules/IPool.sol";

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

    modifier onlyActivePolicy(bytes32 processId) {
        PolicyController policy = getPolicyContract();
        require(
            policy.getPolicy(processId).state == IPolicy.PolicyState.Active,
            "ERROR:PFD-001:POLICY_NOT_ACTIVE"
        );
        _;
    }

    // solhint-disable-next-line no-empty-blocks
    constructor(address _registry) 
        WithRegistry(_registry) 
    { }

    function newApplication(
        address owner,
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
        policy.createPolicyFlow(owner, processId, productId, metaData);
        policy.createApplication(
            processId, 
            premiumAmount, 
            sumInsuredAmount, 
            applicationData);
    }

    /* success implies the successful creation of a policy */
    function underwrite(bytes32 processId) external returns(bool success){
        IPool pool = getPoolContract();
        success = pool.underwrite(processId);

        if (success) {
            ITreasury treasury = getTreasuryContract();
            success = treasury.processPremium(processId);
            require(success, "ERROR:PFD-004:PREMIUM_TRANSFER_FAILED");

            IPolicy policy = getPolicyContract();
            policy.setApplicationState(processId, IPolicy.ApplicationState.Underwritten);
            policy.createPolicy(processId);
        }
    }

    function decline(bytes32 processId) external {
        PolicyController policy = getPolicyContract();
        require(
            policy.getApplication(processId).state == IPolicy.ApplicationState.Applied,
            "ERROR:PFD-005:INVALID_APPLICATION_STATE"
        );

        policy.setApplicationState(processId, IPolicy.ApplicationState.Declined);
    }

    function newClaim(
        bytes32 processId, 
        uint256 claimAmount,
        bytes calldata data
    )
        external
        onlyActivePolicy(processId)
        returns (uint256 claimId)
    {
        claimId = getPolicyContract().createClaim(
            processId, 
            claimAmount,
            data);
    }

    function confirmClaim(
        bytes32 processId,
        uint256 claimId,
        uint256 payoutAmount,
        bytes calldata data
    ) external returns (uint256 _payoutId) {
        PolicyController policy = getPolicyContract();
        require(
            policy.getClaim(processId, claimId).state ==
            IPolicy.ClaimState.Applied,
            "ERROR:PFD-010:INVALID_CLAIM_STATE"
        );

        policy.setClaimState(processId, claimId, IPolicy.ClaimState.Confirmed);

        _payoutId = policy.createPayout(processId, claimId, payoutAmount, data);
    }

    function declineClaim(bytes32 processId, uint256 _claimId) external {
        PolicyController policy = getPolicyContract();
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
        IPool pool = getPoolContract();
        pool.expire(processId);

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
        PolicyController policy = getPolicyContract();
        return policy.getApplication(processId).data;
    }

    function getClaimData(bytes32 processId, uint256 claimId)
        external
        view
        returns (bytes memory)
    {
        PolicyController policy = getPolicyContract();
        return policy.getClaim(processId, claimId).data;
    }

    function getPayoutData(bytes32 processId, uint256 payoutId)
        external
        view
        returns (bytes memory)
    {
        PolicyController policy = getPolicyContract();
        return policy.getPayout(processId, payoutId).data;
    }

    function getLicenseContract() internal view returns (ILicense) {
        return ILicense(getContractFromRegistry("License"));
    }

    function getPoolContract() internal view returns (IPool) {
        return IPool(getContractFromRegistry("Pool"));
    }

    function getPolicyContract() internal view returns (PolicyController) {
        return PolicyController(getContractFromRegistry("Policy"));
    }

    function getQueryContract() internal view returns (IQuery) {
        return IQuery(getContractFromRegistry("Query"));
    }

    function getTreasuryContract() internal view returns (ITreasury) {
        return ITreasury(getContractFromRegistry("Treasury"));
    }

    // function getContractFromRegistry(bytes32 moduleName) internal view returns(address) {
    //     return _getContractAddress(moduleName);
    // }
}
