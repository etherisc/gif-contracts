import brownie
import pytest
import time

from brownie.network.account import Account
from brownie.network.state import Chain

from scripts.const import ZERO_ADDRESS
from scripts.instance import GifInstance
from scripts.product import GifTestOracle, GifTestProduct, GifTestRiskpool
from scripts.util import b2s

from scripts.setup import (
    apply_for_policy,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_bundle_creation_with_instance_wallet_not_set(
    instanceNoInstanceWallet: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
):
    withRiskpoolWallet = True
    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instanceNoInstanceWallet,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        withRiskpoolWallet
    )

    product = gifProduct.getContract()
    riskpool = gifRiskpool.getContract()
    riskpoolId = riskpool.getId()

    instanceService = instanceNoInstanceWallet.getInstanceService()
    assert instanceService.getInstanceWallet() == ZERO_ADDRESS 
    assert instanceService.getRiskpoolWallet(riskpoolId) == capitalOwner 

    bundleOwner = riskpoolKeeper
    treasury = instanceNoInstanceWallet.getTreasury()
    amount = 10000
    testCoin.transfer(bundleOwner, amount, {'from': owner})
    testCoin.approve(treasury, amount, {'from': bundleOwner})

    with brownie.reverts("ERROR:TRS-001:INSTANCE_WALLET_UNDEFINED"):
        applicationFilter = bytes(0)
        riskpool.createBundle(
            applicationFilter, 
            amount, 
            {'from': bundleOwner})

def test_bundle_creation_with_riskpool_wallet_not_set(
    instance: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    feeOwner: Account,
):
    withRiskpoolWallet = False
    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instance,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        withRiskpoolWallet
    )

    product = gifProduct.getContract()
    riskpool = gifRiskpool.getContract()
    riskpoolId = riskpool.getId()

    instanceService = instance.getInstanceService()
    assert instanceService.getInstanceWallet() == feeOwner 
    assert instanceService.getRiskpoolWallet(riskpoolId) == ZERO_ADDRESS 

    bundleOwner = riskpoolKeeper
    treasury = instance.getTreasury()
    amount = 10000
    testCoin.transfer(bundleOwner, amount, {'from': owner})
    testCoin.approve(treasury, amount, {'from': bundleOwner})

    with brownie.reverts("ERROR:TRS-003:RISKPOOL_WALLET_UNDEFINED"):
        applicationFilter = bytes(0)
        riskpool.createBundle(
            applicationFilter, 
            amount, 
            {'from': bundleOwner})

def test_bundle_creation_allowance_too_small(
    instance: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
):  
    applicationFilter = bytes(0)

    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instance,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        True
    )

    # prepare allowance too small for riskpool funding 
    safetyFactor = 2
    amount = 10000
    testCoin.transfer(riskpoolKeeper, safetyFactor * amount, {'from': owner})
    testCoin.approve(instance.getTreasury(), 0.9 * amount, {'from': riskpoolKeeper})

    # ensures bundle creation fails due to insufficient allowance
    with brownie.reverts("ERROR:TRS-055:CAPITAL_TRANSFER_FAILED"):
        gifRiskpool.getContract().createBundle(
                applicationFilter, 
                amount, 
                {'from': riskpoolKeeper})


def test_bundle_withdrawal_allowance_too_small(
    instance: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
):  
    applicationFilter = bytes(0)

    # prepare product and riskpool
    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instance,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        True
    )

    # fund bundle
    safetyFactor = 2
    amount = 10000
    testCoin.transfer(riskpoolKeeper, safetyFactor * amount, {'from': owner})
    testCoin.approve(instance.getTreasury(), amount, {'from': riskpoolKeeper})
    riskpool = gifRiskpool.getContract()

    riskpool.createBundle(
                applicationFilter, 
                amount, 
                {'from': riskpoolKeeper})

    bundle = riskpool.getBundle(0)
    print(bundle)

    (bundleId) = bundle[0]

    # check bundle values with expectation
    assert bundleId == 1

    # close bundle
    riskpool.closeBundle(bundleId, {'from': riskpoolKeeper})

    # prepare allowance that is too small for bundle withdrawal
    testCoin.approve(instance.getTreasury(), 0.9 * amount, {'from': riskpoolKeeper})

    # ensures that burning bundle fails during token withdrawal due to insufficient allowance
    with brownie.reverts("ERROR:TRS-063:WITHDRAWAL_TRANSFER_FAILED"):
        riskpool.burnBundle(
                bundleId, 
                {'from': riskpoolKeeper})


def test_payout_allowance_too_small(
    instance: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    customer: Account,
):  
    applicationFilter = bytes(0)

    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instance,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        True
    )

    # prepare product and riskpool
    safetyFactor = 2
    amount = 10000
    testCoin.transfer(riskpoolKeeper, safetyFactor * amount, {'from': owner})
    testCoin.approve(instance.getTreasury(), amount, {'from': riskpoolKeeper})
    riskpool = gifRiskpool.getContract()

    # fund bundle
    riskpool.createBundle(
                applicationFilter, 
                amount, 
                {'from': riskpoolKeeper})

    bundle = riskpool.getBundle(0)
    print(bundle)

    (bundleId) = bundle[0]

    # check bundle values with expectation
    assert bundleId == 1

    # prepare prolicy application
    premium = 100
    sumInsured = 1000
    product = gifProduct.getContract()
    policyController = instance.getPolicy()

    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    claimAmount = 800
    instanceService = instance.getInstanceService()

    # submit a claim for the policy
    tx = product.submitClaimWithDeferredResponse(policyId, claimAmount, {'from': customer})
    (claimId, requestId) = tx.return_value
    claim = instanceService.getClaim(policyId, claimId).dict()
    print(claim)

    assert claim["state"] ==  0 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    # confirm the claim
    product.confirmClaim(policyId, claimId, claimAmount, {'from': productOwner})

    claim = instanceService.getClaim(policyId, claimId).dict()
    assert claim["state"] ==  1 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    # check that it's possible to create payout for claim in confirmed state
    payoutAmount = claimAmount

    # prepare allowance for payout that is too small
    testCoin.approve(instance.getTreasury(), payoutAmount * 0.9, {'from': capitalOwner})

    # ensure that the payout fails due to too small allowance
    with brownie.reverts("ERROR:TRS-043:PAYOUT_TRANSFER_FAILED"):
        product.createPayout(policyId, claimId, payoutAmount, {'from': productOwner})

