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

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
        _pool = PoolController(_getContractAddress("Pool"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));

        _transferOwnership(_msgSender());
        _linkBundleModuleToBundleToken();
        _setDefaultAdminRole();
    }

    function _setDefaultAdminRole() private {
        AccessController access = AccessController(_getContractAddress("Access"));
        access.setDefaultAdminRole(address(this));
    }

    function _linkBundleModuleToBundleToken() private {
        BundleToken token = BundleToken(_getContractAddress("BundleToken"));
        address bundleAddress = _getContractAddress("Bundle");
        token.setBundleModule(bundleAddress);
    }

    /* registry */
    function prepareRelease(bytes32 _newRelease) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _registry.prepareRelease(_newRelease);
    }

    function register(bytes32 _contractName, address _contractAddress)
        external override
        onlyInstanceOperatorAddress
    {
        _registry.register(_contractName, _contractAddress);
    }

    function deregister(bytes32 _contractName) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _registry.deregister(_contractName);
    }

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

    function deregisterInRelease(bytes32 _release, bytes32 _contractName)
        external override
        onlyInstanceOperatorAddress
    {
        _registry.deregisterInRelease(_release, _contractName);
    }
    
    /* access */
    function createRole(bytes32 _role) 
        external override
        onlyInstanceOperatorAddress 
    {
        _access.addRole(_role);
    }

    function invalidateRole(bytes32 _role) 
        external override
        onlyInstanceOperatorAddress 
    {
        _access.invalidateRole(_role);
    }

    function grantRole(bytes32 role, address principal)
        external override
        onlyInstanceOperatorAddress
    {
        _access.grantRole(role, principal);
    }

    function revokeRole(bytes32 role, address principal) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _access.revokeRole(role, principal);
    }

    /* component */
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

    function decline(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.decline(id);
    }

    function suspend(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.suspend(id);
    }

    function resume(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.resume(id);
    }

    function archive(uint256 id) 
        external override 
        onlyInstanceOperatorAddress 
    {
        _component.archiveFromInstanceOperator(id);
    }

    // service staking
    // TODO implement setDefaultStaking staking
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
    function suspendTreasury() 
        external override
        onlyInstanceOperatorAddress
    { 
        _treasury.suspend();
    }

    function resumeTreasury() 
        external override
        onlyInstanceOperatorAddress
    { 
        _treasury.resume();
    }

    function setInstanceWallet(address walletAddress) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setInstanceWallet(walletAddress);
    }

    function setRiskpoolWallet(uint256 riskpoolId, address riskpoolWalletAddress) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setRiskpoolWallet(riskpoolId, riskpoolWalletAddress);
    }

    function setProductToken(uint256 productId, address erc20Address) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setProductToken(productId, erc20Address);
    }

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
    
    function setPremiumFees(ITreasury.FeeSpecification calldata feeSpec) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setPremiumFees(feeSpec);
    }

    function setCapitalFees(ITreasury.FeeSpecification calldata feeSpec) 
        external override
        onlyInstanceOperatorAddress
    {
        _treasury.setCapitalFees(feeSpec);
    }
}
