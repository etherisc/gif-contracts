import brownie
import pytest

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

# test for distribution of policies between the three bundles as two of them should be full at the end
def test_bundle_allocation_with_three_uneven_bundles(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    num_bundles = 3
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpool.setMaximumNumberOfActiveBundles(num_bundles, {'from': riskpoolKeeper})

    initialFunding = [10000, 2500, 1500]
    expectedAllocation = [6000, 2000, 1000]

    # fund the riskpools
    for i in range(num_bundles):
        fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding[i])
    
    assert num_bundles == riskpool.bundles()

    # allocate 3 policies in every bundle
    for _ in range(num_bundles * 3):
        apply_for_policy(instance, owner, product, customer, testCoin, 100, 1000)
    

    # ensure every bundle has same locked capital
    for i in range(num_bundles):
        # get updates bundle values
        bundle = _getBundle(instance, riskpool, i)
        (
            _,
            _,
            _,
            _,
            _,
            _,
            lockedCapital,
            *_
        ) = bundle

        assert expectedAllocation[i] == lockedCapital


def _getBundle(instance, riskpool, bundleIdx):
    instanceService = instance.getInstanceService()
    bundleId = riskpool.getBundleId(bundleIdx)
    return instanceService.getBundle(bundleId)
