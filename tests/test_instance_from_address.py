import pytest

from brownie.network.account import Account

from scripts.instance import (
    GifRegistry,
    GifInstance,
)


def test_instance_addresses(instance: GifInstance):
    address = instance.getRegistry().address
    addrInst = GifInstance(registry_address=address)

    assert addrInst.getInstanceOperatorService().address == instance.getInstanceOperatorService().address
    assert addrInst.getOracleOwnerService().address == instance.getOracleOwnerService().address
    assert addrInst.getOracleService().address == instance.getOracleService().address
    assert addrInst.getPolicyController().address == instance.getPolicyController().address
    assert addrInst.getProductService().address == instance.getProductService().address
    assert addrInst.getRegistry().address == address
