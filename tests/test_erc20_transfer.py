import brownie
import pytest

from brownie import (
    TestTransferFrom,
)

INITIAL_FUNDING = 10**6

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):
    erc20Token.transfer(customer, INITIAL_FUNDING, {'from': instanceOperator})
    erc20Token.transfer(customer2, INITIAL_FUNDING, {'from': instanceOperator})

    erc20TokenAlternative.transfer(customer, INITIAL_FUNDING, {'from': instanceOperator})
    erc20TokenAlternative.transfer(customer2, INITIAL_FUNDING, {'from': instanceOperator})


def test_setup(erc20Token, erc20TokenAlternative, instanceOperator):
    assert erc20Token.symbol() == "TDY"
    assert erc20Token.totalSupply() == erc20Token.balanceOf(instanceOperator)

    assert erc20TokenAlternative.symbol() == "TAC"
    assert erc20TokenAlternative.totalSupply() == erc20TokenAlternative.balanceOf(instanceOperator)


def test_intial_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):
    _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)

    assert erc20Token.balanceOf(customer) == INITIAL_FUNDING
    assert erc20Token.balanceOf(customer2) == INITIAL_FUNDING

    assert erc20TokenAlternative.balanceOf(customer) == INITIAL_FUNDING
    assert erc20TokenAlternative.balanceOf(customer2) == INITIAL_FUNDING


def test_transferFrom_erc20(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):
    _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)

    # check happy path
    smallAmount = 100
    balanceCustomer2 = erc20Token.balanceOf(customer2)

    erc20Token.approve(customer2, smallAmount, {'from': customer})
    success = erc20Token.transferFrom(customer, customer2, smallAmount, {'from': customer2})

    assert success
    assert erc20Token.balanceOf(customer2) == balanceCustomer2 + smallAmount

    # check revert for unsufficient allowance
    with brownie.reverts("ERC20: insufficient allowance"):
        success = erc20Token.transferFrom(customer, customer2, smallAmount, {'from': customer2})

    # check revert for unsufficient balance
    tooBigAmount = INITIAL_FUNDING + smallAmount
    erc20Token.approve(customer2, tooBigAmount, {'from': customer})

    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        success = erc20Token.transferFrom(customer, customer2, tooBigAmount, {'from': customer2})


def test_transferFrom_erc20_alternative(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):
    _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)

    # check happy path
    smallAmount = 100
    balanceCustomer2 = erc20TokenAlternative.balanceOf(customer2)

    erc20TokenAlternative.approve(customer2, smallAmount, {'from': customer})
    success = erc20TokenAlternative.transferFrom(customer, customer2, smallAmount, {'from': customer2})

    assert success
    assert erc20TokenAlternative.balanceOf(customer2) == balanceCustomer2 + smallAmount

    # check outcome for unsufficient allowance
    tx = erc20TokenAlternative.transferFrom(customer, customer2, smallAmount, {'from': customer2})
    assert tx.return_value == False

    # check revert for unsufficient balance
    tooBigAmount = INITIAL_FUNDING + smallAmount
    erc20TokenAlternative.approve(customer2, tooBigAmount, {'from': customer})

    tx = erc20TokenAlternative.transferFrom(customer, customer2, tooBigAmount, {'from': customer2})
    assert tx.return_value == False


def test_transferFrom_unified(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):
    _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)

    smallAmount = 100
    tooBigAmount = INITIAL_FUNDING + smallAmount

    transferrer = TestTransferFrom.deploy({'from': instanceOperator})

    print('--- test happy case for erc20TokenAlternative and erc20Token ---')

    # --- happy case with erc20TokenAlternative
    balanceCustomer2 = erc20TokenAlternative.balanceOf(customer2)
    erc20TokenAlternative.approve(customer2, smallAmount, {'from': customer})
    assert erc20TokenAlternative.allowance(customer, customer2) == smallAmount
    tx = transferrer.unifiedTransferFrom(erc20TokenAlternative, customer, customer2, smallAmount, {'from': customer2})
    print(tx.info())

    assert tx.return_value
    assert erc20TokenAlternative.balanceOf(customer2) == balanceCustomer2 + smallAmount

    # --- happy case with erc20Token
    balanceCustomer2 = erc20Token.balanceOf(customer2)
    erc20Token.approve(customer2, smallAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20Token, customer, customer2, smallAmount, {'from': customer2})

    assert tx.return_value
    assert erc20Token.balanceOf(customer2) == balanceCustomer2 + smallAmount


    print('--- test unsufficient allowance for erc20TokenAlternative and erc20Token ---')
    
    # check outcome for unsufficient allowance
    tx = transferrer.unifiedTransferFrom(erc20TokenAlternative, customer, customer2, smallAmount, {'from': customer2})
    assert tx.return_value == False
    
    # check outcome for unsufficient allowance
    tx = transferrer.unifiedTransferFrom(erc20Token, customer, customer2, smallAmount, {'from': customer2})
    assert tx.return_value == False

    print('--- test unsufficient balance for erc20TokenAlternative and erc20Token ---')

    # check revert for unsufficient balance
    erc20TokenAlternative.approve(customer2, tooBigAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20TokenAlternative, customer, customer2, tooBigAmount, {'from': customer2})
    assert tx.return_value == False

    # check revert for unsufficient balance
    erc20Token.approve(customer2, tooBigAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20Token, customer, customer2, tooBigAmount, {'from': customer2})
    assert tx.return_value == False

