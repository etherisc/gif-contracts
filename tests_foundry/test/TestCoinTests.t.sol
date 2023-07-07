pragma solidity 0.8.2;

import "forge-std/Test.sol";
import "../../contracts/test/TestCoin.sol";

contract TestCoinTest is Test {
    TestCoin private testCoin;

    function setUp() public {
        testCoin = new TestCoin();
    }

    function testName() public {
        assertEq(testCoin.NAME(), "Test Dummy");
    }

    function testSymbol() public {
        assertEq(testCoin.SYMBOL(), "TDY");
    }
}
