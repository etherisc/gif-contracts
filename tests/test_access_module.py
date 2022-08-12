import brownie
import pytest

from scripts.util import keccak256

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
    (poRole, opRole, rkRole) = getRoles(instanceService)

    assert poRole != opRole
    assert poRole != rkRole
    assert opRole != rkRole

    assert poRole == keccak256('PRODUCT_OWNER_ROLE')
    assert opRole == keccak256('ORACLE_PROVIDER_ROLE')
    assert rkRole == keccak256('RISKPOOL_KEEPER_ROLE')

    assert not instanceService.hasRole(poRole, productOwner)
    assert not instanceService.hasRole(opRole, oracleProvider)
    assert not instanceService.hasRole(rkRole, riskpoolKeeper)


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
    
    (poRole, opRole, rkRole) = getRoles(instanceService)

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
    
    (poRole, opRole, rkRole) = getRoles(instanceService)

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

    return (poRole, opRole, rkRole)
