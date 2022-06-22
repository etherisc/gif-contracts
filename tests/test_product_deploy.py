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
    instanceService = instance.getInstanceService()

    # TODO think if/how type specific component counts are really needed
    assert instanceService.oracles() == 0
    assert instanceService.products() == 0

    oracle = GifTestOracle(instance, oracleOwner)

    assert instanceService.oracles() == 1
    assert instanceService.products() == 0

    product = GifTestProduct(instance, oracle, productOwner)

    assert instanceService.oracles() == 1
    assert instanceService.products() == 1


def test_deploy_oracle_and_oracle_provider_role(instance: GifInstance, owner, oracleProvider):
    instanceService = instance.getInstanceService()
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
    providerRole = instanceService.oracleProviderRole()
    operatorService.grantRole(
        providerRole,
        oracleProvider, 
        {'from': instance.getOwner()})

    # try again
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})


def test_deploy_approve_oracle(instance: GifInstance, oracleProvider, productOwner):
    instanceService = instance.getInstanceService()
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()
    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    # add granting role and propose
    providerRole = instanceService.oracleProviderRole()
    operatorService.grantRole(
        providerRole,
        oracleProvider, 
        {'from': instance.getOwner()})
    
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})

    # verify that productOwner cannot approve the oracle
    with brownie.reverts():
        operatorService.approve(
            oracle.getId(),
            {'from': productOwner})

    # verify that instance operator can approve the propsed oracle
    operatorService.approve(
        oracle.getId(),
        {'from': instance.getOwner()})


def test_deploy_approve_product(instance: GifInstance, oracleProvider, productOwner):
    instanceService = instance.getInstanceService()
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()
    registry = instance.getRegistry()

    # oracle owner proposes oracle
    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    # add granting role and propose
    providerRole = instanceService.oracleProviderRole()
    operatorService.grantRole(
        providerRole,
        oracleProvider, 
        {'from': instance.getOwner()})
    
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})

    # instance operator can approve the propsed oracle
    operatorService.approve(
        oracle.getId(),
        {'from': instance.getOwner()})

    product = TestProduct.deploy(
        s2b32("TestProduct"),
        registry,
        oracle.getId(),
        {'from': productOwner})
    
    # add granting role and propose
    ownerRole = instanceService.productOwnerRole()
    operatorService.grantRole(
        ownerRole,
        productOwner, 
        {'from': instance.getOwner()})

    # check that product owner may not propose compoent
    # without being owner
    with brownie.reverts():
        componentOwnerService.propose(
            oracle,
            {'from': productOwner})

    # check that product owner may proposes his/her product
    componentOwnerService.propose(
        product,
        {'from': productOwner})

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
