pragma solidity 0.8.2;

import "forge-std/Test.sol";
import "../../contracts/test/TestCoin.sol";
import "../../contracts/modules/RegistryController.sol";
import "../../contracts/shared/CoreProxy.sol";

contract RegistryControllerTest is Test {
    RegistryController private _registryController;
    CoreProxy private _proxy;

    function setUp() public {
        _registryController = new RegistryController();
        _proxy = new CoreProxy(
            address(_registryController), 
            abi.encodeWithSignature("initializeRegistry(bytes32)", bytes32("1.0.0"))
        );
    }

    function getController() internal view returns (RegistryController) {
        return RegistryController(address(_proxy));
    }

    function testRelease() public {
        assertEq(getController().getRelease(), "1.0.0");
    }

}
