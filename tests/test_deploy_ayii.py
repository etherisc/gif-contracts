import brownie
import pytest

from brownie import (
    TestOracle,
    TestProduct,
)

from scripts.instance import GifInstance

from scripts.ayii_product import (
    GifAyiiOracle,
    GifAyiiProduct,
    GifAyiiRiskpool,
)

from scripts.util import s2b32


# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_deploy_simple(
    instance: GifInstance, 
    testCoin,
    productOwner,
    riskpoolWallet,
    gifAyiiOracle: GifAyiiOracle, 
    gifAyiiRiskpool: GifAyiiRiskpool, 
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 1
    assert instanceService.products() == 0
    assert instanceService.riskpools() == 1

    insurer = productOwner
    product = GifAyiiProduct(
        instance, 
        testCoin, 
        productOwner, 
        insurer,
        gifAyiiOracle, 
        gifAyiiRiskpool)

    assert instanceService.oracles() == 1
    assert instanceService.products() == 1
    assert instanceService.riskpools() == 1

    # asssertions for initialized product
    riskpool = product.getRiskpool().getContract()
    riskpoolId = riskpool.getId()
    assert riskpoolId == gifAyiiRiskpool.getId()
    assert instanceService.getComponentToken(riskpoolId) == testCoin
    assert instanceService.getRiskpoolWallet(riskpoolId) == riskpoolWallet

    pool = instanceService.getRiskpool(riskpoolId)
    assert pool['id'] == riskpoolId
    assert pool['wallet'] == riskpoolWallet
    assert pool['erc20Token'] == testCoin
    assert pool['collateralizationLevel'] == instanceService.getFullCollateralizationLevel()
