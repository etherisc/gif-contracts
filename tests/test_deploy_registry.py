import binascii
import brownie
import pytest

from brownie import (
    CoreProxy,
    RegistryController,
)

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
)

from scripts.util import (
    h2s,
    b322s,
    s2b32,
    encode_function_data,
    contractFromAddress,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_registry_base(owner, customer):
    
    controller = RegistryController.deploy(
        {'from': owner})

    encoded_initializer = encode_function_data(
        s2b32(GIF_RELEASE),
        initializer=controller.initializeRegistry)

    proxy = CoreProxy.deploy(
        controller.address, 
        encoded_initializer, 
        {'from': owner})

    registry = contractFromAddress(RegistryController, proxy.address)

    doAssertions(registry, proxy, controller, owner, customer)


def test_registry(registry, owner, customer):
    proxyAddress = registry.getContract(s2b32("Registry"), {'from': customer})
    controllerAddress = registry.getContract(s2b32("RegistryController"), {'from': customer})

    proxy = contractFromAddress(CoreProxy, proxyAddress)
    controller = contractFromAddress(RegistryController, controllerAddress)

    doAssertions(registry, proxy, controller, owner, customer)


def doAssertions(registry, proxy, controller, owner, customer):
    # ensure release info can be accessed by any account
    assert GIF_RELEASE == b322s(registry.getRelease({'from': owner}))
    assert GIF_RELEASE == b322s(registry.getRelease({'from': customer}))

    # ensure that registering contracts is disallowed for non-owner account (ie customer)
    with brownie.reverts():
        registry.register(s2b32("Registry"), proxy.address, {'from': customer})

    # ensure owner is allowed to register contracts
    registry.register(s2b32("Registry2"), proxy.address, {'from': owner})
    registry.register(s2b32("Registry2Controller"), controller.address, {'from': owner})

    # ensure getting contract info can be accessed by any account
    assert proxy.address == registry.getContract(s2b32("Registry2"), {'from': customer})
    assert controller.address == registry.getContract(s2b32("Registry2Controller"), {'from': customer})
