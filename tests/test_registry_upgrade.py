import binascii
import brownie
import pytest

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
    ZERO_ADDRESS,
    COMPROMISED_ADDRESS,
)

from scripts.util import (
    b322s,
    s2b32,
    encode_function_data,
    contractFromAddress,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_registry_release(registry, owner):
    assert GIF_RELEASE == b322s(registry.getRelease())

def test_registry_update(registry, registryController, registryControllerV2Test, owner):

    # verify implementations
    proxy = contractFromAddress(brownie.CoreProxy, registry.address)
    controllerAddress = proxy.implementation()

    assert registryController.address == controllerAddress
    assert registryController.address != registryControllerV2Test.address

    # prepare registry upgrade
    newMessage = "hey"
    encodedInitializer = encode_function_data(
        newMessage,
        initializer=registryControllerV2Test.upgradeToV2)

    # upgrade registry
    proxy.upgradeToAndCall(
        registryControllerV2Test.address,
        encodedInitializer,
        {'from': owner})

    # verify updated implementations
    assert registryControllerV2Test.address == proxy.implementation()

    # verify existing and new functionality
    registryV2 = contractFromAddress(brownie.TestRegistryControllerUpdated, registry.address)
    assert GIF_RELEASE == b322s(registryV2.getRelease())
    assert newMessage == registryV2.getMessage()

    # ensure calling upgrade a second time fails
    with brownie.reverts():
        proxy.upgradeToAndCall(
            registryControllerV2Test.address,
            encodedInitializer,
            {'from': owner})


# test upgrade with well behaved upgraded module that inherits from CoreController
def test_upgrade_by_anybody_fails(registry, registryController, registryControllerV2Test, customer):

    # verify implementations
    proxy = contractFromAddress(brownie.CoreProxy, registry.address)
    controllerAddress = proxy.implementation()

    assert registryController.address == controllerAddress
    assert registryController.address != registryControllerV2Test.address

    # prepare registry upgrade
    newMessage = "hey (by customer)"
    encodedInitializer = encode_function_data(
        newMessage,
        initializer=registryControllerV2Test.upgradeToV2)

    # verify upgrade cannot be done by non instance operator accounts
    # assumption: well behaved upgraded module that inherits from CoreController
    with brownie.reverts("ERROR:CRP-001:NOT_ADMIN"):
        proxy.upgradeToAndCall(
            registryControllerV2Test.address,
            encodedInitializer,
            {'from': customer})


# test upgrade with compromised module that does not inherit from CoreController
def test_compromised_upgrade_by_anybody_fails(instance, registryCompromisedControllerV2Test, customer):

    registry = instance.getRegistry()

    # verify implementations
    proxy = contractFromAddress(brownie.CoreProxy, registry.address)
    controllerAddress = proxy.implementation()

    # prepare registry upgrade
    queryOriginalQueryAddress = registry.getContract(s2b32("Query"))
    queryOriginalPolicyAddress = registry.getContract(s2b32("Policy"))

    assert COMPROMISED_ADDRESS != queryOriginalPolicyAddress

    encodedInitializer = encode_function_data(
        COMPROMISED_ADDRESS,
        queryOriginalQueryAddress,
        initializer=registryCompromisedControllerV2Test.upgradeToV2)

    # upgrade registry, ensure customer may not upgrade contract
    with brownie.reverts("ERROR:CRP-001:NOT_ADMIN"):
        proxy.upgradeToAndCall(
            registryCompromisedControllerV2Test.address,
            encodedInitializer,
            {'from': customer})

        # verify updated implementations
        assert registryCompromisedControllerV2Test.address == proxy.implementation()

        # verify upgraded registry retuns compromised policy address
        registryV2 = contractFromAddress(brownie.TestRegistryCompromisedController, registry.address)
        assert registryV2.getContract(s2b32("Query")) == queryOriginalQueryAddress
        assert registryV2.getContract(s2b32("Policy")) == COMPROMISED_ADDRESS
        assert registryV2.getContract(s2b32("Pool")) == ZERO_ADDRESS

        # if we landed here this means that compromised upgrade was successful
        assert False
