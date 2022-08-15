import binascii
import brownie
import pytest

from brownie import ComponentOwnerService

from scripts.const import (
    COMPONENT_OWNER_SERVICE_NAME
)

from scripts.util import (
    h2sLeft,
    s2b32,

)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_non_existing_functionality(instance, owner):
    componentOwnerService = instance.getComponentOwnerService()

    with pytest.raises(AttributeError):
        assert componentOwnerService.foo({'from': owner})

def test_component_service_contract_in_registry(instance, owner):
    componentOwnerService = instance.getComponentOwnerService()

    registry = instance.getRegistry()    
    componentOwnerServiceAddress = registry.getContract(s2b32(COMPONENT_OWNER_SERVICE_NAME))

    assert componentOwnerService.address == componentOwnerServiceAddress
    assert componentOwnerService.address != 0x0