def test_two_products_different_coin_same_riskpool(
    instance: GifInstance,
    owner: Account,
    testCoin,
    testCoinX,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
):
    withRiskpoolWallet = True

    # setup riskpool with a product
    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instance,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        withRiskpoolWallet
    )

    # ensure that creating of another product with different token is not allowed
    with brownie.reverts("ERROR:TRS-014:TOKEN_ADDRESS_NOT_MACHING"):
        GifTestProduct(
            instance, 
            testCoinX,
            capitalOwner,
            productOwner,
            gifOracle,
            gifRiskpool,
            'Test.Product2')


def test_two_products_same_riskpool(
    instance: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    customer: Account,
):
    withRiskpoolWallet = True

    # setup riskpool with a product
    (gifProduct, gifRiskpool, gifOracle) = getProductAndRiskpool(
        instance,
        owner,
        testCoin,
        productOwner,
        oracleProvider,
        riskpoolKeeper,
        capitalOwner,
        withRiskpoolWallet
    )

    # ensure that creating of another product with different token succeeds
    gifProduct2 = GifTestProduct(
        instance, 
        testCoin,
        capitalOwner,
        productOwner,
        gifOracle,
        gifRiskpool,
        'Test.Product2')

    # ensure the two products are different
    assert gifProduct2.getContract().getId() != gifProduct.getContract().getId()


def test_overwriting_capital_fees(
    instance: GifInstance,
    instanceOperator: Account,
    gifTestProduct,
    chain: Chain
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    treasury = instance.getTreasury()

    product = gifTestProduct.getContract()
    riskpoolId = gifTestProduct.getRiskpool().getId()

    hundredPercent = instanceService.getFeeFractionFullUnit()

    existingFeeSpec = treasury.getFeeSpecification(riskpoolId)

    # advance chain to ensure new timestamp
    chain.sleep(31337)
    chain.mine()

    # ensure that the new fee spec has a new timstamp
    newRiskpoolFeeSpec = instanceOperatorService.createFeeSpecification(
        riskpoolId, 999, hundredPercent / 200, str.encode("a"))
    assert existingFeeSpec[4] != newRiskpoolFeeSpec[4]

    # ensure that the fee spec is updated and all values except for createdAt are updated
    tx = instanceOperatorService.setCapitalFees(newRiskpoolFeeSpec, {"from": instanceOperator})    
    updatedFeeSpec = treasury.getFeeSpecification(riskpoolId)

    assert existingFeeSpec[0] == updatedFeeSpec[0]
    assert existingFeeSpec[1] != updatedFeeSpec[1]
    assert existingFeeSpec[2] != updatedFeeSpec[2]
    assert existingFeeSpec[3] != updatedFeeSpec[3]
    assert existingFeeSpec[4] == updatedFeeSpec[4]
    assert existingFeeSpec[5] != updatedFeeSpec[5]


def test_overwriting_premium_fees(
    instance: GifInstance,
    instanceOperator: Account,
    gifTestProduct,
    chain: Chain
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    treasury = instance.getTreasury()

    product = gifTestProduct.getContract()
    productId = product.getId()

    hundredPercent = instanceService.getFeeFractionFullUnit()

    existingFeeSpec = treasury.getFeeSpecification(productId)

    # advance chain to ensure new timestamp
    chain.sleep(31337)
    chain.mine()

    # ensure that the new fee spec has a new timstamp
    newProductFeeSpec = instanceOperatorService.createFeeSpecification(
        productId, 999, hundredPercent / 200, str.encode("a"))
    assert existingFeeSpec[4] != newProductFeeSpec[4]

    # ensure that the fee spec is updated and all values except for createdAt are updated
    tx = instanceOperatorService.setPremiumFees(newProductFeeSpec, {"from": instanceOperator})    
    updatedFeeSpec = treasury.getFeeSpecification(productId)

    assert existingFeeSpec[0] == updatedFeeSpec[0]
    assert existingFeeSpec[1] != updatedFeeSpec[1]
    assert existingFeeSpec[2] != updatedFeeSpec[2]
    assert existingFeeSpec[3] != updatedFeeSpec[3]
    assert existingFeeSpec[4] == updatedFeeSpec[4]
    assert existingFeeSpec[5] != updatedFeeSpec[5]


def getProductAndRiskpool(
    instance: GifInstance,
    owner: Account,
    testCoin,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    withRiskpoolWallet: bool
):
    gifOracle = GifTestOracle(
        instance, 
        oracleProvider)

    capitalization = 10**18
    gifRiskpool = GifTestRiskpool(
        instance, 
        riskpoolKeeper, 
        testCoin,
        capitalOwner, 
        capitalization, 
        setRiskpoolWallet = withRiskpoolWallet)

    gifProduct = GifTestProduct(
        instance, 
        testCoin,
        capitalOwner,
        productOwner,
        gifOracle,
        gifRiskpool)

    return (
        gifProduct,
        gifRiskpool,
        gifOracle
    )
