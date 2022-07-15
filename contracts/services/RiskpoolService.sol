// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/BundleController.sol";
import "../modules/ComponentController.sol";
import "../modules/TreasuryModule.sol";
import "../shared/CoreController.sol";

import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/modules/IBundle.sol";
import "@gif-interface/contracts/services/IRiskpoolService.sol";

contract RiskpoolService is
    IRiskpoolService, 
    CoreController
{
    bytes32 public constant RISKPOOL_NAME = "Riskpool";

    ComponentController private _component;
    BundleController private _bundle;
    TreasuryModule private _treasury;

    modifier onlyRiskpool() {
        IComponent component = IComponent(_msgSender());
        require(
            component.isRiskpool(),
            "ERROR:RPS-001:SENDER_NOT_RISKPOOL"
        );
        _;
    }


    function _afterInitialize() internal override onlyInitializing {
        _bundle = BundleController(_getContractAddress("Bundle"));
        _component = ComponentController(_getContractAddress("Component"));
        _treasury = TreasuryModule(_getContractAddress("Treasury"));
    }


    function createBundle(
        address owner, 
        bytes calldata filter, 
        uint256 initialCapital
    ) 
        external override
        onlyRiskpool
        returns(uint256 bundleId)
    {
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        bundleId = _bundle.create(owner, riskpoolId, filter, 0);

        (bool success, uint256 capitalAfterFees) = _treasury.processCapital(bundleId, initialCapital);

        if (success) {
            _bundle.fund(bundleId, capitalAfterFees);
        }
    }

    function unlockCapital(uint256 bundleId, bytes32 processId)
        external
        onlyRiskpool
        returns(uint256 collateralAmount)
    {

    }
    
    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 collateralAmount) 
        external override
        onlyRiskpool
    {
        // TODO refactor reqruire below into modifier onlyAssociatedRiskpool
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            riskpoolId == bundle.riskpoolId,
            "ERROR:RPS-002:NOT_ASSOCIATED_RISKPOOL"
        );

        _bundle.collateralizePolicy(bundleId, processId, collateralAmount);
    }

    function expirePolicy(uint256 bundleId, bytes32 processId)
        external override
        onlyRiskpool
        returns(uint256 collateralAmount)
    {
        // TODO refactor reqruire below into modifier onlyAssociatedRiskpool
        uint256 riskpoolId = _component.getComponentId(_msgSender());
        IBundle.Bundle memory bundle = _bundle.getBundle(bundleId);
        require(
            riskpoolId == bundle.riskpoolId,
            "ERROR:RPS-003:NOT_ASSOCIATED_RISKPOOL"
        );

        collateralAmount = _bundle.expirePolicy(bundleId, processId);
    }
}
