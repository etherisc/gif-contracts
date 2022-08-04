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

def test_pause_unpause(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner,
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()

    instanceService = instance.getInstanceService()
    assert instanceService.getComponentState(riskpoolId) == 3

    initialFunding = 10000
    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding)

    riskpool.bundles() == 1
    bundle = riskpool.getBundle(0)
    print(bundle)

    (
        bundleId,
        riskpoolId,
        tokenId,
        state,
        filter,
        capital,
        lockedCapital,
        balance,
        createdAt,
        updatedAt
    ) = bundle

    # check bundle values with expectation
    assert bundleId == 1
    assert riskpoolId == riskpool.getId()

    # verify that attributes directly from riskpool match with 
    # bundle attributes from instance service
    bundleFromCore = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundleFromCore["id"] == bundleId
    assert bundleFromCore["riskpoolId"] == riskpoolId
    assert bundleFromCore["tokenId"] == tokenId
    assert bundleFromCore["state"] == state
    assert bundleFromCore["filter"] == filter
    assert bundleFromCore["capital"] == capital
    assert bundleFromCore["lockedCapital"] == lockedCapital
    assert bundleFromCore["balance"] == balance
    assert bundleFromCore["createdAt"] == createdAt
    assert bundleFromCore["updatedAt"] == updatedAt

    componentOwnerService = instance.getComponentOwnerService()

    # create test policy before riskpool is paused
    product = gifTestProduct.getContract()
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, 100, 1000)

    # ensure that owner may not pause riskpool
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.pause(riskpoolId, {'from':owner})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpool keeper may pause riskpool
    componentOwnerService.pause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that riskpool actions are blocked for paused riskpool
    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.fundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.lockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.unlockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.closeBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.burnBundle(bundleId, {'from':bundleOwner})

    # ensure underwriting new policies is not possible for paused riskpool
    with brownie.reverts("ERROR:POL-021:RISKPOOL_NOT_ACTIVE"):
        policyId2 = apply_for_policy(instance, owner, product, customer, testCoin, 100, 1000)

    # ensure existing policies may be closed while riskpool is paused
    product.expire(policyId, {'from': productOwner})
    product.close(policyId, {'from': productOwner})

    # recored state of bundle 
    bundleAftePolicy = instanceService.getBundle(bundleId).dict()

    # ensure that owner may not unpause riskpool
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.unpause(riskpoolId, {'from':owner})

    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that riskpool keeper may unpause riskpool
    componentOwnerService.unpause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpol actions work again
    riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})

    bundleDefunded = instanceService.getBundle(bundleId).dict()
    assert bundleDefunded["balance"] == bundleAftePolicy["balance"] - 10

    tx = riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})
    bundle2Id = tx.return_value
    bundle2 = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundle2Id == bundleId + 1

