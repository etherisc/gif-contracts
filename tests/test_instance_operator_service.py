import binascii
import brownie
import pytest

from brownie import InstanceOperatorService

from scripts.const import (
    INSTANCE_OPERATOR_SERVICE_NAME,
)

from scripts.util import (
    h2sLeft,
    s2b32,

)

def test_type(instanceOperatorService):
    serviceName = h2sLeft(instanceOperatorService.NAME.call())
    assert INSTANCE_OPERATOR_SERVICE_NAME == serviceName
    assert InstanceOperatorService._name == serviceName

def test_non_existing_functionality(instanceOperatorService, owner):
    with pytest.raises(AttributeError):
        assert instanceOperatorService.foo({'from': owner})

def test_instance_operator_service_contract_in_registry(instanceOperatorService, registry, owner):
    instanceOperatorServiceAddress = registry.getContract(s2b32(INSTANCE_OPERATOR_SERVICE_NAME))

    assert instanceOperatorService.address == instanceOperatorServiceAddress
    assert instanceOperatorService.address != 0x0
