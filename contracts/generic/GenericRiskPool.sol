// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "@etherisc/gif-interface/contracts/components/BasicRiskpool.sol";

contract GenericRiskpool is BasicRiskpool {
    constructor(
        bytes32 name,
        uint256 collateralization,
        address erc20Token,
        address wallet,
        address registry
    ) BasicRiskpool(name, collateralization, 0, erc20Token, wallet, registry) {
        // not implemented
    }

    function bundleMatchesApplication(
        IBundle.Bundle memory bundle,
        IPolicy.Application memory application
    ) public pure override returns (bool isMatching) {
        isMatching = true;
    }
}
