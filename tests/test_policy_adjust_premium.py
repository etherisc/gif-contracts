import pytest
import brownie

from brownie.network.account import Account
from brownie import (
    Wei,
)

from scripts.setup import (
    fund_riskpool,
)

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestProduct,
)

from scripts.util import (
    s2b32
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_adjust_premium(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, 2 * premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), 2 * premium, {'from': customer})

    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value


    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium

    # adjust premium of policy    
    adjustedPremium = 200
    tx = product.adjustPremiumSumInsured(processId, adjustedPremium, sumInsured, {'from': customer})

    # ensure the premium was adjusted
    assert 'LogApplicationPremiumAdjusted' in tx.events
    assert 'LogPolicyPremiumAdjusted' in tx.events

    assert 'LogApplicationSumInsuredAdjusted' not in tx.events

    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == adjustedPremium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == adjustedPremium
    assert policy['payoutMaxAmount'] == sumInsured


def test_adjust_sumInsured(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, 2 * premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), 2 * premium, {'from': customer})

    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value


    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium

    # adjust premium of policy    
    adjustedSumInsured = 4500
    tx = product.adjustPremiumSumInsured(processId, premium, adjustedSumInsured, {'from': customer})

    # ensure the premium was adjusted
    assert 'LogApplicationPremiumAdjusted' not in tx.events
    assert 'LogPolicyPremiumAdjusted' not in tx.events

    assert 'LogApplicationSumInsuredAdjusted' in tx.events

    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == adjustedSumInsured
    assert policy['premiumExpectedAmount'] == premium
    assert policy['payoutMaxAmount'] == adjustedSumInsured


def test_adjust_premium_and_sumInsured(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, 2 * premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), 2 * premium, {'from': customer})

    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value


    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium

    # adjust premium of policy    
    adjustedPremium = 200
    adjustedSumInsured = 4500
    tx = product.adjustPremiumSumInsured(processId, adjustedPremium, adjustedSumInsured, {'from': customer})

    # ensure the premium was adjusted
    assert 'LogApplicationPremiumAdjusted' in tx.events
    assert 'LogPolicyPremiumAdjusted' in tx.events

    assert 'LogApplicationSumInsuredAdjusted' in tx.events

    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == adjustedPremium
    assert application['sumInsuredAmount'] == adjustedSumInsured
    assert policy['premiumExpectedAmount'] == adjustedPremium
    assert policy['payoutMaxAmount'] == adjustedSumInsured


def test_adjust_premium_sumInsured_too_big(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, 2 * premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), 2 * premium, {'from': customer})

    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value

    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium

    # ensure adjustment cannot increase sum insured
    adjustSumInsured = 6000
    with brownie.reverts("ERROR:POC-026:APPLICATION_SUM_INSURED_INCREASE_INVALID"):
        product.adjustPremiumSumInsured(processId, premium, adjustSumInsured, {'from': customer})


def test_adjust_premium_premium_too_big(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account,
    insurer: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    premiumPaid = 50
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, 2 * premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), 50, {'from': customer})

    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value

    product.collectPremium(processId, premiumPaid)

    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premiumPaid

    # ensure adjustment cannot increase premium to amount > sumInsured
    adjustedPremium = 6000
    with brownie.reverts("ERROR:POC-025:APPLICATION_PREMIUM_INVALID"):
        product.adjustPremiumSumInsured(processId, adjustedPremium, sumInsured, {'from': customer})

    
    # ensure adjustment cannot decrease premium to amount < already paid amount
    adjustedPremium = 40
    with brownie.reverts("ERROR:POC-025:APPLICATION_PREMIUM_INVALID"):
        product.adjustPremiumSumInsured(processId, adjustedPremium, sumInsured, {'from': customer})
        

def test_adjust_premium_premium_too_small(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account,
    insurer: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    premiumPaid = 0
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    
    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value

    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premiumPaid

    # ensure adjustment cannot increase premium to amount > sumInsured
    adjustedPremium = 6000
    with brownie.reverts("ERROR:POC-025:APPLICATION_PREMIUM_INVALID"):
        product.adjustPremiumSumInsured(processId, adjustedPremium, sumInsured, {'from': customer})

    
    # ensure adjustment cannot decrease premium to amount < already paid amount
    adjustedPremium = 0
    with brownie.reverts("ERROR:POC-025:APPLICATION_PREMIUM_INVALID"):
        product.adjustPremiumSumInsured(processId, adjustedPremium, sumInsured, {'from': customer})
        

def test_adjust_premium_sumInsured_too_small(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account,
    insurer: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 15000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    
    # application spec
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, 2 * premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), 2 * premium, {'from': customer})

    # create policies
    process_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    processId = process_tx.return_value


    # check policy state
    policyController = instance.getPolicy()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert policy['premiumExpectedAmount'] == premium

    # adjust premium of policy    
    adjustedSumInsured = 50
    with brownie.reverts("ERROR:POC-025:APPLICATION_PREMIUM_INVALID"):
        tx = product.adjustPremiumSumInsured(processId, premium, adjustedSumInsured, {'from': customer})

