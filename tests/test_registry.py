import binascii
import brownie
import pytest

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
)

from scripts.util import (
    b322s,
    s2b32,
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
