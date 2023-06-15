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

    /**
     * @dev Constructor function to initialize the component with the given parameters.
     * @param fakeProductName The name of the component.
     * @param tokenAddress The address of the token used for the component.
     * @param fakeComponentId The ID of the component.
     * @param fakeRiskpoolId The ID of the risk pool associated with the component.
     * @param registryAddress The address of the registry contract.
     */
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

    /**
     * @dev Allows a policy holder to apply for a new policy by submitting an application with the specified premium, sum insured, metaData, and applicationData.
     * @param premium The amount of premium to be paid for the policy.
     * @param sumInsured The amount of coverage provided by the policy.
     * @param metaData Additional metadata related to the policy application.
     * @param applicationData Additional data related to the policy application.
     * @return processId The process ID of the new policy application.
     */
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

    /**
     * @dev Collects the premium for a given policy.
     * @param policyId The ID of the policy to collect the premium for.
     */
    function collectPremium(bytes32 policyId) 
        external 
    {
        IPolicy.Policy memory policy = _instanceService.getPolicy(policyId);
        _productService.collectPremium(policyId, policy.premiumExpectedAmount);
    }

    /**
     * @dev Allows a policy holder to submit a claim for the specified policy.
     * @param policyId The ID of the policy for which the claim is being submitted.
     * @param claimAmount The amount of the claim being submitted.
     *
     * Emits a ClaimSubmitted event and creates a new claim and payout record.
     */
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
    /**
     * @dev Returns the address of the token used by this contract.
     * @return token The address of the token used by this contract.
     */
    function getToken() external override view returns(address token) { return _tokenAddress; }
    /**
     * @dev Returns the address of the policy flow contract.
     * @return policyFlow The address of the policy flow contract.
     */
    function getPolicyFlow() external override view returns(address policyFlow) { return _getContractAddress(POLICY_FLOW); }
    /**
     * @dev Returns the ID of the risk pool.
     * @return riskpoolId The ID of the risk pool.
     */
    function getRiskpoolId() external override view returns(uint256 riskpoolId) { return _riskpoolId; }

    /**
     * @dev Returns the data structure of the application.
     * @return dataStructure The string representing the data structure of the application.
     */
    function getApplicationDataStructure() external override view returns(string memory dataStructure) { return ""; }
    /**
     * @dev Returns the data structure of the claim data.
     * @return dataStructure The data structure of the claim data as a string.
     */
    function getClaimDataStructure() external override view returns(string memory dataStructure) { return ""; }
    /**
     * @dev Returns the data structure of the payout information.
     * @return dataStructure The string representation of the payout data structure.
     */
    function getPayoutDataStructure() external override view returns(string memory dataStructure) { return ""; }

    /**
     * @dev Callback function to update the risk pool's capacity.
     * @param capacity The new capacity of the risk pool.
     */
    function riskPoolCapacityCallback(uint256 capacity) external override {}

    //--- icomponent --------------------------------------------------------//
    /**
     * @dev Sets the ID of the contract.
     * @param id The ID to be set.
     */
    function setId(uint256 id) external override {} // does not care about id

    /**
     * @dev Returns the name of the component.
     * @return _componentName The name of the component as a bytes32 value.
     */
    function getName() external override view returns(bytes32) { return _componentName; }
    /**
     * @dev Returns the ID of the component.
     * @return The ID of the component as a uint256 value.
     */
    function getId() external override view returns(uint256) { return _componentId; }
    /**
     * @dev Returns the ComponentType of the product.
     * @return The ComponentType of the product.
     */
    function getType() external override view returns(ComponentType) { return IComponent.ComponentType.Product; }
    /**
     * @dev Returns the current state of the component.
     * @return state The current state of the component as a ComponentState enum value.
     */
    function getState() external override view returns(ComponentState) { return IComponent.ComponentState.Active; }
    /**
     * @dev Returns the address of the contract owner.
     * @return The address of the contract owner.
     */
    function getOwner() external override view returns(address) { return owner(); }
    /**
     * @dev Returns the current registry contract instance.
     * @return _registry The current registry contract instance.
     */
    function getRegistry() external override view returns(IRegistry) { return _registry; }

    /**
     * @dev Checks if the contract is a product.
     * @return Returns a boolean value indicating if the contract is a product.
     */
    function isProduct() public override view returns(bool) { return true; }
    /**
     * @dev Returns a boolean value indicating whether the contract is an oracle.
     * @return A boolean value indicating whether the contract is an oracle.
     */
    function isOracle() public override view returns(bool) { return false; }
    /**
     * @dev Check if the contract is a risk pool.
     * @return {bool} Returns a boolean indicating if the contract is a risk pool.
     */
    function isRiskpool() public override view returns(bool) { return false; }

    /**
     * @dev This function is a callback function for proposals.
     *
     * Returns: None
     */
    function proposalCallback() external override {}
    /**
     * @dev This function is a callback function that is called after an approval has been made.
     */
    function approvalCallback() external override {} 
    /**
     * @dev This function is called when a user declines a transaction in the dApp.
     */
    function declineCallback() external override {}
    /**
     * @dev Suspends the callback function.
     */
    function suspendCallback() external override {}
    /**
     * @dev This function is a callback function that is triggered when a paused contract is resumed.
     *
     */
    function resumeCallback() external override {}
    /**
     * @dev Callback function that is called when the contract is paused. This function does not take any parameters.
     */
    function pauseCallback() external override {}
    /**
     * @dev This function is called by the owner of the contract to unpause the contract after it has been paused.
     */
    function unpauseCallback() external override {}
    /**
     * @dev This function is a callback function that is executed when a contract is archived.
     *
     */
    function archiveCallback() external override {}

    /**
     * @dev Returns the instance of the IAccess contract.
     * @return access Returns the instance of the IAccess contract.
     */
    function _getAccess() private view returns (IAccess) {
        return IAccess(_getContractAddress("Access"));        
    }

    /**
     * @dev Returns the instance service contract.
     * @return instanceService The instance service contract.
     */
    function _getInstanceService() private view returns (IInstanceService) {
        return IInstanceService(_getContractAddress("InstanceService"));        
    }

    /**
     * @dev Returns the instance of the ComponentOwnerService contract.
     * @return The ComponentOwnerService contract instance.
     */
    function _getComponentOwnerService() private view returns (IComponentOwnerService) {
        return IComponentOwnerService(_getContractAddress("ComponentOwnerService"));        
    }

    /**
     * @dev Returns the ProductService contract instance.
     * @return productService The ProductService contract instance.
     */
    function _getProductService() private view returns (IProductService) {
        return IProductService(_getContractAddress("ProductService"));        
    }

    /**
     * @dev Returns the address of a registered contract with the given name.
     * @param contractName The name of the contract to retrieve the address for.
     * @return The address of the registered contract with the given name.
     */
    function _getContractAddress(bytes32 contractName) private view returns (address) { 
        return _registry.getContract(contractName);
    }

}