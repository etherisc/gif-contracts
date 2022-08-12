import brownie
import pytest

from brownie import AccessController

from scripts.util import (
    keccak256, 
    s2b32,
    contractFromAddress
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_initial_setup(
    instance,
    owner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    (poRole, opRole, rkRole, daRole) = getRoles(instanceService)

    assert poRole != opRole
    assert poRole != rkRole
    assert poRole != daRole
    assert opRole != rkRole
    assert opRole != daRole
    assert rkRole != daRole

    assert poRole == keccak256('PRODUCT_OWNER_ROLE')
    assert opRole == keccak256('ORACLE_PROVIDER_ROLE')
    assert rkRole == keccak256('RISKPOOL_KEEPER_ROLE')

    # check component owners against their roles
    assert not instanceService.hasRole(poRole, productOwner)
    assert not instanceService.hasRole(opRole, oracleProvider)
    assert not instanceService.hasRole(rkRole, riskpoolKeeper)

    # check default role assignemnt
    assert instanceService.hasRole(daRole, instanceOperatorService.address)


def test_default_admin_role(
    instance,
    owner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
):
    instanceOperatorService = instance.getInstanceOperatorService()
    instanceService = instance.getInstanceService()
    ioDict = {'from': owner}
    
    (poRole, opRole, rkRole, daRole) = getRoles(instanceService)

    # check default admin role assignemnt to instance operator service
    assert instanceService.hasRole(daRole, instanceOperatorService.address)

    registry = instance.getRegistry()
    access = contractFromAddress(AccessController, registry.getContract(s2b32('Access')))

    # check that 'random' accaounts can't re-assign the admin role
    with brownie.reverts('ERROR:ACL-001:ADMIN_ROLE_ALREADY_SET'):
        access.setDefaultAdminRole(productOwner, {'from': productOwner})

    # check that not even the instance operator can change the role assignment
    with brownie.reverts('ERROR:ACL-001:ADMIN_ROLE_ALREADY_SET'):
        access.setDefaultAdminRole(productOwner, ioDict)


def test_role_assignment(
    instance,
    owner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
):
    instanceOperatorService = instance.getInstanceOperatorService()
    instanceService = instance.getInstanceService()
    ioDict = {'from': owner}
    
    (poRole, opRole, rkRole, daRole) = getRoles(instanceService)

    instanceOperatorService.grantRole(poRole, productOwner, ioDict)
    instanceOperatorService.grantRole(opRole, oracleProvider, ioDict)
    instanceOperatorService.grantRole(rkRole, riskpoolKeeper, ioDict)

    assert instanceService.hasRole(poRole, productOwner)
    assert instanceService.hasRole(opRole, oracleProvider)
    assert instanceService.hasRole(rkRole, riskpoolKeeper)

    instanceOperatorService.revokeRole(poRole, productOwner, ioDict)
    instanceOperatorService.revokeRole(opRole, oracleProvider, ioDict)
    instanceOperatorService.revokeRole(rkRole, riskpoolKeeper, ioDict)

    assert not instanceService.hasRole(poRole, productOwner)
    assert not instanceService.hasRole(opRole, oracleProvider)
    assert not instanceService.hasRole(rkRole, riskpoolKeeper)


def test_role_creation(
    instance,
    owner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
):
    instanceOperatorService = instance.getInstanceOperatorService()
    instanceService = instance.getInstanceService()
    ioDict = {'from': owner}

    NEW_ROLE = keccak256('NEW_ROLE')

    # check that unknown roles cannot be granted
    with brownie.reverts('ERROR:ACL-002:ROLE_UNKNOWN_OR_INVALID'):
        instanceOperatorService.grantRole(NEW_ROLE, productOwner, ioDict)

    # check that a non instance operator cannot create new role
    with brownie.reverts('ERROR:IOS-001:NOT_INSTANCE_OPERATOR'):
        instanceOperatorService.createRole(NEW_ROLE, {'from': productOwner})

    # role creation
    instanceOperatorService.createRole(NEW_ROLE, ioDict)

    assert not instanceService.hasRole(NEW_ROLE, productOwner)

    # grant newly created role
    instanceOperatorService.grantRole(NEW_ROLE, productOwner, ioDict)

    # check granting
    assert instanceService.hasRole(NEW_ROLE, productOwner)


def test_role_invalidation(
    instance,
    owner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
):
    instanceOperatorService = instance.getInstanceOperatorService()
    instanceService = instance.getInstanceService()
    ioDict = {'from': owner}
    
    (poRole, opRole, rkRole, daRole) = getRoles(instanceService)

    instanceOperatorService.grantRole(poRole, productOwner, ioDict)

    # check that a non instance operator cannot invalidate a role
    with brownie.reverts('ERROR:IOS-001:NOT_INSTANCE_OPERATOR'):
        instanceOperatorService.invalidateRole(poRole, {'from': productOwner})

    NEW_ROLE = keccak256('NEW_ROLE')

    with brownie.reverts('ERROR:ACL-004:ROLE_UNKNOWN_OR_INVALID'):
        instanceOperatorService.invalidateRole(NEW_ROLE, ioDict)

    instanceOperatorService.invalidateRole(poRole, ioDict)

    with brownie.reverts('ERROR:ACL-002:ROLE_UNKNOWN_OR_INVALID'):
        instanceOperatorService.grantRole(poRole, oracleProvider, ioDict)


def getRoles(instanceService):
    poRole = instanceService.getProductOwnerRole()
    opRole = instanceService.getOracleProviderRole()
    rkRole = instanceService.getRiskpoolKeeperRole()
    daRole = instanceService.getDefaultAdminRole()

    return (poRole, opRole, rkRole, daRole)
