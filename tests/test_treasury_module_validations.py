import brownie
import pytest

from brownie.network.account import Account

from scripts.const import ZERO_ADDRESS
from scripts.instance import GifInstance
from scripts.product import GifTestOracle, GifTestProduct, GifTestRiskpool
from scripts.util import b2s

from scripts.setup import (
    apply_for_policy,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_fee_spec_for_different_components(
    instance,
    gifTestProduct: GifTestProduct, 
):
    product = gifTestProduct.getContract()
    oracle = gifTestProduct.getOracle().getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    instanceService = instance.getInstanceService()
    treasury = instance.getTreasury()

    fixedFee = 0
    fractionalFee = treasury.getFractionFullUnit() / 10
    feeCalculationData = bytes(0)

    feeSpec1 = treasury.createFeeSpecification(product.getId(), fixedFee, fractionalFee, feeCalculationData)
    feeSpec2 = treasury.createFeeSpecification(riskpool.getId(), fixedFee, fractionalFee, feeCalculationData)

    with brownie.reverts('ERROR:TRS-020:ID_NOT_PRODUCT_OR_RISKPOOL'):
        treasury.createFeeSpecification(oracle.getId(), fixedFee, fractionalFee, feeCalculationData)

    with brownie.reverts('ERROR:TRS-020:ID_NOT_PRODUCT_OR_RISKPOOL'):
        treasury.createFeeSpecification(999, fixedFee, fractionalFee, feeCalculationData)



def test_fractional_fee_too_large(
    instance,
    gifTestProduct: GifTestProduct, 
):
    product = gifTestProduct.getContract()
    instanceService = instance.getInstanceService()
    treasury = instance.getTreasury()

    componentId = product.getId()
    fixedFee = 0
    fractionalFee = treasury.getFractionFullUnit() / 10
    maxFractionalFee = treasury.getFractionFullUnit() / 4
    exceedingFractionalFee = treasury.getFractionFullUnit() / 3
    feeCalculationData = bytes(0)

    feeSpec1 = treasury.createFeeSpecification(componentId, fixedFee, fractionalFee, feeCalculationData)
    feeSpec2 = treasury.createFeeSpecification(componentId, fixedFee, maxFractionalFee, feeCalculationData)

    with brownie.reverts('ERROR:TRS-021:FRACIONAL_FEE_TOO_BIG'):
        treasury.createFeeSpecification(componentId, fixedFee, exceedingFractionalFee, feeCalculationData)
