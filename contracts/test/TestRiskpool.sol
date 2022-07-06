// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/IntSet.sol"; // TODO decide on better fitting name
import "../services/InstanceService.sol"; // TODO remove once getBundle is fixed

import "@gif-interface/contracts/modules/IBundle.sol";
import "@gif-interface/contracts/components/Component.sol";
import "@gif-interface/contracts/components/IRiskpool.sol";
import "@gif-interface/contracts/services/IInstanceService.sol";
import "@gif-interface/contracts/services/IRiskpoolService.sol";


contract TestRiskpool is 
    IRiskpool, 
    Component 
{
    // used for representation of collateralization
    // collateralization between 0 and 1 (1=100%) 
    // value might be larger when overcollateralization
    uint256 public constant COLLATERALIZATION_DECIMALS = 10000;

    string public constant DEFAULT_FILTER_DATA_STRUCTURE = "";

    InstanceService private _instanceService; // TODO change to IInstanceService
    IRiskpoolService private _riskpoolService;
    
    uint256 [] private _bundleIds;
    IntSet private _activeBundleIds;

    address private _wallet;
    uint256 private _collateralization;
    uint256 private _valueTotal;
    uint256 private _valueLocked;

    modifier onlyUnderwriting {
        require(
             _msgSender() == _getContractAddress("Underwriting"),
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

    function createBundle(bytes calldata filter, uint256 initialAmount) 
        external override
        returns(uint256 bundleId)
    {
        bundleId = _riskpoolService.createBundle(filter, initialAmount);

        _bundleIds.push(bundleId);
        _activeBundleIds.add(bundleId); // TODO consider to actually check that bundle is active
    }

    function collateralizePolicy(bytes32 processId) 
        external override
        onlyUnderwriting
        returns(bool isSecured) 
    {
        uint256 requiredCapital = _calculateRiskCapital(processId);
        isSecured = _lockCapital(processId, requiredCapital);
    }

    function expirePolicy(bytes32 processId) 
        external override
        onlyUnderwriting
    {
        _freeCapital(processId);
    }


    function preparePayout(bytes32 processId, uint256 payoutId, uint256 amount) external override {
        revert("ERROR:RPL-991:SECURE_PAYOUT_NOT_IMPLEMENTED");
    }

    function executePayout(bytes32 processId, uint256 payoutId) external override {
        revert("ERROR:RPL-991:EXECUTE_PAYOUT_NOT_IMPLEMENTED");
    }

    function _calculateRiskCapital(bytes32 processId) internal view returns (uint256 riskCapital) {
        uint256 sumInsured = _getSumInsured(processId);
        // https://ethereum.stackexchange.com/questions/91367/is-the-safemath-library-obsolete-in-solidity-0-8-0
        riskCapital = (sumInsured * COLLATERALIZATION_DECIMALS) / _collateralization;
    }

    // TODO add to interface- -> to be provided by policy service
    function _getSumInsured(bytes32 processId) internal view returns (uint256) {
        return 0;
    }
    
    // needs to remember which bundles helped to cover ther risk
    // simple (retail) approach: single policy covered by single bundle
    //   forst bundle with a match and sufficient capacity wins
    // complex (wholesale) approach: single policy covered by many bundles
    // Component <- Riskpool <- BasicRiskpool <- TestRiskpool
    // Component <- Riskpool <- AdvancedRiskpool <- TestRiskpool
    function _lockCapital(bytes32 processId, uint256 riskCapital) internal returns(bool success) {
        require(_valueTotal > _valueLocked, "ERROR:RPL-004:NO_FREE_CAPITAL");

        if(_valueTotal >= _valueLocked + riskCapital) {         
            // update value locked before any actual locking in bundles  
            _valueLocked += riskCapital;

            // TODO implement allocation of capital via bundles
            // should be responsibility of riskpoo to decide if a policy should 
            // bbe covered by a single bundle or a set of bundles
            // given a processId riskpool must know which bundle(S) are covering it
            // given a processId a bundle knows how much capital is locked for this policy

            success = true;
        }
    }


    function _freeCapital(bytes32 processId) internal returns(bool success) {
        
        // TODO get risk capital associated with processId
        uint256 riskCapital = 0;
        // TODO implement freeing of capital via bundles

        // update value locked after any actual freeing of capital in bundles  
        _valueLocked -= riskCapital;
    }

    function getCollateralizationLevel() public view override returns (uint256) {
        return _collateralization;
    }


    function getCollateralizationDecimals() public view override returns (uint256) {
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

    function getFilterDataStructure() external override view returns(string memory) {
        return DEFAULT_FILTER_DATA_STRUCTURE;
    }

    function getCapacity() external override view returns(uint256) {
        revert("ERROR:RPL-991:CAPACITY_NOT_IMPLEMENTED");
    }

    function getTotalValueLocked() external override view returns(uint256) {
        revert("ERROR:RPL-991:TVL_NOT_IMPLEMENTED");
    }
    

    function getPrice() external override view returns(uint256) {
        revert("ERROR:RPL-991:PRICE_NOT_IMPLEMENTED");
    }

}