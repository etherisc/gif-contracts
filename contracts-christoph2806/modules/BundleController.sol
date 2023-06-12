// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "./PolicyController.sol";
import "../shared/CoreController.sol";
import "../tokens/BundleToken.sol";

import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/modules/IBundle.sol";
import "./PoolController.sol";


contract BundleController is 
    IBundle,
    CoreController
{

    PolicyController private _policy;
    BundleToken private _token; 

    mapping(uint256 /* bundleId */ => Bundle /* Bundle */) private _bundles;
    mapping(uint256 /* bundleId */ => uint256 /* activePolicyCount */) private _activePolicies;
    mapping(uint256 /* bundleId */ => mapping(bytes32 /* processId */ => uint256 /* lockedCapitalAmount */)) private _valueLockedPerPolicy;
    mapping(uint256 /* riskpoolId */ => uint256 /* numberOfUnburntBundles */) private _unburntBundlesForRiskpoolId;
    

    uint256 private _bundleCount;

    modifier onlyRiskpoolService() {
        require(
            _msgSender() == _getContractAddress("RiskpoolService"),
            "ERROR:BUC-001:NOT_RISKPOOL_SERVICE"
        );
        _;
    }

    modifier onlyFundableBundle(uint256 bundleId) {
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-002:BUNDLE_DOES_NOT_EXIST");
        require(
            bundle.state != IBundle.BundleState.Burned 
            && bundle.state != IBundle.BundleState.Closed, "ERROR:BUC-003:BUNDLE_BURNED_OR_CLOSED"
        );
        _;
    }

    /**
     * @dev Performs internal operations after the contract initialization.
     *
     *
     */
    function _afterInitialize() internal override onlyInitializing {
        _policy = PolicyController(_getContractAddress("Policy"));
        _token = BundleToken(_getContractAddress("BundleToken"));
    }

    /**
     * @dev Creates a new bundle and mints a corresponding NFT token. Only callable by the RiskpoolService contract.
     * @param owner_ The address of the bundle owner.
     * @param riskpoolId_ The ID of the riskpool associated with the bundle.
     * @param filter_ The filter used for the bundle.
     * @param amount_ The amount of capital allocated to the bundle.
     * @return bundleId The ID of the newly created bundle.
     * @notice This function emits 1 events: 
     * - LogBundleCreated
     */
    function create(address owner_, uint riskpoolId_, bytes calldata filter_, uint256 amount_) 
        external override
        onlyRiskpoolService
        returns(uint256 bundleId)
    {   
        // will start with bundleId 1.
        // this helps in maps where a bundleId equals a non-existing entry
        bundleId = _bundleCount + 1;
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt == 0, "ERROR:BUC-010:BUNDLE_ALREADY_EXISTS");

        // mint corresponding nft with bundleId as nft
        uint256 tokenId = _token.mint(bundleId, owner_);

        bundle.id = bundleId;
        bundle.tokenId = tokenId;
        bundle.riskpoolId = riskpoolId_;
        bundle.state = BundleState.Active;
        bundle.filter = filter_;
        bundle.capital = amount_;
        bundle.balance = amount_;
        bundle.createdAt = block.timestamp;
        bundle.updatedAt = block.timestamp;

        // update bundle count
        _bundleCount++;
        _unburntBundlesForRiskpoolId[riskpoolId_]++;

        emit LogBundleCreated(bundle.id, riskpoolId_, owner_, bundle.state, bundle.capital);
    }


    /**
     * @dev Adds funds to a bundle's capital and balance.
     * @param bundleId The ID of the bundle to add funds to.
     * @param amount The amount of funds to add to the bundle.
     * @notice This function emits 1 events: 
     * - LogBundleCapitalProvided
     */
    function fund(uint256 bundleId, uint256 amount)
        external override 
        onlyRiskpoolService
    {
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-011:BUNDLE_DOES_NOT_EXIST");
        require(bundle.state != IBundle.BundleState.Closed, "ERROR:BUC-012:BUNDLE_CLOSED");

        bundle.capital += amount;
        bundle.balance += amount;
        bundle.updatedAt = block.timestamp;

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundleCapitalProvided(bundleId, _msgSender(), amount, capacityAmount);
    }


    /**
     * @dev Allows the Riskpool service to withdraw `amount` from the `bundleId` Bundle.
     * @param bundleId The ID of the Bundle to be defunded.
     * @param amount The amount of tokens to be withdrawn.
     * @notice This function emits 1 events: 
     * - LogBundleCapitalWithdrawn
     */
    function defund(uint256 bundleId, uint256 amount) 
        external override 
        onlyRiskpoolService
    {
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-013:BUNDLE_DOES_NOT_EXIST");
        require(
            bundle.capital >= bundle.lockedCapital + amount
            || (bundle.lockedCapital == 0 && bundle.balance >= amount),
            "ERROR:BUC-014:CAPACITY_OR_BALANCE_TOO_LOW"
        );

        if (bundle.capital >= amount) { bundle.capital -= amount; } 
        else                          { bundle.capital = 0; }

        bundle.balance -= amount;
        bundle.updatedAt = block.timestamp;

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundleCapitalWithdrawn(bundleId, _msgSender(), amount, capacityAmount);
    }

    /**
     * @dev Locks a bundle of assets.
     * @param bundleId The ID of the bundle to be locked.
     */
    function lock(uint256 bundleId)
        external override
        onlyRiskpoolService
    {
        _changeState(bundleId, BundleState.Locked);
    }

    /**
     * @dev Unlocks a bundle, changing its state to active.
     * @param bundleId The ID of the bundle to be unlocked.
     */
    function unlock(uint256 bundleId)
        external override
        onlyRiskpoolService
    {
        _changeState(bundleId, BundleState.Active);
    }

    /**
     * @dev Closes a bundle of policies.
     * @param bundleId The ID of the bundle to close.
     */
    function close(uint256 bundleId)
        external override
        onlyRiskpoolService
    {
        require(_activePolicies[bundleId] == 0, "ERROR:BUC-015:BUNDLE_WITH_ACTIVE_POLICIES");
        _changeState(bundleId, BundleState.Closed);
    }

    /**
     * @dev Burns a bundle and changes its state to Burned.
     * @param bundleId The ID of the bundle to be burned.
     *
     * Requirements:
     * - The bundle must be in the Closed state.
     * - The bundle must have a balance of 0.
     *
     * Emits a {BundleStateChanged} event with BundleState.Burned.
     */
    function burn(uint256 bundleId)    
        external override
        onlyRiskpoolService
    {
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.state == BundleState.Closed, "ERROR:BUC-016:BUNDLE_NOT_CLOSED");
        require(bundle.balance == 0, "ERROR:BUC-017:BUNDLE_HAS_BALANCE");

        // burn corresponding nft -> as a result bundle looses its owner
        _token.burn(bundleId);
        _unburntBundlesForRiskpoolId[bundle.riskpoolId] -= 1;

        _changeState(bundleId, BundleState.Burned);
    }

    /**
     * @dev Collateralizes a policy by locking a specific amount of capital in the corresponding bundle.
     * @param bundleId The ID of the bundle to collateralize.
     * @param processId The ID of the policy to collateralize.
     * @param amount The amount of capital to lock in the bundle.
     *
     * Requirements:
     * - Caller must be the riskpool service.
     * - The bundle must belong to the riskpool that controls the product of the policy.
     * - The bundle must exist and be in an active state.
     * - The capacity of the bundle must be enough to lock the amount of capital.
     * - The policy must not have been previously collateralized.
     *
     * Emits a {LogBundlePolicyCollateralized} event with the bundle ID, policy ID, amount of capital locked, and the remaining capacity of the bundle.
     * @notice This function emits 1 events: 
     * - LogBundlePolicyCollateralized
     */
    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 amount)
        external override 
        onlyRiskpoolService
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.riskpoolId == _getPoolController().getRiskPoolForProduct(metadata.productId), "ERROR:BUC-019:BUNDLE_NOT_IN_RISKPOOL");
        require(bundle.createdAt > 0, "ERROR:BUC-020:BUNDLE_DOES_NOT_EXIST");
        require(bundle.state == IBundle.BundleState.Active, "ERROR:BUC-021:BUNDLE_NOT_ACTIVE");        
        require(bundle.capital >= bundle.lockedCapital + amount, "ERROR:BUC-022:CAPACITY_TOO_LOW");

        // might need to be added in a future relase
        require(_valueLockedPerPolicy[bundleId][processId] == 0, "ERROR:BUC-023:INCREMENTAL_COLLATERALIZATION_NOT_IMPLEMENTED");

        bundle.lockedCapital += amount;
        bundle.updatedAt = block.timestamp;

        _activePolicies[bundleId] += 1;
        _valueLockedPerPolicy[bundleId][processId] = amount;

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundlePolicyCollateralized(bundleId, processId, amount, capacityAmount);
    }


    /**
     * @dev Process the premium payment for a given bundle and update its balance.
     * @param bundleId The ID of the bundle to process the premium payment for.
     * @param processId The ID of the process associated with the policy.
     * @param amount The amount of premium to be processed.
     *
     * Requirements:
     * - The caller must be the riskpool service.
     * - The bundle must exist and be fundable.
     * - The policy associated with the process must not be closed.
     * - The bundle must exist.
     *
     * Effects:
     * - Increases the balance of the bundle by the amount processed.
     * - Updates the updatedAt timestamp of the bundle.
     */
    function processPremium(uint256 bundleId, bytes32 processId, uint256 amount)
        external override
        onlyRiskpoolService
        onlyFundableBundle(bundleId)
    {
        IPolicy.Policy memory policy = _policy.getPolicy(processId);
        require(
            policy.state != IPolicy.PolicyState.Closed,
            "ERROR:POL-030:POLICY_STATE_INVALID"
        );

        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-031:BUNDLE_DOES_NOT_EXIST");
        
        bundle.balance += amount;
        bundle.updatedAt = block.timestamp; // solhint-disable-line
    }


    /**
     * @dev Processes a payout for a policy from a bundle.
     * @param bundleId The ID of the bundle.
     * @param processId The ID of the policy process.
     * @param amount The amount of the payout.
     *
     * Emits a LogBundlePayoutProcessed event.
     * @notice This function emits 1 events: 
     * - LogBundlePayoutProcessed
     */
    function processPayout(uint256 bundleId, bytes32 processId, uint256 amount) 
        external override 
        onlyRiskpoolService
    {
        IPolicy.Policy memory policy = _policy.getPolicy(processId);
        require(
            policy.state != IPolicy.PolicyState.Closed,
            "ERROR:POL-040:POLICY_STATE_INVALID"
        );

        // check there are policies and there is sufficient locked capital for policy
        require(_activePolicies[bundleId] > 0, "ERROR:BUC-041:NO_ACTIVE_POLICIES_FOR_BUNDLE");
        require(_valueLockedPerPolicy[bundleId][processId] >= amount, "ERROR:BUC-042:COLLATERAL_INSUFFICIENT_FOR_POLICY");

        // make sure bundle exists and is not yet closed
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-043:BUNDLE_DOES_NOT_EXIST");
        require(
            bundle.state == IBundle.BundleState.Active
            || bundle.state == IBundle.BundleState.Locked, 
            "ERROR:BUC-044:BUNDLE_STATE_INVALID");
        require(bundle.capital >= amount, "ERROR:BUC-045:CAPITAL_TOO_LOW");
        require(bundle.lockedCapital >= amount, "ERROR:BUC-046:LOCKED_CAPITAL_TOO_LOW");
        require(bundle.balance >= amount, "ERROR:BUC-047:BALANCE_TOO_LOW");

        _valueLockedPerPolicy[bundleId][processId] -= amount;
        bundle.capital -= amount;
        bundle.lockedCapital -= amount;
        bundle.balance -= amount;
        bundle.updatedAt = block.timestamp; // solhint-disable-line

        emit LogBundlePayoutProcessed(bundleId, processId, amount);
    }


    /**
     * @dev Release a policy and update the bundle capital.
     * @param bundleId The ID of the bundle.
     * @param processId The ID of the process.
     * @return remainingCollateralAmount The remaining collateral amount after releasing the policy.
     * @notice This function emits 1 events: 
     * - LogBundlePolicyReleased
     */
    function releasePolicy(uint256 bundleId, bytes32 processId) 
        external override 
        onlyRiskpoolService
        returns(uint256 remainingCollateralAmount)
    {
        IPolicy.Policy memory policy = _policy.getPolicy(processId);
        require(
            policy.state == IPolicy.PolicyState.Closed,
            "ERROR:POL-050:POLICY_STATE_INVALID"
        );

        // make sure bundle exists and is not yet closed
        Bundle storage bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-051:BUNDLE_DOES_NOT_EXIST");
        require(_activePolicies[bundleId] > 0, "ERROR:BUC-052:NO_ACTIVE_POLICIES_FOR_BUNDLE");

        uint256 lockedForPolicyAmount = _valueLockedPerPolicy[bundleId][processId];
        // this should never ever fail ...
        require(
            bundle.lockedCapital >= lockedForPolicyAmount,
            "PANIC:BUC-053:UNLOCK_CAPITAL_TOO_BIG"
        );

        // policy no longer relevant for bundle
        _activePolicies[bundleId] -= 1;
        delete _valueLockedPerPolicy[bundleId][processId];

        // update bundle capital
        bundle.lockedCapital -= lockedForPolicyAmount;
        bundle.updatedAt = block.timestamp; // solhint-disable-line

        uint256 capacityAmount = bundle.capital - bundle.lockedCapital;
        emit LogBundlePolicyReleased(bundleId, processId, lockedForPolicyAmount, capacityAmount);
    }

    /**
     * @dev Returns the address of the owner of the token associated with the given bundle ID.
     * @param bundleId The ID of the bundle.
     * @return The address of the owner of the token.
     */
    function getOwner(uint256 bundleId) public view returns(address) { 
        uint256 tokenId = getBundle(bundleId).tokenId;
        return _token.ownerOf(tokenId); 
    }

    /**
     * @dev Returns the state of the bundle with the given ID.
     * @param bundleId The ID of the bundle to retrieve the state from.
     * @return The state of the bundle with the given ID.
     */
    function getState(uint256 bundleId) public view returns(BundleState) {
        return getBundle(bundleId).state;   
    }

    /**
     * @dev Returns the filter of a given bundle.
     * @param bundleId The ID of the bundle to get the filter from.
     * @return The filter of the bundle as a bytes array.
     */
    function getFilter(uint256 bundleId) public view returns(bytes memory) {
        return getBundle(bundleId).filter;
    }   

    /**
     * @dev Returns the available capacity of a bundle.
     * @param bundleId The ID of the bundle to get the capacity from.
     * @return The available capacity of the bundle.
     */
    function getCapacity(uint256 bundleId) public view returns(uint256) {
        Bundle memory bundle = getBundle(bundleId);
        return bundle.capital - bundle.lockedCapital;
    }

    /**
     * @dev Returns the total value locked in a particular bundle.
     * @param bundleId The ID of the bundle.
     * @return lockedCapital The total value locked in the bundle.
     */
    function getTotalValueLocked(uint256 bundleId) public view returns(uint256) {
        return getBundle(bundleId).lockedCapital;   
    }

    /**
     * @dev Returns the balance of a specific bundle.
     * @param bundleId The ID of the bundle to query.
     * @return The balance of the specified bundle.
     */
    function getBalance(uint256 bundleId) public view returns(uint256) {
        return getBundle(bundleId).balance;   
    }

    /**
     * @dev Returns the BundleToken contract instance.
     * @return _token The BundleToken contract instance.
     */
    function getToken() external view returns(BundleToken) {
        return _token;
    }

    /**
     * @dev Returns the bundle with the specified bundle ID.
     * @param bundleId The ID of the bundle to retrieve.
     * @return bundle The bundle with the specified ID.
     */
    function getBundle(uint256 bundleId) public view returns(Bundle memory) {
        Bundle memory bundle = _bundles[bundleId];
        require(bundle.createdAt > 0, "ERROR:BUC-060:BUNDLE_DOES_NOT_EXIST");
        return bundle;
    }

    /**
     * @dev Returns the number of bundles created.
     * @return _bundleCount The number of bundles created.
     */
    function bundles() public view returns(uint256) {
        return _bundleCount;
    }

    /**
     * @dev Returns the number of unburnt bundles for a given riskpool ID.
     * @param riskpoolId The ID of the riskpool.
     * @return The number of unburnt bundles for the given riskpool ID.
     */
    function unburntBundles(uint256 riskpoolId) external view returns(uint256) {
        return _unburntBundlesForRiskpoolId[riskpoolId];
    }

    /**
     * @dev Returns the pool controller contract instance.
     * @return _poolController The pool controller contract instance.
     */
    function _getPoolController() internal view returns (PoolController _poolController) {
        _poolController = PoolController(_getContractAddress("Pool"));
    }

    /**
     * @dev Changes the state of a bundle.
     * @param bundleId The ID of the bundle to change the state of.
     * @param newState The new state to set for the bundle.
     * @notice This function emits 1 events: 
     * - LogBundleStateChanged
     */
    function _changeState(uint256 bundleId, BundleState newState) internal {
        BundleState oldState = getState(bundleId);

        _checkStateTransition(oldState, newState);
        _setState(bundleId, newState);

        // log entry for successful state change
        emit LogBundleStateChanged(bundleId, oldState, newState);
    }

    /**
     * @dev Sets the state and updated timestamp of a given bundle.
     * @param bundleId The ID of the bundle to update.
     * @param newState The new state of the bundle.
     */
    function _setState(uint256 bundleId, BundleState newState) internal {
        _bundles[bundleId].state = newState;
        _bundles[bundleId].updatedAt = block.timestamp;
    }

    /**
     * @dev Checks if a state transition is valid.
     * @param oldState The previous state of the bundle.
     * @param newState The new state of the bundle.
     *
     * Requirements:
     * - The oldState must be Active, Locked, Closed, or Burned.
     * - The newState must be Locked, Active, Closed, or Burned, depending on the oldState.
     *
     * Error messages:
     * - ERROR:BUC-070:ACTIVE_INVALID_TRANSITION if the oldState is Active and the newState is not Locked or Closed.
     * - ERROR:BUC-071:LOCKED_INVALID_TRANSITION if the oldState is Locked and the newState is not Active or Closed.
     * - ERROR:BUC-072:CLOSED_INVALID_TRANSITION if the oldState is Closed and the newState is not Burned.
     * - ERROR:BUC-073:BURNED_IS_FINAL_STATE if the oldState is Burned.
     * - ERROR:BOC-074:INITIAL_STATE_NOT_HANDLED if the oldState is not Active, Locked, Closed, or Burned.
     */
    function _checkStateTransition(BundleState oldState, BundleState newState) 
        internal 
        pure 
    {
        if (oldState == BundleState.Active) {
            require(
                newState == BundleState.Locked || newState == BundleState.Closed, 
                "ERROR:BUC-070:ACTIVE_INVALID_TRANSITION"
            );
        } else if (oldState == BundleState.Locked) {
            require(
                newState == BundleState.Active || newState == BundleState.Closed, 
                "ERROR:BUC-071:LOCKED_INVALID_TRANSITION"
            );
        } else if (oldState == BundleState.Closed) {
            require(
                newState == BundleState.Burned, 
                "ERROR:BUC-072:CLOSED_INVALID_TRANSITION"
            );
        } else if (oldState == BundleState.Burned) {
            revert("ERROR:BUC-073:BURNED_IS_FINAL_STATE");
        } else {
            revert("ERROR:BOC-074:INITIAL_STATE_NOT_HANDLED");
        }
    }
}
