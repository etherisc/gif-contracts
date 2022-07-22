import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    interface,
    Wei,
    TestProduct,
)

from scripts.const import (
    PRODUCT_NAME,
    PRODUCT_ID,
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

def test_create_policy(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # check funds after capitalization
    capitalFees = initialFunding / 20 + 42
    capitalAfterCost = initialFunding - capitalFees

    assert testCoin.balanceOf(feeOwner) == capitalFees
    assert testCoin.balanceOf(capitalOwner) == capitalAfterCost

    assert riskpool.bundles() == 1
    assert riskpool.getCapacity() == capitalAfterCost

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    product_policies_before = product.policies()
    
    # application spec
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premium, {'from': customer})

    # check funds before application
    balanceCustomerBefore = testCoin.balanceOf(customer)

    # create policy
    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policyId = policy_tx.return_value

    # check funds after application
    premiumFees = premium /10 + 3
    premiumAfterCost = premium - premiumFees

    balanceCustomerAfter = testCoin.balanceOf(customer)
    assert premium == balanceCustomerBefore - balanceCustomerAfter
    assert testCoin.balanceOf(feeOwner) == capitalFees + premiumFees
    assert testCoin.balanceOf(capitalOwner) == capitalAfterCost + premiumAfterCost

    # record balances after policy creation
    product_policies_after = product.policies()

    assert riskpool.getCapacity() == capitalAfterCost - sumInsured
    assert product_policies_before == 0
    assert product_policies_after == 1

    policyController = instance.getPolicy()
    metadata = policyController.getMetadata(policyId).dict()
    application = policyController.getApplication(policyId).dict()
    policy = policyController.getPolicy(policyId).dict()

    assert metadata is not None
    assert metadata['owner'] == customer
    assert metadata['productId'] == product.getId()
    # IPolicy.PolicyFlowState {Started, Paused, Finished}
    assert metadata['state'] == 0
    assert metadata['data'] == metaData
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 2
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    assert application['data'] == applicationData
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    assert policy is not None
    # PolicyState {Active, Expired}
    assert policy['state'] == 0
    assert policy['claimsCount'] == 0
    assert policy['payoutsCount'] == 0
    assert policy['createdAt'] >= application['createdAt']
    assert policy['updatedAt'] >= policy['createdAt']


def test_create_expire_and_close_policy(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    assert product.policies() == 0

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    assert policyId is not None 
    assert product.policies() == 1

    # check funds after capitalization
    capitalFees = initialFunding / 20 + 42
    capitalAfterCost = initialFunding - capitalFees

    # record balances after policy creation
    assert product.policies() == 1
    assert riskpool.getCapacity() == capitalAfterCost - sumInsured

    # close policy
    product.expire(policyId, {'from': productOwner})

    # PolicyState {Active, Expired, Closed}
    policy = _getPolicyDict(instance, policyId)
    assert policy['state'] == 1

    product.close(policyId, {'from': productOwner})

    # check that capacity is restored to initial level
    assert product.policies() == 1
    assert riskpool.getCapacity() == capitalAfterCost

    policy = _getPolicyDict(instance, policyId)
    assert policy['state'] == 2
    assert policy['claimsCount'] == 0
    assert policy['payoutsCount'] == 0
    assert policy['updatedAt'] > policy['createdAt']

    # check that policy can't be expired a 2nd time
    with brownie.reverts('ERROR:PFD-001:POLICY_NOT_ACTIVE'):
        product.expire(
            policyId,
            {'from': productOwner})

    # check that capacity remains at initial level
    assert product.policies() == 1
    assert riskpool.getCapacity() == capitalAfterCost

def test_application_with_insufficient_premium_funding(
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
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    assert product.policies() == 0

    premium = 100
    premiumHalf = premium/2
    sumInsured = 5000

    # transfer premium funds to customer and create allowance
    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premiumHalf, {'from': customer})

    # create minimal policy application
    metaData = bytes(0)
    applicationData = bytes(0)

    # ensure policy creation is not possible
    with brownie.reverts('ERROR:TRS-031:ALLOWANCE_SMALLER_THAN_PREMIUM'):
        policy_tx = product.applyForPolicy(
            premium,
            sumInsured,
            metaData,
            applicationData,
            {'from': customer})

    capitalFees = initialFunding / 20 + 42
    capitalAfterCost = initialFunding - capitalFees

    assert product.policies() == 0
    assert riskpool.getCapacity() == capitalAfterCost


def test_product_inactive(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    customer: Account
):
    componentOwnerService = instance.getComponentOwnerService()
    product = gifTestProduct.getContract()

    # ComponentState {Created,Proposed,Declined,Active,Paused,Suspended}
    assert product.policies() == 0
    assert product.getState() == 3

    componentOwnerService.pause(
        product.getId(), 
        {'from': productOwner})
    
    assert product.getState() == 4

    # create policy
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    # check that inactive product does not lead to policy creation
    with brownie.reverts('ERROR:PRS-001:NOT_AUTHORIZED'):
        apply_tx = product.applyForPolicy(
            premium,
            sumInsured,
            metaData,
            applicationData,
            {'from': customer})

    assert product.applications() == 0
    assert product.policies() == 0


def test_riskpool_inactive(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    owner: Account,
    riskpoolKeeper: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    assert riskpool.bundles() == 1

    product = gifTestProduct.getContract()
    # ComponentState {Created,Proposed,Declined,Active,Paused,Suspended}
    assert product.policies() == 0
    assert riskpool.getState() == 3

    componentOwnerService = instance.getComponentOwnerService()
    componentOwnerService.pause(
        riskpool.getId(), 
        {'from': riskpoolKeeper})
    
    assert riskpool.getState() == 4

    # create policy
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    # check that inactive product does not lead to policy creation
    with brownie.reverts('ERROR:POL-021:RISKPOOL_NOT_ACTIVE'):
        apply_tx = product.applyForPolicy(
            premium,
            sumInsured,
            metaData,
            applicationData,
            {'from': customer})

    assert product.applications() == 0
    assert product.policies() == 0


def test_empty_riskpool(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    customer: Account
):
    product = gifTestProduct.getContract()
    testRiskpool = gifTestProduct.getRiskpool()
    riskpool = testRiskpool.getContract()

    assert riskpool.bundles() == 0
    assert riskpool.getCapacity() == 0
    assert product.applications() == 0
    assert product.policies() == 0
    
    # create policy
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    with brownie.reverts('ERROR:BRP-001:NO_ACTIVE_BUNDLES'):
        apply_tx = product.applyForPolicy(
                premium,
                sumInsured,
                metaData,
                applicationData,
                {'from': customer})

    assert product.applications() == 0
    assert product.policies() == 0


def test_insufficient_capital(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    owner: Account,
    riskpoolKeeper: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 50
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    product = gifTestProduct.getContract()

    assert riskpool.bundles() == 1
    assert product.applications() == 0
    assert product.policies() == 0

    # build and use policy application
    product = gifTestProduct.getContract()
    assert product.policies() == 0

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    assert policyId is not None     
    assert product.applications() == 1
    assert product.policies() == 0


def _getPolicyDict(instance, policyId):
    policyController = instance.getPolicy()
    return policyController.getPolicy(policyId).dict()
