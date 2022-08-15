import binascii
import brownie
import pytest

from brownie import (
    AccessController,
    InstanceOperatorService,
    InstanceService
)

from scripts.const import (
    ACCESS_NAME,
    INSTANCE_OPERATOR_SERVICE_NAME,
    INSTANCE_SERVICE_NAME,
)

from scripts.util import (
    h2sLeft,
    s2b32,
    contractFromAddress
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_non_existing_functionality(instance, owner):
    instanceOperatorService = instance.getInstanceOperatorService()
    with pytest.raises(AttributeError):
        assert instanceOperatorService.foo({'from': owner})


def test_instance_operator_service_contract_in_registry(instance, owner):
    instanceOperatorService = instance.getInstanceOperatorService()
    registry = instance.getRegistry()
    
    instanceOperatorServiceAddress = registry.getContract(s2b32(INSTANCE_OPERATOR_SERVICE_NAME))

    assert instanceOperatorService.address == instanceOperatorServiceAddress
    assert instanceOperatorService.address != 0x0


def test_role_granting(instance, owner, productOwner, customer):
    registry = instance.getRegistry()

    instanceOperatorServiceAddress = registry.getContract(s2b32(INSTANCE_OPERATOR_SERVICE_NAME))
    instanceOperatorService = contractFromAddress(InstanceOperatorService, instanceOperatorServiceAddress)

    instanceServiceAddress = registry.getContract(s2b32(INSTANCE_SERVICE_NAME))
    instanceService = contractFromAddress(InstanceService, instanceServiceAddress)

    # verify that after setup productOwner account does not yet have product owner role
    poRole = instanceService.getProductOwnerRole({'from': customer})
    assert not instanceService.hasRole(poRole, productOwner, {'from': customer})

    print('owner: {}'.format(owner))
    print('instanceOperatorServiceAddress: {}'.format(instanceOperatorServiceAddress))
    print('productOwner: {}'.format(productOwner))
    print('poRole: {}'.format(poRole))

    # verify that addRoleToAccount is protected and not anybody (ie customer) and grant roles
    with brownie.reverts():
        instanceOperatorService.grantRole(poRole, productOwner, {'from': customer})

    instanceOperatorService.grantRole(poRole, productOwner, {'from': owner})

    # verify that productOwner account now has product owner role
    assert instanceService.hasRole(poRole, productOwner, {'from': customer})


def test_default_admin_role_cannot_be_changed(instance, owner, customer):
    registry = instance.getRegistry()

    accessAddress = registry.getContract(s2b32(ACCESS_NAME))
    access = contractFromAddress(AccessController, accessAddress)

    with brownie.reverts():
        access.setDefaultAdminRole(customer, {'from': owner})

