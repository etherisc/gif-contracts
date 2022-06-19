// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

interface ILicense {

    function authorize(address _sender)
        external
        view
        returns (uint256 _id, bool _authorized, address _policyFlow);

}
