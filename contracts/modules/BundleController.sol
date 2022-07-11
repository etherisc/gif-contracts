// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./PolicyController.sol";
import "../shared/CoreController.sol";
import "../tokens/BundleToken.sol";

import "@gif-interface/contracts/modules/IBundle.sol";

contract BundleController is 
    IBundle,
    CoreController
{

    PolicyController private _policy;
    BundleToken private _token; 

    mapping(uint256 => Bundle) private _bundles;
    mapping(uint256 => mapping(bytes32 => uint256)) private _valueLockedPerPolicy;

    uint256 private _bundleCount;

    modifier onlyRiskpoolService() {
        require(
            _msgSender() == _getContractAddress("RiskpoolService"),
            "ERROR:BUC-001:NOT_RISKPOOL_SERVICE"
        );
        _;
    }

    function _afterInitialize() internal override onlyInitializing {
        _policy = PolicyController(_getContractAddress("Policy"));
        _token = BundleToken(_getContractAddress("BundleToken"));
    }

    function create(address owner_, uint riskpoolId_, bytes calldata filter_, uint256 amount_) 
        external override
        onlyRiskpoolService
        returns(uint256 bundleId)
    {   
        // will start with bundleId 1.
        // this helps in maps where a bundleId equals a non-existing entry
        bundleId = _bundleCount + 1;
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt == 0, "ERROR:BUC-002:BUNDLE_ALREADY_EXISTS");

        // register initial bundle data
        bundle.id = bundleId;
        bundle.owner = owner_;
        bundle.riskpoolId = riskpoolId_;
        bundle.state = BundleState.Active;
        bundle.filter = filter_;
        bundle.capital = amount_;
        bundle.balance = amount_;
        bundle.createdAt = block.timestamp;
        bundle.updatedAt = block.timestamp;

        // mint corresponding nft with bundleId as nft id and sender as owner

        // TODO analyze, fix and uncomment
        // in brownie console this leads to 
        // oz tx revert: ERC721: transfer to non ERC721Receiver implementer
        // _token.mint(owner_, bundleId);

        // update bundle count
        _bundleCount += 1;

        emit LogBundleCreated(bundle.id, riskpoolId_, bundle.owner, bundle.state, bundle.capital);
    }

    // TODO decide + implement authz for risk bundle creation
    // funding can come from nft owner or various 2nd level risk pool owners
    // consequently, bundle needs to keep track which investor is related to what share in funding
    function fund(uint256 bundleId, uint256 amount) external override {
        Bundle storage bundle = _bundles[bundleId];
        require(
            bundle.state != IBundle.BundleState.Closed, 
            "ERROR:BUC-003:BUNDLE_CLOSED"
        );

        // TODO add collection of tokens from investor/sender
        // TODO implement fee collection/distribution

        bundle.capital += amount;
        bundle.balance += amount;

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundleCapitalProvided(bundleId, _msgSender(), amount, capacityAmount);
    }

    // TODO decide + implement authz for risk bundle creation
    // should this be onlyOwner?
    function withdraw(uint256 bundleId, uint256 amount) external override {
        Bundle storage bundle = _bundles[bundleId];
        require(
            bundle.capital >= bundle.lockedCapital + amount, 
            "ERROR:BUC-004:CAPACITY_TOO_LOW"
        );

        bundle.capital -= amount;
        bundle.balance -= amount;

        // TODO implement fee collection/distribution
        // TODO add distribution of tokens to investor/sender

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundleCapitalWithdrawn(bundleId, _msgSender(), amount, capacityAmount);
    }

    function lock(uint256 bundleId) external override {
        _changeState(bundleId, BundleState.Locked);
    }

    function unlock(uint256 bundleId) external override {
        _changeState(bundleId, BundleState.Active);
    }

    function close(uint256 bundleId) external override {
        revert("ERROR:BUC-991:CLOSE_NOT_IMPLEMENTED");
    }

    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 amount)
        external override 
        onlyRiskpoolService
    {
        Bundle storage bundle = _bundles[bundleId];
        require(
            bundle.state == IBundle.BundleState.Active, 
            "ERROR:BUC-005:BUNDLE_NOT_ACTIVE"
        );
        
        require(
            bundle.capital >= bundle.lockedCapital + amount, 
            "ERROR:BUC-006:CAPACITY_TOO_LOW"
        );

        bundle.lockedCapital += amount;
        _valueLockedPerPolicy[bundleId][processId] += amount;

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundlePolicyCollateralized(bundleId, processId, amount, capacityAmount);
    }

    function expirePolicy(uint256 bundleId, bytes32 processId) 
        external override 
        onlyRiskpoolService
        returns(uint256 collateralAmount)
    {
        // make sure bundle exists
        Bundle storage bundle = _bundles[bundleId];
        require(
            bundle.createdAt > 0, 
            "ERROR:BUC-007:BUNDLE_DOES_NOT_EXIST"
        );

        // this should never ever fail ...
        collateralAmount = _valueLockedPerPolicy[bundleId][processId];
        require(
            bundle.lockedCapital >= collateralAmount,
            "PANIC:BUC-008:UNLOCK_CAPITAL_TOO_BIG"
        );

        delete _valueLockedPerPolicy[bundleId][processId];
        bundle.lockedCapital -= collateralAmount;

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundlePolicyExpired(bundleId, processId, collateralAmount, capacityAmount);
    }

    function owner(uint256 bundleId) external view returns(address) { 
        return getBundle(bundleId).owner; 
    }

    function state(uint256 bundleId) external view returns(BundleState) {
        return getBundle(bundleId).state;   
    }

    function filter(uint256 bundleId) external view returns(bytes memory) {
        return getBundle(bundleId).filter;
    }   

    function capacity(uint256 bundleId) external view returns(uint256) {
        Bundle memory bundle = getBundle(bundleId);
        return bundle.capital - bundle.lockedCapital;
    }

    function totalValueLocked(uint256 bundleId) external view returns(uint256) {
        return getBundle(bundleId).lockedCapital;   
    }

    function price(uint256 bundleId) external view returns(uint256) {
        return getBundle(bundleId).balance;   
    }

    function getBundle(uint256 bundleId) public view returns(Bundle memory) {
        Bundle memory bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-001:BUNDLE_DOES_NOT_EXIST");
        return bundle;
    }

    function bundles() public view returns(uint256) {
        return _bundleCount;
    }

    function _changeState(uint256 bundleId, BundleState newState) internal {
        BundleState oldState = this.state(bundleId);

        _checkStateTransition(oldState, newState);
        _setState(bundleId, newState);

        // log entry for successful state change
        emit LogBundleStateChanged(bundleId, oldState, newState);
    }

    function _setState(uint256 bundleId, BundleState newState) internal {
        _bundles[bundleId].state = newState;
    }

    function _checkStateTransition(BundleState oldState, BundleState newState) 
        internal 
        pure 
    {
        if (oldState == BundleState.Active) {
            require(
                newState == BundleState.Locked || newState == BundleState.Closed, 
                "ERROR:BUC-013:ACTIVE_INVALID_TRANSITION"
            );
        } else if (oldState == BundleState.Locked) {
            require(
                newState == BundleState.Active || newState == BundleState.Closed, 
                "ERROR:BUC-013:LOCKED_INVALID_TRANSITION"
            );
        } else if (oldState == BundleState.Closed) {
            revert("ERROR:BUC-014:CLOSED_IS_FINAL_STATE");
        } else {
            revert("ERROR:BOC-018:INITIAL_STATE_NOT_HANDLED");
        }
    }
    
}
