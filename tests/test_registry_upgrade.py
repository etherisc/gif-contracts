import binascii
import brownie

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
)

from scripts.util import (
    b322s,
    s2b32,
    encode_function_data,
    contractFromAddress,
)

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

