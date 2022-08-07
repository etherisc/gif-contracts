import brownie

from brownie.network.account import Account

from scripts.const import ZERO_ADDRESS
from scripts.instance import GifInstance
from scripts.product import GifTestProduct

def test_instance_wallet_not_set(
    instanceNoInstanceWallet: GifInstance,
    owner: Account,
    productNoRiskpoolWallet: GifTestProduct,
    testCoin,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    customer: Account,
):
    riskpool = productNoRiskpoolWallet.getRiskpool().getContract()
    bundleOwner = riskpoolKeeper

    instanceService = instanceNoInstanceWallet.getInstanceService()
    assert riskpool.getId() > 0
    assert instanceService.getRiskpoolWallet(riskpool.getId()) == ZERO_ADDRESS 

    amount = 10000
    testCoin.transfer(bundleOwner, amount, {'from': owner})
    testCoin.approve(instanceNoInstanceWallet.getTreasury(), amount, {'from': bundleOwner})

    applicationFilter = bytes(0)
    tx = riskpool.createBundle(
        applicationFilter, 
        amount, 
        {'from': bundleOwner})


