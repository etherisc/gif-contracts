import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    interface,
    Wei,
    TestProduct,
    TestRiskpool,
)

from scripts.util import (
    s2h,
    s2b32,
)

from scripts.setup import (
    fund_riskpool,
    fund_customer,
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
    productOwner,
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
    bundle = _getBundle(instance, riskpool, 0)
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

    # create test policy before riskpool is paused
    product = gifTestProduct.getContract()
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, 100, 1000)

    # ensure that owner may not pause riskpool
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.pause(riskpoolId, {'from':owner})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpool keeper may pause riskpool
    componentOwnerService.pause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that riskpool actions are blocked for paused riskpool
    with brownie.reverts("ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.fundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.lockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.unlockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.closeBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.burnBundle(bundleId, {'from':bundleOwner})

    # ensure underwriting new policies is not possible for paused riskpool
    with brownie.reverts("ERROR:POL-004:RISKPOOL_NOT_ACTIVE"):
        policyId2 = apply_for_policy(instance, owner, product, customer, testCoin, 100, 1000)

    # ensure existing policies may be closed while riskpool is paused
    product.expire(policyId, {'from': productOwner})
    product.close(policyId, {'from': productOwner})

    # recored state of bundle 
    bundleAftePolicy = instanceService.getBundle(bundleId).dict()

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
    assert bundleDefunded["balance"] == bundleAftePolicy["balance"] - 10

    riskpool.setMaximumNumberOfActiveBundles(2, {'from':bundleOwner})
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
    bundle =  _getBundle(instance, riskpool, 0)
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
    with brownie.reverts("ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.fundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.defundBundle(bundleId, 10, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.lockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.unlockBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
        riskpool.closeBundle(bundleId, {'from':bundleOwner})

    with brownie.reverts("ERROR:RPS-007:RISKPOOL_NOT_ACTIVE"):
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

    riskpool.setMaximumNumberOfActiveBundles(2, {'from': riskpoolKeeper})

    tx = riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})
    bundle2Id = tx.return_value
    bundle2 = instanceService.getBundle(bundleId).dict()
    print(bundleFromCore)

    assert bundle2Id == bundleId + 1


