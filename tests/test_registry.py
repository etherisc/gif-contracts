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
    ZERO_ADDRESS,
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

    namesFromRegistry = get_contract_names(registry)
    
    # ignore first three elements 
    for i in range(len(namesFromRegistry[3:])):
        assert b322s(namesFromRegistry[i + 3]) == expectedNames[i]

    # ensure that contract #101 cannot be registered
    with brownie.reverts("ERROR:REC-010:MAX_CONTRACTS_LIMIT"):
        tx = TestCoin.deploy({'from': owner})
        registry.register(s2b32("OneTooMany"), tx, {'from': owner})


def test_registry_deregister(registry, owner):
    assert GIF_RELEASE == b322s(registry.getRelease({'from': owner}))

    name1 = s2b32("TestCoin1")
    name2 = s2b32("TestCoin2")
    name3 = s2b32("TestCoin3")
    
    tx1 = TestCoin.deploy({'from': owner})
    tx = registry.register(name1, tx1, {'from': owner})
    
    tx2 = TestCoin.deploy({'from': owner})
    tx = registry.register(name2, tx2, {'from': owner})
    
    assert tx1 == registry.getContract(name1)
    assert tx2 == registry.getContract(name2)

    with brownie.reverts("ERROR:REC-020:CONTRACT_UNKNOWN"):
        tx = registry.deregister(name3, {'from': owner})

    assert tx1 == registry.getContract(name1)
    assert tx2 == registry.getContract(name2)

    tx = registry.deregister(name1, {'from': owner})
    print(tx.info())

    assert ZERO_ADDRESS == registry.getContract(name1)
    assert tx2 == registry.getContract(name2)
    

def test_register_edgecases(registry, owner):
    name1 = s2b32("TestCoin1")
    name2 = s2b32("TestCoin2")
    
    tx1 = TestCoin.deploy({'from': owner})
    tx2 = TestCoin.deploy({'from': owner})

    with brownie.reverts("ERROR:REC-011:RELEASE_UNKNOWN"):
        registry.registerInRelease(s2b32("unknown release"), name1, tx1, {'from': owner})

    with brownie.reverts("ERROR:REC-012:CONTRACT_NAME_EMPTY"):
        registry.register("", tx1, {'from': owner})

    registry.register(name1, tx1, {'from': owner})
    with brownie.reverts("ERROR:REC-013:CONTRACT_NAME_EXISTS"):
        registry.register(name1, tx2, {'from': owner})
    
    with brownie.reverts("ERROR:REC-014:CONTRACT_ADDRESS_ZERO"):
        registry.register(name2, ZERO_ADDRESS, {'from': owner})



def get_contract_names(registry):
    contract_names = []
    for i in range(registry.contracts()):
        contract_names.append(registry.contractName(i))
    return contract_names
