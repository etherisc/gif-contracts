// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

interface ILicense {

    function authorize(address _sender)
        external
        view
        returns (uint256 _productId, bool _isAuthorized, address _policyFlow);

    function getProductId(address sender) 
        external 
        view 
        returns(uint256 productId);
}
