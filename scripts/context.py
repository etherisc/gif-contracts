import asyncio
import os

from brownie import (
    network,
    accounts,
    UsdcAccounting,
    Wei
)

from scripts.onepassword import signIn, getItem, getSecret
from scripts.deploy_ayii import (from_registry)
from scripts.util import (contract_from_address)


class Context:

    networkName = network.show_active()
    vault = os.getenv('OP_VAULT')
    stakeholders = [
        'fundsOwner',
        'instanceOperator',
        'instanceWallet',
        'oracleProvider',
        'chainlinkNodeOperator',
        'riskpoolKeeper',
        'riskpoolWallet',
        'investor',
        'productOwner',
        'insurer',
        'customer1',
        'customer2'
    ]
    feeCapitalFix = 0
    feeCapitalPercentage = 0
    feePremiumFix = 0
    feePremiumPercentage = 0

    def __init__(self):
        self.secretsItem = f'{self.networkName} secrets'

        asyncio.run(signIn())
        print(f'Getting secrets from {self.vault} item {self.secretsItem}')
        asyncio.run(getItem(self.vault, self.secretsItem))
        self.registry = getSecret('Addresses', 'registry')
        self.usdcAccountingToken = getSecret(
            'Addresses', 'usdc_accounting_token')
        self.usdc = contract_from_address(
            UsdcAccounting, self.usdcAccountingToken
        )

        self.accounts = {
            s: accounts.from_mnemonic(getSecret('Mnemonics', s))
            for s in self.stakeholders
        }
        (
            instance,
            product,
            oracle,
            riskpool,
            componentController
        ) = from_registry(self.registry)
        self.instanceService = instance.getInstanceService()
        self.instance = instance
        self.treasury = instance.getTreasury()
        self.product = product
        self.oracle = oracle
        self.riskpool = riskpool
        self.riskpoolId = riskpool.getId()
        self.oracleId = oracle.getId()
        self.productId = product.getId()
        self.componentController = componentController
        self.instanceOperator = self.accounts['instanceOperator']
        assert self.instanceService.getInstanceOperator() == self.instanceOperator
        assert self.riskpool.getFullCollateralizationLevel() == 1000000000000000000
        self.fullCollateralizationLevel = self.riskpool.getFullCollateralizationLevel()
        self.noPrint = ['accounts', 'stakeholders', 'noPrint']

    def printContext(self):
        print('Context:')
        for k, v in self.__dict__.items():
            if k not in self.noPrint:
                print(f'{k.ljust(30)}: {v}')
        print('Accounts:')
        for k, v in self.accounts.items():
            print(
                f'{k.ljust(30)}: {v.address} {str(Wei(v.balance()).to("ether")).rjust(25)}')
