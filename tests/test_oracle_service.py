import binascii
import brownie
import pytest

from brownie import OracleService

from scripts.const import (
    ORACLE_SERVICE_NAME,
)

from scripts.util import (
    h2sLeft,
    s2b32,
)

def test_type(oracleService):
    serviceName = h2sLeft(oracleService.NAME.call())
    assert ORACLE_SERVICE_NAME == serviceName
    assert OracleService._name == serviceName

def test_non_existing_functionality(oracleService, owner):
    with pytest.raises(AttributeError):
        assert oracleService.foo({'from': owner})

def test_product_service_contract_in_registry(oracleService, registry, owner):
    oracleServiceAddress = registry.getContract(s2b32(ORACLE_SERVICE_NAME))

    assert oracleService.address == oracleServiceAddress
    assert oracleService.address != 0x0
