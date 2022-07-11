// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./Riskpool.sol";
// import "./IdSet.sol";
// import "../services/InstanceService.sol"; // TODO remove once getBundle is fixed

import "@gif-interface/contracts/modules/IBundle.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";
import "@gif-interface/contracts/components/Component.sol";
import "@gif-interface/contracts/components/IRiskpool.sol";
import "@gif-interface/contracts/services/IInstanceService.sol";
import "@gif-interface/contracts/services/IRiskpoolService.sol";

// TODO consider to move bunlde per riskpool book keeping to bundle controller
contract TestRiskpool is Riskpool {

    constructor(
        bytes32 name,
        uint256 collateralization,
        address wallet,
        address registry
    )
        Riskpool(name, collateralization, wallet, registry)
    { }


    function calculateCollateral(IPolicy.Application memory application) 
        public override
        view 
        returns (uint256 collateralAmount) 
    {
        uint256 sumInsured = application.sumInsuredAmount;
        uint256 collateralization = getCollateralizationLevel();

        if (collateralization == COLLATERALIZATION_DECIMALS) {
            collateralAmount = sumInsured;
        } else {
            // https://ethereum.stackexchange.com/questions/91367/is-the-safemath-library-obsolete-in-solidity-0-8-0
            collateralAmount = (collateralization * sumInsured) / COLLATERALIZATION_DECIMALS;
        }
    }
    
    // needs to remember which bundles helped to cover ther risk
    // simple (retail) approach: single policy covered by single bundle
    //   forst bundle with a match and sufficient capacity wins
    // complex (wholesale) approach: single policy covered by many bundles
    // Component <- Riskpool <- BasicRiskpool <- TestRiskpool
    // Component <- Riskpool <- AdvancedRiskpool <- TestRiskpool
    function _lockCollateral(bytes32 processId, uint256 collateralAmount) 
        internal override
        returns(bool success) 
    {
        uint256 activeBundles = _idSetSize();
        uint256 capital = getCapital();
        uint256 lockedCapital = getTotalValueLocked();

        require(activeBundles > 0, "ERROR:RPL-004:NO_ACTIVE_BUNDLES");
        require(capital > lockedCapital, "ERROR:RPL-005:NO_FREE_CAPITAL");

        // ensure there is a chance to find the collateral
        if(capital >= lockedCapital + collateralAmount) {
            IPolicy.Application memory application = _instanceService.getApplication(processId);

            // basic riskpool implementation: policy coverage by single bundle only
            uint i;
            while (i < activeBundles && !success) {
                uint256 bundleId = _idInSetAt(i);
                IBundle.Bundle memory bundle = _instanceService.getBundle(bundleId);
                bool isMatching = bundleMatchesApplication(bundle, application);
                emit LogRiskpoolBundleMatchesPolicy(bundleId, isMatching);

                if (isMatching) {
                    uint256 maxAmount = bundle.capital - bundle.lockedCapital;

                    if (maxAmount >= collateralAmount) {
                        _riskpoolService.collateralizePolicy(bundleId, processId, collateralAmount);
                        _collateralizedBy[processId] = bundleId;
                        success = true;
                    } else {
                        i++;
                    }
                }
            }
        }
    }

    // // this is the product/riskpool specific definition of what can be done with filters
    // function _maxCollateralFromBundle(uint256 bundleId, IPolicy.Application memory application)
    //     internal
    //     returns(uint256 maxCollateralAmount)
    // {
    //     IBundle.Bundle memory bundle = _instanceService.getBundle(bundleId);
        
    //     if (bundleMatchesApplication(bundle, application)) {
    //         maxCollateralAmount = bundle.capital - bundle.lockedCapital;
    //     }
    // }

    // default/trivial implementation
    function bundleMatchesApplication(
        IBundle.Bundle memory bundle, 
        IPolicy.Application memory application
    ) 
        public
        view
        returns(bool isMatching) 
    {
        // matches with any application
        uint256 bundleId = bundle.id;
        isMatching = true;
    }


    function _freeCollateral(bytes32 processId) 
        internal override
        returns(uint256 collateralAmount) 
    {        
        uint256 bundleId = _collateralizedBy[processId];
        collateralAmount = _riskpoolService.expirePolicy(bundleId, processId);
    }
}