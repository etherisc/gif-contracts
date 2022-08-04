import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    interface,
    Wei,
    TestProduct,
    TestRiskpool,
)

from scripts.const import (
    PRODUCT_NAME,
    PRODUCT_ID,
    RISKPOOL_NAME,
)

from scripts.util import (
    s2h,
    s2b32,
)

from scripts.setup import (
    fund_riskpool,
    apply_for_policy,
)

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestProduct,
    GifTestRiskpool,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_pause_unpause(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()

    instanceService = instance.getInstanceService()
    assert instanceService.getComponentState(riskpoolId) == 3

    initialFunding = 10000
    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding)

    riskpool.bundles() == 1
    bundle = riskpool.getBundle(0)
    print(bundle)

    (
        bundleId,
        riskpoolId,
        tokenId,
        state,
        filter,
        capital,
        lockedCapital,
        balance,
        createdAt,
        updatedAt
    ) = bundle

    # check bundle values with expectation
    assert bundleId == 1
    assert riskpoolId == riskpool.getId()

    # verify that attributes directly from riskpool match with 
    # bundle attributes from instance service
    bundleFromCore = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundleFromCore["id"] == bundleId
    assert bundleFromCore["riskpoolId"] == riskpoolId
    assert bundleFromCore["tokenId"] == tokenId
    assert bundleFromCore["state"] == state
    assert bundleFromCore["filter"] == filter
    assert bundleFromCore["capital"] == capital
    assert bundleFromCore["lockedCapital"] == lockedCapital
    assert bundleFromCore["balance"] == balance
    assert bundleFromCore["createdAt"] == createdAt
    assert bundleFromCore["updatedAt"] == updatedAt

    componentOwnerService = instance.getComponentOwnerService()

    # ensure that owner may not pause riskpool
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.pause(riskpoolId, {'from':owner})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpool keeper may pause riskpool
    componentOwnerService.pause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that riskpool actions are now blocked
    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.fundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.lockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.unlockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.closeBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.burnBundle(bundleId, {'from':bundleOwner})

    # ensure that owner may not unpause riskpool
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.unpause(riskpoolId, {'from':owner})

    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that riskpool keeper may unpause riskpool
    componentOwnerService.unpause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpol actions work again
    riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})
    bundleDefunded = instanceService.getBundle(bundleId).dict()
    assert bundleDefunded["balance"] == balance - 10

    tx = riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})
    bundle2Id = tx.return_value
    bundle2 = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundle2Id == bundleId + 1

def test_suspend_resume(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    capitalOwner: Account
):
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()

    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    assert instanceService.getComponentState(riskpoolId) == 3

    initialFunding = 10000
    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding)

    riskpool.bundles() == 1
    bundle = riskpool.getBundle(0)
    print(bundle)

    (
        bundleId,
        riskpoolId,
        tokenId,
        state,
        filter,
        capital,
        lockedCapital,
        balance,
        createdAt,
        updatedAt
    ) = bundle

    # check bundle values with expectation
    assert bundleId == 1
    assert riskpoolId == riskpool.getId()
    assert owner != riskpool.owner()
    print(riskpool.owner())

    # verify that attributes directly from riskpool match with 
    # bundle attributes from instance service
    bundleFromCore = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundleFromCore["id"] == bundleId
    assert bundleFromCore["riskpoolId"] == riskpoolId
    assert bundleFromCore["tokenId"] == tokenId
    assert bundleFromCore["state"] == state
    assert bundleFromCore["filter"] == filter
    assert bundleFromCore["capital"] == capital
    assert bundleFromCore["lockedCapital"] == lockedCapital
    assert bundleFromCore["balance"] == balance
    assert bundleFromCore["createdAt"] == createdAt
    assert bundleFromCore["updatedAt"] == updatedAt

    componentOwnerService = instance.getComponentOwnerService()

    # ensure that component owner may not suspend riskpool
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:IOS-001:NOT_INSTANCE_OPERATOR"):
        instanceOperatorService.suspend(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that instance operator may suspend riskpool
    instanceOperatorService.suspend(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 5

    # ensure that riskpool actions are now blocked
    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.fundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.lockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.unlockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.closeBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.burnBundle(bundleId, {'from':bundleOwner})

    # ensure that a suspended component cannot be paused
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.pause(riskpoolId, {'from':owner})

    # ensure that a suspended component cannot be unpaused
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.unpause(riskpoolId, {'from':owner})

    # ensure that component owner may not resume riskpool
    with brownie.reverts("ERROR:IOS-001:NOT_INSTANCE_OPERATOR"):
        instanceOperatorService.resume(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 5

    # ensure that instance operator may resume riskpool
    instanceOperatorService.resume(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpol actions work again
    riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})
    bundleDefunded = instanceService.getBundle(bundleId).dict()
    assert bundleDefunded["balance"] == balance - 10

    tx = riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})
    bundle2Id = tx.return_value
    bundle2 = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundle2Id == bundleId + 1


def test_propose_decline(
    instance: GifInstance, 
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()
    name="Test.Riskpool.ToBeDeclined"
    collateralization = 10**18
    publishSource=False

    # 1) add role to keeper
    keeperRole = instanceService.getRiskpoolKeeperRole()
    instanceOperatorService.grantRole(
        keeperRole, 
        riskpoolKeeper, 
        {'from': instance.getOwner()})

    # 2) keeper deploys riskpool
    riskpool = TestRiskpool.deploy(
        s2b32(name),
        collateralization,
        capitalOwner,
        instance.getRegistry(),
        {'from': riskpoolKeeper},
        publish_source=publishSource)

    # 3) riskpool keeperproposes riskpool to instance
    componentOwnerService.propose(
        riskpool,
        {'from': riskpoolKeeper})

    riskpoolId = riskpool.getId()

    # ensure component is proposed
    assert instanceService.getComponentState(riskpoolId) == 1

    # ensure that component owner may not decline riskpool
    with brownie.reverts("ERROR:IOS-001:NOT_INSTANCE_OPERATOR"):
        instanceOperatorService.decline(riskpoolId, {'from':riskpoolKeeper})

    instanceOperatorService.decline(riskpoolId, {'from': instance.getOwner()})

    # ensure component is declined
    assert instanceService.getComponentState(riskpoolId) == 2

    with brownie.reverts("ERROR:CMP-014:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.approve(
            riskpoolId,
            {'from': instance.getOwner()})
    
    with brownie.reverts("ERROR:CMP-014:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.suspend(
            riskpoolId,
            {'from': instance.getOwner()})

    with brownie.reverts("ERROR:CMP-014:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.resume(
            riskpoolId,
            {'from': instance.getOwner()})
        
    with brownie.reverts("ERROR:CMP-014:DECLINED_IS_FINAL_STATE"):
        componentOwnerService.pause(
            riskpoolId,
            {'from': riskpoolKeeper})

    with brownie.reverts("ERROR:CMP-014:DECLINED_IS_FINAL_STATE"):
        componentOwnerService.unpause(
            riskpoolId,
            {'from': riskpoolKeeper})
    
    with brownie.reverts("ERROR:RPS-002:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':riskpoolKeeper})
