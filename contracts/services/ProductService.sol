// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/WithRegistry.sol";
import "../shared/Delegator.sol";
import "../modules/ILicense.sol";
import "@openzeppelin/contracts/utils/Context.sol";

contract ProductService is 
    WithRegistry, 
    Delegator,
    Context
 {
    bytes32 public constant NAME = "ProductService";

    // solhint-disable-next-line no-empty-blocks
    constructor(address _registry) WithRegistry(_registry) {}

    fallback() external {
        (uint256 id, bool authorized, address policyFlow) = _license().authorize(_msgSender());
        require(authorized, "ERROR:PRS-001:NOT_AUTHORIZED");
        require(policyFlow != address(0),"ERROR:PRS-002:POLICY_FLOW_NOT_RESOLVED");

        _delegate(policyFlow);
    }
    
    function _license() internal view returns (ILicense) {
        return ILicense(registry.getContract("License"));
    }
}
