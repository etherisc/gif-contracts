// SPDX-License-Identifier: MIT
pragma solidity 0.8.2;

import "../shared/TransferHelper.sol";

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

import "@etherisc/gif-interface/contracts/components/Product.sol";
import "../modules/PolicyController.sol";

import "../modules/AccessController.sol";

contract AyiiProduct is 
    Product, 
    AccessControl,
    Initializable
{
    using EnumerableSet for EnumerableSet.Bytes32Set;

    bytes32 public constant NAME = "AreaYieldIndexProduct";
    bytes32 public constant VERSION = "0.1";
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";

    bytes32 public constant INSURER_ROLE = keccak256("INSURER");

    uint256 public constant PERCENTAGE_MULTIPLIER = 2**24;

    uint256 public constant AAAY_MIN = 0;
    uint256 public constant AAAY_MAX = 15;

    uint256 public constant RISK_APH_MAX = 15 * PERCENTAGE_MULTIPLIER;
    uint256 public constant RISK_EXIT_MAX = PERCENTAGE_MULTIPLIER / 5;
    uint256 public constant RISK_TSI_AT_EXIT_MIN = PERCENTAGE_MULTIPLIER / 2;

    // group policy data structure
    struct Risk {
        bytes32 id; // hash over projectId, uaiId, cropId
        bytes32 projectId; // assumption: this makes risk unique over aggregarors/customers/seasons
        bytes32 uaiId; // region id
        bytes32 cropId; // crop id
        uint256 trigger; // at and above this harvest ratio no payout is made 
        uint256 exit; // at and below this harvest ration the max payout is made
        uint256 tsi; // total sum insured at exit: max . payout percentage at exit
        uint256 aph; // average historical area yield for this crop and region
        uint256 requestId; 
        bool requestTriggered;
        uint256 responseAt;
        uint256 aaay; // average area yield for current season for this crop and region
        uint256 payoutPercentage; // payout percentage for this year for this crop and region
        uint256 createdAt;
        uint256 updatedAt;
    }

    uint256 private _oracleId;
    IERC20 private _token;

    bytes32 [] private _riskIds;
    mapping(bytes32 /* riskId */ => Risk) private _risks;
    mapping(bytes32 /* riskId */ => EnumerableSet.Bytes32Set /* processIds */) private _policies;
    bytes32 [] private _applications; // useful for debugging, might need to get rid of this

    event LogAyiiPolicyApplicationCreated(bytes32 policyId, address policyHolder, uint256 premiumAmount, uint256 sumInsuredAmount);
    event LogAyiiPolicyCreated(bytes32 policyId, address policyHolder, uint256 premiumAmount, uint256 sumInsuredAmount);
    event LogAyiiRiskDataCreated(bytes32 riskId, bytes32 productId, bytes32 uaiId, bytes32 cropId);
    event LogAyiiRiskDataBeforeAdjustment(bytes32 riskId, uint256 trigger, uint256 exit, uint256 tsi, uint aph);
    event LogAyiiRiskDataAfterAdjustment(bytes32 riskId, uint256 trigger, uint256 exit, uint256 tsi, uint aph);
    event LogAyiiRiskDataRequested(uint256 requestId, bytes32 riskId, bytes32 projectId, bytes32 uaiId, bytes32 cropId);
    event LogAyiiRiskDataReceived(uint256 requestId, bytes32 riskId, uint256 aaay);
    event LogAyiiRiskDataRequestCancelled(bytes32 processId, uint256 requestId);
    event LogAyiiRiskProcessed(bytes32 riskId, uint256 policies);
    event LogAyiiPolicyProcessed(bytes32 policyId);
    event LogAyiiClaimCreated(bytes32 policyId, uint256 claimId, uint256 payoutAmount);
    event LogAyiiPayoutCreated(bytes32 policyId, uint256 payoutAmount);

    event LogTransferHelperInputValidation1Failed(bool tokenIsContract, address from, address to);
    event LogTransferHelperInputValidation2Failed(uint256 balance, uint256 allowance);
    event LogTransferHelperCallFailed(bool callSuccess, uint256 returnDataLength, bytes returnData);

    /**
     * @dev Constructor function for creating a new instance of a Product contract.
     * @param productName Name of the product.
     * @param registry Address of the registry contract.
     * @param token Address of the token contract.
     * @param oracleId ID of the oracle.
     * @param riskpoolId ID of the risk pool.
     * @param insurer Address of the insurer.
     */
    constructor(
        bytes32 productName,
        address registry,
        address token,
        uint256 oracleId,
        uint256 riskpoolId,
        address insurer
    )
        Product(productName, token, POLICY_FLOW, riskpoolId, registry)
    {
        _token = IERC20(token);
        _oracleId = oracleId;

        _setupRole(DEFAULT_ADMIN_ROLE, _msgSender());
        _setupRole(INSURER_ROLE, insurer);
    }

    /**
     * @dev Creates a new risk for a project, UAI and crop with the specified parameters.
     * @param projectId The ID of the project associated with the risk.
     * @param uaiId The ID of the UAI associated with the risk.
     * @param cropId The ID of the crop associated with the risk.
     * @param trigger The trigger value for the risk.
     * @param exit The exit value for the risk.
     * @param tsi The total sum insured for the risk.
     * @param aph The area per hectare for the crop.
     * @return riskId The ID of the newly created risk.
     * @notice This function emits 1 events: 
     * - LogAyiiRiskDataCreated
     */
    function createRisk(
        bytes32 projectId,
        bytes32 uaiId,
        bytes32 cropId,
        uint256 trigger,
        uint256 exit,
        uint256 tsi,
        uint256 aph
    )
        external
        onlyRole(INSURER_ROLE)
        returns(bytes32 riskId)
    {
        _validateRiskParameters(trigger, exit, tsi, aph);

        riskId = getRiskId(projectId, uaiId, cropId);
        _riskIds.push(riskId);

        Risk storage risk = _risks[riskId];
        require(risk.createdAt == 0, "ERROR:AYI-001:RISK_ALREADY_EXISTS");

        risk.id = riskId;
        risk.projectId = projectId;
        risk.uaiId = uaiId;
        risk.cropId = cropId;
        risk.trigger = trigger;
        risk.exit = exit;
        risk.tsi = tsi;
        risk.aph = aph;
        risk.createdAt = block.timestamp; // solhint-disable-line
        risk.updatedAt = block.timestamp; // solhint-disable-line

        emit LogAyiiRiskDataCreated(
            risk.id, 
            risk.projectId,
            risk.uaiId, 
            risk.cropId);
    }

    /**
     * @dev Allows the insurer to adjust the parameters of an existing risk.
     * @param riskId The ID of the risk to be adjusted.
     * @param trigger The new trigger value for the risk.
     * @param exit The new exit value for the risk.
     * @param tsi The new total sum insured value for the risk.
     * @param aph The new annual premium value for the risk.
     *
     * Emits a LogAyiiRiskDataBeforeAdjustment event with the risk's data before adjustment.
     * Emits a LogAyiiRiskDataAfterAdjustment event with the risk's data after adjustment.
     *
     * Requirements:
     * - The caller must have the INSURER_ROLE.
     * - The risk must exist.
     * - The risk must have no policies associated with it.
     * @notice This function emits 2 events: 
     * - LogAyiiRiskDataAfterAdjustment
     * - LogAyiiRiskDataBeforeAdjustment
     */
    function adjustRisk(
        bytes32 riskId,
        uint256 trigger,
        uint256 exit,
        uint256 tsi,
        uint256 aph
    )
        external
        onlyRole(INSURER_ROLE)
    {
        _validateRiskParameters(trigger, exit, tsi, aph);

        Risk storage risk = _risks[riskId];
        require(risk.createdAt > 0, "ERROR:AYI-002:RISK_UNKNOWN");
        require(EnumerableSet.length(_policies[riskId]) == 0, "ERROR:AYI-003:RISK_WITH_POLICIES_NOT_ADJUSTABLE");

        emit LogAyiiRiskDataBeforeAdjustment(
            risk.id, 
            risk.trigger,
            risk.exit, 
            risk.tsi,
            risk.aph);
        
        risk.trigger = trigger;
        risk.exit = exit;
        risk.tsi = tsi;
        risk.aph = aph;

        emit LogAyiiRiskDataAfterAdjustment(
            risk.id, 
            risk.trigger,
            risk.exit, 
            risk.tsi,
            risk.aph);
    }

    /**
     * @dev Calculates the unique risk ID for a project, UAI and crop.
     * @param projectId The bytes32 ID of the project.
     * @param uaiId The bytes32 ID of the UAI.
     * @param cropId The bytes32 ID of the crop.
     * @return riskId The bytes32 ID of the unique risk.
     */
    function getRiskId(
        bytes32 projectId,
        bytes32 uaiId,
        bytes32 cropId
    )
        public
        pure
        returns(bytes32 riskId)
    {
        riskId = keccak256(abi.encode(projectId, uaiId, cropId));
    }


    /**
     * @dev Creates a new policy application for a given policy holder and risk.
     * @param policyHolder The address of the policy holder.
     * @param premium The amount of premium to be paid for the policy.
     * @param sumInsured The amount of coverage provided by the policy.
     * @param riskId The unique identifier of the risk associated with the policy.
     * @return processId The unique identifier of the newly created policy application.
     * @notice This function emits 2 events: 
     * - LogAyiiPolicyApplicationCreated
     * - LogAyiiPolicyCreated
     */
    function applyForPolicy(
        address policyHolder, 
        uint256 premium, 
        uint256 sumInsured,
        bytes32 riskId
    ) 
        external 
        onlyRole(INSURER_ROLE)
        returns(bytes32 processId)
    {
        Risk storage risk = _risks[riskId];
        require(risk.createdAt > 0, "ERROR:AYI-004:RISK_UNDEFINED");
        require(policyHolder != address(0), "ERROR:AYI-005:POLICY_HOLDER_ZERO");

        bytes memory metaData = "";
        bytes memory applicationData = abi.encode(riskId);

        processId = _newApplication(
            policyHolder, 
            premium, 
            sumInsured,
            metaData,
            applicationData);

        _applications.push(processId);

        emit LogAyiiPolicyApplicationCreated(
            processId, 
            policyHolder, 
            premium, 
            sumInsured);

        bool success = _underwrite(processId);

        if (success) {
            EnumerableSet.add(_policies[riskId], processId);
   
            emit LogAyiiPolicyCreated(
                processId, 
                policyHolder, 
                premium, 
                sumInsured);
        }
    }

    /**
     * @dev Allows the INSURER_ROLE to underwrite an insurance application for a given processId.
     * @param processId The unique identifier of the insurance application.
     * @return success A boolean indicating whether the underwriting process was successful or not.
     *
     * Emits a LogAyiiPolicyCreated event if the underwriting process is successful, containing the processId, the owner of the application, the premium amount and the sum insured amount.
     * @notice This function emits 1 events: 
     * - LogAyiiPolicyCreated
     */
    function underwrite(
        bytes32 processId
    ) 
        external 
        onlyRole(INSURER_ROLE)
        returns(bool success)
    {
        // ensure the application for processId exists
        _getApplication(processId);
        success = _underwrite(processId);

        if (success) {
            IPolicy.Application memory application = _getApplication(processId);
            IPolicy.Metadata memory metadata = _getMetadata(processId);
            emit LogAyiiPolicyCreated(
                processId, 
                metadata.owner, 
                application.premiumAmount, 
                application.sumInsuredAmount);
        }
    }

    /**
     * @dev Collects the premium for a specific policy.
     * @param policyId The ID of the policy for which to collect the premium.
     * @return success A boolean indicating whether the premium was collected successfully.
     * @return fee The fee collected by the insurer.
     * @return netPremium The net premium collected by the insurer after deducting the fee.
     */
    function collectPremium(bytes32 policyId) 
        external
        onlyRole(INSURER_ROLE)
        returns(bool success, uint256 fee, uint256 netPremium)
    {
        (success, fee, netPremium) = _collectPremium(policyId);
    }

    /* premium collection always moves funds from the customers wallet to the riskpool wallet.
     * to stick to this principle: this method implements a two part transferFrom. 
     * the 1st transfer moves the specified amount from the 'from' sender address to the customer
     * the 2nd transfer transfers the amount from the customer to the riskpool wallet (and some 
     * fees to the instance wallet)
     */ 
    /**
     * @dev Collects premium from a policyholder for a specific policy.
     * @param policyId The ID of the policy for which premium is being collected.
     * @param from The address of the policyholder from whom the premium is being collected.
     * @param amount The amount of premium being collected.
     * @return success A boolean indicating whether the premium collection was successful or not.
     * @return fee The fee charged for the premium collection.
     * @return netPremium The net premium collected after deducting the fee.
     */
    function collectPremium(bytes32 policyId, address from, uint256 amount) 
        external
        onlyRole(INSURER_ROLE)
        returns(bool success, uint256 fee, uint256 netPremium)
    {
        IPolicy.Metadata memory metadata = _getMetadata(policyId);

        if (from != metadata.owner) {
            bool transferSuccessful = TransferHelper.unifiedTransferFrom(_token, from, metadata.owner, amount);

            if (!transferSuccessful) {
                return (transferSuccessful, 0, amount);
            }
        }

        (success, fee, netPremium) = _collectPremium(policyId, amount);
    }

    /**
     * @dev Adjusts the premium and sum insured amounts for a given insurance process.
     * @param processId The unique identifier of the insurance process.
     * @param expectedPremiumAmount The expected premium amount for the insurance process.
     * @param sumInsuredAmount The sum insured amount for the insurance process.
     */
    function adjustPremiumSumInsured(
        bytes32 processId,
        uint256 expectedPremiumAmount,
        uint256 sumInsuredAmount
    )
        external
        onlyRole(INSURER_ROLE)
    {
        _adjustPremiumSumInsured(processId, expectedPremiumAmount, sumInsuredAmount);
    }

    /**
     * @dev Triggers an oracle request for a specific process ID.
     * @param processId The ID of the process to trigger the oracle request for.
     * @return requestId The ID of the oracle request triggered.
     *
     * Emits a LogAyiiRiskDataRequested event with the requestId, risk ID, project ID, UAI ID and crop ID.
     *
     * Requirements:
     * - Caller must have the INSURER_ROLE.
     * - The risk must be defined.
     * - The oracle must not have already responded to the request.
     * @notice This function emits 1 events: 
     * - LogAyiiRiskDataRequested
     */
    function triggerOracle(bytes32 processId) 
        external
        onlyRole(INSURER_ROLE)
        returns(uint256 requestId)
    {
        Risk storage risk = _risks[_getRiskId(processId)];
        require(risk.createdAt > 0, "ERROR:AYI-010:RISK_UNDEFINED");
        require(risk.responseAt == 0, "ERROR:AYI-011:ORACLE_ALREADY_RESPONDED");

        bytes memory queryData = abi.encode(
            risk.projectId,
            risk.uaiId,
            risk.cropId
        );

        requestId = _request(
                processId, 
                queryData,
                "oracleCallback",
                _oracleId
            );

        risk.requestId = requestId;
        risk.requestTriggered = true;
        risk.updatedAt = block.timestamp; // solhint-disable-line

        emit LogAyiiRiskDataRequested(
            risk.requestId, 
            risk.id, 
            risk.projectId, 
            risk.uaiId, 
            risk.cropId);
    }    

    /**
     * @dev Allows the insurer to cancel a specific oracle request for a given process ID.
     * @param processId The unique process ID associated with the risk.
     *
     * Emits a LogAyiiRiskDataRequestCancelled event indicating the cancellation of the oracle request.
     *
     * Requirements:
     * - The caller must have the INSURER_ROLE.
     * - The risk must exist in the _risks mapping.
     * - The oracle request must have been triggered for the risk.
     * - There must not be an existing callback for the oracle request.
     * @notice This function emits 1 events: 
     * - LogAyiiRiskDataRequestCancelled
     */
    function cancelOracleRequest(bytes32 processId) 
        external
        onlyRole(INSURER_ROLE)
    {
        Risk storage risk = _risks[_getRiskId(processId)];
        require(risk.createdAt > 0, "ERROR:AYI-012:RISK_UNDEFINED");
        require(risk.requestTriggered, "ERROR:AYI-013:ORACLE_REQUEST_NOT_FOUND");
        require(risk.responseAt == 0, "ERROR:AYI-014:EXISTING_CALLBACK");

        _cancelRequest(risk.requestId);

        // reset request id to allow to trigger again
        risk.requestTriggered = false;
        risk.updatedAt = block.timestamp; // solhint-disable-line

        emit LogAyiiRiskDataRequestCancelled(processId, risk.requestId);
    }    

    /**
     * @dev Callback function for the oracle to update the risk data for a project.
     * @param requestId The ID of the oracle request.
     * @param processId The ID of the oracle process.
     * @param responseData The response data from the oracle, which is expected to be an ABI-encoded tuple containing the following fields:
     *                      - projectId: The ID of the project.
     *                      - uaiId: The ID of the UAI.
     *                      - cropId: The ID of the crop.
     *                      - aaay: The AAAY value for the project.
     * @notice This function emits 1 events: 
     * - LogAyiiRiskDataReceived
     */
    function oracleCallback(
        uint256 requestId, 
        bytes32 processId, 
        bytes calldata responseData
    ) 
        external 
        onlyOracle
    {
        (
            bytes32 projectId, 
            bytes32 uaiId, 
            bytes32 cropId, 
            uint256 aaay
        ) = abi.decode(responseData, (bytes32, bytes32, bytes32, uint256));

        bytes32 riskId = _getRiskId(processId);
        require(riskId == getRiskId(projectId, uaiId, cropId), "ERROR:AYI-020:RISK_ID_MISMATCH");

        Risk storage risk = _risks[riskId];
        require(risk.createdAt > 0, "ERROR:AYI-021:RISK_UNDEFINED");
        require(risk.requestId == requestId, "ERROR:AYI-022:REQUEST_ID_MISMATCH");
        require(risk.responseAt == 0, "ERROR:AYI-023:EXISTING_CALLBACK");

        require(aaay >= (AAAY_MIN * PERCENTAGE_MULTIPLIER) 
                && aaay < (AAAY_MAX * PERCENTAGE_MULTIPLIER), 
                "ERROR:AYI-024:AAAY_INVALID");

        // update risk using aaay info
        risk.aaay = aaay;
        risk.payoutPercentage = calculatePayoutPercentage(
            risk.tsi,
            risk.trigger,
            risk.exit,
            risk.aph,
            risk.aaay
        );

        risk.responseAt = block.timestamp; // solhint-disable-line
        risk.updatedAt = block.timestamp; // solhint-disable-line

        emit LogAyiiRiskDataReceived(
            requestId, 
            riskId,
            aaay);
    }

    /**
     * @dev Process a batch of policies for a given risk.
     * @param riskId ID of the risk to process policies for.
     * @param batchSize Number of policies to process in a single batch.
     * @return processedPolicies An array of policy IDs that were processed.
     * Emits a LogAyiiRiskProcessed event with the processed batch size.
     * Requirements:
     * - Caller must have the INSURER_ROLE.
     * - The risk must have a response from the oracle.
     * - The policies set for the given risk must not be empty.
     * - If batchSize is 0, processes all policies in a single batch.
     * - If batchSize is greater than the number of policies, processes all policies in a single batch.
     * - If batchSize is less than the number of policies, processes batchSize policies in a single batch.
     * @notice This function emits 2 events: 
     * - LogAyiiRiskProcessed
     * - LogAyiiRiskProcessed
     */
    function processPoliciesForRisk(bytes32 riskId, uint256 batchSize)
        external
        onlyRole(INSURER_ROLE)
        returns(bytes32 [] memory processedPolicies)
    {
        Risk memory risk = _risks[riskId];
        require(risk.responseAt > 0, "ERROR:AYI-030:ORACLE_RESPONSE_MISSING");

        uint256 elements = EnumerableSet.length(_policies[riskId]);
        if (elements == 0) {
            emit LogAyiiRiskProcessed(riskId, 0);
            return new bytes32[](0);
        }

        if (batchSize == 0) { batchSize = elements; } 
        else                 { batchSize = min(batchSize, elements); }

        processedPolicies = new bytes32[](batchSize);
        uint256 elementIdx = elements - 1;

        for (uint256 i = 0; i < batchSize; i++) {
            // grab and process the last policy
            bytes32 policyId = EnumerableSet.at(_policies[riskId], elementIdx - i);
            processPolicy(policyId);
            processedPolicies[i] = policyId;
        }

        emit LogAyiiRiskProcessed(riskId, batchSize);
    }

    /**
     * @dev Processes a policy by calculating the claim amount, creating a new claim, and emitting events for the claim and payout.
     * @param policyId The ID of the policy to be processed.
     * @notice This function emits 3 events: 
     * - LogAyiiPayoutCreated
     * - LogAyiiClaimCreated
     * - LogAyiiPolicyProcessed
     */
    function processPolicy(bytes32 policyId)
        public
        onlyRole(INSURER_ROLE)
    {
        IPolicy.Application memory application = _getApplication(policyId);
        bytes32 riskId = abi.decode(application.data, (bytes32));
        Risk memory risk = _risks[riskId];

        require(risk.id == riskId, "ERROR:AYI-031:RISK_ID_INVALID");
        require(risk.responseAt > 0, "ERROR:AYI-032:ORACLE_RESPONSE_MISSING");
        require(EnumerableSet.contains(_policies[riskId], policyId), "ERROR:AYI-033:POLICY_FOR_RISK_UNKNOWN");

        EnumerableSet.remove(_policies[riskId], policyId);


        uint256 claimAmount = calculatePayout(
            risk.payoutPercentage, 
            application.sumInsuredAmount);
        
        uint256 claimId = _newClaim(policyId, claimAmount, "");
        emit LogAyiiClaimCreated(policyId, claimId, claimAmount);

        if (claimAmount > 0) {
            uint256 payoutAmount = claimAmount;
            _confirmClaim(policyId, claimId, payoutAmount);

            uint256 payoutId = _newPayout(policyId, claimId, payoutAmount, "");
            _processPayout(policyId, payoutId);

            emit LogAyiiPayoutCreated(policyId, payoutAmount);
        }
        else {
            _declineClaim(policyId, claimId);
            _closeClaim(policyId, claimId);
        }

        _expire(policyId);
        _close(policyId);

        emit LogAyiiPolicyProcessed(policyId);
    }

    /**
     * @dev Calculates the payout amount based on the payout percentage and sum insured amount.
     * @param payoutPercentage The percentage of the sum insured amount that will be paid out.
     * @param sumInsuredAmount The total amount that is insured.
     * @return payoutAmount The calculated payout amount.
     */
    function calculatePayout(uint256 payoutPercentage, uint256 sumInsuredAmount)
        public
        pure
        returns(uint256 payoutAmount)
    {
        payoutAmount = payoutPercentage * sumInsuredAmount / PERCENTAGE_MULTIPLIER;
    }

    /**
     * @dev Calculates the payout percentage based on the given parameters.
     * @param tsi The maximum payout percentage.
     * @param trigger The harvest ratio at and above which no payout is made.
     * @param exit The harvest ratio at and below which the maximum payout is made.
     * @param aph The average historical yield.
     * @param aaay This season's yield.
     * @return payoutPercentage The calculated payout percentage.
     */
    function calculatePayoutPercentage(
        uint256 tsi, // max payout percentage
        uint256 trigger,// at and above this harvest ratio no payout is made 
        uint256 exit, // at and below this harvest ration the max payout is made
        uint256 aph, // average historical yield
        uint256 aaay // this season's yield
    )
        public
        pure
        returns(uint256 payoutPercentage)
    {
        // this year's harvest at or above threshold for any payouts
        if (aaay * PERCENTAGE_MULTIPLIER >= aph * trigger) {
            return 0;
        }

        // this year's harvest at or below threshold for maximal payout
        if (aaay * PERCENTAGE_MULTIPLIER <= aph * exit) {
            return tsi;
        }

        // calculated payout between exit and trigger
        uint256 harvestRatio = PERCENTAGE_MULTIPLIER * aaay / aph;
        payoutPercentage = tsi * (trigger - harvestRatio) / (trigger - exit);
    }

    /**
     * @dev Returns the percentage multiplier used in calculations.
     * @return multiplier The value of the percentage multiplier.
     */
    function getPercentageMultiplier() external pure returns(uint256 multiplier) {
        return PERCENTAGE_MULTIPLIER;
    }

    /**
     * @dev Returns the minimum value between two uint256 numbers.
     * @param a The first uint256 number to compare.
     * @param b The second uint256 number to compare.
     * @return The minimum value between a and b.
     */
    function min(uint256 a, uint256 b) private pure returns (uint256) {
        return a <= b ? a : b;
    }


    /**
     * @dev Returns the number of risk ids in the _riskIds array.
     * @return The length of the _riskIds array.
     */
    function risks() external view returns(uint256) { return _riskIds.length; }
    /**
     * @dev Returns the risk ID at the given index.
     * @param idx The index of the risk ID to retrieve.
     * @return riskId The risk ID at the given index.
     */
    function getRiskId(uint256 idx) external view returns(bytes32 riskId) { return _riskIds[idx]; }
    /**
     * @dev Returns the Risk struct associated with the given riskId.
     * @param riskId The unique identifier of the Risk to retrieve.
     * @return risk The Risk struct containing the details of the requested risk.
     */
    function getRisk(bytes32 riskId) external view returns(Risk memory risk) { return _risks[riskId]; }

    /**
     * @dev Returns the number of applications submitted.
     * @return applicationCount The number of applications submitted.
     */
    function applications() external view returns(uint256 applicationCount) {
        return _applications.length;
    }

    /**
     * @dev Returns the process ID of a specific application.
     * @param applicationIdx The index of the application in the array.
     * @return processId The process ID of the application.
     */
    function getApplicationId(uint256 applicationIdx) external view returns(bytes32 processId) {
        return _applications[applicationIdx];
    }

    /**
     * @dev Returns the number of policies for a given risk ID.
     * @param riskId The ID of the risk.
     * @return policyCount The number of policies for the given risk ID.
     */
    function policies(bytes32 riskId) external view returns(uint256 policyCount) {
        return EnumerableSet.length(_policies[riskId]);
    }

    /**
     * @dev Returns the processId of the policy at the specified index in the list of policies associated with the given riskId.
     * @param riskId The unique identifier of the risk.
     * @param policyIdx The index of the policy in the list of policies associated with the given riskId.
     * @return processId The unique identifier of the process associated with the policy at the specified index.
     */
    function getPolicyId(bytes32 riskId, uint256 policyIdx) external view returns(bytes32 processId) {
        return EnumerableSet.at(_policies[riskId], policyIdx);
    }

    /**
     * @dev Returns the data structure of the application.
     * @return dataStructure A string representing the data structure of the application, which consists of a single parameter:
     * - riskId: A bytes32 value representing the unique identifier of the risk.
     */
    function getApplicationDataStructure() external override pure returns(string memory dataStructure) {
        return "(bytes32 riskId)";
    }


    /**
     * @dev Validates the risk parameters for a new position.
     * @param trigger The trigger percentage for the new position.
     * @param exit The exit percentage for the new position.
     * @param tsi The TSI (Time Since Inception) for the new position.
     * @param aph The APH (Annual Premium Hours) for the new position.
     *
     */
    function _validateRiskParameters(
        uint256 trigger, 
        uint256 exit,
        uint256 tsi,
        uint256 aph
    )
        internal
    {
        require(trigger <= PERCENTAGE_MULTIPLIER, "ERROR:AYI-040:RISK_TRIGGER_TOO_LARGE");
        require(trigger > exit, "ERROR:AYI-041:RISK_TRIGGER_NOT_LARGER_THAN_EXIT");
        require(exit <= RISK_EXIT_MAX, "ERROR:AYI-042:RISK_EXIT_TOO_LARGE");
        require(tsi >= RISK_TSI_AT_EXIT_MIN , "ERROR:AYI-043:RISK_TSI_TOO_SMALL");
        require(tsi <= PERCENTAGE_MULTIPLIER , "ERROR:AYI-044:RISK_TSI_TOO_LARGE");
        require(tsi + exit <= PERCENTAGE_MULTIPLIER, "ERROR:AYI-045:RISK_TSI_EXIT_SUM_TOO_LARGE");
        require(aph > 0, "ERROR:AYI-046:RISK_APH_ZERO_INVALID");
        require(aph <= RISK_APH_MAX, "ERROR:AYI-047:RISK_APH_TOO_LARGE");
    }

    /**
     * @dev Processes a policy by calculating the claim amount, creating a claim, confirming it, creating a payout, processing it, and emitting events accordingly.
     * @param policyId The ID of the policy to be processed.
     * @param risk The Risk struct containing the payout percentage.
     * @notice This function emits 3 events: 
     * - LogAyiiPolicyProcessed
     * - LogAyiiPayoutCreated
     * - LogAyiiClaimCreated
     */
    function _processPolicy(bytes32 policyId, Risk memory risk)
        internal
    {
        IPolicy.Application memory application 
            = _getApplication(policyId);

        uint256 claimAmount = calculatePayout(
            risk.payoutPercentage, 
            application.sumInsuredAmount);
        
        uint256 claimId = _newClaim(policyId, claimAmount, "");
        emit LogAyiiClaimCreated(policyId, claimId, claimAmount);

        if (claimAmount > 0) {
            uint256 payoutAmount = claimAmount;
            _confirmClaim(policyId, claimId, payoutAmount);

            uint256 payoutId = _newPayout(policyId, claimId, payoutAmount, "");
            _processPayout(policyId, payoutId);

            emit LogAyiiPayoutCreated(policyId, payoutAmount);
        }
        else {
            _declineClaim(policyId, claimId);
            _closeClaim(policyId, claimId);
        }

        emit LogAyiiPolicyProcessed(policyId);
    }

    /**
     * @dev Returns the risk ID associated with a given process ID.
     * @param processId The process ID for which to retrieve the risk ID.
     * @return riskId The risk ID associated with the given process ID.
     */
    function _getRiskId(bytes32 processId) private view returns(bytes32 riskId) {
        IPolicy.Application memory application = _getApplication(processId);
        (riskId) = abi.decode(application.data, (bytes32));
    }
}