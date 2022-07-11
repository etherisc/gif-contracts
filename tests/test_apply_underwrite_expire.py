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

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestProduct,
    GifTestRiskpool,
)


def test_create_policy(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    customer: Account
):
    # add bundle with funding to riskpool
    testRiskpool = gifTestProduct.getRiskpool()
    riskpool = testRiskpool.getContract()

    applicationFilter = bytes(0)
    initialFunding = 10000
    riskpool.createBundle(
        applicationFilter, 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 1
    assert riskpool.getCapacity() == initialFunding

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    product_policies_before = product.policies()

    # create policy
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policyId = policy_tx.return_value

    # record balances after policy creation
    product_policies_after = product.policies()

    assert riskpool.getCapacity() == initialFunding - sumInsured
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


def test_create_and_expire_policy(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    customer: Account
):
    # add bundle with funding to riskpool
    testRiskpool = gifTestProduct.getRiskpool()
    riskpool = testRiskpool.getContract()

    applicationFilter = bytes(0)
    initialFunding = 10000
    riskpool.createBundle(
        applicationFilter, 
        initialFunding, 
        {'from': riskpoolKeeper})

    # record number of policies before policy creation
    product = gifTestProduct.getContract()
    assert product.policies() == 0

    # create policy
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policyId = policy_tx.return_value

    # record balances after policy creation
    assert product.policies() == 1
    assert riskpool.getCapacity() == initialFunding - sumInsured

    # expire policy
    product.expire(
        policyId,
        {'from': productOwner})

    # check that capacity is restored to initial level
    assert product.policies() == 1
    assert riskpool.getCapacity() == initialFunding

    policyController = instance.getPolicy()
    policy = policyController.getPolicy(policyId).dict()

    # ensure policy data is updated properly
    assert policy is not None
    # PolicyState {Active, Expired}
    assert policy['state'] == 1
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
    assert riskpool.getCapacity() == initialFunding


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
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    customer: Account
):
    componentOwnerService = instance.getComponentOwnerService()
    gifRiskpool = gifTestProduct.getRiskpool()
    riskpool = gifRiskpool.getContract()
    product = gifTestProduct.getContract()

    # add bundle with funding to riskpool
    testRiskpool = gifTestProduct.getRiskpool()
    riskpool = testRiskpool.getContract()

    applicationFilter = bytes(0)
    initialFunding = 10000
    riskpool.createBundle(
        applicationFilter, 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 1
    assert riskpool.getCapacity() == initialFunding

    # ComponentState {Created,Proposed,Declined,Active,Paused,Suspended}
    assert product.policies() == 0
    assert riskpool.getState() == 3

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
    with brownie.reverts('ERROR:POL-005:RISKPOOL_NOT_ACTIVE'):
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
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    customer: Account
):
    product = gifTestProduct.getContract()

    # create bundle for riskpool with some capital but 
    # not enough to cover the application
    testRiskpool = gifTestProduct.getRiskpool()
    riskpool = testRiskpool.getContract()

    applicationFilter = bytes(0)
    initialFunding = 50
    riskpool.createBundle(
        applicationFilter, 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 1
    assert riskpool.getCapacity() == initialFunding
    assert product.applications() == 0
    assert product.policies() == 0
    
    # create policy: should not work as not enough collateral
    # is made available in the bundle
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    apply_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    assert product.applications() == 1
    assert product.policies() == 0
