// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../modules/ComponentController.sol";
import "../modules/PoolController.sol";
import "../modules/PolicyController.sol";
import "../modules/QueryModule.sol";
import "../modules/TreasuryModule.sol";
import "../shared/WithRegistry.sol";

import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";
// import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";
import "@etherisc/gif-interface/contracts/modules/IPool.sol";


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

    modifier notClosedPolicy(bytes32 processId) {
        PolicyController policy = getPolicyContract();
        require(
            policy.getPolicy(processId).state != IPolicy.PolicyState.Closed,
            "ERROR:PFD-003:POLICY_CLOSED"
        );
        _;
    }

    modifier onlyResponsibleProduct(bytes32 processId) {
        PolicyController policy = getPolicyContract();
        IPolicy.Metadata memory metadata = policy.getMetadata(processId);
        ComponentController component = ComponentController(getContractFromRegistry("Component"));
        require(metadata.productId == component.getComponentId(address(msg.sender)), "ERROR:PFD-004:PROCESSID_PRODUCT_MISMATCH");
        _;
    }

    modifier onlyMatchingProduct(uint256 requestId) {
        QueryModule query = getQueryContract();
        bytes32 processId = getQueryContract().getProcessId(requestId);
        PolicyController policy = getPolicyContract();
        IPolicy.Metadata memory metadata = policy.getMetadata(processId);
        ComponentController component = ComponentController(getContractFromRegistry("Component"));
        require(metadata.productId == component.getComponentId(address(msg.sender)), "ERROR:PFD-005:REQUESTID_PRODUCT_MISMATCH");
        _;
    }

    // ComponentController private _component;

    // solhint-disable-next-line no-empty-blocks
    /**
     * @dev Constructor function that initializes the contract with a given registry address.
     * @param _registry The address of the registry contract.
     */
    constructor(address _registry) 
        WithRegistry(_registry) 
    { 
    }

    /**
     * @dev Creates a new insurance application and returns the process ID.
     * @param owner The address of the owner of the new application.
     * @param premiumAmount The amount of premium to be paid for the application.
     * @param sumInsuredAmount The amount of insurance coverage requested for the application.
     * @param metaData Additional metadata for the application.
     * @param applicationData Additional data for the application.
     * @return processId The unique process ID of the created application.
     */
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

    /**
     * @dev Revokes an application for a specific processId.
     * @param processId The unique identifier of the process.
     */
    function revoke(bytes32 processId)
        external 
        onlyResponsibleProduct(processId)
    {
        IPolicy policy = getPolicyContract();
        policy.revokeApplication(processId);
    }

    /* success implies the successful creation of a policy */
    /**
     * @dev Attempts to get the collateral to secure the policy.
     * @param processId The unique identifier of the underwriting process.
     * @return success A boolean indicating whether the underwriting was successful.
     *
     * If successful, creates a policy and transfers the premium amount.
     * The premium collection part is a TODO and should be implemented on the product level.
     * This function should only be called by a responsible product.
     * */
    function underwrite(bytes32 processId) 
        external 
        onlyResponsibleProduct(processId)
        returns(bool success) 
    {
        // attempt to get the collateral to secure the policy
        PoolController pool = getPoolContract();
        success = pool.underwrite(processId);

        // TODO remove premium collection part below
        // this should be implemented on the prduct level
        // it's too much magic in the platform and not transparent enough
        // also, bad naming: the function name is 'underwrite? and not
        // 'underwriteAndIfSuccessfulCollectPremiumToo'
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
    /**
     * @dev Collects the premium for a given policy and updates the book keeping of the policy and the risk pool.
     * @param processId The ID of the premium payment process.
     * @param amount The amount of premium to be collected.
     * @return success A boolean indicating whether the premium collection was successful or not.
     * @return feeAmount The amount of fee collected by the treasury module.
     * @return netPremiumAmount The net amount of premium collected after deducting the fee.
     */
    function collectPremium(bytes32 processId, uint256 amount) 
        public 
        notClosedPolicy(processId)
        onlyResponsibleProduct(processId)
        returns(
            bool success, 
            uint256 feeAmount, 
            uint256 netPremiumAmount
        ) 
    {
        TreasuryModule treasury = getTreasuryContract();
        PolicyController policy = getPolicyContract();

        (success, feeAmount, netPremiumAmount) = treasury.processPremium(processId, amount);

        // if premium collected: update book keeping of policy and riskpool
        if (success) {
            policy.collectPremium(processId, netPremiumAmount + feeAmount);

            PoolController pool = getPoolContract();
            pool.processPremium(processId, netPremiumAmount);
        }
    }
    
    /**
     * @dev Adjusts the premium and sum insured amounts of a policy.
     * @param processId The ID of the policy process.
     * @param expectedPremiumAmount The expected premium amount.
     * @param sumInsuredAmount The sum insured amount.
     */
    function adjustPremiumSumInsured(
        bytes32 processId, 
        uint256 expectedPremiumAmount,
        uint256 sumInsuredAmount
    )
        external
        notClosedPolicy(processId)
        onlyResponsibleProduct(processId)
    {
        PolicyController policy = getPolicyContract();
        policy.adjustPremiumSumInsured(processId, expectedPremiumAmount, sumInsuredAmount);
    }


    /**
     * @dev Allows the responsible product to decline an application for a policy.
     * @param processId The unique identifier of the application process.
     */
    function decline(bytes32 processId) 
        onlyResponsibleProduct(processId)
        external 
    {
        IPolicy policy = getPolicyContract();
        policy.declineApplication(processId);
    }

    /**
     * @dev Expire the policy identified by the given process ID.
     * @param processId The ID of the process corresponding to the policy to be expired.
     */
    function expire(bytes32 processId) 
        external
        onlyActivePolicy(processId)
        onlyResponsibleProduct(processId)
    {
        IPolicy policy = getPolicyContract();
        policy.expirePolicy(processId);
    }

    /**
     * @dev Closes a policy and releases the corresponding funds from the pool.
     * @param processId The ID of the policy to be closed.
     */
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

    /**
     * @dev Creates a new claim for a given process ID, claim amount and data.
     * @param processId The ID of the process to create the claim for.
     * @param claimAmount The amount of the claim to be created.
     * @param data Additional data to be included with the claim.
     * @return claimId The ID of the newly created claim.
     */
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

    /**
     * @dev Confirms a claim for a specific process and claim ID, updating the confirmed amount.
     * @param processId The ID of the process where the claim was made.
     * @param claimId The ID of the claim to be confirmed.
     * @param confirmedAmount The amount confirmed for the claim.
     */
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

    /**
     * @dev Allows the responsible product to decline a claim.
     * @param processId The unique identifier of the claim process.
     * @param claimId The unique identifier of the claim to be declined.
     */
    function declineClaim(bytes32 processId, uint256 claimId) 
        external 
        onlyResponsibleProduct(processId)
    {
        PolicyController policy = getPolicyContract();
        policy.declineClaim(processId, claimId);
    }

    /**
     * @dev Closes a claim for a specific process and claim ID.
     * @param processId The ID of the process to which the claim belongs.
     * @param claimId The ID of the claim to be closed.
     */
    function closeClaim(bytes32 processId, uint256 claimId) 
        external 
        onlyResponsibleProduct(processId)
    {
        PolicyController policy = getPolicyContract();
        policy.closeClaim(processId, claimId);
    }

    /**
     * @dev Creates a new payout for a specific claim.
     * @param processId The ID of the process associated with the claim.
     * @param claimId The ID of the claim for which the payout is being created.
     * @param amount The amount of the payout to be created.
     * @param data Additional data related to the payout.
     * @return payoutId The ID of the newly created payout.
     */
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

    /**
     * @dev Processes a payout for a specific process and payout ID.
     * @param processId The ID of the process for which the payout is being processed.
     * @param payoutId The ID of the payout being processed.
     * @return success A boolean indicating whether the payout was successfully processed.
     * @return feeAmount The amount of fees deducted from the payout.
     * @return netPayoutAmount The net amount paid out to the policyholder after deducting fees.
     */
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
        pool.processPayout(processId, netPayoutAmount + feeAmount);
    }

    /**
     * @dev Sends a request to the query contract to initiate a new process.
     * @param processId The ID of the process to be initiated.
     * @param _input The input data for the process.
     * @param _callbackMethodName The name of the callback method in the callback contract.
     * @param _callbackContractAddress The address of the callback contract.
     * @param _responsibleOracleId The ID of the oracle responsible for handling the request.
     * @return _requestId The ID of the new request.
     */
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

    /**
     * @dev Cancels a request with the given requestId.
     * @param requestId The ID of the request to be cancelled.
     */
    function cancelRequest(
        uint256 requestId
    ) 
        external 
        onlyMatchingProduct(requestId)
    {
        getQueryContract().cancel(requestId);
    }

    /**
     * @dev Returns the application data associated with the given process ID.
     * @param processId The ID of the process.
     * @return data The application data as bytes.
     */
    function getApplicationData(bytes32 processId)
        external
        view
        returns (bytes memory)
    {
        PolicyController policy = getPolicyContract();
        return policy.getApplication(processId).data;
    }

    /**
     * @dev Returns the claim data of a specific claim for a given process ID.
     * @param processId The ID of the process the claim belongs to.
     * @param claimId The ID of the claim.
     * @return data The claim data as bytes.
     */
    function getClaimData(bytes32 processId, uint256 claimId)
        external
        view
        returns (bytes memory)
    {
        PolicyController policy = getPolicyContract();
        return policy.getClaim(processId, claimId).data;
    }

    /**
     * @dev Returns the payout data for a given process and payout ID.
     * @param processId The ID of the process.
     * @param payoutId The ID of the payout.
     * @return data The payout data as a bytes array.
     */
    function getPayoutData(bytes32 processId, uint256 payoutId)
        external
        view
        returns (bytes memory)
    {
        PolicyController policy = getPolicyContract();
        return policy.getPayout(processId, payoutId).data;
    }

    /**
     * @dev Returns the ComponentController contract instance.
     * @return The ComponentController contract instance.
     */
    function getComponentContract() internal view returns (ComponentController) {
        return ComponentController(getContractFromRegistry("Component"));
    }

    /**
     * @dev Returns the PoolController contract instance from the registry.
     * @return poolController The PoolController contract instance.
     */
    function getPoolContract() internal view returns (PoolController) {
        return PoolController(getContractFromRegistry("Pool"));
    }

    /**
     * @dev Returns the PolicyController contract instance from the registry.
     * @return The PolicyController contract instance.
     */
    function getPolicyContract() internal view returns (PolicyController) {
        return PolicyController(getContractFromRegistry("Policy"));
    }

    /**
     * @dev Returns the QueryModule contract instance from the registry.
     * @return QueryModule instance.
     */
    function getQueryContract() internal view returns (QueryModule) {
        return QueryModule(getContractFromRegistry("Query"));
    }

    /**
     * @dev Retrieves the TreasuryModule contract instance.
     * @return The instance of the TreasuryModule contract.
     */
    function getTreasuryContract() internal view returns (TreasuryModule) {
        return TreasuryModule(getContractFromRegistry("Treasury"));
    }
}
