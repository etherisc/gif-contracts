// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/ComponentController.sol";
import "../modules/BundleController.sol";
import "../modules/PolicyController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/CoreController.sol";
import "../services/InstanceOperatorService.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
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
    bytes32 public constant COMPONENT_NAME = "Component";
    bytes32 public constant POLICY_NAME = "Policy";
    bytes32 public constant BUNDLE_NAME = "Bundle";

    bytes32 public constant COMPONENT_OWNER_SERVICE_NAME = "ComponentOwnerService";
    bytes32 public constant INSTANCE_OPERATOR_SERVICE_NAME = "InstanceOperatorService";
    bytes32 public constant ORACLE_SERVICE_NAME = "OracleService";
    bytes32 public constant PRODUCT_SERVICE_NAME = "ProductService";
    bytes32 public constant RISKPOOL_SERVICE_NAME = "RiskpoolService";

    BundleController _bundle;
    ComponentController _component;
    PolicyController _policy;
    TreasuryModule private _treasury;

    function _afterInitialize() internal override onlyInitializing {
        _bundle = BundleController(_getContractAddress("Bundle"));
        _component = ComponentController(_getContractAddress("Component"));
        _policy = PolicyController(_getContractAddress("Policy"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));
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

    function getOwner() external override view returns(address) {
        InstanceOperatorService ios = InstanceOperatorService(_getContractAddress(INSTANCE_OPERATOR_SERVICE_NAME));
        return ios.owner();
    }

    // TODO decide how to protect registry access
    function getRegistry() external view returns(IRegistry service) {
        return _registry;
    }

    /* access */
    function getProductOwnerRole() external override view returns(bytes32) {
        return _access.productOwnerRole();
    }

    function getOracleProviderRole() external override view returns(bytes32) {
        return _access.oracleProviderRole();
    }

    function getRiskpoolKeeperRole() external override view returns(bytes32) {
        return _access.riskpoolKeeperRole();
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

    function getComponent(uint256 id) external override view returns(IComponent) {
        return _component.getComponent(id);
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

    /* service staking */
    function getStakingRequirements(uint256 id) 
        external override 
        view 
        returns(bytes memory data) 
    {
        revert("ERROR:IS-001:IMPLEMENATION_MISSING");
    }

    function getStakedAssets(uint256 id)
        external override 
        view 
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
