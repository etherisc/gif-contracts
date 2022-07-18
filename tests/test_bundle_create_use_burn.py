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

    assert testCoin.balanceOf(feeOwner) == 0
    assert testCoin.balanceOf(capitalOwner) == 0

    initialFunding = 10000
    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    bundle = _getBundleDict(riskpool, 0)
    capitalFee = initialFunding / 20 + 42
    bundleExpectedCapital = initialFunding - capitalFee
    capitalOwnerBalance = testCoin.balanceOf(capitalOwner)
    feeOwnerBalance = testCoin.balanceOf(feeOwner)

    # ensure consistent capital amounts for bundle, riskpool and riskpool wallet
    assert bundle['capital'] == bundleExpectedCapital
    assert bundle['lockedCapital'] == 0
    assert bundle['balance'] == bundleExpectedCapital
    assert riskpool.getCapital() == bundleExpectedCapital
    assert riskpool.getTotalValueLocked() == 0
    assert riskpool.getBalance() == bundleExpectedCapital
    assert testCoin.balanceOf(capitalOwner) == bundleExpectedCapital
    assert testCoin.balanceOf(feeOwner) == capitalFee

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    bundle = _getBundleDict(riskpool, 0)
    print(bundle)

    premiumFee = premium / 10 + 3
    premiumAfterFee = premium - premiumFee

    # ensure consistent capital amounts for bundle, riskpool and riskpool wallet
    assert bundle['capital'] == bundleExpectedCapital
    assert bundle['lockedCapital'] == sumInsured
    assert bundle['balance'] == bundleExpectedCapital + premiumAfterFee
    assert riskpool.getCapital() == bundleExpectedCapital
    assert riskpool.getTotalValueLocked() == sumInsured
    assert riskpool.getBalance() == bundleExpectedCapital + premiumAfterFee
    assert testCoin.balanceOf(capitalOwner) == bundleExpectedCapital + premiumAfterFee
    assert testCoin.balanceOf(feeOwner) == capitalFee + premiumFee

    # check remaining bundle values against expectation
    bundleId = bundle['id']
    tokenId = bundle['tokenId']
    assert bundleId == 1
    assert tokenId == 1
    assert bundle['riskpoolId'] == riskpool.getId()
    assert bundle['state'] == 0 # BundleState { Active, Locked, Closed }
    assert bundle['filter'] == '0x'
    assert bundle['createdAt'] > 0
    assert bundle['updatedAt'] >= bundle['createdAt']

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
    productOwner: Account,
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

    bundle = _getBundleDict(riskpool, 0)
    bundleId = bundle['id']
    bundleBalance = bundle['balance']
    bundleCapital = bundle['capital']

    product.expire(policyId, {'from': productOwner})

    assert _getBundleDict(riskpool, 0)['lockedCapital'] == sumInsured
    assert _getBundleDict(riskpool, 0)['balance'] == bundleBalance

    # check that bundle may not be closed with non-closed policies
    with brownie.reverts('ERROR:BUC-015:BUNDLE_WITH_ACTIVE_POLICIES'):
        riskpool.closeBundle(bundleId)

    assert _getPolicyDict(instance, policyId)['state'] == 1

    bundle = _getBundleDict(riskpool, 0)
    bundleBalance = bundle['balance']
    assert bundle['state'] == 0
    assert bundle['capital'] == bundleCapital
    assert bundle['lockedCapital'] == sumInsured
    assert bundle['balance'] == bundleBalance
    
    product.close(policyId, {'from': productOwner})

    assert _getPolicyDict(instance, policyId)['state'] == 2
    bundle = _getBundleDict(riskpool, 0)
    assert bundle['state'] == 0
    assert bundle['capital'] == bundleCapital
    assert bundle['lockedCapital'] == 0
    assert bundle['balance'] == bundleBalance

    # check that is now ok to close the bundle
    riskpool.closeBundle(bundleId)

    bundle = _getBundleDict(riskpool, 0)
    assert bundle['state'] == 2 # BundleState { Active, Locked, Closed }
    assert bundle['capital'] == bundleCapital
    assert bundle['lockedCapital'] == 0
    assert bundle['balance'] == bundleBalance

    # check that close is final state
    with brownie.reverts('ERROR:BUC-014:CLOSED_IS_FINAL_STATE'):
        riskpool.closeBundle(bundleId)

    with brownie.reverts('ERROR:BUC-014:CLOSED_IS_FINAL_STATE'):
        riskpool.lockBundle(bundleId)

    with brownie.reverts('ERROR:BUC-014:CLOSED_IS_FINAL_STATE'):
        riskpool.unlockBundle(bundleId)


# TODO implement test
def test_fund_defund_bundle(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    productOwner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    pass


def _getApplicationDict(instance, policyId):
    policyController = instance.getPolicy()
    return policyController.getApplication(policyId).dict()

def _getPolicyDict(instance, policyId):
    policyController = instance.getPolicy()
    return policyController.getPolicy(policyId).dict()

def _getBundleDict(riskpool, bundleId):
    return riskpool.getBundle(bundleId).dict()
