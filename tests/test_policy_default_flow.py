import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    Wei,
    TestProduct,
)

from scripts.const import (
    ZERO_ADDRESS
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

def test_apppy_with_zero_address(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpoolWallet = capitalOwner
    investor = riskpoolKeeper

    riskpool = gifTestProduct.getRiskpool().getContract()
    fund_riskpool(instance, owner, riskpoolWallet, riskpool, investor, testCoin, 1000)

    metaData = bytes(0)
    applicationData = bytes(0)

    with brownie.reverts("ERROR:POL-001:INVALID_OWNER"):
        product.applyForPolicy(
            ZERO_ADDRESS,
            10,
            100,
            metaData,
            applicationData,
            {'from': customer}
        )
    