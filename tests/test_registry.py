import binascii
from pprint import pp
import brownie
import pytest

from brownie import (
    AccessController,
    InstanceOperatorService,
    TestCoin
)

from scripts.const import (
    GIF_RELEASE,
    INSTANCE_OPERATOR_SERVICE_NAME,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
)

from scripts.util import (
    b322s,
    s2b32,
    deployGifModuleV2,
    contract_from_address,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_registry_release(registry, owner):
    assert GIF_RELEASE == b322s(registry.getRelease({'from': owner}))

def test_registry_release_any_account(registry, accounts):
    assert GIF_RELEASE == b322s(registry.getRelease({'from': accounts[0]}))

def test_registry_controller(registry, registryController, owner, accounts):
    release = registry.getRelease({'from': owner})
    controllerAddress = registry.getContract(s2b32(REGISTRY_CONTROLLER_NAME))
    registryAddress = registry.getContract(s2b32(REGISTRY_NAME))

    assert registryController.address == controllerAddress
    assert registry.address == registryAddress


def test_registry_max_coponents(registry, owner):
    assert GIF_RELEASE == b322s(registry.getRelease({'from': owner}))
    # assert registry has three contracts (instance operator service, registry, registry proxy)
    assert 3 == registry.contracts()

    expectedNames = []

    # register another 97 contracts
    for i in range(97):
        name = "TestCoin%s" % i
        tx = TestCoin.deploy({'from': owner})
        tx = registry.register(s2b32(name), tx, {'from': owner})
        expectedNames.append(name)

    assert 100 == registry.contracts()

    namesFromRegistry = registry.contractNames()
    
    # ignore first three elements 
    for i in range(len(namesFromRegistry[3:])):
        assert b322s(namesFromRegistry[i + 3]) == expectedNames[i]

    # ensure that contract #101 cannot be registered
    with brownie.reverts("ERROR:REC-005:MAX_CONTRACTS_LIMIT"):
        tx = TestCoin.deploy({'from': owner})
        registry.register(s2b32("OneTooMany"), tx, {'from': owner})

