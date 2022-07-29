import brownie
import pytest

from brownie import TestOracle

from scripts.instance import GifInstance
from scripts.product import GifTestOracle
from scripts.util import s2b32

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

# def test_deploy(instance: GifInstance, oracleOwner, productOwner):
def test_deploy_simple(
    instance: GifInstance, 
    gifTestOracle: GifTestOracle
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 1
    assert instanceService.products() == 0
    assert instanceService.riskpools() == 0

    # TODO add asserts to check inital state of oracle


def test_deploy_and_propose(instance: GifInstance, owner, oracleProvider):
    instanceService = instance.getInstanceService()
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    # assert that proposal fails with missing role
    providerRole = instanceService.getOracleProviderRole()
    operatorService.revokeRole(
        providerRole, 
        oracleProvider,
        {'from': instance.getOwner()})
    
    assert not instanceService.hasRole(providerRole, oracleProvider)

    with brownie.reverts():
        componentOwnerService.propose(
            oracle,
            {'from': oracleProvider})
    
    # add granting role
    operatorService.grantRole(
        providerRole,
        oracleProvider, 
        {'from': instance.getOwner()})

    # try again
    componentOwnerService.propose(
        oracle,
        {'from': oracleProvider})


def test_deploy_and_approve(instance: GifInstance, oracleProvider, productOwner):
    instanceService = instance.getInstanceService()
    operatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    oracle = TestOracle.deploy(
        s2b32("TestOracle"),
        instance.getRegistry(),
        {'from': oracleProvider})
    
    # add granting role and propose
    providerRole = instanceService.getOracleProviderRole()
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
