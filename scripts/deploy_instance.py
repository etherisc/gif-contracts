from brownie import web3

from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    interface,
    network,
    TestCoin,
    InstanceService,
    InstanceOperatorService,
    ComponentOwnerService,
)

from scripts.instance import GifInstance

def deploy_instance_ganache():
    instanceOperator=accounts[0]
    instanceWallet=accounts[1]

    instance = GifInstance(instanceOperator, instanceWallet=instanceWallet)
    registry = instance.getRegistry()
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    return (registry, instanceOperator, instanceService)
