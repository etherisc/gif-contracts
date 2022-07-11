import brownie
import pytest

from scripts.const import (
    GIF_RELEASE,
    REGISTRY_NAME,
    ACCESS_NAME,
    BUNDLE_NAME,
    COMPONENT_NAME,
    LICENSE_NAME,
    POLICY_NAME,
    POLICY_FLOW_DEFAULT_NAME,
    POOL_NAME,
    COMPONENT_OWNER_SERVICE_NAME,
    INSTANCE_OPERATOR_SERVICE_NAME,
    INSTANCE_SERVICE_NAME,
    ORACLE_SERVICE_NAME,
    PRODUCT_SERVICE_NAME,
    RISKPOOL_SERVICE_NAME,
)

from scripts.instance import GifInstance
from scripts.util import s2b32


def test_Registry(instance: GifInstance, owner):
    registry = instance.getRegistry()

    assert registry.address == registry.getContract(s2b32(REGISTRY_NAME))
    assert registry.getRelease() == s2b32(GIF_RELEASE)

    with pytest.raises(AttributeError):
        assert registry.foo({'from': owner})


def test_Access(instance: GifInstance, owner):
    registry = instance.getRegistry()
    access = instance.getAccess()

    assert access.address == registry.getContract(s2b32(ACCESS_NAME))
    assert access.address != 0x0

    assert access.productOwnerRole() != access.oracleProviderRole()
    assert access.oracleProviderRole() != access.riskpoolKeeperRole()
    assert access.riskpoolKeeperRole() != access.productOwnerRole()

    with pytest.raises(AttributeError):
        assert access.foo({'from': owner})


def test_Bundle(instance: GifInstance, owner):
    registry = instance.getRegistry()
    bundle = instance.getBundle()

    assert bundle.address == registry.getContract(s2b32(BUNDLE_NAME))
    assert bundle.address != 0x0

    assert bundle.bundles() == 0

    with brownie.reverts('ERROR:BUC-001:BUNDLE_DOES_NOT_EXIST'):
        bundle.getBundle(0)

    with pytest.raises(AttributeError):
        assert bundle.foo({'from': owner})


def test_Component(instance: GifInstance, owner):
    registry = instance.getRegistry()
    component = instance.getComponent()

    assert component.address == registry.getContract(s2b32(COMPONENT_NAME))
    assert component.address != 0x0

    assert component.exists(1) == False 
    assert component.components() == 0
    assert component.products() == 0
    assert component.oracles() == 0
    assert component.riskpools() == 0

    with pytest.raises(AttributeError):
        assert component.foo({'from': owner})


def test_License(instance: GifInstance, owner):
    registry = instance.getRegistry()
    license = instance.getLicense()

    assert license.address == registry.getContract(s2b32(LICENSE_NAME))
    assert license.address != 0x0

    assert license.getProductId(owner) == 0

    with pytest.raises(AttributeError):
        assert license.foo({'from': owner})


def test_Policy(instance: GifInstance, owner):
    registry = instance.getRegistry()
    policy = instance.getPolicy()

    assert policy.address == registry.getContract(s2b32(POLICY_NAME))
    assert policy.address != 0x0

    assert policy.processIds() == 0
    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        policy.getPolicy(s2b32(''))

    with pytest.raises(AttributeError):
        assert policy.foo({'from': owner})


def test_PolicyFlowDefault(instance: GifInstance, owner):
    registry = instance.getRegistry()
    policyFlowDefault = instance.getPolicyFlowDefault()

    policyFlowDefaultAddress = registry.getContract(s2b32(POLICY_FLOW_DEFAULT_NAME))

    assert policyFlowDefault.address == policyFlowDefaultAddress
    assert policyFlowDefault.address != 0x0

    with brownie.reverts('ERROR:POC-051:APPLICATION_DOES_NOT_EXIST'):
        policyFlowDefault.decline(s2b32(''))

    with pytest.raises(AttributeError):
        assert policyFlowDefault.foo({'from': owner})


def test_Pool(instance: GifInstance, owner):
    registry = instance.getRegistry()
    pool = instance.getPool()

    assert pool.address == registry.getContract(s2b32(POOL_NAME))
    assert pool.address != 0x0

    assert pool.riskpools() == 0

    with pytest.raises(AttributeError):
        assert pool.foo({'from': owner})


def test_InstanceService(instance, registry, owner):
    registry = instance.getRegistry()
    instanceService = instance.getInstanceService()

    assert instanceService.address == registry.getContract(s2b32(INSTANCE_SERVICE_NAME))
    assert instanceService.getOwner() == owner
    assert owner != 0x0

    with pytest.raises(AttributeError):
        assert instanceService.foo({'from': owner})


def test_OracleService(instance, registry, owner):
    registry = instance.getRegistry()
    oracleService = instance.getOracleService()

    assert oracleService.address == registry.getContract(s2b32(ORACLE_SERVICE_NAME))
    assert oracleService.address != 0x0

    with pytest.raises(AttributeError):
        assert oracleService.foo({'from': owner})


def test_ProductService(instance, registry, owner):
    registry = instance.getRegistry()
    productService = instance.getProductService()

    assert productService.address == registry.getContract(s2b32(PRODUCT_SERVICE_NAME))
    assert productService.address != 0x0

    with pytest.raises(AttributeError):
        assert productService.foo({'from': owner})


def test_RiskpoolService(instance, registry, owner):
    registry = instance.getRegistry()
    riskpoolService = instance.getRiskpoolService()

    assert riskpoolService.address == registry.getContract(s2b32(RISKPOOL_SERVICE_NAME))
    assert riskpoolService.address != 0x0

    with pytest.raises(AttributeError):
        assert riskpoolService.foo({'from': owner})
