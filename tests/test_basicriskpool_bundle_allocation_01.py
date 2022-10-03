import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    interface,
    Wei,
    TestProduct,
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


def test_bundle_allocation_with_one_bundle(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    
    initialFunding = 10000

    # fund the riskpool with two bundles
    bid1 = fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)
    
    assert 1 == riskpool.bundles()

    # ensure the bundles are configured
    bundle = _getBundle(instance, riskpool, 0)
    (
        bundleId,
        riskpoolId,
        _,
        state,
        _,
        _,
        lockedCapital,
        *_
    ) = bundle

    assert bundleId == 1
    assert riskpoolId == riskpool.getId()
    assert lockedCapital == 0

    # apply for the first policy
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, 100, 3000)
    
    # ensure is correctly configured
    policyController = instance.getPolicy()
    application = policyController.getApplication(policyId).dict()
    policy = policyController.getPolicy(policyId).dict()

    assert policy is not None
    # PolicyState {Active, Expired}
    assert application['state'] == 2
    assert policy['state'] == 0

    # apply for the second policy    
    policyId2 = apply_for_policy(instance, owner, product, customer, testCoin, 100, 4000)

    # ensure is correctly configured    
    metadata2 = policyController.getMetadata(policyId2).dict()
    application2 = policyController.getApplication(policyId2).dict()
    policy2 = policyController.getPolicy(policyId2).dict()

    assert policy2 is not None
    # PolicyState {Active, Expired}
    assert application2['state'] == 2
    assert policy2['state'] == 0


    # get updates bundle values
    bundle = _getBundle(instance, riskpool, 0)
    (
        bundleId,
        riskpoolId,
        _,
        state,
        _,
        _,
        lockedCapital,
        *_
    ) = bundle

    # ensure the policies were allocated to different bundles
    assert lockedCapital == 7000

def test_bundle_allocation_with_three_equal_bundles(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    num_bundles = 3
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpool.setMaximumNumberOfActiveBundles(num_bundles, {'from': riskpoolKeeper})

    initialFunding = 10000

    # fund the riskpools
    for _ in range(num_bundles):
        fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)
    
    assert num_bundles == riskpool.bundles()

    # allocate 3 policies in every bundle
    for _ in range(num_bundles * 3):
        apply_for_policy(instance, owner, product, customer, testCoin, 100, 1000)
    

    # ensure every bundle has same locked capital
    for i in range(num_bundles):
        # get updates bundle values
        bundle = _getBundle(instance, riskpool, i)
        (
            _,
            _,
            _,
            _,
            _,
            _,
            lockedCapital,
            *_
        ) = bundle

        assert 3000 == lockedCapital


def test_failing_bundle_allocation(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):    
    num_bundles = 2
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpool.setMaximumNumberOfActiveBundles(num_bundles, {'from': riskpoolKeeper})
    instanceService = instance.getInstanceService()

    initialFunding = 1000

    # fund the riskpools
    for _ in range(num_bundles):
        fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create minimal policy application
    premium = 100
    sumInsured = 1200
    metaData = bytes(0)
    applicationData = bytes(0)

    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premium, {'from': customer})

    tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    
    processId = tx.return_value

    print('processId {}'.format(processId))
    print(tx.info())

    assert 'LogRiskpoolCollateralizationFailed' in tx.events
    assert len(tx.events['LogRiskpoolCollateralizationFailed']) == 1

    failedEvent = tx.events['LogRiskpoolCollateralizationFailed'][0]
    assert failedEvent['processId'] == processId
    assert failedEvent['amount'] == sumInsured

    application = instanceService.getApplication(processId)
    applicationState = application[0]
    assert applicationState == 0 # enum ApplicationState {Applied, Revoked, Underwritten, Declined}


def _getBundle(instance, riskpool, bundleIdx):
    instanceService = instance.getInstanceService()
    bundleId = riskpool.getBundleId(bundleIdx)
    return instanceService.getBundle(bundleId)
