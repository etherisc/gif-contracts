import brownie
import pytest

from scripts.instance import GifInstance
from scripts.product import GifTestRiskpool
from scripts.util import s2b32

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_deploy_simple(
    instance: GifInstance, 
    gifTestRiskpool: GifTestRiskpool,
    capitalOwner,
    testCoin
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 0
    assert instanceService.products() == 0
    assert instanceService.riskpools() == 1

    riskpool = gifTestRiskpool.getContract()
    assert riskpool.getCollateralizationLevel() == riskpool.getFullCollateralizationLevel()

    assert riskpool.getWallet() == capitalOwner
    assert riskpool.getErc20Token() == testCoin

    assert riskpool.bundles() == 0
    assert riskpool.getCapital() == 0
    assert riskpool.getTotalValueLocked() == 0
    assert riskpool.getCapacity() == 0
    assert riskpool.getBalance() == 0
    assert riskpool.getMaximumNumberOfActiveBundles() == 1
