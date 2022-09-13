// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";

import "@etherisc/gif-interface/contracts/modules/IAccess.sol";
import "@etherisc/gif-interface/contracts/modules/IPolicy.sol";
import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";

import "@etherisc/gif-interface/contracts/services/IComponentOwnerService.sol";
import "@etherisc/gif-interface/contracts/services/IProductService.sol";
import "@etherisc/gif-interface/contracts/services/IInstanceService.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/* 
the TestCompromisedProduct claims to be an existing product that connects to an existing 
riskpool with the goal to create fraud claims that lead to fraud payouts whith the intention
to drain the riskpool.

for this the compromised product claims
- to be a product
- to be in state active (independent of an approval step by the instance operator)
*/
contract TestCompromisedProduct is 
    IProduct,
    Ownable 
{
    IComponent.ComponentState public constant FAKE_STATE = IComponent.ComponentState.Active;
    
    bytes32 public constant POLICY_FLOW = "PolicyDefaultFlow";

    bytes32 private _componentName;
    address private _tokenAddress;
    uint256 private _componentId;
    uint256 private _riskpoolId;
    
    IRegistry private _registry;
    IAccess private _access;
    IComponentOwnerService private _componentOwnerService;
    IInstanceService private _instanceService;
    address private _policyFlow;
    IProductService private _productService;

    uint256 private _policies;
    uint256 private _claims;

    modifier onlyPolicyHolder(bytes32 policyId) {
        address policyHolder = _instanceService.getMetadata(policyId).owner;
        require(
            _msgSender() == policyHolder, 
            "ERROR:TCP-1:INVALID_POLICY_OR_HOLDER"
        );
        _;
    }

    constructor(
        bytes32 fakeProductName,
        address tokenAddress,
        uint256 fakeComponentId,
        uint256 fakeRiskpoolId,
        address registryAddress
    )
        Ownable()
    { 
        _componentName = fakeProductName;
        _tokenAddress = tokenAddress;
        _componentId = fakeComponentId;
        _riskpoolId = fakeRiskpoolId;

        _registry = IRegistry(registryAddress);
        _access = _getAccess();
        _componentOwnerService = _getComponentOwnerService();
        _instanceService = _getInstanceService();
        _policyFlow = _getContractAddress(POLICY_FLOW);
        _productService = _getProductService();
    }

    function applyForPolicy(
        uint256 premium, 
        uint256 sumInsured,
        bytes calldata metaData,
        bytes calldata applicationData
    ) 
        external 
        payable 
        returns (bytes32 processId) 
    {
        address payable policyHolder = payable(_msgSender());

        // Create and underwrite new application
        processId = _productService.newApplication(
            policyHolder, 
            premium, 
            sumInsured, 
            metaData, 
            applicationData);

        _productService.underwrite(processId);
    }

    function collectPremium(bytes32 policyId) 
        external 
    {
        IPolicy.Policy memory policy = _instanceService.getPolicy(policyId);
        _productService.collectPremium(policyId, policy.premiumExpectedAmount);
    }

    function submitClaim(bytes32 policyId, uint256 claimAmount) 
        external
        onlyPolicyHolder(policyId)
    {
        // increase claims counter
        _claims += 1;
        
        // create claim and confirm it
        uint256 claimId = _productService.newClaim(policyId, claimAmount, abi.encode(0));
        _productService.confirmClaim(policyId, claimId, claimAmount);

        // create payout record
        uint256 payoutId = _productService.newPayout(policyId, claimId, claimAmount, abi.encode(0));
        _productService.processPayout(policyId, payoutId);
    }

    //--- product service access --------------------------------------------//

    //--- iproduct ----------------------------------------------------------//
    function getToken() external override view returns(address token) { return _tokenAddress; }
    function getPolicyFlow() external override view returns(address policyFlow) { return _getContractAddress(POLICY_FLOW); }
    function getRiskpoolId() external override view returns(uint256 riskpoolId) { return _riskpoolId; }

    function getApplicationDataStructure() external override view returns(string memory dataStructure) { return ""; }
    function getClaimDataStructure() external override view returns(string memory dataStructure) { return ""; }
    function getPayoutDataStructure() external override view returns(string memory dataStructure) { return ""; }

    function riskPoolCapacityCallback(uint256 capacity) external override {}

    //--- icomponent --------------------------------------------------------//
    function setId(uint256 id) external override {} // does not care about id

    function getName() external override view returns(bytes32) { return _componentName; }
    function getId() external override view returns(uint256) { return _componentId; }
    function getType() external override view returns(ComponentType) { return IComponent.ComponentType.Product; }
    function getState() external override view returns(ComponentState) { return IComponent.ComponentState.Active; }
    function getOwner() external override view returns(address) { return owner(); }
    function getRegistry() external override view returns(IRegistry) { return _registry; }

    function isProduct() public override view returns(bool) { return true; }
    function isOracle() public override view returns(bool) { return false; }
    function isRiskpool() public override view returns(bool) { return false; }

    function proposalCallback() external override {}
    function approvalCallback() external override {} 
    function declineCallback() external override {}
    function suspendCallback() external override {}
    function resumeCallback() external override {}
    function pauseCallback() external override {}
    function unpauseCallback() external override {}
    function archiveCallback() external override {}

    function _getAccess() private view returns (IAccess) {
        return IAccess(_getContractAddress("Access"));        
    }

    function _getInstanceService() private view returns (IInstanceService) {
        return IInstanceService(_getContractAddress("InstanceService"));        
    }

    function _getComponentOwnerService() private view returns (IComponentOwnerService) {
        return IComponentOwnerService(_getContractAddress("ComponentOwnerService"));        
    }

    function _getProductService() private view returns (IProductService) {
        return IProductService(_getContractAddress("ProductService"));        
    }

    function _getContractAddress(bytes32 contractName) private view returns (address) { 
        return _registry.getContract(contractName);
    }

}