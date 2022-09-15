// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../modules/RegistryController.sol";


contract TestRegistryControllerUpdated is RegistryController {

    string message;
    bool upgradeV2;

    function setMessage(string memory _message) public onlyInstanceOperator { message = _message; }
    function getMessage() public view returns (string memory) { return message; }

    function upgradeToV2(string memory _message) public { 
        require(!upgradeV2, "ERROR:REC-102:UPGRADE_ONCE_OMLY");
        upgradeV2 = true;

        setMessage(_message); 
    }
}
