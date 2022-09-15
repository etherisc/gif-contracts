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

    function _afterInitialize() internal override onlyInitializing {
        _bundle = BundleController(_getContractAddress(BUNDLE_NAME));
        _component = ComponentController(_getContractAddress(COMPONENT_NAME));
        _policy = PolicyController(_getContractAddress(POLICY_NAME));
        _pool = PoolController(_getContractAddress(POOL_NAME));
        _treasury = TreasuryModule(_getContractAddress(TREASURY_NAME));

        _setChainNames();
    }

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
    function getChainId() public override view returns(uint256 chainId) {
        chainId = block.chainid;
    }

    function getChainName() public override view returns(string memory chainName) {
        chainName = _chainName[block.chainid];
    }

    function getInstanceId() public override view returns(bytes32 instanceId) {
        instanceId = keccak256(
            abi.encodePacked(
                block.chainid, 
                address(_registry)));
    }

    function getInstanceOperator() external override view returns(address) {
        InstanceOperatorService ios = InstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
        return ios.owner();
    }
    
    /* registry */
    function getComponentOwnerService() external override view returns(IComponentOwnerService service) {
        return IComponentOwnerService(_getContractAddress(COMPONENT_OWNER_SERVICE_NAME));
    }

    function getInstanceOperatorService() external override view returns(IInstanceOperatorService service) {
        return IInstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
    }

    function getOracleService() external override view returns(IOracleService service) {
        return IOracleService(_getContractAddress(ORACLE_SERVICE_NAME));
    }

    function getProductService() external override view returns(IProductService service) {
        return IProductService(_getContractAddress(PRODUCT_SERVICE_NAME));
    }

    function getRiskpoolService() external override view returns(IRiskpoolService service) {
        return IRiskpoolService(_getContractAddress(RISKPOOL_SERVICE_NAME));
    }

    /* registry */
    function getRegistry() external view returns(IRegistry service) {
        return _registry;
    }

    function contracts() external view override returns (uint256 numberOfContracts) {
        numberOfContracts = _registry.contracts();
    }
        
    function contractName(uint256 idx) external view override returns (bytes32 name) {
        name = _registry.contractName(idx);
    }

    /* access */
    function getDefaultAdminRole() external override view returns(bytes32) {
        return _access.getDefaultAdminRole();
    }

    function getProductOwnerRole() external override view returns(bytes32) {
        return _access.getProductOwnerRole();
    }

    function getOracleProviderRole() external override view returns(bytes32) {
        return _access.getOracleProviderRole();
    }

    function getRiskpoolKeeperRole() external override view returns(bytes32) {
        return _access.getRiskpoolKeeperRole();
    }

    function hasRole(bytes32 role, address principal)
        external override view 
        returns(bool)
    {
        return _access.hasRole(role, principal);
    }

    /* component */
    function products() external override view returns(uint256) {
        return _component.products();
    }

    function oracles() external override view returns(uint256) {
        return _component.oracles();
    }

    function riskpools() external override view returns(uint256) {
        return _component.riskpools();
    }

    function getComponentId(address componentAddress) external override view returns(uint256 componentId) {
        return _component.getComponentId(componentAddress);
    }

    function getComponentType(uint256 componentId)
        external override 
        view 
        returns(IComponent.ComponentType componentType)
    {
        return _component.getComponentType(componentId);
    }

    function getComponentState(uint256 componentId) 
        external override
        view 
        returns(IComponent.ComponentState componentState)
    {
        componentState = _component.getComponentState(componentId);
    }

    function getComponent(uint256 id) external override view returns(IComponent) {
        return _component.getComponent(id);
    }

    function getOracleId(uint256 idx) public view returns (uint256 oracleId) {
        return _component.getOracleId(idx);
    }

    function getRiskpoolId(uint256 idx) public view returns (uint256 riskpoolId) {
        return _component.getRiskpoolId(idx);
    }

    function getProductId(uint256 idx) public view returns (uint256 productId) {
        return _component.getProductId(idx);
    }

    /* service staking */
    function getStakingRequirements(uint256 id) 
        external override 
        pure 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-001:IMPLEMENATION_MISSING");
    }

    function getStakedAssets(uint256 id)
        external override 
        pure 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-002:IMPLEMENATION_MISSING");
    }

    /* policy */
    function processIds() external override view returns(uint256 numberOfProcessIds) {
        numberOfProcessIds = _policy.processIds();
    }

    function getMetadata(bytes32 bpKey) external override view returns(IPolicy.Metadata memory metadata) {
        metadata = _policy.getMetadata(bpKey);
    }

    function getApplication(bytes32 processId) external override view returns(IPolicy.Application memory application) {
        application = _policy.getApplication(processId);
    }

    function getPolicy(bytes32 processId) external override view returns(IPolicy.Policy memory policy) {
        policy = _policy.getPolicy(processId);
    }
    
    function claims(bytes32 processId) external override view returns(uint256 numberOfClaims) {
        numberOfClaims = _policy.getNumberOfClaims(processId);
    }
    
    function payouts(bytes32 processId) external override view returns(uint256 numberOfPayouts) {
        numberOfPayouts = _policy.getNumberOfPayouts(processId);
    }
    
    function getClaim(bytes32 processId, uint256 claimId) external override view returns (IPolicy.Claim memory claim) {
        claim = _policy.getClaim(processId, claimId);
    }
    
    function getPayout(bytes32 processId, uint256 payoutId) external override view returns (IPolicy.Payout memory payout) {
        payout = _policy.getPayout(processId, payoutId);
    }

    /* riskpool */
    function getRiskpool(uint256 riskpoolId) external override view returns(IPool.Pool memory riskPool) {
        return _pool.getRiskpool(riskpoolId);
    }

    function getFullCollateralizationLevel() external override view returns (uint256) {
        return _pool.getFullCollateralizationLevel();
    }

    function getCapital(uint256 riskpoolId) external override view returns(uint256 capitalAmount) {
        return _pool.getRiskpool(riskpoolId).capital;
    }

    function getTotalValueLocked(uint256 riskpoolId) external override view returns(uint256 totalValueLockedAmount) {
        return _pool.getRiskpool(riskpoolId).lockedCapital;
    }

    function getCapacity(uint256 riskpoolId) external override view returns(uint256 capacityAmount) {
        IPool.Pool memory pool = _pool.getRiskpool(riskpoolId);
        return pool.capital - pool.lockedCapital;
    }

    function getBalance(uint256 riskpoolId) external override view returns(uint256 balanceAmount) {
        return _pool.getRiskpool(riskpoolId).balance;
    }

    function activeBundles(uint256 riskpoolId) external override view returns(uint256 numberOfActiveBundles) {
        return _pool.activeBundles(riskpoolId);
    }

    function getActiveBundleId(uint256 riskpoolId, uint256 bundleIdx) external override view returns(uint256 bundleId) {
        return _pool.getActiveBundleId(riskpoolId, bundleIdx);
    }
    function getMaximumNumberOfActiveBundles(uint256 riskpoolId) external override view returns(uint256 maximumNumberOfActiveBundles) {
        return _pool.getMaximumNumberOfActiveBundles(riskpoolId);
    }

    /* bundle */
    function getBundleToken() external override view returns(IBundleToken token) {
        BundleToken bundleToken = _bundle.getToken();
        token = IBundleToken(bundleToken);
    }
    
    function getBundle(uint256 bundleId) external override view returns (IBundle.Bundle memory bundle) {
        bundle = _bundle.getBundle(bundleId);
    }

    function bundles() external override view returns (uint256) {
        return _bundle.bundles();
    }

    function unburntBundles(uint256 riskpoolId) external override view returns(uint256 numberOfUnburntBundles) {
        numberOfUnburntBundles = _bundle.unburntBundles(riskpoolId);
    }

    /* treasury */
    function getTreasuryAddress() external override view returns(address) { 
        return address(_treasury);
    }

    function getInstanceWallet() external override view returns(address) { 
        return _treasury.getInstanceWallet();
    }

    function getRiskpoolWallet(uint256 riskpoolId) external override view returns(address) { 
        return _treasury.getRiskpoolWallet(riskpoolId);
    }

    function getComponentToken(uint256 componentId) external override view returns(IERC20) { 
        return _treasury.getComponentToken(componentId);
    }

    function getFeeFractionFullUnit() external override view returns(uint256) {
        return _treasury.getFractionFullUnit();
    }
}
