// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/Product.sol";


import "./DepegRiskpool.sol";

contract DepegProduct is 
    Product
{

    bytes32 public constant NAME = "DepegProduct";
    bytes32 public constant VERSION = "0.1";
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";

    bytes32 [] private _applications; // useful for debugging, might need to get rid of this
    bytes32 [] private _policies;

    event LogDepegApplicationCreated(bytes32 policyId, address policyHolder, uint256 premiumAmount, uint256 sumInsuredAmount);
    event LogDepegPolicyCreated(bytes32 policyId, address policyHolder, uint256 premiumAmount, uint256 sumInsuredAmount);
    event LogDepegPolicyProcessed(bytes32 policyId);

    event LogDepegOracleTriggered(uint256 exchangeRate);

    DepegRiskpool private _riskPool;

    constructor(
        bytes32 productName,
        address registry,
        address token,
        uint256 riskpoolId
    )
        Product(productName, token, POLICY_FLOW, riskpoolId, registry)
    {
        IComponent poolComponent = _instanceService.getComponent(riskpoolId); 
        address poolAddress = address(poolComponent);
        _riskPool = DepegRiskpool(poolAddress);
    }


    function applyForPolicy(
        uint256 sumInsured,
        uint256 duration,
        uint256 maxPremium
    ) 
        external 
        returns(bytes32 processId)
    {
        address policyHolder = msg.sender;
        bytes memory metaData = "";
        bytes memory applicationData = _riskPool.encodeApplicationParameterAsData(
            duration,
            maxPremium
        );

        // TODO proper mechanism to decide premium
        // maybe hook after policy creation with adjustpremiumsuminsured?
        uint256 premium = maxPremium;

        processId = _newApplication(
            policyHolder, 
            premium, 
            sumInsured,
            metaData,
            applicationData);

        _applications.push(processId);

        emit LogDepegApplicationCreated(
            processId, 
            policyHolder, 
            premium, 
            sumInsured);

        bool success = _underwrite(processId);

        if (success) {
            _policies.push(processId);

            emit LogDepegPolicyCreated(
                processId, 
                policyHolder, 
                premium, 
                sumInsured);
        }
    }

    function getBestQuote(
        uint256 sumInsured,
        uint256 duration
    )
        public 
        // view // TODO should be view, for now bundleMatchesApplication forces non-view visibility
        returns(uint256 lowestPremiumAmount)
    {
        bytes memory applicationData = _riskPool.encodeApplicationParameterAsData(
            duration, 
            sumInsured - 1 // ridiculously high max premium
        );

        IPolicy.Application memory applicationForQuote = IPolicy.Application(
            IPolicy.ApplicationState.Applied, // state, not relevant
            0, // premium, not relevant
            sumInsured,
            applicationData, // contains duration
            0, // created at, not relevant
            0 // updated at, not relevant
        );

        uint256[] memory bundleIds = _riskPool.getActiveBundleIds();

        for(uint256 i = 0; i < bundleIds.length; i++) {
            IBundle.Bundle memory bundle = _instanceService.getBundle(bundleIds[i]);

            // check if bundle has enough capital
            if(applicationForQuote.sumInsuredAmount < bundle.capital - bundle.lockedCapital) {
                // check if application parameters match with bundle parameters
                if(_riskPool.bundleMatchesApplication2(bundle, applicationForQuote)) {
                    (
                        uint256 minSumInsured,
                        uint256 maxSumInsured,
                        uint256 minDuration,
                        uint256 maxDuration,
                        uint256 annualPercentageReturn
                    ) = _riskPool.decodeBundleParamsFromFilter(bundle.filter);

                    return _riskPool.calculatePremium(sumInsured, duration, annualPercentageReturn);
                }
            }
        }
    }

    function triggerOracle() 
        external
    {

        uint256 exchangeRate = 10**6;

        emit LogDepegOracleTriggered(
            exchangeRate
        );
    }    

    function processPolicy(bytes32 processId)
        public
    {

        _expire(processId);
        _close(processId);

        emit LogDepegPolicyProcessed(processId);
    }

    function applications() external view returns(uint256 applicationCount) {
        return _applications.length;
    }

    function getApplicationId(uint256 applicationIdx) external view returns(bytes32 processId) {
        return _applications[applicationIdx];
    }

    function policies() external view returns(uint256 policyCount) {
        return _policies.length;
    }

    function getPolicyId(uint256 policyIdx) external view returns(bytes32 processId) {
        return _policies[policyIdx];
    }

    function getApplicationDataStructure() external override pure returns(string memory dataStructure) {
        return "(uint256 duration,uint256 maxPremium)";
    }
}