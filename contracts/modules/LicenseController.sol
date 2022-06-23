// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "../shared/CoreController.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/components/IProduct.sol";
import "@gif-interface/contracts/modules/ILicense.sol";


contract LicenseController is
    ILicense, 
    CoreController
{

    ComponentController private _component;

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    function getAuthorizationStatus(address productAddress)
        public override
        view
        returns (uint256 productId, bool isAuthorized, address policyFlow)
    {
        productId = getProductId(productAddress);
        isAuthorized = _isValidCall(IComponent(productAddress));
        policyFlow = _getProduct(productId).getPolicyFlow();
    }

    function getProductId(address sender) 
        public override 
        view 
        returns(uint256 productId) 
    {
        productId = _component.getComponentId(sender);
    }

    function _isValidCall(IComponent component) internal view returns (bool) {
        return component.getStatus() == ComponentStatus.Active;
    }

    function _getProduct(uint256 id) internal view returns (IProduct product) {
        IComponent cmp = _component.getComponent(id);
        require(cmp.isProduct(), "ERROR:LIC-001:COMPONENT_NOT_PRODUCT");
        product = IProduct(address(cmp));
    }
}
