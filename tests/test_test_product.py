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


def test_policy_application(instance: GifInstance, testProduct: TestProduct, customer: Account):

    # record balances before policy creation
    product_policies_before = testProduct.policies()

    # TODO record balacnes of customer and capital+fee owner before and after
    # policy application

    # create policy
    premium = 100
    sumInsured = 5000
    policy_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})

    policy_id = policy_tx.return_value

    # record balances after policy creation
    product_policies_after = testProduct.policies()

    assert not policy_tx is None
    assert policy_id == '0x76c2e3b708d8fcc307d69c21a89f15c54e99ccd4744e4227151d7e488eb2ebae'

    assert product_policies_before == 0
    assert product_policies_after == 1

    # TODO add assersion for token balances before and after policy application

    policyController = instance.getPolicyController()
    policy = policyController.getPolicy(policy_id)
    assert policy is not None


def test_policy_application_and_product_activation(instance: GifInstance, testProduct: TestProduct, customer: Account, productOwner: Account):
    # pause product
    productId = testProduct.getId()
    instance.getComponentOwnerService().pause(productId, {'from': productOwner})

    # check policy application for initial product state does not work
    premium = 100
    sumInsured = 5000
    with brownie.reverts():

        testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})

    assert testProduct.policies() == 0

    # unpause and try again
    instance.getComponentOwnerService().unpause(productId, {'from': productOwner})
    policy_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})

    assert testProduct.policies() == 1


def test_claim_submission(testProduct: TestProduct, customer: Account, productOwner: Account):
    premium = 100
    sumInsured = 5000

    # create 1st policy
    policy1_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})
    
    policy1_id = policy1_tx.return_value
    
    assert policy1_id is not None 

    # TODO verify balance after application
    assert customer.balance() + premium == customer_initial_balance
    assert testProduct.balance() == premium

    # ensure successful policy creation
    assert testProduct.policies() == 1
    assert testProduct.claims() == 0
    
    # TODO adapt tests for claims handling with riskpools
    # TODO implement claims handling

    # # only policy holder may sumit a claim
    # with brownie.reverts():
    #     testProduct.submitClaim(policy1_id, Wei('0.1 ether'), {'from': productOwner})

    # # submit claim
    # claim_tx = testProduct.submitClaim(policy1_id, Wei('0.1 ether'), {'from': customer})
    # assert testProduct.claims() == 1
    # assert testProduct.getClaimId(policy1_id) == 0


def test_claim_submission_for_expired_policy(testProduct: TestProduct, customer: Account, productOwner: Account):
    premium = 100
    sumInsured = 5000

    # create 1st policy
    policy_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})

    policy_id = policy_tx.return_value
    
    # only product owner may expire a policy
    with brownie.reverts():
        testProduct.expire(policy_id, {'from': customer})

    testProduct.expire(policy_id, {'from': productOwner})

    # attempt to submit a claim and verify attempt reverts
    with brownie.reverts():
        testProduct.submitClaim(policy_id, Wei('0.1 ether'), {'from': customer})


def test_multiple_claim_submission(instance:GifInstance, testProduct: TestProduct, customer: Account):
    premium = 100
    sumInsured = 5000

    # create 1st policy
    policy1_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})

    policy1_id = policy1_tx.return_value
    
    assert policy1_id is not None 
    assert customer.balance() + premium == customer_initial_balance
    assert testProduct.balance() == premium

    # create 2nd policy
    policy2_tx = testProduct.applyForPolicy(
        premium,
        sumInsured,
        {'from': customer})

    policy2_id = policy2_tx.return_value
    
    assert policy2_id is not None 
    assert policy1_id != policy2_id
    assert customer.balance() + 2 * premium == customer_initial_balance
    assert testProduct.balance() == 2 * premium

    instanceService = instance.getInstanceService()

    # ensure successful policy creation
    assert testProduct.policies() == 2
    assert testProduct.claims() == 0

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


