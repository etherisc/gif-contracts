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

    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

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
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

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


def test_close_and_burn_bundle(
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

    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding)

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    bundle = _getBundleDict(riskpool, 0)
    bundleId = bundle['id']
    bundleCapital = bundle['capital']
    bundleBalance = bundle['balance']

    product.expire(policyId, {'from': productOwner})

    assert _getBundleDict(riskpool, 0)['lockedCapital'] == sumInsured
    assert _getBundleDict(riskpool, 0)['balance'] == bundleBalance

    # check that bundle may not be closed with non-closed policies
    with brownie.reverts('ERROR:BUC-001:NOT_BUNDLE_OWNER'):
        riskpool.closeBundle(bundleId, {'from': owner})

    with brownie.reverts('ERROR:BUC-015:BUNDLE_WITH_ACTIVE_POLICIES'):
        riskpool.closeBundle(bundleId, {'from': bundleOwner})

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
    with brownie.reverts('ERROR:BUC-001:NOT_BUNDLE_OWNER'):
        riskpool.closeBundle(bundleId, {'from': owner})
    
    riskpool.closeBundle(bundleId, {'from': bundleOwner})

    bundle = _getBundleDict(riskpool, 0)
    assert bundle['state'] == 2 # BundleState { Active, Locked, Closed, Burned }
    assert bundle['capital'] == bundleCapital
    assert bundle['lockedCapital'] == 0
    assert bundle['balance'] == bundleBalance

    # check associated nft
    bundleToken = instance.getBundleToken()
    tokenId = bundle['tokenId']

    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False
    assert bundleToken.ownerOf(tokenId) == bundleOwner
    assert bundleToken.getBundleId(tokenId) == bundleId
    
    # check that defunding works even when bundle is closed
    riskpoolWalletBefore = testCoin.balanceOf(capitalOwner)
    bundleOwnerBefore = testCoin.balanceOf(bundleOwner)

    withdrawalAmount = 999
    tx = riskpool.defundBundle(bundleId, withdrawalAmount, {'from': bundleOwner})
    (success, netWithdrawalAmount) = tx.return_value

    assert success
    assert netWithdrawalAmount == withdrawalAmount

    expectedBalance = bundleBalance - netWithdrawalAmount
    bundle = _getBundleDict(riskpool, 0)
    assert bundle['capital'] == bundleCapital - netWithdrawalAmount
    assert bundle['balance'] == expectedBalance

    assert testCoin.balanceOf(capitalOwner) == expectedBalance
    assert testCoin.balanceOf(bundleOwner) == bundleOwnerBefore + netWithdrawalAmount

    # check that close results in blocking all other actions on the bundle
    with brownie.reverts('ERROR:BUC-052:CLOSED_INVALID_TRANSITION'):
        riskpool.closeBundle(bundleId, {'from': bundleOwner})

    with brownie.reverts('ERROR:BUC-052:CLOSED_INVALID_TRANSITION'):
        riskpool.lockBundle(bundleId, {'from': bundleOwner})

    with brownie.reverts('ERROR:BUC-052:CLOSED_INVALID_TRANSITION'):
        riskpool.unlockBundle(bundleId, {'from': bundleOwner})

    with brownie.reverts('ERROR:RPS-003:BUNDLE_CLOSED'):
        fundingAmount = 100000
        riskpool.fundBundle(bundleId, fundingAmount, {'from': bundleOwner})

    # attempt to burn bundle with imposter
    with brownie.reverts('ERROR:BUC-001:NOT_BUNDLE_OWNER'):
        riskpool.burnBundle(bundleId, {'from': customer})

    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False
    assert bundleToken.ownerOf(tokenId) == bundleOwner
    assert bundleToken.getBundleId(tokenId) == bundleId
    
    bundle = _getBundleDict(riskpool, 0)
    print(bundle)

    # bundle owner buring her/his token
    riskpool.burnBundle(bundleId, {'from': bundleOwner})

    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == True
    assert bundleToken.getBundleId(tokenId) == bundleId

    with brownie.reverts('ERC721: invalid token ID'):
        bundleToken.ownerOf(tokenId) == bundleOwner

    bundle = _getBundleDict(riskpool, 0)
    assert bundle['capital'] == 0
    assert bundle['lockedCapital'] == 0
    assert bundle['balance'] == 0

    assert riskpool.getCapital() == 0
    assert riskpool.getTotalValueLocked() == 0
    assert riskpool.getBalance() == 0

    assert testCoin.balanceOf(capitalOwner) == 0


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
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000

    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding)

    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    bundle = _getBundleDict(riskpool, 0)
    bundleId = bundle['id']
    bundleCapital = bundle['capital']
    bundleBalance = bundle['balance']

    assert riskpool.getBalance() == bundleBalance
    assert testCoin.balanceOf(capitalOwner) == bundleBalance

    withdrawalAmount = 999
    # (success, netWithdrawlAmount) = riskpool.defundBundle(bundleId, withdrawalAmount, {'from': bundleOwner})
    tx = riskpool.defundBundle(bundleId, withdrawalAmount, {'from': bundleOwner})
    (success, netWithdrawlAmount) = tx.return_value

    assert success
    assert netWithdrawlAmount == withdrawalAmount

    bundle = _getBundleDict(riskpool, 0)
    expectedCapital = bundleCapital - netWithdrawlAmount
    expectedBalance = bundleBalance - netWithdrawlAmount
    assert bundle['capital'] == expectedCapital
    assert bundle['balance'] == expectedBalance
    assert riskpool.getCapital() == expectedCapital
    assert riskpool.getBalance() == expectedBalance
    assert testCoin.balanceOf(capitalOwner) == expectedBalance

    fundingAmount = 2000
    tx = riskpool.fundBundle(bundleId, fundingAmount, {'from': bundleOwner})
    (success, netFundingAmount) = tx.return_value

    assert success
    assert netFundingAmount == fundingAmount - (fundingAmount / 20 + 42)

    bundle = _getBundleDict(riskpool, 0)
    expectedCapital = bundleCapital - netWithdrawlAmount + netFundingAmount
    expectedBalance = bundleBalance - netWithdrawlAmount + netFundingAmount
    assert bundle['capital'] == expectedCapital
    assert bundle['balance'] == expectedBalance
    assert riskpool.getCapital() == expectedCapital
    assert riskpool.getBalance() == expectedBalance
    assert testCoin.balanceOf(capitalOwner) == expectedBalance


def _getApplicationDict(instance, policyId):
    policyController = instance.getPolicy()
    return policyController.getApplication(policyId).dict()

def _getPolicyDict(instance, policyId):
    policyController = instance.getPolicy()
    return policyController.getPolicy(policyId).dict()

def _getBundleDict(riskpool, bundleId):
    return riskpool.getBundle(bundleId).dict()