def test_suspend_archive(
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
    bundle =  _getBundle(instance, riskpool, 0)
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

    # ensure that component owner and instance operator may not archive riskpool
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:CCR-024:ACTIVE_INVALID_TRANSITION"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})

    with brownie.reverts("ERROR:CCR-024:ACTIVE_INVALID_TRANSITION"):
        componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that instance operator may archive riskpool
    instanceOperatorService.suspend(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 5

    # ensure that instance operator may not archive riskpool due to active bundles
    with brownie.reverts("ERROR:RPL-010:RISKPOOL_HAS_UNBURNT_BUNDLES"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})

    # ensure that riskpool can be archived by burning bundle
    instanceOperatorService.resume(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 3
    riskpool.closeBundle(bundleId, {'from':bundleOwner})
    riskpool.burnBundle(bundleId, {'from':bundleOwner})
    instanceOperatorService.suspend(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 5

    # ensure that instance operator may archive riskpool
    instanceOperatorService.archive(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 6

    # ensure that riskpool actions are now blocked
    with brownie.reverts("ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    # ensure that a suspended component cannot be paused
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.pause(riskpoolId, {'from':owner})

    # ensure that a suspended component cannot be unpaused
    with brownie.reverts("ERROR:COS-004:NOT_OWNER"):
        componentOwnerService.unpause(riskpoolId, {'from':owner})

    # ensure that component owner may not archive archived riskpool
    with brownie.reverts("ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL"):
        componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})

    # ensure that component owner may not resume riskpool
    with brownie.reverts("ERROR:CCR-027:INITIAL_STATE_NOT_HANDLED"):
        instanceOperatorService.resume(riskpoolId, {'from':owner})

    # ensure that instance operator may not archive archived riskpool
    with brownie.reverts("ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})
    

def test_pause_archive_as_owner(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner,
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
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
    bundle =  _getBundle(instance, riskpool, 0)
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

    # ensure that owner may not archive riskpool
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:CCR-024:ACTIVE_INVALID_TRANSITION"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})

    with brownie.reverts("ERROR:CCR-024:ACTIVE_INVALID_TRANSITION"):
        componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpool keeper may pause riskpool
    componentOwnerService.pause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that instance operator may not archive riskpool due to active bundles
    with brownie.reverts("ERROR:RPL-010:RISKPOOL_HAS_UNBURNT_BUNDLES"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})

    # ensure that riskpool can be archived by burning bundle
    componentOwnerService.unpause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 3
    riskpool.closeBundle(bundleId, {'from':bundleOwner})
    riskpool.burnBundle(bundleId, {'from':bundleOwner})
    componentOwnerService.pause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that riskpool keeper may archive riskpool
    componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 6

    # ensure that riskpool actions are blocked for archived riskpool
    with brownie.reverts("ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    # ensure that owner may not unpause archived riskpool
    with brownie.reverts("ERROR:CCR-027:INITIAL_STATE_NOT_HANDLED"):
        componentOwnerService.unpause(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 6

    # ensure that component owner may not archive archived riskpool
    with brownie.reverts("ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL"):
        componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})
    
    # ensure that instance operator may not archive archived riskpool
    with brownie.reverts("ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})


def test_pause_archive_as_instance_operator(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner,
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()

    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    assert instanceService.getComponentState(riskpoolId) == 3

    initialFunding = 10000
    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding, False)

    assert 0 == riskpool.bundles()
    assert riskpoolId == riskpool.getId()

    componentOwnerService = instance.getComponentOwnerService()

    # ensure that instance operator may not archive active riskpool 
    assert owner != riskpoolKeeper
    with brownie.reverts("ERROR:CCR-024:ACTIVE_INVALID_TRANSITION"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})

    # ensure that owner may not archive active riskpool 
    with brownie.reverts("ERROR:CCR-024:ACTIVE_INVALID_TRANSITION"):
        componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 3

    # ensure that riskpool keeper may pause riskpool
    componentOwnerService.pause(riskpoolId, {'from':riskpoolKeeper})
    assert instanceService.getComponentState(riskpoolId) == 4

    # ensure that the instance operator may archive the paused riskpool
    instanceOperatorService.archive(riskpoolId, {'from':owner})
    assert instanceService.getComponentState(riskpoolId) == 6

    # ensure that riskpool actions are blocked for archived riskpool
    with brownie.reverts("ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':bundleOwner})

    # ensure that owner may not unpause archived riskpool
    with brownie.reverts("ERROR:CCR-027:INITIAL_STATE_NOT_HANDLED"):
        componentOwnerService.unpause(riskpoolId, {'from':riskpoolKeeper})

    assert instanceService.getComponentState(riskpoolId) == 6

        # ensure that component owner may not archive archived riskpool
    with brownie.reverts("ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL"):
        componentOwnerService.archive(riskpoolId, {'from':riskpoolKeeper})
    
    # ensure that instance operator may not archive archived riskpool
    with brownie.reverts("ERROR:CCR-020:SOURCE_AND_TARGET_STATE_IDENTICAL"):
        instanceOperatorService.archive(riskpoolId, {'from':owner})


def test_propose_decline(
    instance: GifInstance, 
    riskpoolKeeper: Account,
    testCoin: Account,
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
        testCoin,
        capitalOwner,
        instance.getRegistry(),
        {'from': riskpoolKeeper},
        publish_source=publishSource)

    # 3) riskpool keeperproposes riskpool to instance
    componentOwnerService.propose(
        riskpool,
        {'from': riskpoolKeeper})

    riskpoolId = riskpool.getId()

    pool = instanceService.getRiskpool(riskpoolId).dict();
    print(pool)
    assert pool['id'] == riskpoolId
    assert pool['wallet'] == riskpool.getWallet()
    assert pool['erc20Token'] == riskpool.getErc20Token()
    assert pool['collateralizationLevel'] == riskpool.getCollateralizationLevel()
    assert pool['sumOfSumInsuredCap'] == riskpool.getSumOfSumInsuredCap()

    # ensure component is proposed
    assert instanceService.getComponentState(riskpoolId) == 1

    # ensure that component owner may not decline riskpool
    with brownie.reverts("ERROR:IOS-001:NOT_INSTANCE_OPERATOR"):
        instanceOperatorService.decline(riskpoolId, {'from':riskpoolKeeper})

    # ensure that instance operator may decline riskpool
    instanceOperatorService.decline(riskpoolId, {'from': instance.getOwner()})

    # ensure component is declined
    assert instanceService.getComponentState(riskpoolId) == 2

    # ensure that declined riskpool cannot be approved 
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.approve(
            riskpoolId,
            {'from': instance.getOwner()})
    
    # ensure that declined riskpool cannot be suspended
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.suspend(
            riskpoolId,
            {'from': instance.getOwner()})

    # ensure that declined riskpool cannot be resumed
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.resume(
            riskpoolId,
            {'from': instance.getOwner()})

    # ensure that declined riskpool cannot be archived by instance operator
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        instanceOperatorService.archive(
            riskpoolId,
            {'from': instance.getOwner()})
        
    # ensure that declined riskpool cannot be paused
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        componentOwnerService.pause(
            riskpoolId,
            {'from': riskpoolKeeper})

    # ensure that declined riskpool cannot be unpaused
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        componentOwnerService.unpause(
            riskpoolId,
            {'from': riskpoolKeeper})

    # ensure that declined riskpool cannot be archived by owner
    with brownie.reverts("ERROR:CCR-023:DECLINED_IS_FINAL_STATE"):
        componentOwnerService.archive(
            riskpoolId,
            {'from': riskpoolKeeper})
    
    # ensure that no bundles can be created on declined riskpool
    with brownie.reverts("ERROR:RPS-004:RISKPOOL_NOT_ACTIVE"):
        riskpool.createBundle(bytes(0), 50, {'from':riskpoolKeeper})


def _getBundle(instance, riskpool, bundleIdx):
    instanceService = instance.getInstanceService()
    bundleId = riskpool.getBundleId(bundleIdx)
    return instanceService.getBundle(bundleId)

def test_policy_application_with_inactive_riskpool(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    instanceOperator: Account,
    productOwner: Account,
    riskpoolKeeper: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()
    initialFunding = 10000
    fund_riskpool(instance, instanceOperator, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # pause riskpool
    componentOwnerService = instance.getComponentOwnerService()
    componentOwnerService.pause(riskpoolId, {'from': riskpoolKeeper})    
    assert riskpool.getState() == 4

    # attempt to create policy
    product = gifTestProduct.getContract()
    premium = 300
    sumInsured = 2000

    with brownie.reverts('ERROR:POL-004:RISKPOOL_NOT_ACTIVE'):
        product.applyForPolicy(premium, sumInsured, bytes(0), bytes(0), {'from': customer})

    assert product.policies() == 0

    # unpuase riskpool again
    componentOwnerService.unpause(riskpoolId, {'from': riskpoolKeeper})    
    assert riskpool.getState() == 3

    # verify that policy creation works
    tx = product.applyForPolicy(premium, sumInsured, bytes(0), bytes(0), {'from': customer})
    processId = tx.return_value

    assert product.policies() == 1


def test_collect_premium_with_inactive_riskpool(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    instanceOperator: Account,
    productOwner: Account,
    riskpoolKeeper: Account,
    customer: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()
    initialFunding = 10000
    fund_riskpool(instance, instanceOperator, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create policy
    product = gifTestProduct.getContract()
    premium = 300
    sumInsured = 2000
    tx = product.applyForPolicy(premium, sumInsured, bytes(0), bytes(0), {'from': customer})
    processId = tx.return_value

    # ComponentState {Created,Proposed,Declined,Active,Paused,Suspended}
    assert product.policies() == 1
    assert riskpool.getState() == 3

    # pause riskpool
    componentOwnerService = instance.getComponentOwnerService()
    componentOwnerService.pause(riskpoolId, {'from': riskpoolKeeper})
    
    assert riskpool.getState() == 4
    # fund customer to pay premium now
    fund_customer(instance, instanceOperator, customer, testCoin, premium)
    assert testCoin.balanceOf(customer) == premium
    assert testCoin.allowance(customer, instance.getTreasury()) == premium

    # attempt to collect premium with paused riskpool
    with brownie.reverts('ERROR:POL-004:RISKPOOL_NOT_ACTIVE'):
        product.collectPremium(processId, premium, {'from': productOwner})

    assert testCoin.balanceOf(customer) == premium

    # unpuase riskpool
    componentOwnerService.unpause(riskpoolId, {'from': riskpoolKeeper})    
    assert riskpool.getState() == 3

    # ensure that collecting premiums works again
    tx = product.collectPremium(processId, premium, {'from': productOwner})
    (success, fee, netPremium) = tx.return_value

    assert success
    assert testCoin.balanceOf(customer) == 0




def test_payout_processing_with_inactive_riskpool(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    instanceOperator: Account,
    productOwner: Account,
    riskpoolKeeper: Account,
    customer: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()

    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()
    initialFunding = 10000
    fund_riskpool(instance, instanceOperator, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # fund customer to pay premium now
    premium = 300
    fund_customer(instance, instanceOperator, customer, testCoin, premium)
    assert testCoin.balanceOf(customer) == premium
    assert testCoin.allowance(customer, instance.getTreasury()) == premium

    # create policy
    product = gifTestProduct.getContract()
    sumInsured = 2000
    tx = product.applyForPolicy(premium, sumInsured, bytes(0), bytes(0), {'from': customer})
    processId = tx.return_value

    # ComponentState {Created,Proposed,Declined,Active,Paused,Suspended}
    assert instanceService.processIds() == 1
    assert instanceService.claims(processId) == 0
    assert product.policies() == 1
    assert riskpool.getState() == 3

    # pause riskpool
    componentOwnerService = instance.getComponentOwnerService()
    componentOwnerService.pause(riskpoolId, {'from': riskpoolKeeper})
    
    assert riskpool.getState() == 4

    claimAmount = 3 * premium
    (claimId, payoutId) = create_claim_no_oracle(product, customer, productOwner, processId, claimAmount)

    assert instanceService.claims(processId) == 1
    assert instanceService.payouts(processId) == 1
    assert testCoin.balanceOf(customer) == 0

    # attempt to process payout
    with brownie.reverts('ERROR:POL-004:RISKPOOL_NOT_ACTIVE'):
        product.processPayout(processId, payoutId, {'from':productOwner})

    assert instanceService.claims(processId) == 1
    assert instanceService.payouts(processId) == 1
    assert testCoin.balanceOf(customer) == 0

    # unpause riskpool
    componentOwnerService = instance.getComponentOwnerService()
    componentOwnerService.unpause(riskpoolId, {'from': riskpoolKeeper})
    
    assert riskpool.getState() == 3

    # enwure process payout works again
    product.processPayout(processId, payoutId, {'from':productOwner})

    assert instanceService.claims(processId) == 1
    assert instanceService.payouts(processId) == 1
    assert testCoin.balanceOf(customer) == claimAmount

    # ensure it's not possible to process same payout a 2nd time
    with brownie.reverts('ERROR:POC-091:POLICY_WITHOUT_OPEN_CLAIMS'):
        product.processPayout(processId, payoutId, {'from':productOwner})

    assert instanceService.claims(processId) == 1
    assert instanceService.payouts(processId) == 1
    assert testCoin.balanceOf(customer) == claimAmount


def create_claim_no_oracle(product, customer, productOwner, processId, claimAmount):
    tx = product.submitClaimNoOracle(processId, claimAmount, {'from':customer})
    claimId = tx.return_value
    product.confirmClaim(processId, claimId, claimAmount, {'from':productOwner})

    tx = product.newPayout(processId, claimId, claimAmount, {'from':productOwner})
    payoutId = tx.return_value

    return (claimId, payoutId)
