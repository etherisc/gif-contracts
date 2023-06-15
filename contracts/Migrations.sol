// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

contract Migrations {
    address public owner;
    uint256 public last_completed_migration; // solhint-disable-line

    /**
     * @dev Constructor function that sets the contract owner to the address of the sender.
     */
    constructor() {
        owner = msg.sender;
    }

    modifier restricted() {
        if (msg.sender == owner) _;
    }

    /**
     * @dev Sets the value of the last completed migration to the given value.
     * @param _completed The new value for the last completed migration.
     */
    function setCompleted(uint256 _completed) public restricted {
        last_completed_migration = _completed;
    }

    /**
     * @dev Upgrades the Migrations contract to a new address.
     * @param _newAddress The address of the new Migrations contract.
     */
    function upgrade(address _newAddress) public restricted {
        Migrations upgraded = Migrations(_newAddress);
        upgraded.setCompleted(last_completed_migration);
    }
}
