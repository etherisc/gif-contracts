// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

contract Delegator {

    event LogDelDummy1();
    event LogDelDummy2(
        address delegationAddress
    );
    
    function _delegate(address _implementation) internal {

        emit LogDelDummy1();

        require(
            _implementation != address(0),
            "ERROR:DEL-001:UNKNOWN_IMPLEMENTATION"
        );

        emit LogDelDummy2(_implementation);

        bytes memory data = msg.data;

        /* solhint-disable no-inline-assembly */
        assembly {
            let result := delegatecall(
                gas(),
                _implementation,
                add(data, 0x20),
                mload(data),
                0,
                0
            )
            let size := returndatasize()
            let ptr := mload(0x40)
            returndatacopy(ptr, 0, size)
            switch result
                case 0 {
                    revert(ptr, size)
                }
                default {
                    return(ptr, size)
                }
        }
        /* solhint-enable no-inline-assembly */
    }
}
