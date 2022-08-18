// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ComponentController.sol";
import "../modules/PoolController.sol";
import "../modules/PolicyController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/WithRegistry.sol";

import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";
import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";
import "@etherisc/gif-interface/contracts/modules/IPool.sol";

/*
 * PolicyFlowDefault is a delegate of ProductService.sol.
 * Access Control is maintained:
 * 1) by checking condition in ProductService.sol
 * 2) by modifiers "onlyPolicyFlow" in StakeController.sol
 * For all functions here, msg.sender is = address of ProductService.sol which is registered in the Registry.
 * (if not, it reverts in StakeController.sol)
 */

contract PolicyDefaultFlow is 
    WithRegistry 
{
    bytes32 public constant NAME = "PolicyDefaultFlow";

    modifier onlyActivePolicy(bytes32 processId) {
        PolicyController policy = getPolicyContract();
        require(
            policy.getPolicy(processId).state == IPolicy.PolicyState.Active,
            "ERROR:PFD-001:POLICY_NOT_ACTIVE"
        );
        _;
    }

    modifier onlyExpiredPolicy(bytes32 processId) {
        PolicyController policy = getPolicyContract();
        require(
            policy.getPolicy(processId).state == IPolicy.PolicyState.Expired,
            "ERROR:PFD-002:POLICY_NOT_EXPIRED"
        );
        _;
    }

    modifier onlyResponsibleProduct(bytes32 processId) {
        PolicyController policy = getPolicyContract();
        IPolicy.Metadata memory metadata = policy.getMetadata(processId);
        ComponentController component = ComponentController(getContractFromRegistry("Component"));
        require(metadata.productId == component.getComponentId(address(msg.sender)), "ERROR:PFD-003:PROCESSID_PRODUCT_MISMATCH");
        _;
    }

    // ComponentController private _component;

    // solhint-disable-next-line no-empty-blocks
    constructor(address _registry) 
        WithRegistry(_registry) 
    { 
    }

    function newApplication(
        address owner,
        uint256 premiumAmount,
        uint256 sumInsuredAmount,
        bytes calldata metaData, 
        bytes calldata applicationData 
    )
        external 
        returns(bytes32 processId)
    {
        ComponentController component = getComponentContract();
        uint256 productId = component.getComponentId(msg.sender);

        IPolicy policy = getPolicyContract();
        processId = policy.createPolicyFlow(owner, productId, metaData);
        policy.createApplication(
            processId, 
            premiumAmount, 
            sumInsuredAmount, 
            applicationData);
    }

    function revoke(bytes32 processId)
        external 
        onlyResponsibleProduct(processId)
    {
        IPolicy policy = getPolicyContract();
        policy.revokeApplication(processId);
    }

    /* success implies the successful creation of a policy */
    function underwrite(bytes32 processId) 
        external 
        onlyResponsibleProduct(processId)
        returns(bool success) 
    {
        // attempt to get the collateral to secure the policy
        PoolController pool = getPoolContract();
        success = pool.underwrite(processId);

        if (success) {
            PolicyController policyController = getPolicyContract();
            policyController.underwriteApplication(processId);
            policyController.createPolicy(processId);

            // transfer premium amount
            IPolicy.Policy memory policy = policyController.getPolicy(processId);
            collectPremium(processId, policy.premiumExpectedAmount);
        }
    }

    /* success implies the successful collection of the amount for the policy.
     * valid amounts need to be > 0 up to the full premium amount
     * if no fee structure is defined for the policy, this call will revert. 
     */
    function collectPremium(bytes32 processId, uint256 amount) 
        public 
        onlyResponsibleProduct(processId)
        returns(
            bool success, 
            uint256 feeAmount, 
            uint256 netPremiumAmount
        ) 
    {
        TreasuryModule treasury = getTreasuryContract();
        PolicyController policy = getPolicyContract();
        address owner = policy.getMetadata(processId).owner;

        (success, feeAmount, netPremiumAmount) = treasury.processPremium(processId, amount);

        // if premium collected: update book keeping of policy and riskpool
        if (success) {
            policy.collectPremium(processId, netPremiumAmount + feeAmount);

            PoolController pool = getPoolContract();
            pool.increaseBalance(processId, netPremiumAmount);
        }
    }

    function decline(bytes32 processId) 
        onlyResponsibleProduct(processId)
        external 
    {
        IPolicy policy = getPolicyContract();
        policy.declineApplication(processId);
    }

    function expire(bytes32 processId) 
        external
        onlyActivePolicy(processId)
        onlyResponsibleProduct(processId)
    {
        IPolicy policy = getPolicyContract();
        policy.expirePolicy(processId);
    }

    function close(bytes32 processId) 
        external
        onlyExpiredPolicy(processId)
        onlyResponsibleProduct(processId)
    {
        IPolicy policy = getPolicyContract();
        policy.closePolicy(processId);

        IPool pool = getPoolContract();
        pool.release(processId);
    }

    function newClaim(
        bytes32 processId, 
        uint256 claimAmount,
        bytes calldata data
    )
        external
        onlyActivePolicy(processId)
        onlyResponsibleProduct(processId)
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
        uint256 confirmedAmount
    ) 
        external
        onlyResponsibleProduct(processId) 
    {
        PolicyController policy = getPolicyContract();
        policy.confirmClaim(processId, claimId, confirmedAmount);
    }

    function declineClaim(bytes32 processId, uint256 claimId) 
        external 
        onlyResponsibleProduct(processId)
    {
        PolicyController policy = getPolicyContract();
        policy.declineClaim(processId, claimId);
    }

    function closeClaim(bytes32 processId, uint256 claimId) 
        external 
        onlyResponsibleProduct(processId)
    {
        PolicyController policy = getPolicyContract();
        policy.closeClaim(processId, claimId);
    }

    function newPayout(
        bytes32 processId,
        uint256 claimId,
        uint256 amount,
        bytes calldata data
    ) 
        external 
        onlyResponsibleProduct(processId)
        returns(uint256 payoutId)
    {
        payoutId = getPolicyContract()
            .createPayout(processId, claimId, amount, data);
    }

    function processPayout(
        bytes32 processId,
        uint256 payoutId
    )
        external 
        onlyResponsibleProduct(processId)
        returns(
            bool success,
            uint256 feeAmount,
            uint256 netPayoutAmount
        )
    {
        TreasuryModule treasury = getTreasuryContract();
        (feeAmount, netPayoutAmount) = treasury.processPayout(processId, payoutId);

        // if payout successful: update book keeping of policy and riskpool
        IPolicy policy = getPolicyContract();
        policy.processPayout(processId, payoutId);

        PoolController pool = getPoolContract();
        pool.decreaseBalance(processId, netPayoutAmount + feeAmount);
    }

    function request(
        bytes32 processId,
        bytes calldata _input,
        string calldata _callbackMethodName,
        address _callbackContractAddress,
        uint256 _responsibleOracleId
    ) 
        external 
        onlyResponsibleProduct(processId)
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

    function getComponentContract() internal view returns (ComponentController) {
        return ComponentController(getContractFromRegistry("Component"));
    }

    function getPoolContract() internal view returns (PoolController) {
        return PoolController(getContractFromRegistry("Pool"));
    }

    function getPolicyContract() internal view returns (PolicyController) {
        return PolicyController(getContractFromRegistry("Policy"));
    }

    function getQueryContract() internal view returns (IQuery) {
        return IQuery(getContractFromRegistry("Query"));
    }

    function getTreasuryContract() internal view returns (TreasuryModule) {
        return TreasuryModule(getContractFromRegistry("Treasury"));
    }

    // function getContractFromRegistry(bytes32 moduleName) internal view returns(address) {
    //     return _getContractAddress(moduleName);
    // }
}
