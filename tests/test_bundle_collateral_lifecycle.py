import brownie
import pytest

from web3 import Web3

from brownie.network.account import Account
from brownie import (
    interface,
    Wei,
    TestProduct,
)

from scripts.util import (
    s2h,
    s2b32,
)

from scripts.setup import (
    fund_riskpool,
    apply_for_policy,
)

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestProduct,
    GifTestRiskpool,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_apply_decline(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    expectedBalance = 0.95 * initialFunding - 42
    expectedCapital = expectedBalance
    expectedLockedCapital = 0

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['id'] == bundleId
    assert bundle['riskpoolId'] == riskpool.getId()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    # create application
    (premium, sumInsured) = 50, 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin, approve=True)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    product.decline(processId)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance


def test_apply_revoke(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    expectedBalance = 0.95 * initialFunding - 42
    expectedCapital = expectedBalance
    expectedLockedCapital = 0

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    # create application
    (premium, sumInsured) = 50, 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin, approve=False)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    product.revoke(processId, {'from': customer})

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance


def test_apply_underwrite(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    expectedBalance = 0.95 * initialFunding - 42
    expectedCapital = expectedBalance
    expectedLockedCapital = 0

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    (premium, sumInsured) = 50, 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin, approve=False)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    product.underwrite(processId, {'from': productOwner})
    expectedLockedCapital = sumInsured

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance


def test_collect_premium(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    initialFunding = 10000
    (premium, sumInsured) = (50, 1000)
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin, approve=False)
    product.underwrite(processId, {'from': productOwner})

    expectedBalance = 0.95 * initialFunding - 42
    expectedCapital = expectedBalance
    expectedLockedCapital = sumInsured

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    testCoin.approve(instance.getTreasury(), premium, {'from': customer})
    tx = product.collectPremium(processId, {'from': productOwner})
    print(tx.events)

    netPremium = 0.9 * premium - 3
    expectedBalance += netPremium

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    # add another policy
    (premium2, sumInsured2) = (10, 500)
    netPremium2 = 0.9 * premium2 - 3
    
    processId2 = create_policy(customer, premium2, sumInsured2, instance, owner, product, testCoin)

    expectedBalance += netPremium2
    expectedLockedCapital += sumInsured2
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance


def test_create_claim(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    initialFunding = 10000
    (premium, sumInsured) = (50, 1000)
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)
    processId = create_policy(customer, premium, sumInsured, instance, owner, product, testCoin)

    netCapital = 0.95 * initialFunding - 42
    netPremium = 0.9 * premium - 3
    expectedCapital = netCapital
    expectedLockedCapital = sumInsured
    expectedBalance = netCapital + netPremium

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    (claim1, claim2, claim3) = (0, 150, sumInsured - 150)
    
    claimAmount = 50
    claimId = create_claim_no_oracle(product, customer, productOwner, processId, claimAmount)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    tx = product.newPayout(processId, claimId, claimAmount)
    payoutId = tx.return_value

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    tx = product.processPayout(processId, payoutId)

    expectedCapital -= claimAmount
    expectedLockedCapital -= claimAmount
    expectedBalance -= claimAmount

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    claimAmount2 = 100
    (claimId2, payoutId2) = create_claim_with_payout(product, customer, productOwner, processId, claimAmount2)

    expectedCapital -= claimAmount2
    expectedLockedCapital -= claimAmount2
    expectedBalance -= claimAmount2

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance


def test_expire_close_medium_claim(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    initialFunding = 10000
    (premium, sumInsured) = (50, 1000)
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)
    processId = create_policy(customer, premium, sumInsured, instance, owner, product, testCoin)

    netCapital = 0.95 * initialFunding - 42
    netPremium = 0.9 * premium - 3
    expectedCapital = netCapital
    expectedLockedCapital = sumInsured
    expectedBalance = netCapital + netPremium

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    claimAmount = sumInsured / 2
    (claimId2, payoutId2) = create_claim_with_payout(product, customer, productOwner, processId, claimAmount)

    expectedCapital -= claimAmount
    expectedLockedCapital -= claimAmount
    expectedBalance -= claimAmount

    assert expectedLockedCapital == sumInsured / 2

    product.expire(processId)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    product.close(processId)

    expectedLockedCapital = 0
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance


def test_expire_close_max_claim(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    initialFunding = 10000
    (premium, sumInsured) = (50, 1000)
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)
    processId = create_policy(customer, premium, sumInsured, instance, owner, product, testCoin)

    netCapital = 0.95 * initialFunding - 42
    netPremium = 0.9 * premium - 3
    expectedCapital = netCapital
    expectedLockedCapital = sumInsured
    expectedBalance = netCapital + netPremium

    bundleId = _getBundleDict(instanceService, riskpool, 0)['id'] 
    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    claimAmount = sumInsured
    (claimId2, payoutId2) = create_claim_with_payout(product, customer, productOwner, processId, claimAmount)

    expectedCapital -= claimAmount
    expectedLockedCapital -= claimAmount
    expectedBalance -= claimAmount

    assert expectedLockedCapital == 0

    product.expire(processId)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance

    product.close(processId)

    bundle = instanceService.getBundle(bundleId).dict()
    assert bundle['state'] == 0
    assert bundle['capital'] == expectedCapital
    assert bundle['lockedCapital'] == expectedLockedCapital
    assert bundle['balance'] == expectedBalance



def create_claim_no_oracle(product, customer, productOwner, processId, claimAmount):
    tx = product.submitClaimNoOracle(processId, claimAmount, {'from':customer})
    claimId = tx.return_value
    product.confirmClaim(processId, claimId, claimAmount, {'from':productOwner})
    return claimId


def create_claim_with_payout(product, customer, productOwner, processId, claimAmount):
    tx = product.submitClaimNoOracle(processId, claimAmount, {'from':customer})
    claimId = tx.return_value

    product.confirmClaim(processId, claimId, claimAmount, {'from':productOwner})
    tx = product.createPayout(processId, claimId, claimAmount, {'from':productOwner})
    payoutId = tx.return_value

    return (claimId, payoutId)


def create_policy(customer, premium, sumInsured, instance, owner, product, erc20token):
    erc20token.transfer(customer, premium, {'from': owner})
    erc20token.approve(instance.getTreasury(), premium, {'from': customer})

    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        bytes(0),
        bytes(0),
        {'from': customer})

    processId = policy_tx.return_value
    return processId


def create_application(customer, premium, sumInsured, instance, owner, product, erc20token, approve=True, printTx=False):
    erc20token.transfer(customer, premium, {'from': owner})

    if approve:
        erc20token.approve(instance.getTreasury(), premium, {'from': customer})

    # create policy
    policy_tx = product.newAppliation(
        premium,
        sumInsured,
        bytes(0),
        bytes(0),
        {'from': customer})

    if printTx:
        print(policy_tx.info())        

    processId = policy_tx.return_value
    return processId


def _getBundleDict(instanceService, riskpool, bundleIdx):
    return _getBundle(instanceService, riskpool, bundleIdx).dict()

def _getBundle(instanceService, riskpool, bundleIdx):
    bundleId = riskpool.getBundleId(bundleIdx)
    return instanceService.getBundle(bundleId)