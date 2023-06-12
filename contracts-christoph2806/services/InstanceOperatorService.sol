// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../modules/AccessController.sol";
import "../modules/BundleController.sol";
import "../modules/ComponentController.sol";
import "../modules/PoolController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/CoreController.sol";
import "../test/TestProduct.sol";
import "../tokens/BundleToken.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/modules/IQuery.sol";
import "@etherisc/gif-interface/contracts/modules/ITreasury.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceOperatorService.sol";

import "@openzeppelin/contracts/access/Ownable.sol";

contract InstanceOperatorService is 
    IInstanceOperatorService, 
    CoreController, 
    Ownable 
{
    ComponentController private _component;
    PoolController private _pool;
    TreasuryModule private _treasury;

    modifier onlyInstanceOperatorAddress() {
        require(owner() == _msgSender(), "ERROR:IOS-001:NOT_INSTANCE_OPERATOR");
        _;
    }

    /**
     * @dev Performs the necessary setup after contract initialization.
     *      - Sets the component, pool, and treasury contracts.
     *      - Transfers ownership to the message sender.
     *      - Links the bundle module to the bundle token.
     *      - Sets the default admin role.
     */
    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
        _pool = PoolController(_getContractAddress("Pool"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));

        _transferOwnership(_msgSender());
        _linkBundleModuleToBundleToken();
        _setDefaultAdminRole();
    }

    /**
     * @dev Sets the default admin role for the contract calling this function.
     *
     *
     */
    function _setDefaultAdminRole() private {
        AccessController access = AccessController(_getContractAddress("Access"));
        access.setDefaultAdminRole(address(this));
    }

    /**
     * @dev Links the Bundle module to the BundleToken contract.
     */
    function _linkBundleModuleToBundleToken() private {
        BundleToken token = BundleToken(_getContractAddress("BundleToken"));
        address bundleAddress = _getContractAddress("Bundle");
        token.setBundleModule(bundleAddress);
    }

    /* registry */
    /**
     * @dev Prepares a new release by calling the prepareRelease function from the Registry contract.
     * @param _newRelease The hash of the new release.
     *
     * Requirements:
     * - Caller must be the instance operator address.
     */
    function prepareRelease(bytes32 _newRelease) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _registry.prepareRelease(_newRelease);
    }

    /**
     * @dev Registers a contract in the registry.
     * @param _contractName The name of the contract to be registered.
     * @param _contractAddress The address of the contract to be registered.
     */
    function register(bytes32 _contractName, address _contractAddress)
        external override
        onlyInstanceOperatorAddress
    {
        _registry.register(_contractName, _contractAddress);
    }

    /**
     * @dev Deregisters a contract from the registry.
     * @param _contractName The name of the contract to be deregistered.
     */
    function deregister(bytes32 _contractName) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _registry.deregister(_contractName);
    }

    /**
     * @dev Registers a contract in a specific release.
     * @param _release The release identifier where the contract will be registered.
     * @param _contractName The name of the contract to be registered.
     * @param _contractAddress The address of the contract to be registered.
     */
    function registerInRelease(
        bytes32 _release,
        bytes32 _contractName,
        address _contractAddress
    ) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _registry.registerInRelease(_release, _contractName, _contractAddress);
    }

    /**
     * @dev Deregisters a contract from a specific release in the registry.
     * @param _release The identifier of the release to deregister the contract from.
     * @param _contractName The name of the contract to be deregistered.
     */
    function deregisterInRelease(bytes32 _release, bytes32 _contractName)
        external override
        onlyInstanceOperatorAddress
    {
        _registry.deregisterInRelease(_release, _contractName);
    }
    
    /* access */
    /**
     * @dev Adds a new role to the access control contract.
     * @param _role The name of the new role to be added.
     */
    function createRole(bytes32 _role) 
        external override
        onlyInstanceOperatorAddress 
    {
        _access.addRole(_role);
    }

    /**
     * @dev Invalidates a role.
     * @param _role The role to invalidate.
     */
    function invalidateRole(bytes32 _role) 
        external override
        onlyInstanceOperatorAddress 
    {
        _access.invalidateRole(_role);
    }

    /**
     * @dev Grants a role to a principal.
     * @param role The role to be granted.
     * @param principal The address of the principal to whom the role is granted.
     */
    function grantRole(bytes32 role, address principal)
        external override
        onlyInstanceOperatorAddress
    {
        _access.grantRole(role, principal);
    }

    /**
     * @dev Revokes a role from a principal.
     * @param role The role to revoke.
     * @param principal The address of the principal to revoke the role from.
     */
    function revokeRole(bytes32 role, address principal) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _access.revokeRole(role, principal);
    }

    /* component */
    /**
     * @dev Approves a component with the given ID and sets its corresponding riskpool ID in the pool contract.
     * @param id The ID of the component to be approved.
     */
    function approve(uint256 id)
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.approve(id);

        if (_component.isProduct(id)) {
            IComponent component = _component.getComponent(id);
            IProduct product = IProduct(address(component));

            _pool.setRiskpoolForProduct(
                id,
                product.getRiskpoolId());
        }
    }

    /**
     * @dev Declines a component with the specified ID.
     * @param id The ID of the component to decline.
     */
    function decline(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.decline(id);
    }

    /**
     * @dev Suspends the component with the given ID.
     * @param id The ID of the component to be suspended.
     */
    function suspend(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.suspend(id);
    }

    /**
     * @dev Resumes the execution of a paused component instance.
     * @param id The ID of the component instance to be resumed.
     */
    function resume(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.resume(id);
    }

    /**
     * @dev Archives a component with the given ID from the instance operator's address.
     * @param id The ID of the component to be archived.
     */
    function archive(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.archiveFromInstanceOperator(id);
    }

    // service staking
    // TODO implement setDefaultStaking staking
    /**
     * @dev Sets the default staking for a specific component type.
     * @param componentType The type of component to set the default staking for.
     * @param data The data containing the default staking information.
     */
    function setDefaultStaking(
        uint16 componentType, 
        bytes calldata data
    )
        external override
        onlyInstanceOperatorAddress
    {
        revert("ERROR:IOS-010:IMPLEMENATION_MISSING");
    }

    // TODO implement adjustStakingRequirements staking
    /**
     * @dev Adjusts the staking requirements for a specific instance operator by providing the operator ID and the new staking requirements.
     * @param id The ID of the instance operator whose staking requirements are being adjusted.
     * @param data The new staking requirements encoded as bytes.
     */
    function adjustStakingRequirements(
        uint256 id, 
        bytes calldata data
    )
        external override
        onlyInstanceOperatorAddress
    {
        revert("ERROR:IOS-011:IMPLEMENATION_MISSING");
    }

    /* treasury */
    /**
     * @dev Suspends the treasury functionality.
     *
     *
     */
    function suspendTreasury() 
        external override
        onlyInstanceOperatorAddress
    { 
        _treasury.suspend();
    }

    /**
     * @dev Resumes the treasury contract.
     *
     *
     */
    function resumeTreasury() 
        external override
        onlyInstanceOperatorAddress
    { 
        _treasury.resume();
    }

    /**
     * @dev Sets the wallet address of the instance operator.
     * @param walletAddress The address of the wallet to be set.
     */
    function setInstanceWallet(address walletAddress) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setInstanceWallet(walletAddress);
    }

    /**
     * @dev Sets the wallet address for a specific risk pool.
     * @param riskpoolId The ID of the risk pool to set the wallet address for.
     * @param riskpoolWalletAddress The address of the wallet to set for the specified risk pool.
     */
    function setRiskpoolWallet(uint256 riskpoolId, address riskpoolWalletAddress) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setRiskpoolWallet(riskpoolId, riskpoolWalletAddress);
    }

    /**
     * @dev Sets the ERC20 token address for a given product ID.
     * @param productId The ID of the product to set the token address for.
     * @param erc20Address The address of the ERC20 token to set.
     */
    function setProductToken(uint256 productId, address erc20Address) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setProductToken(productId, erc20Address);
    }

    /**
     * @dev Returns a FeeSpecification object created with the given parameters.
     * @param componentId The ID of the component for which the fee is being created.
     * @param fixedFee The fixed fee amount to be charged for the component.
     * @param fractionalFee The fractional fee to be charged for the component.
     * @param feeCalculationData The data required for calculating the fee.
     * @return Returns a FeeSpecification object with the given parameters.
     */
    function createFeeSpecification(
        uint256 componentId,
        uint256 fixedFee,
        uint256 fractionalFee,
        bytes calldata feeCalculationData
    )
        external override
        view 
        returns(ITreasury.FeeSpecification memory)
    {
        return _treasury.createFeeSpecification(
            componentId,
            fixedFee,
            fractionalFee,
            feeCalculationData
        );
    }
    
    /**
     * @dev Sets the premium fees for the treasury.
     * @param feeSpec The fee specification struct containing the following parameters:
     *     - feeType: The type of fee (e.g. premium fee).
     *     - numerator: The numerator of the fee percentage.
     *     - denominator: The denominator of the fee percentage.
     */
    function setPremiumFees(ITreasury.FeeSpecification calldata feeSpec) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setPremiumFees(feeSpec);
    }

    /**
     * @dev Sets the fee specification for capital fees in the treasury contract.
     * @param feeSpec The fee specification struct containing the details of the capital fees.
     */
    function setCapitalFees(ITreasury.FeeSpecification calldata feeSpec) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setCapitalFees(feeSpec);
    }
}
