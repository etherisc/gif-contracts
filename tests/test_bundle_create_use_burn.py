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

def test_create_bundle(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000

    fund_riskpool(instance, owner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    riskpool.bundles() == 1
    bundle = riskpool.getBundle(0)

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

    print(bundle)
    capitalFee = initialFunding / 20 +42
    bundleExpectedCapital = initialFunding - capitalFee

    # check bundle values with expectation
    assert bundleId == 1
    assert riskpoolId == riskpool.getId()
    assert tokenId == 1
    assert state == 0 # BundleState { Active, Locked, Closed }
    assert filter == '0x'
    assert capital == bundleExpectedCapital
    assert lockedCapital == 0
    assert balance == bundleExpectedCapital
    assert createdAt > 0
    assert updatedAt >= createdAt

    # check associated nft
    bundleToken = instance.getBundleToken()

    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False
    assert bundleToken.ownerOf(tokenId) == riskpoolKeeper
    assert bundleToken.getBundleId(tokenId) == bundleId

    # check riskpool and bundle are consistent
    assert riskpool.getCapital() == capital
    assert riskpool.getTotalValueLocked() == lockedCapital
    assert riskpool.getBalance() == balance


def test_use_bundle(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000

    fund_riskpool(instance, owner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    riskpool.bundles() == 1
    bundle = riskpool.getBundle(0)

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

    print(bundle)

    capitalFee = initialFunding / 20 + 42
    bundleExpectedCapital = initialFunding - capitalFee

    premiumFee = premium / 10 + 3
    premiumAfterFee = premium - premiumFee

    # check bundle values with expectation
    assert bundleId == 1
    assert riskpoolId == riskpool.getId()
    assert tokenId == 1
    assert state == 0 # BundleState { Active, Locked, Closed }
    assert filter == '0x'
    assert capital == bundleExpectedCapital
    assert lockedCapital == sumInsured
    assert balance == bundleExpectedCapital + premiumAfterFee
    assert createdAt > 0
    assert updatedAt >= createdAt

    # check riskpool and bundle are consistent
    assert riskpool.getCapital() == capital
    assert riskpool.getTotalValueLocked() == lockedCapital
    assert riskpool.getBalance() == balance

    # check associated nft
    bundleToken = instance.getBundleToken()

    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False
    assert bundleToken.ownerOf(tokenId) == riskpoolKeeper
    assert bundleToken.getBundleId(tokenId) == bundleId


def test_close_bundle(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000

    fund_riskpool(instance, owner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
