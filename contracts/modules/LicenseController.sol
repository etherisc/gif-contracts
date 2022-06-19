// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ILicense.sol";
import "../test/IProduct.sol";
import "./ComponentController.sol";
import "../shared/CoreController.sol";
import "@gif-interface/contracts/components/IComponent.sol";


contract LicenseController is
    ILicense, 
    CoreController
{

    bytes32 public constant NAME = "LicenseController";
    function authorize(address _sender)
        public override
        view
        returns (uint256 _id, bool _authorized, address _policyFlow)
    {
        _id = _component().getComponentId(_sender);
        IProduct product = _getProduct(_id);
        _authorized = _isValidCall(IComponent(_sender));
        _policyFlow = product.getPolicyFlow();
    }

    function _isValidCall(IComponent component) internal view returns (bool) {
        // TODO replace hardcoded 3 with access function call
        return component.getState() == 3;
    }

    function _getProduct(uint256 id) internal view returns (IProduct product) {
        IComponent cmp = _component().getComponent(id);
        require(cmp.getType() == 1, "ERROR:LIC-001:COMPONENT_NOT_PRODUCT");
        product = IProduct(address(cmp));
    }

    function _component() internal view returns (ComponentController) {
        return ComponentController(_getContractAddress("Component"));
    }
}
