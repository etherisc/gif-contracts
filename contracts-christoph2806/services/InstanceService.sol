// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../modules/ComponentController.sol";
import "../modules/BundleController.sol";
import "../modules/PolicyController.sol";
import "../modules/PoolController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/CoreController.sol";
import "../services/InstanceOperatorService.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IOracle.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/components/IRiskpool.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";
import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";
import "@etherisc/gif-interface/contracts/services/IComponentOwnerService.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceService.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceOperatorService.sol";
import "@etherisc/gif-interface/contracts/services/IOracleService.sol";
import "@etherisc/gif-interface/contracts/services/IProductService.sol";
import "@etherisc/gif-interface/contracts/services/IRiskpoolService.sol";
import "@etherisc/gif-interface/contracts/tokens/IBundleToken.sol";

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";

contract InstanceService is 
    IInstanceService, 
    CoreController
{
    bytes32 public constant BUNDLE_NAME = "Bundle";
    bytes32 public constant COMPONENT_NAME = "Component";
    bytes32 public constant POLICY_NAME = "Policy";
    bytes32 public constant POOL_NAME = "Pool";
    bytes32 public constant TREASURY_NAME = "Treasury";

    bytes32 public constant COMPONENT_OWNER_SERVICE_NAME = "ComponentOwnerService";
    bytes32 public constant INSTANCE_OPERATOR_SERVICE_NAME = "InstanceOperatorService";
    bytes32 public constant ORACLE_SERVICE_NAME = "OracleService";
    bytes32 public constant PRODUCT_SERVICE_NAME = "ProductService";
    bytes32 public constant RISKPOOL_SERVICE_NAME = "RiskpoolService";

    BundleController _bundle;
    ComponentController _component;
    PolicyController _policy;
    PoolController _pool;
    TreasuryModule private _treasury;

    mapping(uint256 /* chain id */ => string /* chain name */) private _chainName;

    /**
     * @dev Internal function that is called after initialization is complete. It sets the bundle, component, policy, pool, and treasury controllers by retrieving their contract addresses. It also sets the chain names.
     *
     */
    function _afterInitialize() internal override onlyInitializing {
        _bundle = BundleController(_getContractAddress(BUNDLE_NAME));
        _component = ComponentController(_getContractAddress(COMPONENT_NAME));
        _policy = PolicyController(_getContractAddress(POLICY_NAME));
        _pool = PoolController(_getContractAddress(POOL_NAME));
        _treasury = TreasuryModule(_getContractAddress(TREASURY_NAME));

        _setChainNames();
    }

    /**
     * @dev Sets the names for several blockchain networks by assigning them to their respective chain IDs.
     *
     * Sets the names for the Ethereum Mainnet/ETH, Goerli/ETH, Ganache, Gnosis/xDai, Sokol/SPOA, Polygon Mainnet/MATIC, Mumbai/MATIC, Avalanche C-Chain/AVAX and Avalanche Fuji Testnet/AVAX blockchain networks by assigning them to their respective chain IDs.
     */
    function _setChainNames() internal {
        _chainName[1] = "Ethereum Mainnet/ETH"; 
        _chainName[5] = "Goerli/ETH"; 
        _chainName[1337] = "Ganache"; 
        _chainName[100] = "Gnosis/xDai"; 
        _chainName[77] = "Sokol/SPOA"; 
        _chainName[137] = "Polygon Mainnet/MATIC"; 
        _chainName[8001] = "Mumbai/MATIC"; 
        _chainName[43114] = "Avalanche C-Chain/AVAX"; 
        _chainName[43113] = "Avalanche Fuji Testnet/AVAX"; 
    }

    /* instance service */
    /**
     * @dev Returns the chain ID of the current blockchain.
     * @return chainId The ID of the current blockchain.
     */
    function getChainId() public override view returns(uint256 chainId) {
        chainId = block.chainid;
    }

    /**
     * @dev Returns the name of the chain based on its ID.
     *
     * @return chainName The name of the chain as a string.
     */
    function getChainName() public override view returns(string memory chainName) {
        chainName = _chainName[block.chainid];
    }

    /**
     * @dev Returns the instance ID of the contract, which is a hash of the chain ID and the registry address.
     *
     * @return instanceId The instance ID of the contract.
     */
    function getInstanceId() public override view returns(bytes32 instanceId) {
        instanceId = keccak256(
            abi.encodePacked(
                block.chainid, 
                address(_registry)));
    }

    /**
     * @dev Returns the address of the current instance operator.
     * @return The address of the instance operator.
     */
    function getInstanceOperator() external override view returns(address) {
        InstanceOperatorService ios = InstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
        return ios.owner();
    }
    
    /* registry */
    /**
     * @dev Returns the address of the Component Owner Service contract.
     * @return service The Component Owner Service contract address.
     */
    function getComponentOwnerService() external override view returns(IComponentOwnerService service) {
        return IComponentOwnerService(_getContractAddress(COMPONENT_OWNER_SERVICE_NAME));
    }

    /**
     * @dev Returns the instance operator service contract address.
     * @return service The instance operator service contract address.
     */
    function getInstanceOperatorService() external override view returns(IInstanceOperatorService service) {
        return IInstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
    }

    /**
     * @dev Returns the Oracle Service contract instance.
     * @return service The instance of the Oracle Service contract.
     */
    function getOracleService() external override view returns(IOracleService service) {
        return IOracleService(_getContractAddress(ORACLE_SERVICE_NAME));
    }

    /**
     * @dev Returns the address of the Product Service contract.
     * @return service The Product Service contract address.
     */
    function getProductService() external override view returns(IProductService service) {
        return IProductService(_getContractAddress(PRODUCT_SERVICE_NAME));
    }

    /**
     * @dev Returns the IRiskpoolService contract instance.
     * @return service The IRiskpoolService contract instance.
     */
    function getRiskpoolService() external override view returns(IRiskpoolService service) {
        return IRiskpoolService(_getContractAddress(RISKPOOL_SERVICE_NAME));
    }

    /* registry */
    /**
     * @dev Returns the current instance of the IRegistry contract.
     * @return service The IRegistry contract instance.
     */
    function getRegistry() external view returns(IRegistry service) {
        return _registry;
    }

    /**
     * @dev Returns the number of contracts registered in the registry.
     * @return numberOfContracts The total number of contracts registered in the registry.
     */
    function contracts() external view override returns (uint256 numberOfContracts) {
        numberOfContracts = _registry.contracts();
    }
        
    /**
     * @dev Returns the name of the contract at the specified index in the registry.
     * @param idx The index of the contract.
     * @return name The name of the contract as a bytes32 value.
     */
    function contractName(uint256 idx) external view override returns (bytes32 name) {
        name = _registry.contractName(idx);
    }

    /* access */
    /**
     * @dev Returns the default admin role for the AccessControl contract.
     *
     * @return The default admin role as a bytes32 value.
     */
    function getDefaultAdminRole() external override view returns(bytes32) {
        return _access.getDefaultAdminRole();
    }

    /**
     * @dev Returns the role identifier of the product owner role.
     * @return The role identifier of the product owner role.
     */
    function getProductOwnerRole() external override view returns(bytes32) {
        return _access.getProductOwnerRole();
    }

    /**
     * @dev Returns the role identifier for the oracle provider role.
     * @return The role identifier for the oracle provider role.
     */
    function getOracleProviderRole() external override view returns(bytes32) {
        return _access.getOracleProviderRole();
    }

    /**
     * @dev Returns the role identifier for the Riskpool Keeper role.
     * @return The role identifier for the Riskpool Keeper role as a bytes32 value.
     */
    function getRiskpoolKeeperRole() external override view returns(bytes32) {
        return _access.getRiskpoolKeeperRole();
    }

    /**
     * @dev Checks if an address has a specific role.
     * @param role The bytes32 identifier of the role being checked.
     * @param principal The address of the account being checked for the role.
     * @return A boolean indicating whether the address has the specified role or not.
     */
    function hasRole(bytes32 role, address principal)
        external override view 
        returns(bool)
    {
        return _access.hasRole(role, principal);
    }

    /* component */
    /**
     * @dev Returns the number of products in the component contract.
     * @return products The number of products in the component contract.
     */
    function products() external override view returns(uint256) {
        return _component.products();
    }

    /**
     * @dev Returns the number of oracles registered in the component.
     * @return The number of oracles registered in the component.
     */
    function oracles() external override view returns(uint256) {
        return _component.oracles();
    }

    /**
     * @dev Returns the number of risk pools in the component.
     * @return The number of risk pools as an unsigned integer.
     */
    function riskpools() external override view returns(uint256) {
        return _component.riskpools();
    }

    /**
     * @dev Returns the component ID of a given component address.
     * @param componentAddress The address of the component.
     * @return componentId The ID of the component.
     */
    function getComponentId(address componentAddress) external override view returns(uint256 componentId) {
        return _component.getComponentId(componentAddress);
    }

    /**
     * @dev Returns the type of a component given its ID.
     * @param componentId The ID of the component.
     * @return componentType The type of the component.
     */
    function getComponentType(uint256 componentId)
        external override 
        view 
        returns(IComponent.ComponentType componentType)
    {
        return _component.getComponentType(componentId);
    }

    /**
     * @dev Returns the current state of a specific component.
     * @param componentId The ID of the component to retrieve the state for.
     * @return componentState The current state of the specified component.
     */
    function getComponentState(uint256 componentId) 
        external override
        view 
        returns(IComponent.ComponentState componentState)
    {
        componentState = _component.getComponentState(componentId);
    }

    /**
     * @dev Returns the component with the specified ID.
     * @param id The ID of the component to retrieve.
     * @return The component with the specified ID.
     */
    function getComponent(uint256 id) external override view returns(IComponent) {
        return _component.getComponent(id);
    }

    /**
     * @dev Returns the oracle ID at the specified index.
     * @param idx The index of the oracle ID to retrieve.
     * @return oracleId The ID of the oracle at the specified index.
     */
    function getOracleId(uint256 idx) public view returns (uint256 oracleId) {
        return _component.getOracleId(idx);
    }

    /**
     * @dev Returns the riskpool ID for the given index.
     * @param idx The index of the riskpool ID to retrieve.
     * @return riskpoolId The ID of the riskpool.
     */
    function getRiskpoolId(uint256 idx) public view returns (uint256 riskpoolId) {
        return _component.getRiskpoolId(idx);
    }

    /**
     * @dev Returns the product ID of the component at the given index.
     * @param idx The index of the component.
     * @return productId The product ID of the component.
     */
    function getProductId(uint256 idx) public view returns (uint256 productId) {
        return _component.getProductId(idx);
    }

    /* service staking */
    /**
     * @dev Returns the staking requirements for a specific ID.
     * @param id The ID of the staking requirements to retrieve.
     * @return data The staking requirements data as a bytes array.
     */
    function getStakingRequirements(uint256 id) 
        external override 
        pure 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-001:IMPLEMENATION_MISSING");
    }

    /**
     * @dev Returns the staked assets for a given ID.
     * @param id The ID of the staked assets.
     * @return data The staked assets data in bytes format.
     */
    function getStakedAssets(uint256 id)
        external override 
        pure 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-002:IMPLEMENATION_MISSING");
    }

    /* policy */
    /**
     * @dev Returns the number of process IDs in the policy contract.
     * @return numberOfProcessIds The number of process IDs.
     */
    function processIds() external override view returns(uint256 numberOfProcessIds) {
        numberOfProcessIds = _policy.processIds();
    }

    /**
     * @dev Returns the metadata associated with a given business process key.
     * @param bpKey The business process key for which to retrieve the metadata.
     * @return metadata The metadata associated with the given business process key.
     */
    function getMetadata(bytes32 bpKey) external override view returns(IPolicy.Metadata memory metadata) {
        metadata = _policy.getMetadata(bpKey);
    }

    /**
     * @dev Returns the application data associated with the given process ID.
     * @param processId The ID of the process to retrieve the application data for.
     * @return application The application data associated with the given process ID.
     */
    function getApplication(bytes32 processId) external override view returns(IPolicy.Application memory application) {
        application = _policy.getApplication(processId);
    }

    /**
     * @dev Returns the policy associated with the given process ID.
     * @param processId The ID of the process.
     * @return policy The policy associated with the given process ID.
     */
    function getPolicy(bytes32 processId) external override view returns(IPolicy.Policy memory policy) {
        policy = _policy.getPolicy(processId);
    }
    
    /**
     * @dev Returns the number of claims associated with a given process ID.
     * @param processId The ID of the process to retrieve the number of claims for.
     * @return numberOfClaims The number of claims associated with the given process ID.
     */
    function claims(bytes32 processId) external override view returns(uint256 numberOfClaims) {
        numberOfClaims = _policy.getNumberOfClaims(processId);
    }
    
    /**
     * @dev Returns the number of payouts for a given processId.
     * @param processId The unique identifier of the process.
     * @return numberOfPayouts The total number of payouts for the given processId.
     */
    function payouts(bytes32 processId) external override view returns(uint256 numberOfPayouts) {
        numberOfPayouts = _policy.getNumberOfPayouts(processId);
    }
    
    /**
     * @dev Returns the claim with the given claimId for the specified processId.
     * @param processId The unique identifier of the process.
     * @param claimId The unique identifier of the claim.
     * @return claim The claim data, including the claimId, processId, claimant, amount, and status.
     */
    function getClaim(bytes32 processId, uint256 claimId) external override view returns (IPolicy.Claim memory claim) {
        claim = _policy.getClaim(processId, claimId);
    }
    
    /**
     * @dev Returns the information of a specific payout.
     * @param processId The ID of the process.
     * @param payoutId The ID of the payout.
     * @return payout The payout information, including the ID, amount, and recipient.
     */
    function getPayout(bytes32 processId, uint256 payoutId) external override view returns (IPolicy.Payout memory payout) {
        payout = _policy.getPayout(processId, payoutId);
    }

    /* riskpool */
    /**
     * @dev Returns the risk pool with the given ID.
     * @param riskpoolId The ID of the risk pool to retrieve.
     * @return riskPool The risk pool with the given ID.
     */
    function getRiskpool(uint256 riskpoolId) external override view returns(IPool.Pool memory riskPool) {
        return _pool.getRiskpool(riskpoolId);
    }

    /**
     * @dev Returns the full collateralization level of the pool.
     * @return The full collateralization level as a uint256 value.
     */
    function getFullCollateralizationLevel() external override view returns (uint256) {
        return _pool.getFullCollateralizationLevel();
    }

    /**
     * @dev Returns the capital amount of a given risk pool.
     * @param riskpoolId The ID of the risk pool to retrieve the capital amount from.
     * @return capitalAmount The amount of capital in the risk pool.
     */
    function getCapital(uint256 riskpoolId) external override view returns(uint256 capitalAmount) {
        return _pool.getRiskpool(riskpoolId).capital;
    }

    /**
     * @dev Returns the total value locked in a specific risk pool.
     * @param riskpoolId The ID of the risk pool to query.
     * @return totalValueLockedAmount The amount of tokens locked in the specified risk pool.
     */
    function getTotalValueLocked(uint256 riskpoolId) external override view returns(uint256 totalValueLockedAmount) {
        return _pool.getRiskpool(riskpoolId).lockedCapital;
    }

    /**
     * @dev Returns the available capacity of a risk pool.
     * @param riskpoolId The ID of the risk pool to get the capacity for.
     * @return capacityAmount The available capacity of the risk pool.
     */
    function getCapacity(uint256 riskpoolId) external override view returns(uint256 capacityAmount) {
        IPool.Pool memory pool = _pool.getRiskpool(riskpoolId);
        return pool.capital - pool.lockedCapital;
    }

    /**
     * @dev Returns the balance amount of a specific risk pool.
     * @param riskpoolId The ID of the risk pool to get the balance amount from.
     * @return balanceAmount The balance amount of the specified risk pool.
     */
    function getBalance(uint256 riskpoolId) external override view returns(uint256 balanceAmount) {
        return _pool.getRiskpool(riskpoolId).balance;
    }

    /**
     * @dev Returns the number of active bundles for a given risk pool.
     * @param riskpoolId The ID of the risk pool.
     * @return numberOfActiveBundles The number of active bundles for the specified risk pool.
     */
    function activeBundles(uint256 riskpoolId) external override view returns(uint256 numberOfActiveBundles) {
        return _pool.activeBundles(riskpoolId);
    }

    /**
     * @dev Returns the active bundle ID for a given risk pool and bundle index.
     * @param riskpoolId The ID of the risk pool.
     * @param bundleIdx The index of the bundle within the risk pool.
     * @return bundleId The ID of the active bundle.
     */
    function getActiveBundleId(uint256 riskpoolId, uint256 bundleIdx) external override view returns(uint256 bundleId) {
        return _pool.getActiveBundleId(riskpoolId, bundleIdx);
    }
    /**
     * @dev Returns the maximum number of active bundles for a given risk pool ID.
     * @param riskpoolId The ID of the risk pool to query.
     * @return maximumNumberOfActiveBundles The maximum number of active bundles for the given risk pool ID.
     */
    function getMaximumNumberOfActiveBundles(uint256 riskpoolId) external override view returns(uint256 maximumNumberOfActiveBundles) {
        return _pool.getMaximumNumberOfActiveBundles(riskpoolId);
    }

    /* bundle */
    /**
     * @dev Returns the bundle token contract address.
     * @return token The bundle token contract address.
     */
    function getBundleToken() external override view returns(IBundleToken token) {
        BundleToken bundleToken = _bundle.getToken();
        token = IBundleToken(bundleToken);
    }
    
    /**
     * @dev Returns the bundle with the given ID.
     * @param bundleId The ID of the bundle to retrieve.
     * @return bundle The bundle with the given ID.
     */
    function getBundle(uint256 bundleId) external override view returns (IBundle.Bundle memory bundle) {
        bundle = _bundle.getBundle(bundleId);
    }

    /**
     * @dev Returns the number of bundles in the `_bundle` contract.
     * @return The number of bundles as a uint256 value.
     */
    function bundles() external override view returns (uint256) {
        return _bundle.bundles();
    }

    /**
     * @dev Returns the number of unburnt bundles for a given risk pool ID.
     * @param riskpoolId The ID of the risk pool to check.
     * @return numberOfUnburntBundles The number of unburnt bundles for the given risk pool ID.
     */
    function unburntBundles(uint256 riskpoolId) external override view returns(uint256 numberOfUnburntBundles) {
        numberOfUnburntBundles = _bundle.unburntBundles(riskpoolId);
    }

    /* treasury */
    /**
     * @dev Returns the address of the treasury contract.
     *
     * @return The address of the treasury contract.
     */
    function getTreasuryAddress() external override view returns(address) { 
        return address(_treasury);
    }

    /**
     * @dev Returns the address of the instance wallet associated with the treasury.
     *
     * @return The address of the instance wallet.
     */
    function getInstanceWallet() external override view returns(address) { 
        return _treasury.getInstanceWallet();
    }

    /**
     * @dev Returns the wallet address of the specified riskpool.
     * @param riskpoolId The ID of the riskpool to retrieve the wallet address for.
     * @return The address of the wallet associated with the specified riskpool.
     */
    function getRiskpoolWallet(uint256 riskpoolId) external override view returns(address) { 
        return _treasury.getRiskpoolWallet(riskpoolId);
    }

    /**
     * @dev Returns the IERC20 token associated with the given component ID.
     * @param componentId The ID of the component for which to get the associated token.
     * @return The IERC20 token associated with the given component ID.
     */
    function getComponentToken(uint256 componentId) external override view returns(IERC20) { 
        return _treasury.getComponentToken(componentId);
    }

    /**
     * @dev Returns the fraction of the treasury fee expressed in full units.
     *
     * @return The fraction of the treasury fee expressed in full units.
     */
    function getFeeFractionFullUnit() external override view returns(uint256) {
        return _treasury.getFractionFullUnit();
    }
}
