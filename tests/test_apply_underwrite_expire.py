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

def test_process_id_creation(
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

    instanceService = instance.getInstanceService()
    chainId = Web3().eth.chain_id
    registryAddress = instanceService.getRegistry()

    # compute expected process id values
    expectedProcessId1 = Web3.solidityKeccak(
        ['uint256', 'address', 'uint256'], 
        [chainId, registryAddress, product.policies() + 1]).hex()

    expectedProcessId2 = Web3.solidityKeccak(
        ['uint256', 'address', 'uint256'], 
        [chainId, registryAddress, product.policies() + 2]).hex()

    # create policies
    tx1 = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    tx2 = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    assert product.policies() == 2

    processId1 = tx1.return_value
    processId2 = tx2.return_value

    assert processId1 != expectedProcessId2
    assert processId1 == expectedProcessId1
    assert processId2 == expectedProcessId2



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
    assert metadata['state'] == 1
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
    assert policy['createdAt'] >= application['createdAt']
    assert policy['updatedAt'] >= policy['createdAt']

    instanceService = instance.getInstanceService()
    assert instanceService.payouts(policyId) == 0



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
    assert policy['updatedAt'] > policy['createdAt']

    instanceService = instance.getInstanceService()
    assert instanceService.payouts(policyId) == 0

    # check that policy can't be expired a 2nd time
    with brownie.reverts('ERROR:PFD-001:POLICY_NOT_ACTIVE'):
        product.expire(
            policyId,
            {'from': productOwner})

    # check that capacity remains at initial level
    assert product.policies() == 1
    assert riskpool.getCapacity() == capitalAfterCost


def test_application_with_delayed_premium_payment(
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
    assert product.applications() == 0
    assert product.policies() == 0

    # create minimal policy application
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # ensure policy creation is not possible
    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policyId = policy_tx.return_value

    assert product.applications() == 1
    assert product.policies() == 1

    # verify premium and sum insured
    policyController = instance.getPolicy()
    application = policyController.getApplication(policyId).dict()
    assert application['premiumAmount'] == premium
    assert application['sumInsuredAmount'] == sumInsured
    
    # verify that no premium is payed so far
    policy = policyController.getPolicy(policyId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == 0

    # transfer premium funds to customer and create allowance
    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premium, {'from': customer})

    # verify premium collection
    premium_tx = product.collectPremium(policyId)
    (success, fee, netPremium) = premium_tx.return_value
    assert success
    assert premium == fee + netPremium

    policy = policyController.getPolicy(policyId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premium



def test_application_with_premium_payment_in_bits(
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
    assert product.applications() == 0
    assert product.policies() == 0

    # create minimal policy application
    premium = 100
    sumInsured = 5000
    metaData = bytes(0)
    applicationData = bytes(0)

    # ensure policy creation is not possible
    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policyId = policy_tx.return_value

    assert product.applications() == 1
    assert product.policies() == 1
    
    # verify that no premium is payed so far
    policyController = instance.getPolicy()
    policy = policyController.getPolicy(policyId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == 0

    # transfer premium funds to customer and create allowance
    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premium, {'from': customer})

    # verify premium collection
    premiumPart1 = 20
    premiumPart2 = 50
    premiumPart3 = 30
    
    # 1st part
    premium_tx = product.collectPremium(policyId, premiumPart1)
    (success, fee, netPremium) = premium_tx.return_value
    assert success
    assert premiumPart1 == fee + netPremium

    policy = policyController.getPolicy(policyId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premiumPart1
    
    # 2nd part
    premium_tx = product.collectPremium(policyId, premiumPart2)
    (success, fee, netPremium) = premium_tx.return_value
    assert success
    assert premiumPart2 == fee + netPremium

    policy = policyController.getPolicy(policyId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premiumPart1 + premiumPart2
    
    # 3rd part
    premium_tx = product.collectPremium(policyId, premiumPart3)
    (success, fee, netPremium) = premium_tx.return_value
    assert success
    assert premiumPart3 == fee + netPremium

    policy = policyController.getPolicy(policyId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premiumPart1 + premiumPart2 + premiumPart3
    assert policy['premiumPaidAmount'] == policy['premiumExpectedAmount']


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
    with brownie.reverts('ERROR:POL-004:RISKPOOL_NOT_ACTIVE'):
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
