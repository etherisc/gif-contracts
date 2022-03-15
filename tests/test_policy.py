import binascii
import brownie
import pytest

# from exceptions import AttributeError

from scripts.const import (
    POLICY_CONTROLLER_NAME,
    POLICY_NAME,
)

from scripts.util import (
    s2b32,
)

def test_non_existing_functionality(policy, owner):
    with pytest.raises(AttributeError):
        assert policy.foo({'from': owner})

def test_policy_contracts_in_registry(registry, policy, owner):
    policyAddress = registry.getContract(s2b32(POLICY_NAME))
    policyControllerAddress = registry.getContract(s2b32(POLICY_CONTROLLER_NAME))

    assert policy.address == policyAddress
    assert policy.address != policyControllerAddress
    assert policy.address != 0x0
