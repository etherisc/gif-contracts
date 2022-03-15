import binascii
import brownie
import pytest

from brownie import OracleOwnerService

from scripts.const import (
    ORACLE_OWNER_SERVICE_NAME,
)

from scripts.util import (
    h2sLeft,
    s2b32,

)

def test_type(oracleOwnerService):
    serviceName = h2sLeft(oracleOwnerService.NAME.call())
    assert ORACLE_OWNER_SERVICE_NAME == serviceName
    assert OracleOwnerService._name == serviceName

def test_non_existing_functionality(oracleOwnerService, owner):
    with pytest.raises(AttributeError):
        assert oracleOwnerService.foo({'from': owner})

def test_product_service_contract_in_registry(oracleOwnerService, registry, owner):
    oracleOwnerServiceAddress = registry.getContract(s2b32(ORACLE_OWNER_SERVICE_NAME))

    assert oracleOwnerService.address == oracleOwnerServiceAddress
    assert oracleOwnerService.address != 0x0
