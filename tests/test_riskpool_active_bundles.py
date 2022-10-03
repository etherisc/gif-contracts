import brownie
import pytest

from brownie.network.account import Account

from scripts.setup import (
    fund_riskpool,
)

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestProduct,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_create_bundle_max_active(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    riskpoolKeeper: Account,
    owner: Account,
    riskpoolWallet: Account
):
    riskpool = gifTestProduct.getRiskpool().getContract()
    riskpoolId = riskpool.getId()

    instanceService = instance.getInstanceService()
    assert instanceService.getComponentState(riskpoolId) == 3

    initialFunding = 10000
    fund_riskpool(instance, owner, riskpoolWallet, riskpool, riskpoolKeeper, testCoin, initialFunding)

    testCoin.transfer(riskpoolKeeper, 10 * initialFunding, {'from': owner})
    testCoin.approve(instance.getTreasury(), 10 * initialFunding, {'from': riskpoolKeeper})
    
    assert riskpool.bundles() == 1
    assert riskpool.activeBundles() == 1
    assert instanceService.activeBundles(riskpoolId) == 1

    bundle1 = _getBundle(instance, riskpool, 0)

    # ensure creation of another bundle is not allowed (max active bundles is 1 by default)
    with brownie.reverts("ERROR:POL-043:MAXIMUM_NUMBER_OF_ACTIVE_BUNDLES_REACHED"):
        riskpool.createBundle(
                bytes(0), 
                initialFunding, 
                {'from': riskpoolKeeper})

    riskpool.closeBundle(bundle1[0], {'from': riskpoolKeeper})

    assert riskpool.bundles() == 1
    assert riskpool.activeBundles() == 0
    assert instanceService.activeBundles(riskpoolId) == 0

    riskpool.createBundle(
        bytes(0), 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 2
    assert riskpool.activeBundles() == 1
    assert instanceService.activeBundles(riskpoolId) == 1

    # ensure a seconds bundle can be added when setting max active bundles to 2
    riskpool.setMaximumNumberOfActiveBundles(2, {'from': riskpoolKeeper})
    riskpool.createBundle(
        bytes(0), 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 3
    assert riskpool.activeBundles() == 2
    assert instanceService.activeBundles(riskpoolId) == 2

    bundle2 = _getBundle(instance, riskpool, 1)
    bundle3 = _getBundle(instance, riskpool, 2)
    
    with brownie.reverts("ERROR:POL-043:MAXIMUM_NUMBER_OF_ACTIVE_BUNDLES_REACHED"):
        riskpool.createBundle(
            bytes(0), 
            initialFunding, 
            {'from': riskpoolKeeper})

    # ensure another bundle can be created only after locking one bundle
    riskpool.lockBundle(bundle2[0], {'from': riskpoolKeeper})

    assert riskpool.bundles() == 3
    assert riskpool.activeBundles() == 1
    assert instanceService.activeBundles(riskpoolId) == 1

    riskpool.createBundle(
        bytes(0), 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 4
    assert riskpool.activeBundles() == 2
    assert instanceService.activeBundles(riskpoolId) == 2

    # ensure locked bundle cannot be unlocked while max active bundles are in use
    with brownie.reverts("ERROR:POL-043:MAXIMUM_NUMBER_OF_ACTIVE_BUNDLES_REACHED"):
        riskpool.unlockBundle(bundle2[0], {'from': riskpoolKeeper})
    
    riskpool.closeBundle(bundle3[0], {'from': riskpoolKeeper})

    assert riskpool.bundles() == 4
    assert riskpool.activeBundles() == 1
    assert instanceService.activeBundles(riskpoolId) == 1

    # ensure bundles can be created after closing one more bundle
    riskpool.createBundle(
        bytes(0), 
        initialFunding, 
        {'from': riskpoolKeeper})

    assert riskpool.bundles() == 5
    assert riskpool.activeBundles() == 2
    assert instanceService.activeBundles(riskpoolId) == 2


def _getBundle(instance, riskpool, bundleIdx):
    instanceService = instance.getInstanceService()
    bundleId = riskpool.getBundleId(bundleIdx)
    return instanceService.getBundle(bundleId)
