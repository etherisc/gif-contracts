import brownie
import pytest

from brownie import (
    interface,
    AreaYieldIndexOracle
)

from scripts.area_yield_index import (
    GifAreaYieldIndexOracle,
    GifAreaYieldIndexProduct
)

from scripts.instance import GifInstance
from scripts.util import s2b32, contractFromAddress

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_deploy_oracle(
    instance: GifInstance, 
    gifAreaYieldIndexOracle: GifAreaYieldIndexOracle
):
    instanceService = instance.getInstanceService()
    
    assert instanceService.oracles() == 1
    assert instanceService.products() == 0
    assert instanceService.riskpools() == 0

    oracle = gifAreaYieldIndexOracle.getContract()
    oracle.getName() == s2b32('AreaYieldIndexOracle')
    oracle.getId() == 0
    oracle.getType() == 0
    oracle.getState() == 3



def test_deploy_product(
    instance: GifInstance, 
    gifAreaYieldIndexProduct: GifAreaYieldIndexProduct,
    testCoin,
    capitalOwner
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 1
    assert instanceService.products() == 1
    assert instanceService.riskpools() == 1

    # product assertions
    product = gifAreaYieldIndexProduct.getContract()
    product.getName() == s2b32('AreaYieldIndexProduct')
    product.getId() == 2
    product.getType() == 1
    product.getState() == 3

    # asssertions for initialized product
    riskpoolId = product.getRiskpoolId()
    component = instanceService.getComponent(riskpoolId)
    riskpool = contractFromAddress(interface.IRiskpool, component) 

    assert instanceService.getComponentToken(product.getId()) == testCoin
    assert instanceService.getRiskpoolWallet(riskpoolId) == capitalOwner

    # check capitalization for riskpool
    assert riskpool.getCollateralizationLevel() == riskpool.getFullCollateralizationLevel()
