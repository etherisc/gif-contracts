// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableMap.sol";

import "@etherisc/gif-interface/contracts/components/Product.sol";
import "../modules/AccessController.sol";

contract AyiiProduct is 
    Product, 
    AccessControl 
{
    bytes32 public constant NAME = "AreaYieldIndexProduct";
    bytes32 public constant VERSION = "0.1";
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";

    bytes32 public constant INSURER_ROLE = keccak256("INSURER");

    uint256 public constant PERCENTAGE_MULTIPLIER = 2**18;

    // group policy data structure
    struct Risk {
        bytes32 id; // hash over projectId, uaiId, cropId
        bytes32 projectId; // assumption: this makes risk unique over aggregarors/customers/seasons
        bytes32 uaiId;
        bytes32 cropId;
        uint256 trigger;
        uint256 exit;
        uint256 tsi;
        uint256 aph;
        uint256 requestId;
        uint256 responseAt;
        uint256 aaay;
        uint256 payoutFactor;
        uint256 createdAt;
        uint256 updatedAt;
    }

    uint256 private _oracleId;

    mapping(bytes32 /* riskId */ => Risk) private _risks;
    mapping(bytes32 /* riskId */ => bytes32 [] /*policyIds*/) private _policies;
    bytes32 [] private _applications; // useful for debugging, might need to get rid of this

    event LogAyiiPolicyCreated(bytes32 policyId, address policyHolder, uint256 premiumAmount, uint256 sumInsuredAmount);
    event LogAyiiRiskDataCreated(bytes32 riskId, bytes32 productId, bytes32 uaiId, bytes32 cropId);
    event LogAyiiRiskDataRequested(uint256 requestId, bytes32 projectId, bytes32 riskId, bytes32 uaiId, bytes32 cropId);
    event LogAyiiRiskDataReceived(uint256 requestId, bytes32 riskId, uint256 aaay);
    event LogAyiiRiskProcessed(bytes32 riskId, uint256 policies);
    event LogAyiiPolicyProcessed(bytes32 policyId);
    event LogAyiiClaimCreated(bytes32 policyId, uint256 claimId, uint256 payoutAmount);
    event LogAyiiPayoutCreated(bytes32 policyId, uint256 payoutAmount);

    // TODO decide if token address should be part of conxtructor
    // and if product should have getToken() function
    // "issue"/open question: product-token association currently 
    // handled via gif. maybe better if product directly hardwires 
    // with which token to work
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
        _oracleId = oracleId;

        _setupRole(DEFAULT_ADMIN_ROLE, _msgSender());
        _setupRole(INSURER_ROLE, insurer);
    }

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
        // TODO add input parameter validation

        riskId = getRiskId(projectId, uaiId, cropId);
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
        risk.createdAt = block.timestamp;
        risk.updatedAt = block.timestamp;

        emit LogAyiiRiskDataCreated(
            risk.id, 
            risk.projectId,
            risk.uaiId, 
            risk.cropId);
    }

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
        require(risk.createdAt > 0, "ERROR:AYI-002:RISK_UNDEFINED");
        require(policyHolder != address(0), "ERROR:AYI-003:POLICY_HOLDER_ZERO");

        processId = uniqueId(policyHolder);
        bytes memory metaData = "";
        bytes memory applicationData = abi.encode(riskId);

        _newApplication(
            policyHolder, 
            processId, 
            premium, 
            sumInsured,
            metaData,
            applicationData);

        _applications.push(processId);

        bool success = _underwrite(processId);

        if (success) {
            _policies[riskId].push(processId);

            emit LogAyiiPolicyCreated(
                processId, 
                policyHolder, 
                premium, 
                sumInsured);
        }
    }

    function triggerOracle(bytes32 riskId) 
        external
        onlyRole(INSURER_ROLE)
    {
        Risk storage risk = _risks[riskId];
        require(risk.createdAt > 0, "ERROR:AYI-010:RISK_UNDEFINED");
        require(risk.requestId == 0, "ERROR:AYI-011:ORACLE_ALREADY_TRIGGERED");

        bytes memory queryData = abi.encode(
            risk.projectId,
            risk.uaiId,
            risk.cropId
        );

        risk.requestId = _request(
                riskId,
                queryData,
                "oracleCallback",
                _oracleId
            );

        risk.updatedAt = block.timestamp;

        emit LogAyiiRiskDataRequested(
            risk.requestId, 
            risk.id, 
            risk.projectId, 
            risk.uaiId, 
            risk.cropId);
    }    

    function oracleCallback(
        uint256 requestId, 
        bytes32 riskId, 
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

        require(riskId == getRiskId(projectId, uaiId, cropId), "ERROR:AYI-020:RISK_ID_MISMATCH");

        Risk storage risk = _risks[riskId];
        require(risk.createdAt > 0, "ERROR:AYI-021:RISK_UNDEFINED");
        require(risk.requestId == requestId, "ERROR:AYI-022:REQUEST_ID_MISMATCH");
        require(risk.responseAt == 0, "ERROR:AYI-023:EXISTING_CALLBACK");

        // update risk using aaay info
        risk.aaay = aaay;
        risk.payoutFactor = calculatePayoutFactor(risk);
        risk.responseAt = block.timestamp;
        risk.updatedAt = block.timestamp;

        emit LogAyiiRiskDataReceived(
            requestId, 
            riskId,
            aaay);

        _processPoliciesForRisk(risk);
    }

    // TODO verify this is good enough or if we need to allow for
    // external batch processing
    function _processPoliciesForRisk(Risk memory risk)
        internal
    {
        bytes32 [] memory policyIds = _policies[risk.id];

        for (uint256 i; i < policyIds.length; i++) {
            _processPolicy(policyIds[i], risk);
        }

        emit LogAyiiRiskProcessed(risk.id, policyIds.length);
    }

    function _processPolicy(bytes32 policyId, Risk memory risk)
        internal
    {
        IPolicy.Application memory application 
            = _getApplication(policyId);

        uint256 claimFactor = risk.payoutFactor * application.sumInsuredAmount;
        uint256 claimAmount = claimFactor / PERCENTAGE_MULTIPLIER;

        uint256 claimId = _newClaim(policyId, claimAmount, "");
        emit LogAyiiClaimCreated(policyId, claimId, claimAmount);

        if (claimAmount > 0) {
            uint256 payoutAmount = claimAmount;
            uint256 payoutId = _confirmClaim(policyId, claimId, payoutAmount, "");

            bool isComplete = true;
            _processPayout(policyId, payoutId, isComplete, "");
            emit LogAyiiPayoutCreated(policyId, payoutAmount);
        }
        else {
            _declineClaim(policyId, claimId);
        }

        emit LogAyiiPolicyProcessed(policyId);
    }

    // TODO: make safe (add tests)
    function calculatePayoutFactor(Risk memory risk)
        public 
        pure 
        returns(uint256 payout)
    {
        uint nominator = risk.tsi * (risk.trigger - (PERCENTAGE_MULTIPLIER / risk.aph * risk.aaay));
        uint denominator = PERCENTAGE_MULTIPLIER * (risk.trigger - risk.exit);
        payout = min(risk.tsi, nominator * PERCENTAGE_MULTIPLIER / denominator);
    }

    function max(uint a, uint b) private pure returns (uint) {
        return a >= b ? a : b;
    }

    function min(uint a, uint b) private pure returns (uint) {
        return a <= b ? a : b;
    }

    function uniqueId(address _addr) 
        internal 
        returns (bytes32 _uniqueId) 
    {
        return keccak256(abi.encode(_addr, _applications.length));
    }

    // TODO comment out once function declared as virtual in product contract
    // function getApplicationDataStructure() external override view returns(string memory dataStructure) {
    //     return "(bytes32 riskId)";
    // }
}