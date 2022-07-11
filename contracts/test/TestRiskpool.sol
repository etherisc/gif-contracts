// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./IdSet.sol";
import "../services/InstanceService.sol"; // TODO remove once getBundle is fixed

import "@gif-interface/contracts/modules/IBundle.sol";
import "@gif-interface/contracts/modules/IPolicy.sol";
import "@gif-interface/contracts/components/Component.sol";
import "@gif-interface/contracts/components/IRiskpool.sol";
import "@gif-interface/contracts/services/IInstanceService.sol";
import "@gif-interface/contracts/services/IRiskpoolService.sol";

// TODO consider to move bunlde per riskpool book keeping to bundle controller
contract TestRiskpool is 
    IRiskpool, 
    IdSet,
    Component 
{

    event LogRiskpoolBundleCreated(uint256 bundleId, uint256 amount);
    event LogRiskpoolRequiredCollateral(bytes32 processId, uint256 sumInsured, uint256 collateral);
    event LogRiskpoolBundleMatchesPolicy(uint256 bundleId, bool isMatching);
    event LogRiskpoolCollateralLocked(bytes32 processId, uint256 collateralAmount, bool isSecured);
    
    // used for representation of collateralization
    // collateralization between 0 and 1 (1=100%) 
    // value might be larger when overcollateralization
    uint256 public constant COLLATERALIZATION_DECIMALS = 10000;

    string public constant DEFAULT_FILTER_DATA_STRUCTURE = "";

    InstanceService private _instanceService; // TODO change to IInstanceService
    IRiskpoolService private _riskpoolService;
    
    uint256 [] private _bundleIds;

    // remember bundleId for each processId
    // approach only works for basic risk pool where a
    // policy is collateralized by exactly one bundle
    mapping(bytes32 => uint256) private _collateralizedBy;

    address private _wallet;
    uint256 private _collateralization;
    uint256 private _capital;
    uint256 private _lockedCapital;
    uint256 private _balance;

    modifier onlyPool {
        require(
             _msgSender() == _getContractAddress("Pool"),
            "ERROR:RPL-001:ACCESS_DENIED"
        );
        _;
    }

    constructor(
        bytes32 name,
        uint256 collateralization,
        address wallet,
        address registry
    )
        Component(name, ComponentType.Riskpool, registry)
    { 
        require(wallet != address(0), "ERROR:RPL-002:COLLATERALIZATION_ZERO");
        _collateralization = collateralization;

        require(wallet != address(0), "ERROR:RPL-003:WALLET_ADDRESS_ZERO");
        _wallet = wallet;

        _instanceService = InstanceService(_getContractAddress("InstanceService")); // TODO change to IInstanceService
        _riskpoolService = IRiskpoolService(_getContractAddress("RiskpoolService"));
    }

    // TODO decide on authz for bundle creation
    function createBundle(bytes calldata filter, uint256 initialAmount) 
        external override
        returns(uint256 bundleId)
    {
        address bundleOwner = _msgSender();
        bundleId = _riskpoolService.createBundle(bundleOwner, filter, initialAmount);

        _bundleIds.push(bundleId);
        _addIdToSet(bundleId); // TODO consider to actually check that bundle is active

        // update financials
        _capital += initialAmount;
        _balance += initialAmount;

        emit LogRiskpoolBundleCreated(bundleId, initialAmount);
    }


    function collateralizePolicy(bytes32 processId) 
        external override
        onlyPool
        returns(bool isSecured) 
    {
        IPolicy.Application memory application = _instanceService.getApplication(processId);
        uint256 sumInsured = application.sumInsuredAmount;
        uint256 collateralAmount = _calculateCollateralAmount(application);
        emit LogRiskpoolRequiredCollateral(processId, sumInsured, collateralAmount);

        isSecured = _lockCollateral(processId, collateralAmount);
        emit LogRiskpoolCollateralLocked(processId, collateralAmount, isSecured);
    }

    function expirePolicy(bytes32 processId) 
        external override
        onlyPool
    {
        _freeCollateral(processId);
    }


    function preparePayout(bytes32 processId, uint256 payoutId, uint256 amount) external override {
        revert("ERROR:RPL-991:SECURE_PAYOUT_NOT_IMPLEMENTED");
    }

    function executePayout(bytes32 processId, uint256 payoutId) external override {
        revert("ERROR:RPL-991:EXECUTE_PAYOUT_NOT_IMPLEMENTED");
    }

    function _calculateCollateralAmount(IPolicy.Application memory application) internal view returns (uint256 collateralAmount) {
        uint256 sumInsured = application.sumInsuredAmount;

        if (_collateralization == COLLATERALIZATION_DECIMALS) {
            collateralAmount = sumInsured;
        } else {
            // https://ethereum.stackexchange.com/questions/91367/is-the-safemath-library-obsolete-in-solidity-0-8-0
            collateralAmount = (_collateralization * sumInsured) / COLLATERALIZATION_DECIMALS;
        }
    }
    
    // needs to remember which bundles helped to cover ther risk
    // simple (retail) approach: single policy covered by single bundle
    //   forst bundle with a match and sufficient capacity wins
    // complex (wholesale) approach: single policy covered by many bundles
    // Component <- Riskpool <- BasicRiskpool <- TestRiskpool
    // Component <- Riskpool <- AdvancedRiskpool <- TestRiskpool
    function _lockCollateral(bytes32 processId, uint256 collateralAmount) internal returns(bool success) {
        uint256 activeBundles = _idSetSize();
        require(activeBundles > 0, "ERROR:RPL-004:NO_ACTIVE_BUNDLES");
        require(_capital > _lockedCapital, "ERROR:RPL-005:NO_FREE_CAPITAL");

        // ensure there is a chance to find the collateral
        if(_capital >= _lockedCapital + collateralAmount) {
            IPolicy.Application memory application = _instanceService.getApplication(processId);

            // basic riskpool implementation: policy coverage by single bundle only
            uint i;
            while (i < activeBundles && !success) {
                uint256 bundleId = _idInSetAt(i);
                uint256 maxAmount = _maxCollateralFromBundle(bundleId, application);

                if (maxAmount >= collateralAmount) {
                    _riskpoolService.collateralizePolicy(bundleId, processId, collateralAmount);
                    _collateralizedBy[processId] = bundleId;

                    _lockedCapital += collateralAmount;
                    success = true;
                } else {
                    i++;
                }
            }
        }
    }

    // this is the product/riskpool specific definition of what can be done with filters
    function _maxCollateralFromBundle(uint256 bundleId, IPolicy.Application memory application)
        internal
        returns(uint256 maxCollateralAmount)
    {
        IBundle.Bundle memory bundle = _instanceService.getBundle(bundleId);
        
        if (_bundleFilterMatchesApplication(bundle, application)) {
            maxCollateralAmount = bundle.capital - bundle.lockedCapital;
        }
    }

    // default/trivial implementation
    function _bundleFilterMatchesApplication(
        IBundle.Bundle memory bundle, 
        IPolicy.Application memory application
    ) 
        internal 
        returns(bool isMatching) 
    {
        // matches with any application
        uint256 bundleId = bundle.id;
        isMatching = true;

        emit LogRiskpoolBundleMatchesPolicy(bundleId, isMatching);
    }


    function _freeCollateral(bytes32 processId) internal returns(bool success) {
        
        uint256 bundleId = _collateralizedBy[processId];
        uint256 freedCollateral = _riskpoolService.expirePolicy(bundleId, processId);

        // update value locked after any actual freeing of capital in bundles  
        _lockedCapital -= freedCollateral;
    }

    function getCollateralizationLevel() public view override returns (uint256) {
        return _collateralization;
    }


    function getCollateralizationDecimals() public pure override returns (uint256) {
        return COLLATERALIZATION_DECIMALS;
    }

    function bundles() public override view returns(uint256) {
        return _bundleIds.length;
    }

    function getBundle(uint256 idx) public override view returns(IBundle.Bundle memory) {
        require(idx < _bundleIds.length, "ERROR:RPL-005:BUNDLE_INDEX_TOO_LARGE");

        uint256 bundleIdx = _bundleIds[idx];
        return _instanceService.getBundle(bundleIdx);
    }

    function getFilterDataStructure() external override pure returns(string memory) {
        return DEFAULT_FILTER_DATA_STRUCTURE;
    }

    function getCapacity() external override view returns(uint256) {
        return _capital - _lockedCapital;
    }

    function getTotalValueLocked() external override view returns(uint256) {
        return _lockedCapital;
    }

    function getBalance() external override view returns(uint256) {
        return _balance;
    }

}