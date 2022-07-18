import brownie

from scripts.instance import GifInstance
from scripts.product import GifTestRiskpool
from scripts.util import s2b32

def test_deploy_simple(
    instance: GifInstance, 
    gifTestRiskpool: GifTestRiskpool
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 0
    assert instanceService.products() == 0
    assert instanceService.riskpools() == 1

    # TODO add asserts for initial state of riskpool

# TODO add explicit deployment & approval path as defined in GifTestRiskpool