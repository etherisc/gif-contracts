import pytest

from brownie.network.account import Account

from scripts.instance import (
    GifRegistry,
    GifInstance,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_module_addresses(instance: GifInstance):
    address = instance.getRegistry().address
    addrInst = GifInstance(registryAddress=address)

    assert addrInst.getRegistry().address == address
    assert addrInst.getAccess().address == instance.getAccess().address
    assert addrInst.getBundle().address == instance.getBundle().address
    assert addrInst.getComponent().address == instance.getComponent().address
    assert addrInst.getLicense().address == instance.getLicense().address
    assert addrInst.getPolicy().address == instance.getPolicy().address
    assert addrInst.getPool().address == instance.getPool().address
    assert addrInst.getQuery().address == instance.getQuery().address


def test_service_addresses(instance: GifInstance):
    address = instance.getRegistry().address
    addrInst = GifInstance(registryAddress=address)

    assert addrInst.getComponentOwnerService().address == instance.getComponentOwnerService().address
    assert addrInst.getInstanceOperatorService().address == instance.getInstanceOperatorService().address
    assert addrInst.getProductService().address == instance.getProductService().address
    assert addrInst.getOracleService().address == instance.getOracleService().address
    assert addrInst.getRiskpoolService().address == instance.getRiskpoolService().address
    assert addrInst.getInstanceService().address == instance.getInstanceService().address
