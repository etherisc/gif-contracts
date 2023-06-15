// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../modules/RegistryController.sol";


contract TestRegistryControllerUpdated is RegistryController {

    string message;
    bool upgradeV2;

    /**
     * @dev Sets the message variable to a given string.
     * @param _message The string to be set as the message.
     */
    function setMessage(string memory _message) public onlyInstanceOperator { message = _message; }
    /**
     * @dev Returns the current message stored in the contract.
     * @return message The current message stored in the contract.
     */
    function getMessage() public view returns (string memory) { return message; }

    /**
     * @dev Upgrades the contract to version 2.
     * @param _message The message to set for the upgraded contract.
     */
    function upgradeToV2(string memory _message) public { 
        require(!upgradeV2, "ERROR:REC-102:UPGRADE_ONCE_OMLY");
        upgradeV2 = true;

        setMessage(_message); 
    }
}
