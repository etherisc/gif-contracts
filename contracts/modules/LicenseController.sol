// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "./ComponentController.sol";
import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/components/IComponent.sol";
import "@etherisc/gif-interface/contracts/components/IProduct.sol";
import "@etherisc/gif-interface/contracts/modules/ILicense.sol";

/**
 * @dev The smart contract serves as a controller contract for managing licenses related to products in an insurance ecosystem.
 * The contract implements the `ILicense` interface and extends the `CoreController` contract.
 *
 * The contract imports two other contracts: `ComponentController.sol` and `CoreController.sol`, which are expected to be located in specific file paths.
 * It also imports several interfaces from the "etherisc/gif-interface" library, including `IComponent.sol`, `IProduct.sol`, and `ILicense.sol`.
 * The contract includes a private variable `_component` of type `ComponentController`, which is used to interact with the `ComponentController` contract.
 *
 * Functions:
 *
 * - `_afterInitialize()`: Called after the contract is initialized. This function sets the `_component` variable to the address of the `ComponentController` contract.
 * - `getAuthorizationStatus(address productAddress)`: Takes a product address as input and returns the authorization status of the product. It retrieves the product's ID using the `_component.getComponentId(productAddress)` function, checks if the product is authorized by calling the internal `_isValidCall(productId)` function, and retrieves the associated policy flow address using the `_component.getPolicyFlow(productId)` function.
 * - `_isValidCall(uint256 productId)`: Checks if a product with the given ID is currently active. It does this by calling `_component.getComponentState(productId)` and comparing the returned value to `IComponent.ComponentState.Active`.
 * - `_getProduct(uint256 id)`: Retrieves the product associated with the given ID. It checks if the ID corresponds to a valid product using `_component.isProduct(id)` and then retrieves the product using `_component.getComponent(id)`.
 *
 * Overall, the `LicenseController` contract serves as a controller for managing licenses and provides functions to check the authorization status and activity of products within an insurance ecosystem.
 */

contract LicenseController is ILicense, CoreController {
    ComponentController private _component;

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
    }

    // ensures that calling component (productAddress) is a product
    function getAuthorizationStatus(
        address productAddress
    )
        public
        view
        override
        returns (uint256 productId, bool isAuthorized, address policyFlow)
    {
        productId = _component.getComponentId(productAddress);
        isAuthorized = _isValidCall(productId);
        policyFlow = _component.getPolicyFlow(productId);
    }

    function _isValidCall(uint256 productId) internal view returns (bool) {
        return
            _component.getComponentState(productId) ==
            IComponent.ComponentState.Active;
    }

    function _getProduct(uint256 id) internal view returns (IProduct product) {
        require(
            _component.isProduct(id),
            "ERROR:LIC-001:COMPONENT_NOT_PRODUCT"
        );
        IComponent cmp = _component.getComponent(id);
        product = IProduct(address(cmp));
    }
}
