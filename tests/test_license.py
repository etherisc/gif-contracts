import binascii
import brownie
import pytest

# from exceptions import AttributeError

from scripts.const import (
    LICENSE_NAME,
    LICENSE_CONTROLLER_NAME,
)

from scripts.util import (
    s2b32,
)

def test_non_existing_product(license, owner, accounts):
    productId = 0
    assert not license.isApprovedProduct(productId, {'from': owner})
    assert not license.isApprovedProduct(productId, {'from': accounts[0]})

def test_non_existing_functionality(license, owner):
    with pytest.raises(AttributeError):
        assert license.foo({'from': owner})

def test_licence_contracts_in_registry(registry, license, owner):
    licenseAddress = registry.getContract(s2b32(LICENSE_NAME))
    licenseControllerAddress = registry.getContract(s2b32(LICENSE_CONTROLLER_NAME))

    assert license.address == licenseAddress
    assert license.address != licenseControllerAddress
    assert license.address != 0x0
