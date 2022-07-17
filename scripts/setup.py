from brownie.network.account import Account
from scripts.instance import GifInstance

def fund_riskpool(
    instance: GifInstance, 
    owner: Account,
    riskpool,
    bundleOwner: Account,
    coin,
    amount: int 
):
    # transfer funds to riskpool keeper and create allowance
    coin.transfer(bundleOwner, amount, {'from': owner})
    coin.approve(instance.getTreasury(), amount, {'from': bundleOwner})

    applicationFilter = bytes(0)
    riskpool.createBundle(
        applicationFilter, 
        amount, 
        {'from': bundleOwner})


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