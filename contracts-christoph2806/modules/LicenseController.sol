// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

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

    /**
     * @dev This function is called after the contract is initialized and sets the `_component` variable to the address of the `ComponentController` contract.
     *
     */
    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    // ensures that calling component (productAddress) is a product
    /**
     * @dev Returns the authorization status of a given product address.
     * @param productAddress The address of the product to check authorization status for.
     * @return productId The ID of the product.
     * @return isAuthorized A boolean indicating whether the product is authorized or not.
     * @return policyFlow The address of the policy flow associated with the product.
     */
    function getAuthorizationStatus(address productAddress)
        public override
        view
        returns (uint256 productId, bool isAuthorized, address policyFlow)
    {
        productId = _component.getComponentId(productAddress);
        isAuthorized = _isValidCall(productId);
        policyFlow = _component.getPolicyFlow(productId);
    }

    /**
     * @dev Checks if a product is currently active.
     * @param productId The ID of the product to check.
     * @return A boolean indicating if the product is active or not.
     */
    function _isValidCall(uint256 productId) internal view returns (bool) {
        return _component.getComponentState(productId) == IComponent.ComponentState.Active;
    }

    /**
     * @dev Returns the product associated with the given ID.
     * @param id The ID of the product to retrieve.
     * @return product The product associated with the given ID.
     */
    function _getProduct(uint256 id) internal view returns (IProduct product) {
        require(_component.isProduct(id), "ERROR:LIC-001:COMPONENT_NOT_PRODUCT");
        IComponent cmp = _component.getComponent(id);
        product = IProduct(address(cmp));
    }
}
