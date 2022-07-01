import brownie

from brownie import DummyCoin

def test_setup(dummyCoin, owner):
    assert dummyCoin.symbol() == "DMY"
    assert dummyCoin.totalSupply() == dummyCoin.balanceOf(owner)


def test_direct_transfer(dummyCoin, owner, customer):
    transferAmount = 1313
    transferBack = 42
    transferBackTooMuch = 42000

    # transfer some
    dummyCoin.transfer(customer, transferAmount, {'from': owner})
    assert dummyCoin.balanceOf(owner) == dummyCoin.totalSupply() - transferAmount
    assert dummyCoin.balanceOf(customer) == transferAmount

    # tansfer back little
    dummyCoin.transfer(owner, transferBack, {'from': customer})
    assert dummyCoin.balanceOf(owner) == dummyCoin.totalSupply() - transferAmount + transferBack
    assert dummyCoin.balanceOf(customer) == transferAmount - transferBack

    # transfer back too much
    with brownie.reverts('ERC20: transfer amount exceeds balance'):
        dummyCoin.transfer(owner, transferBackTooMuch, {'from': customer})


def test_transfer_with_approval(dummyCoin, owner, customer):
    approvedAmount = 1500
    transferAmount = 1313

    # try to transfer without allowance
    assert dummyCoin.allowance(owner, customer) == 0
    with brownie.reverts('ERC20: insufficient allowance'):
        dummyCoin.transferFrom(owner, customer, transferAmount, {'from': customer})

    # owner creates allowance
    dummyCoin.approve(customer, approvedAmount, {'from': owner})
    assert dummyCoin.allowance(owner, customer) == approvedAmount

    # transfer from with allowance
    dummyCoin.transferFrom(owner, customer, transferAmount, {'from': customer})

    # check balance after transfer and check updated allowance
    assert dummyCoin.balanceOf(customer) == transferAmount
    assert dummyCoin.allowance(owner, customer) == approvedAmount - transferAmount
