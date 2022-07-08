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
    metaData = s2b32('')
    applicationData = s2b32('')

    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policy_id = policy_tx.return_value

    # record balances after policy creation
    product_policies_after = product.policies()

    assert product_policies_before == 0
    assert product_policies_after == 1

    policyController = instance.getPolicy()
    policy = policyController.getPolicy(policy_id)
    assert policy is not None

    # TODO add checks for owner, policy state, premium and sum insured
    assert riskpool.getCapacity() == initialFunding - sumInsured
