import binascii
import brownie
import pytest

# from exceptions import AttributeError

from scripts.const import (
    QUERY_CONTROLLER_NAME,
    QUERY_NAME,
)

from scripts.util import (
    s2b32,
)

def test_non_existing_functionality(query, owner):
    with pytest.raises(AttributeError):
        assert query.foo({'from': owner})

def test_policy_contracts_in_registry(registry, query, owner):
    queryAddress = registry.getContract(s2b32(QUERY_NAME))
    queryControllerAddress = registry.getContract(s2b32(QUERY_CONTROLLER_NAME))

    assert query.address == queryAddress
    assert query.address != queryControllerAddress
    assert query.address != 0x0
