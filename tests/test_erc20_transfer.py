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
    tx = erc20TokenAlternative.transferFrom(customer, customer2, smallAmount, {'from': customer2})

    assert tx.return_value
    assert erc20TokenAlternative.balanceOf(customer2) == balanceCustomer2 + smallAmount

    # check outcome for unsufficient allowance
    tx = erc20TokenAlternative.transferFrom(customer, customer2, smallAmount, {'from': customer2})
    assert tx.return_value == False

    # check revert for unsufficient balance
    tooBigAmount = INITIAL_FUNDING + smallAmount
    erc20TokenAlternative.approve(customer2, tooBigAmount, {'from': customer})

    tx = erc20TokenAlternative.transferFrom(customer, customer2, tooBigAmount, {'from': customer2})
    assert tx.return_value == False

def test_unified_transfer_from_happy_path(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):

    (transferrer, smallAmount, tooBigAmount
    ) = _create_transferrer_with_unified_setup(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)

    # check happy path for erc20Token 
    erc20Token.approve(transferrer, smallAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20Token, customer, customer2, smallAmount, {'from': customer2})
    _print_transfer_from_info(tx, 'erc20Token', erc20Token, customer, customer2, transferrer)

    assert tx.return_value
    assert erc20Token.balanceOf(customer2) == INITIAL_FUNDING + smallAmount
    assert 'Approval' in tx.events
    assert 'Transfer' in tx.events
    assert 'LogTransferHelperInputValidation1Failed' not in tx.events
    assert 'LogTransferHelperInputValidation2Failed' not in tx.events

    # check happy path for erc20TokenAlternative 
    erc20TokenAlternative.approve(transferrer, smallAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20TokenAlternative, customer, customer2, smallAmount, {'from': customer2})

    _print_transfer_from_info(tx, 'erc20TokenAlternative', erc20TokenAlternative, customer, customer2, transferrer)

    assert tx.return_value
    assert erc20TokenAlternative.balanceOf(customer2) == INITIAL_FUNDING + smallAmount
    assert 'Approval' in tx.events
    assert 'Transfer' in tx.events
    assert 'LogTransferHelperInputValidation1Failed' not in tx.events
    assert 'LogTransferHelperInputValidation2Failed' not in tx.events


def test_unified_transfer_from_bad_allowance(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):

    (transferrer, smallAmount, tooBigAmount
    ) = _create_transferrer_with_unified_setup(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)
    
    # check outcome erc20TokenAlternative for unsufficient allowance
    tx = transferrer.unifiedTransferFrom(erc20TokenAlternative, customer, customer2, smallAmount, {'from': customer2})
    assert tx.return_value == False
    assert erc20TokenAlternative.balanceOf(customer2) == INITIAL_FUNDING
    assert 'Approval' not in tx.events
    assert 'Transfer' not in tx.events
    assert 'LogTransferHelperInputValidation1Failed' not in tx.events
    assert 'LogTransferHelperInputValidation2Failed' in tx.events
    
    # check erc20Token outcome for unsufficient allowance
    tx = transferrer.unifiedTransferFrom(erc20Token, customer, customer2, smallAmount, {'from': customer2})
    assert tx.return_value == False
    assert erc20TokenAlternative.balanceOf(customer2) == INITIAL_FUNDING
    assert 'Approval' not in tx.events
    assert 'Transfer' not in tx.events
    assert 'LogTransferHelperInputValidation1Failed' not in tx.events
    assert 'LogTransferHelperInputValidation2Failed' in tx.events


def test_unified_transfer_from_bad_balance(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):

    (transferrer, smallAmount, tooBigAmount
    ) = _create_transferrer_with_unified_setup(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)

    # check revert for unsufficient balance
    erc20TokenAlternative.approve(customer2, tooBigAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20TokenAlternative, customer, customer2, tooBigAmount, {'from': customer2})
    assert tx.return_value == False
    assert erc20TokenAlternative.balanceOf(customer2) == INITIAL_FUNDING
    assert 'Approval' not in tx.events
    assert 'Transfer' not in tx.events
    assert 'LogTransferHelperInputValidation1Failed' not in tx.events
    assert 'LogTransferHelperInputValidation2Failed' in tx.events

    # check revert for unsufficient balance
    erc20Token.approve(customer2, tooBigAmount, {'from': customer})
    tx = transferrer.unifiedTransferFrom(erc20Token, customer, customer2, tooBigAmount, {'from': customer2})
    assert tx.return_value == False
    assert erc20Token.balanceOf(customer2) == INITIAL_FUNDING
    assert 'Approval' not in tx.events
    assert 'Transfer' not in tx.events
    assert 'LogTransferHelperInputValidation1Failed' not in tx.events
    assert 'LogTransferHelperInputValidation2Failed' in tx.events


def _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):
    erc20Token.transfer(customer, INITIAL_FUNDING, {'from': instanceOperator})
    erc20Token.transfer(customer2, INITIAL_FUNDING, {'from': instanceOperator})

    erc20TokenAlternative.transfer(customer, INITIAL_FUNDING, {'from': instanceOperator})
    erc20TokenAlternative.transfer(customer2, INITIAL_FUNDING, {'from': instanceOperator})


def _create_transferrer_with_unified_setup(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2):

    _distribute_funds(erc20Token, erc20TokenAlternative, instanceOperator, customer, customer2)
    assert erc20Token.balanceOf(customer2) == INITIAL_FUNDING
    assert erc20TokenAlternative.balanceOf(customer2) == INITIAL_FUNDING

    transferrer = TestTransferFrom.deploy({'from': instanceOperator})
    smallAmount = 100
    tooBigAmount = 100

    return (transferrer, smallAmount, tooBigAmount)


def _print_transfer_from_info(tx, tokenName, token, customer, customer2, transferrer):
    print('token: {} ({})'.format(tokenName, token))
    print('customer: {}'.format(customer))
    print('customer2: {}'.format(customer2))
    print('transferrer: {}'.format(transferrer))
    print('tx.info(): {}'.format(tx.info()))
    print('tx.return_value: {}'.format(tx.return_value))
    print('balance(customer2): {}'.format(token.balanceOf(customer2)))

