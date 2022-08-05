from brownie.network.account import Account
from scripts.instance import GifInstance

def fund_riskpool(
    instance: GifInstance, 
    owner: Account,
    capitalOwner: Account,
    riskpool,
    bundleOwner: Account,
    coin,
    amount: int,
    createBundle: bool = True 
):
    # transfer funds to riskpool keeper and create allowance
    safetyFactor = 2
    coin.transfer(bundleOwner, safetyFactor * amount, {'from': owner})
    coin.approve(instance.getTreasury(), safetyFactor * amount, {'from': bundleOwner})

    # create approval for treasury from capital owner to allow for withdrawls
    maxUint256 = 2**256-1
    coin.approve(instance.getTreasury(), maxUint256, {'from': capitalOwner})

    applicationFilter = bytes(0)

    if (createBundle):
        riskpool.createBundle(
            applicationFilter, 
            amount, 
            {'from': bundleOwner})


def fund_customer(
    instance: GifInstance, 
    owner: Account,
    account: Account,
    coin,
    amount: int
):
    coin.transfer(account, amount, {'from': owner})
    coin.approve(instance.getTreasury(), amount, {'from': account})


def apply_for_policy(
    instance: GifInstance, 
    owner: Account,
    product, 
    customer: Account,
    coin,
    premium: int,
    sumInsured: int
):
    # transfer premium funds to customer and create allowance
    coin.transfer(customer, premium, {'from': owner})
    coin.approve(instance.getTreasury(), premium, {'from': customer})

    # create minimal policy application
    metaData = bytes(0)
    applicationData = bytes(0)

    tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    
    # returns policy id
    return tx.return_value