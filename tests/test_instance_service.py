import binascii
import brownie
import pytest

from web3 import Web3

from brownie import (
    InstanceService,
    interface
)

from scripts.const import (
    COMPONENT_OWNER_SERVICE_NAME,
    INSTANCE_OPERATOR_SERVICE_NAME,
    INSTANCE_SERVICE_NAME,
    ORACLE_SERVICE_NAME,
    PRODUCT_SERVICE_NAME,
    RISKPOOL_SERVICE_NAME,
    ZERO_ADDRESS
)

from scripts.util import (
    contractFromAddress,
    s2b32,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_get_chain_id(instance):
    w3 = Web3()
    instanceService = instance.getInstanceService()
    assert instanceService.getChainId() == w3.eth.chain_id


def test_get_instance_id(instance):
    instanceService = instance.getInstanceService()
    registryAddress = instanceService.getRegistry()

    gifInstanceId = instanceService.getInstanceId()
    web3keccak = Web3.solidityKeccak(
        ['uint256', 'address'], 
        [instanceService.getChainId(), registryAddress]).hex()

    assert gifInstanceId == web3keccak


def test_services_against_registry(instance, owner):
    instanceService = instance.getInstanceService()
    registryAddress = instanceService.getRegistry()
    registry = contractFromAddress(interface.IRegistry, registryAddress)
    isAddressFromRegistry = _addressFrom(registry, INSTANCE_SERVICE_NAME)

    assert instanceService.address == isAddressFromRegistry
    assert instanceService.address != 0x0

    psAddress = _addressFrom(registry, PRODUCT_SERVICE_NAME)
    assert psAddress != ZERO_ADDRESS
    assert instanceService.getProductService() == psAddress

    osAddress = _addressFrom(registry, ORACLE_SERVICE_NAME)
    assert osAddress != ZERO_ADDRESS
    assert instanceService.getOracleService() == osAddress

    rsAddress = _addressFrom(registry, RISKPOOL_SERVICE_NAME)
    assert rsAddress != ZERO_ADDRESS
    assert instanceService.getRiskpoolService() == rsAddress

    cosAddress = _addressFrom(registry, COMPONENT_OWNER_SERVICE_NAME)
    assert cosAddress != ZERO_ADDRESS
    assert instanceService.getComponentOwnerService() == cosAddress

    iosAddress = _addressFrom(registry, INSTANCE_OPERATOR_SERVICE_NAME)
    assert iosAddress != ZERO_ADDRESS
    assert instanceService.getInstanceOperatorService() == iosAddress

def _addressFrom(registry, contractName):
    return registry.getContract(s2b32(contractName))
