import brownie
import pytest

from brownie.network.account import Account
from brownie import (
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

def fund_riskpool(gifTestProduct: GifTestProduct, bundleOwner: Account):
    # add bundle with funding to riskpool
    testRiskpool = gifTestProduct.getRiskpool()
    riskpool = testRiskpool.getContract()

    applicationFilter = bytes(0)
    initialFunding = 10000

    riskpool.createBundle(
        applicationFilter, 
        initialFunding, 
        {'from': bundleOwner})


def test_policy_application_and_product_activation(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account
):
    fund_riskpool(gifTestProduct, riskpoolKeeper)
    
    # pause product
    testProduct = gifTestProduct.getContract()
    productId = testProduct.getId()
    instance.getComponentOwnerService().pause(productId, {'from': productOwner})

    # check policy application for initial product state does not work
    premium = 100
    sumInsured = 5000
    metaData = s2b32('')
    applicationData = s2b32('')

    with brownie.reverts():
        testProduct.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    assert testProduct.policies() == 0

    # unpause and try again
    instance.getComponentOwnerService().unpause(productId, {'from': productOwner})
    policy_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    assert testProduct.policies() == 1


def test_claim_submission(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account
):
    fund_riskpool(gifTestProduct, riskpoolKeeper)

    premium = 100
    sumInsured = 5000
    metaData = s2b32('')
    applicationData = s2b32('')

    # create 1st policy
    testProduct = gifTestProduct.getContract()
    policy1_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    
    policy1_id = policy1_tx.return_value
    
    assert policy1_id is not None 

    # TODO verify balance after application

    # ensure successful policy creation
    assert testProduct.policies() == 1
    assert testProduct.claims() == 0
    
    # TODO adapt tests for claims handling with riskpools
    # TODO implement claims handling

    # only policy holder may sumit a claim
    claimAmount = 300
    with brownie.reverts():
        testProduct.submitClaim(
            policy1_id, 
            claimAmount, 
            {'from': productOwner})

    # submit claim
    claim_tx = testProduct.submitClaim(
        policy1_id, 
        claimAmount, 
        {'from': customer})
    
    assert testProduct.claims() == 1
    assert testProduct.getClaimId(policy1_id) == 0


def test_claim_submission_for_expired_policy(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account
):
    fund_riskpool(gifTestProduct, riskpoolKeeper)

    premium = 100
    sumInsured = 5000
    metaData = s2b32('')
    applicationData = s2b32('')

    # create 1st policy
    testProduct = gifTestProduct.getContract()
    policy_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policy_id = policy_tx.return_value
    
    # only product owner may expire a policy
    with brownie.reverts():
        testProduct.expire(policy_id, {'from': customer})

    testProduct.expire(policy_id, {'from': productOwner})

    # attempt to submit a claim and verify attempt reverts
    with brownie.reverts():
        testProduct.submitClaim(policy_id, Wei('0.1 ether'), {'from': customer})


def test_multiple_claim_submission(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account
):
    fund_riskpool(gifTestProduct, riskpoolKeeper)

    premium = 100
    sumInsured = 5000
    metaData = s2b32('')
    applicationData = s2b32('')

    # create 1st policy
    testProduct = gifTestProduct.getContract()
    policy1_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policy1_id = policy1_tx.return_value
    
    assert policy1_id is not None 

    # TODO add assertions to check coin balance

    # create 2nd policy
    policy2_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policy2_id = policy2_tx.return_value
    
    assert policy2_id is not None 
    assert policy1_id != policy2_id
    
    # TODO add assertions to check coin balance

    # ensure successful policy creation
    assert testProduct.policies() == 2
    assert testProduct.claims() == 0

    instanceService = instance.getInstanceService()
    assert instanceService.claims(policy1_id) == 0
    assert instanceService.payouts(policy1_id) == 0
    assert instanceService.claims(policy2_id) == 0
    assert instanceService.payouts(policy2_id) == 0
    
    # submit claim for 1st policy
    testProduct.submitClaim(policy1_id, Wei('0.1 ether'), {'from': customer})
    assert testProduct.claims() == 1
    assert testProduct.getClaimId(policy1_id) == 0

    assert instanceService.claims(policy1_id) == 1
    assert instanceService.payouts(policy1_id) == 1
    assert instanceService.claims(policy2_id) == 0
    assert instanceService.payouts(policy2_id) == 0
    
    # submit claim for 1st policy (every 2nd claim does not have any payout)
    testProduct.submitClaim(policy2_id, Wei('0.1 ether'), {'from': customer})
    assert testProduct.claims() == 2
    assert testProduct.getClaimId(policy2_id) == 0

    assert instanceService.claims(policy1_id) == 1
    assert instanceService.payouts(policy1_id) == 1
    assert instanceService.claims(policy2_id) == 1
    assert instanceService.payouts(policy2_id) == 0
    
    # submit 2nd claim for 1st policy
    testProduct.submitClaim(policy1_id, Wei('0.1 ether'), {'from': customer})
    assert testProduct.claims() == 3
    assert testProduct.getClaimId(policy1_id) == 1

    assert instanceService.claims(policy1_id) == 2
    assert instanceService.payouts(policy1_id) == 2
    assert instanceService.claims(policy2_id) == 1
    assert instanceService.payouts(policy2_id) == 0


