// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableMap.sol";

// import "@etherisc/gif-contracts/contracts/modules/AccessController.sol";
import "../modules/AccessController.sol";
import "@etherisc/gif-interface/contracts/components/Product.sol";

// abstract 
contract AreaYieldIndexProduct1 is Product, AccessControl {
    using SafeERC20 for IERC20;

    bytes32 public constant NAME = "AreaYieldIndexProduct";
    bytes32 public constant VERSION = "0.1";
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";

    bytes32 public constant INVESTOR_ROLE = keccak256("INVESTOR");
    bytes32 public constant INSURER_ROLE = keccak256("INSURER");

    struct Peril {
        bytes32 ID; // UUID
        uint32 UAI; // Unit Area of Insurance, comprising one or more AEZs
        uint32 cropID;
        uint32 trigger; // The threshold below which the farmers receive a payout
        uint32 exit; // The threshold below which farmers receive the max possible payout
        uint32 TSI; // Total Sum Insured At Exit; The maximum possible payout
        uint32 APH; // Average Production History
        uint insuredAmount;
        uint premiumAmount;
        address payoutAddress;
    }

    uint numActivePolicies;
    mapping(bytes32 /* policyId */ => Peril) public policies;
    mapping(bytes32 /* policyId */ => uint32 /* AAAY */) public resolutions;

    IERC20 public paymentToken;
    uint public totalReceivedInvestments;
    uint public totalReceivedPremiums;
    uint public totalInsured;
    uint public totalPayouts;

    uint256 public uniqueIndex;
    uint256 public oracleId;
    uint256 public riskpoolId;

    event ReceiveInvestment(address indexed investor, uint amount);
    event ReceivePremium(address indexed insurer, address indexed insuree, uint amount);
    event TriggerResolutions(uint32 UAI);
    event Resolution(bytes32 indexed policyId, uint32 AAAY);
    event ResolutionProcessing(bytes32 indexed policyId, uint amount);
    event Withdraw(uint remainder);

    constructor(
        bytes32 _productName,
        address _registry,
        uint256 _oracleId,
        uint256 _riskpoolId, // mzi
        address _paymentToken,
        address _investor,
        address _insurer
    )
    Product(_productName, POLICY_FLOW, _registry)
    {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(INVESTOR_ROLE, _investor);
        _setupRole(INSURER_ROLE, _insurer);

        oracleId = _oracleId;
        riskpoolId = _riskpoolId;
        paymentToken = IERC20(_paymentToken);
    }

    // mzi begin
    function getApplicationDataStructure() external override view returns(string memory dataStructure) {
        return "";
    }    
    function getClaimDataStructure() external override view returns(string memory dataStructure) {
        return "";
    }    
    function getPayoutDataStructure() external override view returns(string memory dataStructure) {
        return "";
    }

    function getRiskpoolId() external override view returns(uint256) {
        return riskpoolId;
    }

    function riskPoolCapacityCallback(uint256 capacity) external override {
        
    }
    // mzi end

    function receiveInvestment(uint amount) external onlyRole(INVESTOR_ROLE) {
        totalReceivedInvestments += amount;
        paymentToken.safeTransferFrom(msg.sender, address(this), amount);
        emit ReceiveInvestment(msg.sender, amount);
    }

    function applyForPolicy(Peril[] calldata _perils) external onlyRole(INSURER_ROLE) {
        require(_perils.length > 0, "no perils");

        uint premiumsAmount = 0;

        for (uint i; i < _perils.length; i++) {
            Peril calldata peril = _perils[i];

            bytes32 processId = uniqueId(msg.sender);
            bytes memory metaData = abi.encode("");
            bytes memory applicationData = abi.encode(peril.ID);

            _newApplication(
                peril.payoutAddress, 
                processId, 
                peril.premiumAmount, 
                peril.insuredAmount, 
                metaData, 
                applicationData);

            // check that `peril.ID` is unique.
            if (policies[peril.ID].ID != 0) {
                _decline(processId);
                continue;
            }

            // mzi commented out
            // // check that enough available collateral exists.
            // uint availableCollateral = totalReceivedInvestments + totalReceivedPremiums - totalInsured;
            // if (availableCollateral < peril.insuredAmount) {
            //     _decline(processId);
            //     continue;
            // }

            _underwrite(processId);
            policies[peril.ID] = peril;
            numActivePolicies++;

            premiumsAmount += peril.premiumAmount;
            totalReceivedPremiums += peril.premiumAmount;
            totalInsured += peril.insuredAmount;

            emit ReceivePremium(msg.sender, peril.payoutAddress, peril.premiumAmount);
        }

        // mzi commented out
        // paymentToken.safeTransferFrom(msg.sender, address(this), premiumsAmount);
    }

    function triggerResolutions(uint32 UAI) external {
        bytes memory UAIBytes = abi.encodePacked(UAI);
        bytes32 UAIBytes32;
        assembly {
            UAIBytes32 := mload(add(UAIBytes, 32))
        }

        _request(
            UAIBytes32, // the index of the request
            UAIBytes, // input to oracle
            "triggerResolutionsCallback",
            oracleId
        );

        emit TriggerResolutions(UAI);
    }

    function triggerResolutionsCallback(uint256 _requestId, bytes32 _index, bytes memory _response) external {
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
            if (policies[policyId].ID == 0) {
                continue;
            }

            // check request/data integrity.
            if (policies[policyId].UAI != UAI) {
                require(false, "");
            }

            // decode and cache the result.
            (AAAY) = abi.decode(abi.encodePacked(AAAYBytes32), (uint));
            resolutions[policyId] = uint32(AAAY);
            emit Resolution(policyId, uint32(AAAY));
        }
    }

    function triggerResolutionProcessing(bytes32[] calldata _policyIds) public {
        for (uint i; i < _policyIds.length; i++) {
            Peril memory peril = policies[_policyIds[i]];
            uint32 AAAY = resolutions[_policyIds[i]];

            uint payoutAmount = calculatePayout(peril, AAAY);
            emit ResolutionProcessing(_policyIds[i], payoutAmount);

            if (payoutAmount > 0) {
                totalPayouts += payoutAmount;
                paymentToken.safeTransfer(peril.payoutAddress, payoutAmount);
            }

            totalInsured -= peril.insuredAmount;
            numActivePolicies--;
        }
    }

    function withdrawRemainder() external onlyRole(INVESTOR_ROLE) {
        require(numActivePolicies == 0, "active policies exists");

        uint remainder = paymentToken.balanceOf(address(this));
        paymentToken.safeTransfer(msg.sender, remainder);
        emit Withdraw(remainder);
    }

    // TODO: make safe
    function calculatePayoutPercentage(Peril memory _peril, uint32 _AAAY, uint precisionMultiplier) public pure returns (uint) {
        uint nominator = _peril.TSI * (_peril.trigger - (precisionMultiplier / _peril.APH * _AAAY));
        uint denominator = precisionMultiplier * (_peril.trigger - _peril.exit);
        return min(_peril.TSI, nominator * precisionMultiplier / denominator);
    }

    function calculatePayout(Peril memory _peril, uint32 _AAAY) public pure returns (uint) {
        uint precisionMultiplier = 10 ** 6;
        uint payout = _peril.insuredAmount * calculatePayoutPercentage(_peril, _AAAY, precisionMultiplier);
        return payout / precisionMultiplier;
    }

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







