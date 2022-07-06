import binascii
import brownie
import pytest

# from exceptions import AttributeError

from scripts.const import (
    RISKPOOL_CONTROLLER_NAME,
    RISKPOOL_NAME,
)

from scripts.util import (
    s2b32,
)

def test_non_existing_functionality(riskpool, owner):
    with pytest.raises(AttributeError):
        assert riskpool.foo({'from': owner})

def test_riskpool_contracts_in_registry(registry, riskpool, owner):
    riskpoolAddress = registry.getContract(s2b32(RISKPOOL_NAME))
    riskpoolControllerAddress = registry.getContract(s2b32(RISKPOOL_CONTROLLER_NAME))

    assert riskpool.address == riskpoolAddress
    assert riskpool.address != riskpoolControllerAddress
    assert riskpool.address != 0x0
