// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "./ComponentController.sol";
import "./PolicyController.sol";
import "./BundleController.sol";
import "./PoolController.sol";
import "../shared/CoreController.sol";
import "../shared/TransferHelper.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";
import "@etherisc/gif-interface/contracts/modules/ITreasury.sol";

import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract TreasuryModule is 
    ITreasury,
    CoreController,
    Pausable
{
    uint256 public constant FRACTION_FULL_UNIT = 10**18;
    uint256 public constant FRACTIONAL_FEE_MAX = FRACTION_FULL_UNIT / 4; // max frctional fee is 25%

    event LogTransferHelperInputValidation1Failed(bool tokenIsContract, address from, address to);
    event LogTransferHelperInputValidation2Failed(uint256 balance, uint256 allowance);
    event LogTransferHelperCallFailed(bool callSuccess, uint256 returnDataLength, bytes returnData);

    address private _instanceWalletAddress;
    mapping(uint256 => address) private _riskpoolWallet; // riskpoolId => walletAddress
    mapping(uint256 => FeeSpecification) private _fees; // componentId => fee specification
    mapping(uint256 => IERC20) private _componentToken; // productId/riskpoolId => erc20Address

    BundleController private _bundle;
    ComponentController private _component;
    PolicyController private _policy;
    PoolController private _pool;

    modifier instanceWalletDefined() {
        require(
            _instanceWalletAddress != address(0),
            "ERROR:TRS-001:INSTANCE_WALLET_UNDEFINED");
        _;
    }

    modifier riskpoolWalletDefinedForProcess(bytes32 processId) {
        (uint256 riskpoolId, address walletAddress) = _getRiskpoolWallet(processId);
        require(
            walletAddress != address(0),
            "ERROR:TRS-002:RISKPOOL_WALLET_UNDEFINED");
        _;
    }

    modifier riskpoolWalletDefinedForBundle(uint256 bundleId) {
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            getRiskpoolWallet(bundle.riskpoolId) != address(0),
            "ERROR:TRS-003:RISKPOOL_WALLET_UNDEFINED");
        _;
    }

    // surrogate modifier for whenNotPaused to create treasury specific error message
    modifier whenNotSuspended() {
        require(!paused(), "ERROR:TRS-004:TREASURY_SUSPENDED");
        _;
    }

    modifier onlyRiskpoolService() {
        require(
            _msgSender() == _getContractAddress("RiskpoolService"),
            "ERROR:TRS-005:NOT_RISKPOOL_SERVICE"
        );
        _;
    }

    /**
     * @dev Sets the addresses of the BundleController, ComponentController, PolicyController, and PoolController contracts.
     *
     *
     */
    function _afterInitialize() internal override onlyInitializing {
        _bundle = BundleController(_getContractAddress("Bundle"));
        _component = ComponentController(_getContractAddress("Component"));
        _policy = PolicyController(_getContractAddress("Policy"));
        _pool = PoolController(_getContractAddress("Pool"));
    }

    /**
     * @dev Suspends the treasury contract, preventing any further transfers or withdrawals.
     *      Can only be called by the instance operator.
     *
     * @notice This function emits 1 events: 
     * - LogTreasurySuspended
     */
    function suspend() 
        external 
        onlyInstanceOperator
    {
        _pause();
        emit LogTreasurySuspended();
    }

    /**
     * @dev Resumes the treasury contract after it has been paused.
     *
     *
     * @notice This function emits 1 events: 
     * - LogTreasuryResumed
     */
    function resume() 
        external 
        onlyInstanceOperator
    {
        _unpause();
        emit LogTreasuryResumed();
    }

    /**
     * @dev Sets the ERC20 token address for a given product ID and its associated risk pool.
     * @param productId The ID of the product for which the token address is being set.
     * @param erc20Address The address of the ERC20 token to be set.
     *
     * Emits a LogTreasuryProductTokenSet event with the product ID, risk pool ID, and ERC20 token address.
     *
     * Requirements:
     * - The ERC20 token address must not be zero.
     * - The product must exist.
     * - The product token must not have already been set.
     * - The product token address must match the token address of the corresponding product.
     * - If the risk pool token address has already been set, it must match the product token address.
     * @notice This function emits 1 events: 
     * - LogTreasuryProductTokenSet
     */
    function setProductToken(uint256 productId, address erc20Address)
        external override
        whenNotSuspended
        onlyInstanceOperator
    {
        require(erc20Address != address(0), "ERROR:TRS-010:TOKEN_ADDRESS_ZERO");

        require(_component.isProduct(productId), "ERROR:TRS-011:NOT_PRODUCT");
        require(address(_componentToken[productId]) == address(0), "ERROR:TRS-012:PRODUCT_TOKEN_ALREADY_SET");    
        
        IComponent component = _component.getComponent(productId);
        require(address(IProduct(address(component)).getToken()) == erc20Address, "ERROR:TRS-013:PRODUCT_TOKEN_ADDRESS_NOT_MATCHING");

        uint256 riskpoolId = _pool.getRiskPoolForProduct(productId);

        // require if riskpool token is already set and product token does match riskpool token
        require(address(_componentToken[riskpoolId]) == address(0)
                || address(_componentToken[riskpoolId]) == erc20Address, 
                "ERROR:TRS-014:RISKPOOL_TOKEN_ADDRESS_NOT_MACHING");
        
        _componentToken[productId] = IERC20(erc20Address);
        _componentToken[riskpoolId] = IERC20(erc20Address);

        emit LogTreasuryProductTokenSet(productId, riskpoolId, erc20Address);
    }

    /**
     * @dev Sets the address of the instance wallet.
     * @param instanceWalletAddress The address of the instance wallet to be set.
     *
     * Emits a LogTreasuryInstanceWalletSet event.
     * @notice This function emits 1 events: 
     * - LogTreasuryInstanceWalletSet
     */
    function setInstanceWallet(address instanceWalletAddress) 
        external override
        whenNotSuspended
        onlyInstanceOperator
    {
        require(instanceWalletAddress != address(0), "ERROR:TRS-015:WALLET_ADDRESS_ZERO");
        _instanceWalletAddress = instanceWalletAddress;

        emit LogTreasuryInstanceWalletSet (instanceWalletAddress);
    }

    /**
     * @dev Sets the wallet address for a specific riskpool.
     * @param riskpoolId The ID of the riskpool.
     * @param riskpoolWalletAddress The wallet address to set for the riskpool.
     *
     * Requirements:
     * - The caller must be the instance operator.
     * - The riskpool must exist.
     * - The wallet address cannot be the zero address.
     *
     * Emits a {LogTreasuryRiskpoolWalletSet} event.
     * @notice This function emits 1 events: 
     * - LogTreasuryRiskpoolWalletSet
     */
    function setRiskpoolWallet(uint256 riskpoolId, address riskpoolWalletAddress) 
        external override
        whenNotSuspended
        onlyInstanceOperator
    {
        IComponent component = _component.getComponent(riskpoolId);
        require(_component.isRiskpool(riskpoolId), "ERROR:TRS-016:NOT_RISKPOOL");
        require(riskpoolWalletAddress != address(0), "ERROR:TRS-017:WALLET_ADDRESS_ZERO");
        _riskpoolWallet[riskpoolId] = riskpoolWalletAddress;

        emit LogTreasuryRiskpoolWalletSet (riskpoolId, riskpoolWalletAddress);
    }

    /**
     * @dev Creates a fee specification for a given component.
     * @param componentId The ID of the component for which to create the fee specification.
     * @param fixedFee The fixed fee amount in wei.
     * @param fractionalFee The fractional fee amount as a percentage of the total value.
     * @param feeCalculationData Additional data required for calculating the fee.
     * @return Returns a FeeSpecification struct containing the fee details.
     */
    function createFeeSpecification(
        uint256 componentId,
        uint256 fixedFee,
        uint256 fractionalFee,
        bytes calldata feeCalculationData
    )
        external override
        view 
        returns(FeeSpecification memory)
    {
        require(_component.isProduct(componentId) || _component.isRiskpool(componentId), "ERROR:TRS-020:ID_NOT_PRODUCT_OR_RISKPOOL");
        require(fractionalFee <= FRACTIONAL_FEE_MAX, "ERROR:TRS-021:FRACIONAL_FEE_TOO_BIG");

        return FeeSpecification(
            componentId,
            fixedFee,
            fractionalFee,
            feeCalculationData,
            block.timestamp,  // solhint-disable-line
            block.timestamp   // solhint-disable-line
        ); 
    }

    /**
     * @dev Sets the premium fees for a specific component.
     * @param feeSpec The fee specification for the component.
     *                Includes the component ID, fixed fee, and fractional fee.
     *
     * Emits a LogTreasuryPremiumFeesSet event with the following parameters:
     * - componentId: The ID of the component for which the fees were set.
     * - fixedFee: The fixed fee for the component.
     * - fractionalFee: The fractional fee for the component.
     *
     * Requirements:
     * - The caller must be the instance operator.
     * - The component ID must correspond to a valid product.
     * - The contract must not be suspended.
     * @notice This function emits 1 events: 
     * - LogTreasuryPremiumFeesSet
     */
    function setPremiumFees(FeeSpecification calldata feeSpec) 
        external override
        whenNotSuspended
        onlyInstanceOperator
    {
        require(_component.isProduct(feeSpec.componentId), "ERROR:TRS-022:NOT_PRODUCT");
        
        // record  original creation timestamp 
        uint256 originalCreatedAt = _fees[feeSpec.componentId].createdAt;
        _fees[feeSpec.componentId] = feeSpec;

        // set original creation timestamp if fee spec already existed
        if (originalCreatedAt > 0) {
            _fees[feeSpec.componentId].createdAt = originalCreatedAt;
        }

        emit LogTreasuryPremiumFeesSet (
            feeSpec.componentId,
            feeSpec.fixedFee, 
            feeSpec.fractionalFee);
    }


    /**
     * @dev Sets the fee specification for a given component, which includes the fixed and fractional fees.
     * @param feeSpec The fee specification struct containing the component ID, fixed fee, and fractional fee.
     *
     * Emits a {LogTreasuryCapitalFeesSet} event with the component ID, fixed fee, and fractional fee.
     * @notice This function emits 1 events: 
     * - LogTreasuryCapitalFeesSet
     */
    function setCapitalFees(FeeSpecification calldata feeSpec) 
        external override
        whenNotSuspended
        onlyInstanceOperator
    {
        require(_component.isRiskpool(feeSpec.componentId), "ERROR:TRS-023:NOT_RISKPOOL");

        // record  original creation timestamp 
        uint256 originalCreatedAt = _fees[feeSpec.componentId].createdAt;
        _fees[feeSpec.componentId] = feeSpec;

        // set original creation timestamp if fee spec already existed
        if (originalCreatedAt > 0) {
            _fees[feeSpec.componentId].createdAt = originalCreatedAt;
        }

        emit LogTreasuryCapitalFeesSet (
            feeSpec.componentId,
            feeSpec.fixedFee, 
            feeSpec.fractionalFee);
    }


    /**
     * @dev Calculates the fee amount and net amount for a given component ID and amount.
     * @param componentId The ID of the component for which the fee is being calculated.
     * @param amount The amount for which the fee is being calculated.
     * @return feeAmount The amount of the fee calculated.
     * @return netAmount The net amount after the fee has been deducted.
     */
    function calculateFee(uint256 componentId, uint256 amount)
        public 
        view
        returns(uint256 feeAmount, uint256 netAmount)
    {
        FeeSpecification memory feeSpec = getFeeSpecification(componentId);
        require(feeSpec.createdAt > 0, "ERROR:TRS-024:FEE_SPEC_UNDEFINED");
        feeAmount = _calculateFee(feeSpec, amount);
        netAmount = amount - feeAmount;
    }
    

    /*
     * Process the remaining premium by calculating the remaining amount, the fees for that amount and 
     * then transfering the fees to the instance wallet and the net premium remaining to the riskpool. 
     * This will revert if no fee structure is defined. 
     */
    /**
     * @dev Processes the premium for a given policy process ID.
     * @param processId The process ID of the policy to process the premium for.
     * @return success A boolean indicating whether the premium was successfully processed or not.
     * @return feeAmount The amount of fees charged for processing the premium.
     * @return netPremiumAmount The net amount of premium received after deducting fees.
     */
    function processPremium(bytes32 processId) 
        external override 
        whenNotSuspended
        onlyPolicyFlow("Treasury")
        returns(
            bool success, 
            uint256 feeAmount, 
            uint256 netPremiumAmount
        ) 
    {
        IPolicy.Policy memory policy =  _policy.getPolicy(processId);

        if (policy.premiumPaidAmount < policy.premiumExpectedAmount) {
            (success, feeAmount, netPremiumAmount) 
                = processPremium(processId, policy.premiumExpectedAmount - policy.premiumPaidAmount);
        }
    }

    /*
     * Process the premium by calculating the fees for the amount and 
     * then transfering the fees to the instance wallet and the net premium to the riskpool. 
     * This will revert if no fee structure is defined. 
     */
    /**
     * @dev Processes a premium payment for a policy.
     * @param processId The ID of the policy process.
     * @param amount The amount of premium to be processed.
     * @return success A boolean indicating whether the premium payment was successful or not.
     * @return feeAmount The amount of fees collected from the premium payment.
     * @return netAmount The net amount of premium transferred to the riskpool wallet.
     *
     * Requirements:
     * - The policy process must exist.
     * - The premium payment amount must not exceed the expected premium amount.
     * - The caller must have sufficient allowance to transfer the requested amount of tokens.
     * - The instance wallet and riskpool wallet must be defined for the policy process.
     * - The caller must be authorized to perform the action.
     *
     * Emits:
     * - LogTreasuryFeesTransferred: When the fees are successfully transferred to the instance wallet.
     * - LogTreasuryPremiumTransferred: When the net premium amount is successfully transferred to the riskpool wallet.
     * - LogTreasuryPremiumProcessed: When the premium payment is successfully processed.
     *
     * Throws:
     * - "ERROR:TRS-030:AMOUNT_TOO_BIG": If the premium payment amount exceeds the expected premium amount.
     * - "ERROR:TRS-031:FEE_TRANSFER_FAILED": If the transfer of fees to the instance wallet fails.
     * - "ERROR:TRS-032:PREMIUM_TRANSFER_FAILED": If the transfer of net premium to the riskpool wallet fails.
     * @notice This function emits 3 events: 
     * - LogTreasuryPremiumProcessed
     * - LogTreasuryPremiumTransferred
     * - LogTreasuryFeesTransferred
     */
    function processPremium(bytes32 processId, uint256 amount) 
        public override 
        whenNotSuspended
        instanceWalletDefined
        riskpoolWalletDefinedForProcess(processId)
        onlyPolicyFlow("Treasury")
        returns(
            bool success, 
            uint256 feeAmount, 
            uint256 netAmount
        ) 
    {
        IPolicy.Policy memory policy =  _policy.getPolicy(processId);
        require(
            policy.premiumPaidAmount + amount <= policy.premiumExpectedAmount, 
            "ERROR:TRS-030:AMOUNT_TOO_BIG"
        );

        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        (feeAmount, netAmount) 
            = calculateFee(metadata.productId, amount);

        // check if allowance covers requested amount
        IERC20 token = getComponentToken(metadata.productId);
        if (token.allowance(metadata.owner, address(this)) < amount) {
            success = false;
            return (success, feeAmount, netAmount);
        }

        // collect premium fees
        success = TransferHelper.unifiedTransferFrom(token, metadata.owner, _instanceWalletAddress, feeAmount);
        emit LogTreasuryFeesTransferred(metadata.owner, _instanceWalletAddress, feeAmount);
        require(success, "ERROR:TRS-031:FEE_TRANSFER_FAILED");

        // transfer premium net amount to riskpool for product
        // actual transfer of net premium to riskpool
        (uint256 riskpoolId, address riskpoolWalletAddress) = _getRiskpoolWallet(processId);
        success = TransferHelper.unifiedTransferFrom(token, metadata.owner, riskpoolWalletAddress, netAmount);

        emit LogTreasuryPremiumTransferred(metadata.owner, riskpoolWalletAddress, netAmount);
        require(success, "ERROR:TRS-032:PREMIUM_TRANSFER_FAILED");

        emit LogTreasuryPremiumProcessed(processId, amount);
    }


    /**
     * @dev Processes a payout for a specific process and payout ID.
     * @param processId The ID of the process for which the payout is being processed.
     * @param payoutId The ID of the payout being processed.
     * @return feeAmount The amount of fees deducted from the payout.
     * @return netPayoutAmount The net payout amount after fees have been deducted.
     * @notice This function emits 2 events: 
     * - LogTreasuryPayoutTransferred
     * - LogTreasuryPayoutProcessed
     */
    function processPayout(bytes32 processId, uint256 payoutId) 
        external override
        whenNotSuspended
        instanceWalletDefined
        riskpoolWalletDefinedForProcess(processId)
        onlyPolicyFlow("Treasury")
        returns(
            uint256 feeAmount,
            uint256 netPayoutAmount
        )
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        IERC20 token = getComponentToken(metadata.productId);
        (uint256 riskpoolId, address riskpoolWalletAddress) = _getRiskpoolWallet(processId);

        IPolicy.Payout memory payout =  _policy.getPayout(processId, payoutId);
        require(
            token.balanceOf(riskpoolWalletAddress) >= payout.amount, 
            "ERROR:TRS-042:RISKPOOL_WALLET_BALANCE_TOO_SMALL"
        );
        require(
            token.allowance(riskpoolWalletAddress, address(this)) >= payout.amount, 
            "ERROR:TRS-043:PAYOUT_ALLOWANCE_TOO_SMALL"
        );

        // actual payout to policy holder
        bool success = TransferHelper.unifiedTransferFrom(token, riskpoolWalletAddress, metadata.owner, payout.amount);
        feeAmount = 0;
        netPayoutAmount = payout.amount;

        emit LogTreasuryPayoutTransferred(riskpoolWalletAddress, metadata.owner, payout.amount);
        require(success, "ERROR:TRS-044:PAYOUT_TRANSFER_FAILED");

        emit LogTreasuryPayoutProcessed(riskpoolId,  metadata.owner, payout.amount);
    }

    /**
     * @dev Processes capital for a given bundle ID and calculates fees. Transfers fees to the instance wallet and net capital to the riskpool wallet.
     * @param bundleId The ID of the bundle for which to process capital.
     * @param capitalAmount The amount of capital to be processed.
     * @return feeAmount The amount of fees calculated and transferred to the instance wallet.
     * @return netCapitalAmount The amount of net capital transferred to the riskpool wallet.
     * @notice This function emits 3 events: 
     * - LogTreasuryFeesTransferred
     * - LogTreasuryCapitalProcessed
     * - LogTreasuryCapitalTransferred
     */
    function processCapital(uint256 bundleId, uint256 capitalAmount) 
        external override 
        whenNotSuspended
        instanceWalletDefined
        riskpoolWalletDefinedForBundle(bundleId)
        onlyRiskpoolService
        returns(
            uint256 feeAmount,
            uint256 netCapitalAmount
        )
    {
        // obtain relevant fee specification
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        address bundleOwner = _bundle.getOwner(bundleId);

        FeeSpecification memory feeSpec = getFeeSpecification(bundle.riskpoolId);
        require(feeSpec.createdAt > 0, "ERROR:TRS-050:FEE_SPEC_UNDEFINED");

        // obtain relevant token for product/riskpool pair
        IERC20 token = _componentToken[bundle.riskpoolId];

        // calculate fees and net capital
        feeAmount = _calculateFee(feeSpec, capitalAmount);
        netCapitalAmount = capitalAmount - feeAmount;

        // check balance and allowance before starting any transfers
        require(token.balanceOf(bundleOwner) >= capitalAmount, "ERROR:TRS-052:BALANCE_TOO_SMALL");
        require(token.allowance(bundleOwner, address(this)) >= capitalAmount, "ERROR:TRS-053:CAPITAL_TRANSFER_ALLOWANCE_TOO_SMALL");

        bool success = TransferHelper.unifiedTransferFrom(token, bundleOwner, _instanceWalletAddress, feeAmount);

        emit LogTreasuryFeesTransferred(bundleOwner, _instanceWalletAddress, feeAmount);
        require(success, "ERROR:TRS-054:FEE_TRANSFER_FAILED");

        // transfer net capital
        address riskpoolWallet = getRiskpoolWallet(bundle.riskpoolId);
        success = TransferHelper.unifiedTransferFrom(token, bundleOwner, riskpoolWallet, netCapitalAmount);

        emit LogTreasuryCapitalTransferred(bundleOwner, riskpoolWallet, netCapitalAmount);
        require(success, "ERROR:TRS-055:CAPITAL_TRANSFER_FAILED");

        emit LogTreasuryCapitalProcessed(bundle.riskpoolId, bundleId, capitalAmount);
    }

    /**
     * @dev Processes a withdrawal of a specified amount from a bundle, transferring the funds to the bundle owner's wallet.
     * @param bundleId The ID of the bundle from which the withdrawal is made.
     * @param amount The amount of tokens to withdraw.
     * @return feeAmount The amount of fees charged for the withdrawal.
     * @return netAmount The net amount of tokens transferred to the bundle owner's wallet.
     *
     * Requirements:
     * - The function can only be called when the contract is not suspended.
     * - The instance wallet must be defined.
     * - The riskpool wallet must be defined for the specified bundle.
     * - Only the riskpool service can call this function.
     * - The bundle must have sufficient capacity or balance to cover the withdrawal.
     * - The riskpool wallet must have sufficient balance of the token to cover the withdrawal.
     * - The contract must have sufficient allowance to withdraw the token from the riskpool wallet.
     * - The withdrawal transfer must be successful.
     *
     * Emits a {LogTreasuryWithdrawalTransferred} event indicating the transfer of the withdrawn tokens to the bundle owner's wallet.
     * Emits a {LogTreasuryWithdrawalProcessed} event indicating the successful processing of the withdrawal.
     * @notice This function emits 2 events: 
     * - LogTreasuryWithdrawalTransferred
     * - LogTreasuryWithdrawalProcessed
     */
    function processWithdrawal(uint256 bundleId, uint256 amount) 
        external override
        whenNotSuspended
        instanceWalletDefined
        riskpoolWalletDefinedForBundle(bundleId)
        onlyRiskpoolService
        returns(
            uint256 feeAmount,
            uint256 netAmount
        )
    {
        // obtain relevant bundle info
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            bundle.capital >= bundle.lockedCapital + amount
            || (bundle.lockedCapital == 0 && bundle.balance >= amount),
            "ERROR:TRS-060:CAPACITY_OR_BALANCE_SMALLER_THAN_WITHDRAWAL"
        );

        // obtain relevant token for product/riskpool pair
        address riskpoolWallet = getRiskpoolWallet(bundle.riskpoolId);
        address bundleOwner = _bundle.getOwner(bundleId);
        IERC20 token = _componentToken[bundle.riskpoolId];

        require(
            token.balanceOf(riskpoolWallet) >= amount, 
            "ERROR:TRS-061:RISKPOOL_WALLET_BALANCE_TOO_SMALL"
        );
        require(
            token.allowance(riskpoolWallet, address(this)) >= amount, 
            "ERROR:TRS-062:WITHDRAWAL_ALLOWANCE_TOO_SMALL"
        );

        // TODO consider to introduce withdrawal fees
        // ideally symmetrical reusing capital fee spec for riskpool
        feeAmount = 0;
        netAmount = amount;
        bool success = TransferHelper.unifiedTransferFrom(token, riskpoolWallet, bundleOwner, netAmount);

        emit LogTreasuryWithdrawalTransferred(riskpoolWallet, bundleOwner, netAmount);
        require(success, "ERROR:TRS-063:WITHDRAWAL_TRANSFER_FAILED");

        emit LogTreasuryWithdrawalProcessed(bundle.riskpoolId, bundleId, netAmount);
    }


    /**
     * @dev Returns the ERC20 token address associated with the given component ID.
     * @param componentId The ID of the component to retrieve the token address for.
     * @return token The ERC20 token address associated with the component ID.
     */
    function getComponentToken(uint256 componentId) 
        public override
        view
        returns(IERC20 token) 
    {
        require(_component.isProduct(componentId) || _component.isRiskpool(componentId), "ERROR:TRS-070:NOT_PRODUCT_OR_RISKPOOL");
        return _componentToken[componentId];
    }

    /**
     * @dev Returns the fee specification of a given component.
     * @param componentId The ID of the component.
     * @return fees The fee specification of the component.
     */
    function getFeeSpecification(uint256 componentId) public override view returns(FeeSpecification memory) {
        return _fees[componentId];
    }

    /**
     * @dev Returns the value of the constant FRACTION_FULL_UNIT.
     * @return The value of FRACTION_FULL_UNIT as an unsigned integer.
     */
    function getFractionFullUnit() public override pure returns(uint256) { 
        return FRACTION_FULL_UNIT; 
    }

    /**
     * @dev Returns the address of the instance wallet.
     * @return The address of the instance wallet.
     */
    function getInstanceWallet() public override view returns(address) { 
        return _instanceWalletAddress; 
    }

    /**
     * @dev Returns the wallet address of the specified risk pool.
     * @param riskpoolId The unique identifier of the risk pool.
     * @return The wallet address associated with the specified risk pool.
     */
    function getRiskpoolWallet(uint256 riskpoolId) public override view returns(address) {
        return _riskpoolWallet[riskpoolId];
    }


    /**
     * @dev Calculates the premium fee for a given fee specification and process ID.
     * @param feeSpec The fee specification to be used for the calculation.
     * @param processId The process ID of the application for which the fee is being calculated.
     * @return application The application object retrieved from the policy contract.
     * @return feeAmount The amount of the premium fee calculated based on the fee specification and premium amount of the application.
     */
    function _calculatePremiumFee(
        FeeSpecification memory feeSpec, 
        bytes32 processId
    )
        internal
        view
        returns (
            IPolicy.Application memory application, 
            uint256 feeAmount
        )
    {
        application =  _policy.getApplication(processId);
        feeAmount = _calculateFee(feeSpec, application.premiumAmount);
    } 


    /**
     * @dev Calculates the fee amount based on the given fee specification and the transaction amount.
     * @param feeSpec The fee specification in the form of a FeeSpecification struct.
     * @param amount The transaction amount to calculate the fee for.
     * @return feeAmount The calculated fee amount.
     */
    function _calculateFee(
        FeeSpecification memory feeSpec, 
        uint256 amount
    )
        internal
        pure
        returns (uint256 feeAmount)
    {
        if (feeSpec.feeCalculationData.length > 0) {
            revert("ERROR:TRS-090:FEE_CALCULATION_DATA_NOT_SUPPORTED");
        }

        // start with fixed fee
        feeAmount = feeSpec.fixedFee;

        // add fractional fee on top
        if (feeSpec.fractionalFee > 0) {
            feeAmount += (feeSpec.fractionalFee * amount) / FRACTION_FULL_UNIT;
        }

        // require that fee is smaller than amount
        require(feeAmount < amount, "ERROR:TRS-091:FEE_TOO_BIG");
    } 

    /**
     * @dev Returns the riskpool ID and wallet address for a given process ID.
     * @param processId The ID of the process.
     * @return riskpoolId The ID of the riskpool associated with the process.
     * @return riskpoolWalletAddress The wallet address of the riskpool associated with the process.
     */
    function _getRiskpoolWallet(bytes32 processId)
        internal
        view
        returns(uint256 riskpoolId, address riskpoolWalletAddress)
    {
        IPolicy.Metadata memory metadata = _policy.getMetadata(processId);
        riskpoolId = _pool.getRiskPoolForProduct(metadata.productId);
        require(riskpoolId > 0, "ERROR:TRS-092:PRODUCT_WITHOUT_RISKPOOL");
        riskpoolWalletAddress = _riskpoolWallet[riskpoolId];
    }
}
