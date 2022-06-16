import binascii
import brownie
import pytest

# from exceptions import AttributeError

from scripts.const import (
    ACCESS_NAME,
    ACCESS_CONTROLLER_NAME,
)

from scripts.util import (
    s2b32,
)

def test_non_existing_functionality(access, owner):
    with pytest.raises(AttributeError):
        assert access.foo({'from': owner})

def test_access_contracts_in_registry(registry, access, owner):
    accessAddress = registry.getContract(s2b32(ACCESS_NAME))
    accessControllerAddress = registry.getContract(s2b32(ACCESS_CONTROLLER_NAME))

    assert access.address == accessAddress
    assert access.address != accessControllerAddress
    assert access.address != 0x0
