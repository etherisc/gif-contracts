import brownie
import pytest

from brownie.network.account import Account

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

def test_guard_processPremium(
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

        # prepare prolicy application
    premium = 100
    sumInsured = 1000
    product = gifProduct.getContract()
    policyController = instance.getPolicy()

    processId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    with brownie.reverts("ERROR:CRC-003:NOT_PRODUCT_SERVICE"):
        instance.getTreasury().processPremium(processId, {'from': customer})
    
    with brownie.reverts("ERROR:CRC-003:NOT_PRODUCT_SERVICE"):
        instance.getTreasury().processPremium(processId, premium, {'from': customer})


def test_guard_processPayout(
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

        # prepare prolicy application
    premium = 100
    sumInsured = 1000
    product = gifProduct.getContract()
    policyController = instance.getPolicy()

    processId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    with brownie.reverts("ERROR:CRC-003:NOT_PRODUCT_SERVICE"):
        instance.getTreasury().processPayout(processId, "123", {'from': customer})
    


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