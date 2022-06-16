import brownie

from brownie import (
    TestOracle,
    TestProduct,
)

from scripts.instance import GifInstance

from scripts.product import (
    GifTestOracle,
    GifTestProduct,
)

from scripts.util import s2b32


def test_deploy(instance: GifInstance, oracleOwner, productOwner):
    ios = instance.getInstanceOperatorService()

    # TODO think if/how type specific component counts are really needed
    # assert ios.oracles() == 0
    assert ios.products() == 0

    oracle = GifTestOracle(instance, oracleOwner)

    # assert ios.oracles() == 1
    assert ios.products() == 0

    product = GifTestProduct(instance, oracle, productOwner)

    # assert ios.oracles() == 1
    assert ios.products() == 1


def test_deploy_oracle_and_oracle_provider_role(instance: GifInstance, owner, oracleProvider):
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    with brownie.reverts():
        componentOwnerService.propose(
            oracle,
            {'from': oracleProvider})
    
    # add granting role
    opRole = operatorService.oracleProviderRole()
    operatorService.addRoleToAccount(oracleProvider, opRole)

    # try again
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})


def test_deploy_approve_oracle(instance: GifInstance, oracleProvider, productOwner):
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()
    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    # add granting role and propose
    opRole = operatorService.oracleProviderRole()
    operatorService.addRoleToAccount(oracleProvider, opRole)
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})

    # verify that productOwner cannot approve the oracle
    with brownie.reverts():
        operatorService.approveOracle(
            oracle.getId(),
            {'from': productOwner})

    # verify that instance operator can approve the propsed oracle
    operatorService.approveOracle(
        oracle.getId(),
        {'from': instance.getOwner()})


def test_deploy_approve_product(instance: GifInstance, oracleProvider, productOwner):
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()
    productService = instance.getProductService()

    # oracle owner proposes oracle
    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    # add granting role and propose
    opRole = operatorService.oracleProviderRole()
    operatorService.addRoleToAccount(oracleProvider, opRole)
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})


    # instance operator can approve the propsed oracle
    operatorService.approveOracle(
        oracle.getId(),
        {'from': instance.getOwner()})

    product = TestProduct.deploy(
        productService,
        s2b32("TestProduct"),
        oracle.getId(),
        {'from': productOwner})

    productId = product.getId()

    # verify that oracleOwner or productOwner cannot approve the product
    with brownie.reverts():
        operatorService.approveProduct(
            productId,
            {'from': oracleProvider})

    with brownie.reverts():
        operatorService.approveProduct(
            productId,
            {'from': productOwner})

    # verify that instance operator can approve the propsed product
    operatorService.approveProduct(
        productId,
        {'from': instance.getOwner()})
