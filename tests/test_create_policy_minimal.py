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


def test_create_policy(
    instance: GifInstance, 
    testProduct: TestProduct, 
    customer: Account
):
    # record number of policies before policy creation
    product_policies_before = testProduct.policies()

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

    assert product_policies_before == 0
    assert product_policies_after == 1

    policyController = instance.getPolicyController()
    policy = policyController.getPolicy(policy_id)
    assert policy is not None

    # TODO add checks for owner, policy state, premium and sum insured
