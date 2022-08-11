import brownie
import pytest

from brownie import (
    TestOracle,
    TestProduct,
)

from scripts.instance import GifInstance

from scripts.product import (
    GifTestOracle,
    GifTestProduct,
    GifTestRiskpool,
)

from scripts.util import s2b32


# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_deploy_simple(
    instance: GifInstance, 
    testCoin,
    capitalOwner,
    productOwner,
    gifTestOracle: GifTestOracle, 
    gifTestRiskpool: GifTestRiskpool, 
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 1
    assert instanceService.products() == 0
    assert instanceService.riskpools() == 1

    product = GifTestProduct(
        instance, 
        testCoin, 
        capitalOwner, 
        productOwner, 
        gifTestOracle, 
        gifTestRiskpool)

    assert instanceService.oracles() == 1
    assert instanceService.products() == 1
    assert instanceService.riskpools() == 1

    # asssertions for initialized product
    assert instanceService.getComponentToken(product.getId()) == testCoin
    assert instanceService.getRiskpoolWallet(gifTestRiskpool.getId()) == capitalOwner

    # check capitalization for riskpool
    riskpool = gifTestRiskpool.getContract()
    assert riskpool.getCollateralizationLevel() == riskpool.getFullCollateralizationLevel()



def test_deploy_approve_product(
    instance: GifInstance, 
    testCoin, 
    capitalOwner, 
    productOwner,
    oracleProvider,
    riskpoolKeeper, 
):
    instanceService = instance.getInstanceService()
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()
    registry = instance.getRegistry()

    oracle = GifTestOracle(
        instance, 
        oracleProvider,
        name='TestOracle2')

    collateralization = 10000
    riskpool = GifTestRiskpool(
        instance,
        riskpoolKeeper,
        capitalOwner,
        testCoin,
        collateralization,
        name='TestRiskpool2')

    product = TestProduct.deploy(
        s2b32("TestProduct"),
        testCoin.address,
        capitalOwner,
        oracle.getId(),
        riskpool.getId(),
        registry,
        {'from': productOwner})
    
    # add granting role and propose
    ownerRole = instanceService.getProductOwnerRole()
    operatorService.grantRole(
        ownerRole,
        productOwner, 
        {'from': instance.getOwner()})

    # check that product owner may not propose compoent
    # without being owner
    with brownie.reverts():
        componentOwnerService.propose(
            oracle.getContract(),
            {'from': productOwner})

    # check that product owner may proposes his/her product
    componentOwnerService.propose(
        product,
        {'from': productOwner})

    productId = product.getId()
    assert instanceService.getComponentState(productId) == 1
    assert product.getState() == 1

    # verify that oracleOwner or productOwner cannot approve the product
    with brownie.reverts():
        operatorService.approve(
            product.getId(),
            {'from': oracleProvider})

    with brownie.reverts():
        operatorService.approve(
            product.getId(),
            {'from': productOwner})

    # verify that instance operator can approve the propsed product
    operatorService.approve(
        product.getId(),
        {'from': instance.getOwner()})

    assert instanceService.getComponentState(productId) == 3
    assert product.getState() == 3
