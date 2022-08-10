// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/modules/ILicense.sol";


contract LicenseController is
    ILicense, 
    CoreController
{

    ComponentController private _component;

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    // ensures that calling component (productAddress) is a product
    function getAuthorizationStatus(address productAddress)
        public override
        view
        returns (uint256 productId, bool isAuthorized, address policyFlow)
    {
        productId = _component.getComponentId(productAddress);
        isAuthorized = _isValidCall(productId);
        policyFlow = _getProduct(productId).getPolicyFlow();
    }

    function _isValidCall(uint256 productId) internal view returns (bool) {
        return _component.getComponentState(productId) == IComponent.ComponentState.Active;
    }

    function _getProduct(uint256 id) internal view returns (IProduct product) {
        IComponent cmp = _component.getComponent(id);
        require(cmp.isProduct(), "ERROR:LIC-001:COMPONENT_NOT_PRODUCT");
        product = IProduct(address(cmp));
    }
}
