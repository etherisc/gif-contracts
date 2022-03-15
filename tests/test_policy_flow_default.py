import binascii
import brownie
import pytest

from brownie import PolicyFlowDefault

from scripts.const import (
    POLICY_FLOW_DEFAULT_NAME,
)

from scripts.util import (
    h2sLeft,
    s2b32,
)

def test_type(policyFlowDefault):
    serviceName = h2sLeft(policyFlowDefault.NAME.call())
    assert POLICY_FLOW_DEFAULT_NAME == serviceName
    assert PolicyFlowDefault._name == serviceName

def test_non_existing_functionality(policyFlowDefault, owner):
    with pytest.raises(AttributeError):
        assert policyFlowDefault.foo({'from': owner})

def test_product_service_contract_in_registry(policyFlowDefault, registry, owner):
    policyFlowDefaultAddress = registry.getContract(s2b32(POLICY_FLOW_DEFAULT_NAME))

    assert policyFlowDefault.address == policyFlowDefaultAddress
    assert policyFlowDefault.address != 0x0
