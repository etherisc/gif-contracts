import binascii
import brownie
import pytest

from brownie import (
    AccessController
)

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_CONTROLLER_NAME,
    REGISTRY_NAME,
)

from scripts.util import (
    b322s,
    s2b32,
    deployGifModuleV2,
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

    # 2 for registry, 2 for component instance service and 96 for access controlls (each being one component and its proxy)
    for i in range(48):
        print(i)
        deployGifModuleV2("Access%s" % i, AccessController, registry, owner, False)

    with brownie.reverts("ERROR:REC-005:MAX_CONTRACTS_LIMIT"):
        deployGifModuleV2("AccessOneMore", AccessController, registry, owner, False)

