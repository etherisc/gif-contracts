import brownie
import pytest

def _distribute_funds(testCoin, owner, customer):
    testCoin.transfer(customer, 10**6, {'from': owner})

def test_setup(testCoin, owner):
    assert testCoin.symbol() == "TDY"
    assert testCoin.totalSupply() == testCoin.balanceOf(owner)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_test_setup(testCoin, owner, customer):
    _distribute_funds(testCoin, owner, customer)

    assert testCoin.symbol() == "TDY"

    assert testCoin.balanceOf(customer) == 10**6
    assert testCoin.totalSupply() == testCoin.balanceOf(owner) + testCoin.balanceOf(customer)


def test_direct_transfer(testCoin, owner, customer):
    transferAmount = 1313
    transferBack = 42
    transferBackTooMuch = 42000

    # transfer some
    assert testCoin.balanceOf(owner) == testCoin.totalSupply()
    testCoin.transfer(customer, transferAmount, {'from': owner})
    assert testCoin.balanceOf(owner) == testCoin.totalSupply() - transferAmount
    assert testCoin.balanceOf(customer) == transferAmount

    # tansfer back little
    testCoin.transfer(owner, transferBack, {'from': customer})
    assert testCoin.balanceOf(owner) == testCoin.totalSupply() - transferAmount + transferBack
    assert testCoin.balanceOf(customer) == transferAmount - transferBack

    # transfer back too much
    with brownie.reverts('ERC20: transfer amount exceeds balance'):
        testCoin.transfer(owner, transferBackTooMuch, {'from': customer})


def test_transfer_with_approval(testCoin, owner, customer):
    approvedAmount = 1500
    transferAmount = 1313

    # try to transfer without allowance
    assert testCoin.allowance(owner, customer) == 0
    with brownie.reverts('ERC20: insufficient allowance'):
        testCoin.transferFrom(owner, customer, transferAmount, {'from': customer})

    # owner creates allowance
    testCoin.approve(customer, approvedAmount, {'from': owner})
    assert testCoin.allowance(owner, customer) == approvedAmount

    # transfer from with allowance
    testCoin.transferFrom(owner, customer, transferAmount, {'from': customer})

    # check balance after transfer and check updated allowance
    assert testCoin.balanceOf(customer) == transferAmount
    assert testCoin.allowance(owner, customer) == approvedAmount - transferAmount
