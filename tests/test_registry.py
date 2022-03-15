import binascii
import brownie

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
)

from scripts.util import (
    h2s,
    s2b32,
)

def test_registry_release(registry, owner):
    assert GIF_RELEASE == h2s(registry.getRelease({'from': owner}))

def test_registry_release_any_account(registry, accounts):
    assert GIF_RELEASE == h2s(registry.getRelease({'from': accounts[0]}))

def test_registry_controller(registry, registryController, owner, accounts):
    release = registry.getRelease({'from': owner})
    controllerAddress = registry.getContract(s2b32(REGISTRY_CONTROLLER_NAME))
    registryAddress = registry.getContract(s2b32(REGISTRY_NAME))

    assert registryController.address == controllerAddress
    assert registry.address == registryAddress
