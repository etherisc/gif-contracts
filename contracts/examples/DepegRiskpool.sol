// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import "@etherisc/gif-interface/contracts/components/BasicRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";

contract DepegRiskpool is 
    BasicRiskpool
{

    uint256 public constant USD_RISK_CAPITAL_CAP = 1 * 10**6;

    uint256 public constant MAX_BUNDLE_DURATION = 180 * 24 * 3600;
    uint256 public constant MAX_POLICY_DURATION = 180 * 24 * 3600;
    uint256 public constant ONE_YEAR_DURATION = 365 * 24 * 3600; 

    uint256 public constant APR_100_PERCENTAGE = 10**6;
    uint256 public constant MAX_APR = APR_100_PERCENTAGE / 5;

    uint256 private _poolRiskCapitalCap;
    uint256 private _bundleRiskCapitalCap;


    constructor(
        bytes32 name,
        uint256 sumOfSumInsuredCap,
        address erc20Token,
        address wallet,
        address registry
    )
        BasicRiskpool(name, getFullCollateralizationLevel(), sumOfSumInsuredCap, erc20Token, wallet, registry)
    {
        ERC20 token = ERC20(erc20Token);
        _poolRiskCapitalCap = USD_RISK_CAPITAL_CAP * 10 ** token.decimals();

        // HACK this needs to be determined according to max active bundles
        // setMaxActiveBundles in Riskpool needs to become virtual. alternatively 
        // Riskpool could call a virtual postprocessing hook
        _bundleRiskCapitalCap = _poolRiskCapitalCap / 10;

        require(sumOfSumInsuredCap <= _poolRiskCapitalCap, "ERROR:DRP-010:SUM_OF_SUM_INSURED_CAP_TOO_LARGE");
        require(sumOfSumInsuredCap > 0, "ERROR:DRP-011:SUM_OF_SUM_INSURED_CAP_ZERO");

    }

    function createBundle(
        uint256 policyMinSumInsured,
        uint256 policyMaxSumInsured,
        uint256 policyMinDuration,
        uint256 policyMaxDuration,
        uint256 annualPercentageReturn,
        uint256 initialAmount
    ) 
        public
        returns(uint256 bundleId)
    {
        require(policyMaxSumInsured <= _bundleRiskCapitalCap, "ERROR:DRP-020:MAX_SUM_INSURED_TOO_LARGE");
        require(policyMaxSumInsured > 0, "ERROR:DRP-020:MAX_SUM_INSURED_ZERO");
        require(policyMinSumInsured <= policyMaxSumInsured, "ERROR:DRP-020:MIN_SUM_INSURED_TOO_LARGE");

        require(policyMaxDuration <= MAX_POLICY_DURATION, "ERROR:DRP-020:POLICY_MAX_DURATION_TOO_LARGE");
        require(policyMaxDuration > 0, "ERROR:DRP-020:POLICY_MAX_DURATION_ZERO");
        require(policyMinDuration <= policyMaxDuration, "ERROR:DRP-020:POLICY_MIN_DURATION_TOO_LARGE");

        require(annualPercentageReturn <= MAX_APR, "ERROR:DRP-020:APR_TOO_LARGE");
        require(annualPercentageReturn > 0, "ERROR:DRP-020:APR_ZERO");

        require(initialAmount <= _bundleRiskCapitalCap, "ERROR:DRP-020:RISK_CAPITAL_TOO_LARGE");

        bytes memory filter = encodeBundleParamsAsFilter(
            policyMinSumInsured,
            policyMaxSumInsured,
            policyMinDuration,
            policyMaxDuration,
            annualPercentageReturn
        );

        bundleId = super.createBundle(filter, initialAmount);
    }

    // TODO s
    // - add application params to depeg product contract
    // - get toy works up as quickly as possible
    //   + .1 create application
    //   + .2 figure out if there's a matching bundle
    //   + .3 add function that let's user query conditions based on active bundles
    // TODO function defined in base class Riskpool -> needs to be virtual!
    function getFilterDataStructureTemp() external pure returns(string memory) {
        return "(uint256 minSumInsured,uint256 maxSumInsured,uint256 minDuration,uint256 maxDuration,uint256 annualPercentageReturn)";
    }

    function encodeBundleParamsAsFilter(
        uint256 minSumInsured,
        uint256 maxSumInsured,
        uint256 minDuration,
        uint256 maxDuration,
        uint256 annualPercentageReturn
    )
        public pure
        returns (bytes memory filter)
    {
        filter = abi.encode(
            minSumInsured,
            maxSumInsured,
            minDuration,
            maxDuration,
            annualPercentageReturn
        );
    }

    function decodeBundleParamsFromFilter(
        bytes calldata filter
    )
        public pure
        returns (
            uint256 minSumInsured,
            uint256 maxSumInsured,
            uint256 minDuration,
            uint256 maxDuration,
            uint256 annualPercentageReturn
        )
    {
        (
            minSumInsured,
            maxSumInsured,
            minDuration,
            maxDuration,
            annualPercentageReturn
        ) = abi.decode(filter, (uint256, uint256, uint256, uint256, uint256));
    }


    function encodeApplicationParameterAsData(
        uint256 duration,
        uint256 maxPremium
    )
        public pure
        returns (bytes memory data)
    {
        data = abi.encode(
            duration,
            maxPremium
        );
    }


    function decodeApplicationParameterFromData(
        bytes calldata data
    )
        public pure
        returns (
            uint256 duration,
            uint256 maxPremium
        )
    {
        (
            duration,
            maxPremium
        ) = abi.decode(data, (uint256, uint256));
    }


    function bundleMatchesApplication(
        IBundle.Bundle calldata bundle, 
        IPolicy.Application calldata application
    ) 
        public override
        pure
        returns(bool isMatching) 
    {
        (
            uint256 minSumInsured,
            uint256 maxSumInsured,
            uint256 minDuration,
            uint256 maxDuration,
            uint256 annualPercentageReturn
        ) = decodeBundleParamsFromFilter(bundle.filter);
        
        (
            uint256 duration,
            uint256 maxPremium
        ) = decodeApplicationParameterFromData(application.data);

        uint256 sumInsured = application.sumInsuredAmount;

        if(sumInsured < minSumInsured) { return false; }
        if(sumInsured > maxSumInsured) { return false; }
        
        if(duration < minDuration) { return false; }
        if(duration > maxDuration) { return false; }
        
        uint256 policyDurationReturn = annualPercentageReturn * duration / ONE_YEAR_DURATION;
        uint256 premium = sumInsured * policyDurationReturn / APR_100_PERCENTAGE;

        if(premium > maxPremium) { return false; }

        return true;
    }

    function getBundleRiskCapitalCap() public view returns (uint256 bundleRiskCapitalCap) {
        return _bundleRiskCapitalCap;
    }

    function getApr100PercentLevel() public pure returns(uint256 apr100PercentLevel) { 
        return APR_100_PERCENTAGE;
    }
}