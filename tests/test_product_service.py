import binascii
import brownie
import pytest

from brownie import ProductService

from scripts.const import (
    PRODUCT_SERVICE_NAME,
)

from scripts.util import (
    h2sLeft,
    s2b32,
)

def test_type(productService):
    serviceName = h2sLeft(productService.NAME.call())
    assert PRODUCT_SERVICE_NAME == serviceName
    assert ProductService._name == serviceName

def test_non_existing_functionality(productService, owner):
    with pytest.raises(AttributeError):
        assert productService.foo({'from': owner})

def test_product_service_contract_in_registry(productService, registry, owner):
    productServiceAddress = registry.getContract(s2b32(PRODUCT_SERVICE_NAME))

    assert productService.address == productServiceAddress
    assert productService.address != 0x0
