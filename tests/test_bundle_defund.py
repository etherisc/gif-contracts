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

def test_fund_defund_simple(
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

    riskpoolWallet = capitalOwner
    investor = riskpoolKeeper
    fund_riskpool(instance, owner, riskpoolWallet, riskpool, investor, testCoin, initialFunding)

    assert riskpool.bundles() == 1
    bundle = _getBundle(instance, riskpool, 0)
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

    riskpoolWalletBalanceBeforeDefunding = testCoin.balanceOf(riskpoolWallet)
    investorBalanceBeforeDefunding = testCoin.balanceOf(investor)
    bundleBalanceBeforeDefunding = balance

    assert capital == balance
    assert bundleBalanceBeforeDefunding == riskpoolWalletBalanceBeforeDefunding

    riskpool.defundBundle(bundleId, bundleBalanceBeforeDefunding, {'from':investor})

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
    ) = _getBundle(instance, riskpool, 0)

    assert capital == 0
    assert balance == 0

    assert testCoin.balanceOf(riskpoolWallet) == 0
    assert testCoin.balanceOf(investor) == investorBalanceBeforeDefunding + bundleBalanceBeforeDefunding


def test_fund_defund_with_policy(
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

    riskpoolWallet = capitalOwner
    investor = riskpoolKeeper
    fund_riskpool(instance, owner, riskpoolWallet, riskpool, investor, testCoin, initialFunding)

    assert riskpool.bundles() == 1
    bundle = _getBundle(instance, riskpool, 0)
    print('bundle after funding: {}'.format(bundle))

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

    # application spec
    premium = 100
    sumInsured = 5000
    metaData = s2b32('meta')
    applicationData = s2b32('application')

    # transfer funds to customer and create allowance
    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premium, {'from': customer})

    # create policy
    policy_tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})

    policyId = policy_tx.return_value

    print('bundle after premium: {}'.format(_getBundle(instance, riskpool, 0)))

    # expire and close policy to free locked capital in bundle
    product.expire(policyId)
    product.close(policyId)

    # record state before defunding
    bundleBeforeDefunding = _getBundle(instance, riskpool, 0)
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
    ) = bundleBeforeDefunding
    print('bundle after closing policy: {}'.format(bundleBeforeDefunding))

    riskpoolWalletBalanceBeforeDefunding = testCoin.balanceOf(riskpoolWallet)
    investorBalanceBeforeDefunding = testCoin.balanceOf(investor)
    bundleBalanceBeforeDefunding = balance

    # defund amount larger than capital
    defundAmount = balance
    assert defundAmount > capital # balance includes net premium, capital doesn't
    assert bundleBalanceBeforeDefunding == riskpoolWalletBalanceBeforeDefunding

    riskpool.defundBundle(bundleId, defundAmount, {'from':investor})

    bundleAfterDefunding = _getBundle(instance, riskpool, 0)
    print('bundle after defunding by {}: {}'.format(defundAmount, bundleAfterDefunding))

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
    ) = bundleAfterDefunding

    assert capital == 0
    assert balance == 0

    assert testCoin.balanceOf(riskpoolWallet) == 0
    assert testCoin.balanceOf(investor) == investorBalanceBeforeDefunding + defundAmount


def _getBundle(instance, riskpool, bundleIdx):
    instanceService = instance.getInstanceService()
    bundleId = riskpool.getBundleId(bundleIdx)
    return instanceService.getBundle(bundleId)
