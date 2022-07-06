// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./IClaims.sol";

import "./ComponentController.sol";
import "./PolicyController.sol";
import "../shared/CoreController.sol";

import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/components/IRiskpool.sol";


contract ClaimsController is
    IClaims,
    CoreController
{
    ComponentController private _component;

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    function _getRiskpool(uint256 id) internal view returns (IRiskpool riskpool) {
        IComponent cmp = _component.getComponent(id);
        require(cmp.isRiskpool(), "ERROR:CLM-001:COMPONENT_NOT_RISKPOOL");
        riskpool = IRiskpool(address(cmp));
    }
}
