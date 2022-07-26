// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableMap.sol";

import "@etherisc/gif-interface/contracts/components/Product.sol";
import "../modules/AccessController.sol";

contract AreaYieldIndexProduct is Product, AccessControl {
    using SafeERC20 for IERC20;

    bytes32 public constant NAME = "AreaYieldIndexProduct";
    bytes32 public constant VERSION = "0.1";
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";

    bytes32 public constant INVESTOR_ROLE = keccak256("INVESTOR");
    bytes32 public constant INSURER_ROLE = keccak256("INSURER");

    // TODO refactor use gif infra where available and move rest to a Risk structure
    // Risk(projectId, UAI, cropId, trigger, exit, TSI, APH)

    // TODO check if we need projectId as well (or whatever is needed to be 
    // unique over multiple aggregators and seasons)

    // this corresponds to a policy record
    struct Peril {
        bytes32 ID; // UUID (corresponds to a policyId)
        uint32 UAI; // Unit Area of Insurance, comprising one or more AEZs
        uint32 cropID;
        uint32 trigger; // The threshold below which the farmers receive a payout
        uint32 exit; // The threshold below which farmers receive the max possible payout
        uint32 TSI; // Total Sum Insured At Exit; The maximum possible payout (in % of sum insured)
        uint32 APH; // Average Production History
        uint sumInsuredAmount;
        uint premiumAmount;
        address payoutAddress; // policy holder
    }

    mapping(bytes32 /* policyId (Peril.ID) */ => Peril) public activePolicies;
    uint numActivePolicies;

    mapping(bytes32 /* policyId */ => uint32 /* AAAY */) public resolutions;

    IERC20 public paymentToken;
    uint public totalReceivedInvestments;
    uint public totalReceivedPremiums;
    uint public totalSumInsured;
    uint public totalPayouts;

    uint256 public uniqueIndex;
    uint256 public oracleId;
    uint256 public riskpoolId; // mzi

    event LogAYIReceiveInvestment(address indexed investor, uint amount);
    event LogAYIReceivePremium(address indexed insurer, address indexed insuree, uint amount);
    event LogAYITriggerResolutions(uint32 UAI);
    event LogAYIResolution(bytes32 indexed policyId, uint32 AAAY);
    event LogAYIResolutionProcessing(bytes32 indexed policyId, uint amount);
    event LogAYIWithdraw(uint remainder);

    constructor(
        bytes32 _productName,
        address _registry,
        uint256 _oracleId,
        uint256 _riskpoolId, // mzi
        address _paymentToken,
        address _investor,
        address _insurer
    )
        Product(_productName, _paymentToken, POLICY_FLOW, _riskpoolId, _registry)
    {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(INVESTOR_ROLE, _investor);
        _setupRole(INSURER_ROLE, _insurer);

        oracleId = _oracleId;
        riskpoolId = _riskpoolId; // mzi
        paymentToken = IERC20(_paymentToken);
    }

    // mzi handled by gif framework
    // function receiveInvestment(uint amount) external onlyRole(INVESTOR_ROLE) {
    //     totalReceivedInvestments += amount;
    //     paymentToken.safeTransferFrom(msg.sender, address(this), amount);
    //     emit LogAYIReceiveInvestment(msg.sender, amount);
    // }

    function applyForPolicy(Peril[] calldata _perils) 
        external 
        onlyRole(INSURER_ROLE)
        returns(bytes32 [] memory processIds)
    {
        require(_perils.length > 0, "no perils");

        uint premiumsAmount = 0;
        processIds = new bytes32[](_perils.length);

        for (uint i; i < _perils.length; i++) {
            Peril calldata peril = _perils[i];

            address policyOwner = peril.payoutAddress;

            // TODO processId most likely redundant to Peril.ID. if so -> delete
            bytes32 processId = uniqueId(policyOwner);
            bytes memory metaData = "";

            // TODO check if "" doesn't do the trick
            // most likely metadata should hold pointer to Risk
            bytes memory applicationData = abi.encode(policyOwner, peril.ID);

            _newApplication(
                policyOwner, 
                processId, 
                peril.premiumAmount,
                peril.sumInsuredAmount,
                metaData,
                applicationData);

            // TODO might be redundant to peril.ID
            // add processId to result list
            processIds[i] = processId;

            // check that `peril.ID` is unique.
            require(activePolicies[peril.ID].ID == 0, "peril ID already exists");

            // done by policydefaultflow and riskpool
            // // check that enough av/ailable collateral exists.
            // uint availableCollateral = totalReceivedInvestments + totalReceivedPremiums - totalSumInsured;
            // require(availableCollateral >= peril.sumInsuredAmount, "no sufficient collateral");

            _underwrite(processId);
            activePolicies[peril.ID] = peril;
            numActivePolicies++;

            premiumsAmount += peril.premiumAmount;
            totalReceivedPremiums += peril.premiumAmount;
            totalSumInsured += peril.sumInsuredAmount;

            emit LogAYIReceivePremium(policyOwner, peril.payoutAddress, peril.premiumAmount);
        }

        // done by by policydefaultflow treasury and riskpool
        // paymentToken.safeTransferFrom(msg.sender, address(this), premiumsAmount);
    }

    // TODO check if this is sufficient, uai probably is not enough
    // likely project and cropId are needed as well

    // TODO: discuss if/how oracle could be integrated in a more meaningufl way
    // having a function decoupled from policy activation leads to the question
    // why oracle data is not directly injected into the contract by an authorized entity ...
    // especially for a product that needs data once at the end of the season

    // TODO: limit access
    function triggerResolutions(uint32 UAI) 
        external 
        returns(uint256 requestId)
    {
        bytes memory UAIBytes = abi.encodePacked(UAI);
        bytes32 UAIBytes32;
        assembly {
            UAIBytes32 := mload(add(UAIBytes, 32))
        }

       requestId = _request(
            UAIBytes32, // the index of the request
            UAIBytes, // input to oracle
            "triggerResolutionsCallback",
            oracleId
        );

        emit LogAYITriggerResolutions(UAI);
    }

    // TODO limit access to query module (= onlyOracle)
    // TODO refactor for gif semantics
    // current implementation too far away from gif semantics
    // - _index intended for processId=policyId
    // - unclear where oracle has info regarding which policyId are involved with which uai
    // - check if remodeling for risk is more appropriate
    function triggerResolutionsCallback(uint256 _requestId, bytes32 _index, bytes memory _response) public {
        uint32 UAI = uint32(bytes4(_index));

        // parse (policyId,AAAY) pairs of 32 bytes words size.
        uint32 offset = 32;
        while (offset < _response.length) {
            bytes32 policyId;
            bytes32 AAAYBytes32;
            uint AAAY;

            uint32 AAAYOffset = offset + 32;
            assembly {
                policyId := mload(add(_response, offset))
                AAAYBytes32 := mload(add(_response, AAAYOffset))
            }
            offset += 64;

            // check if policy exists.
            if (activePolicies[policyId].ID == 0) {
                continue;
            }

            // check request/data integrity.
            if (activePolicies[policyId].UAI != UAI) {
                require(false, "UAI mismatch");
            }

            // decode and cache the result.
            (AAAY) = abi.decode(abi.encodePacked(AAAYBytes32), (uint));
            resolutions[policyId] = uint32(AAAY);
            emit LogAYIResolution(policyId, uint32(AAAY));
        }
    }

    // TODO: limit access (as same as `triggerResolutions`)
    function triggerResolutionProcessing(bytes32[] calldata _policyIds) public {
        for (uint i; i < _policyIds.length; i++) {
            bytes32 policyId = _policyIds[i];
            require(activePolicies[policyId].ID != 0, "no active policy exists");

            uint payoutAmount = calculatePayout(activePolicies[policyId], resolutions[policyId]);
            emit LogAYIResolutionProcessing(policyId, payoutAmount);

            if (payoutAmount > 0) {
                totalPayouts += payoutAmount;
                paymentToken.safeTransfer(activePolicies[policyId].payoutAddress, payoutAmount);
            }

            totalSumInsured -= activePolicies[policyId].sumInsuredAmount;
            numActivePolicies--;

            delete activePolicies[policyId];
            delete resolutions[policyId];
        }
    }

    // mzi handled by gif framework
    // function withdrawRemainder() external onlyRole(INVESTOR_ROLE) {
    //     require(numActivePolicies == 0, "active policies exists");

    //     uint remainder = paymentToken.balanceOf(address(this));
    //     paymentToken.safeTransfer(msg.sender, remainder);
    //     emit LogAYIWithdraw(remainder);
    // }

    // TODO: make safe
    function calculatePayoutPercentage(Peril memory _peril, uint32 _AAAY, uint precisionMultiplier) public pure returns (uint) {
        uint nominator = _peril.TSI * (_peril.trigger - (precisionMultiplier / _peril.APH * _AAAY));
        uint denominator = precisionMultiplier * (_peril.trigger - _peril.exit);
        return min(_peril.TSI, nominator * precisionMultiplier / denominator);
    }

    function calculatePayout(Peril memory _peril, uint32 _AAAY) public pure returns (uint) {
        uint precisionMultiplier = 10 ** 6;
        uint payout = _peril.sumInsuredAmount * calculatePayoutPercentage(_peril, _AAAY, precisionMultiplier);
        return payout / precisionMultiplier;
    }

    // mzi begin
    // function getApplicationDataStructure() external override view returns(string memory dataStructure) {
    //     return "(address policyOwner, bytes32 perilId)";
    // }    
    // function getClaimDataStructure() external override view returns(string memory dataStructure) {
    //     return "";
    // }    
    // function getPayoutDataStructure() external override view returns(string memory dataStructure) {
    //     return "";
    // }

    // function getRiskpoolId() external override view returns(uint256) {
    //     return riskpoolId;
    // }

    // function riskPoolCapacityCallback(uint256 capacity) external override {
        
    // }
    // mzi end

    function uniqueId(address _addr) internal returns (bytes32 _uniqueId) {
        uniqueIndex += 1;
        return keccak256(abi.encode(_addr, uniqueIndex));
    }

    function max(uint a, uint b) private pure returns (uint) {
        return a >= b ? a : b;
    }

    function min(uint a, uint b) private pure returns (uint) {
        return a <= b ? a : b;
    }
}







