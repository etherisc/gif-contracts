// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../modules/BundleController.sol";
import "../modules/ComponentController.sol";
import "../shared/CoreController.sol";

import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/modules/IBundle.sol";
import "@gif-interface/contracts/services/IRiskpoolService.sol";

contract RiskpoolService is
    IRiskpoolService, 
    CoreController
{
    bytes32 public constant COMPONENT_NAME = "Componet";
    bytes32 public constant BUNDLE_NAME = "Bundle";
    bytes32 public constant RISKPOOL_NAME = "Riskpool";

    modifier onlyRiskpool() {
        IComponent component = IComponent(_msgSender());
        require(
            component.isRiskpool(),
            "ERROR:RPS-001:SENDER_NOT_RISKPOOL"
        );
        _;
    }

    function createBundle(bytes calldata filter, uint256 amount) 
        external override
        onlyRiskpool
        returns(uint256 bundleId)
    {
        uint256 riskpoolId = _component().getComponentId(_msgSender());
        bundleId = _bundle().create(riskpoolId, filter, amount);
    }

    function collateralizePolicy(uint256 bundleId, bytes32 processId, uint256 amount) 
        external override
        onlyRiskpool
    {
        // TODO refactor reqruire below into modifier onlyAssociatedRiskpool
        uint256 riskpoolId = _component().getComponentId(_msgSender());
        IBundle.Bundle memory bundle = _bundle().getBundle(bundleId);
        require(
            riskpoolId == bundle.riskpoolId,
            "ERROR:RPS-002:NOT_ASSOCIATED_RISKPOOL"
        );

        _bundle().collateralizePolicy(bundleId, processId, amount);
    }

    function expirePolicy(uint256 bundleId, bytes32 processId)
        external override
        onlyRiskpool
    {
        // TODO refactor reqruire below into modifier onlyAssociatedRiskpool
        uint256 riskpoolId = _component().getComponentId(_msgSender());
        IBundle.Bundle memory bundle = _bundle().getBundle(bundleId);
        require(
            riskpoolId == bundle.riskpoolId,
            "ERROR:RPS-003:NOT_ASSOCIATED_RISKPOOL"
        );

        _bundle().expirePolicy(bundleId, processId);
    }

    /* internal functions */
    function _bundle() internal view returns(BundleController) {
        return BundleController(_getContractAddress(BUNDLE_NAME));
    }

    function _component() internal view returns(ComponentController) {
        return ComponentController(_getContractAddress(COMPONENT_NAME));
    }
}
