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
    premium = Wei("1.0 ether");

    # record balances before policy creation
    customer_balance_before = customer.balance()
    product_balance_before = testProduct.balance()
    product_policies_before = testProduct.policies()

    # create policy
    policy_tx = testProduct.applyForPolicy({'from': customer, 'amount': premium})
    policy_id = policy_tx.return_value

    # record balances after policy creation
    customer_balance_after = customer.balance()
    product_balance_after = testProduct.balance()
    product_policies_after = testProduct.policies()

    assert not policy_tx is None
    assert policy_id == '0x76c2e3b708d8fcc307d69c21a89f15c54e99ccd4744e4227151d7e488eb2ebae'

    assert product_policies_before == 0
    assert product_policies_after == 1

    # ensure premium amount is subtracted from customer account
    assert customer_balance_before - premium == customer_balance_after
    # ensure premium amount is added to product after policy creation
    assert product_balance_before + premium == product_balance_after

    policyController = instance.getPolicyController()
    policy = policyController.getPolicy(policy_id)
    assert policy is not None
    # assert policy.state == 7


def test_claim_submission(testProduct: TestProduct, customer: Account):
    customer_initial_balance = customer.balance()
    premium = Wei('0.5 ether');

    # create 1st policy
    policy1_tx = testProduct.applyForPolicy({'from': customer, 'amount': premium})
    policy1_id = policy1_tx.return_value
    
    assert policy1_id is not None 
    assert customer.balance() + premium == customer_initial_balance
    assert testProduct.balance() == premium

    # ensure successful policy creation
    assert testProduct.policies() == 1
    assert testProduct.claims() == 0
    
    # submit claim for 1st policy
    claim_tx = testProduct.submitClaim(policy1_id, {'from': customer})
    assert testProduct.claims() == 1
    assert testProduct.getClaimId(policy1_id) == 0

    claim2_tx = testProduct.submitClaim(policy1_id, {'from': customer})
    assert testProduct.claims() == 2
    assert testProduct.getClaimId(policy1_id) == 0


def multiple_claim_submission(testProduct: TestProduct, customer: Account):
    customer_initial_balance = customer.balance()
    premium = Wei('0.5 ether');

    # create 1st policy
    policy1_tx = testProduct.applyForPolicy({'from': customer, 'amount': premium})
    policy1_id = policy1_tx.return_value
    
    assert policy1_id is not None 
    assert customer.balance() + premium == customer_initial_balance
    assert testProduct.balance() == premium

    # create 2nd policy
    policy2_tx = testProduct.applyForPolicy({'from': customer, 'amount': premium})
    policy2_id = policy2_tx.return_value
    
    assert policy2_id is not None 
    assert policy1_id != policy2_id
    assert customer.balance() + 2 * premium == customer_initial_balance
    assert testProduct.balance() == 2 * premium

    # ensure successful policy creation
    assert testProduct.policies() == 2
    assert testProduct.claims() == 0
    
    # submit claim for 1st policy
    testProduct.submitClaim(policy1_id, {'from': customer})
    assert testProduct.claims() == 1
    assert testProduct.getClaimId(policy1_id) == 0
    
    # submit claim for 1st policy
    testProduct.submitClaim(policy2_id, {'from': customer})
    assert testProduct.claims() == 2
    assert testProduct.getClaimId(policy2_id) == 0


