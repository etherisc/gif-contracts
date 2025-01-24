import asyncio
import os
from prompt_toolkit.shortcuts.progress_bar import ProgressBar

from brownie import (
    network,
    accounts,
    UsdcAccounting,
    AyiiProduct,
    AyiiRiskpool,
    AyiiOracle,
    Wei
)

from scripts.onepassword import signIn, getItem, getSecret
from scripts.deploy_ayii import (from_registry)
from scripts.util import (contract_from_address, decodeEnum)


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
        print('Initializing context, please wait...')
        self.secretsItem = f'{self.networkName} secrets'

        asyncio.run(signIn())
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
        self.noPrint = ['accounts', 'stakeholders', 'noPrint', 'components']

    def printContext(self):
        print('Context:')
        for k, v in self.__dict__.items():
            if k not in self.noPrint:
                print(f'{k.ljust(30)}: {v}')
        print('Accounts:')
        for k, v in self.accounts.items():
            print(
                f'{k.ljust(30)}: {v.address} {str(Wei(v.balance()).to("ether")).rjust(25)}')

    def loadComponents(self):
        componentController = self.componentController
        components = componentController.components()
        result = []
        with ProgressBar() as pb:
            for componentIndex in pb(range(1, components+1), label="Fetching components..."):
                cAddress = componentController.getComponent(componentIndex)
                cType = componentController.getComponentType(componentIndex)
                cState = componentController.getComponentState(componentIndex)
                componentData = {
                    'address': cAddress,
                    'type': cType,
                    'state': cState,
                    'typeStr': decodeEnum('ComponentType', cType),
                    'stateStr': decodeEnum('ComponentState', cState)
                }
                try:
                    if cType == 0:  # Oracle
                        componentData['additionalData'] = {}
                    elif cType == 1:  # Product
                        product = contract_from_address(AyiiProduct, cAddress)
                        risks = product.risks()
                        policies = 0
                        for riskIndex in range(0, risks):
                            riskId = product.getRiskId(riskIndex)
                            policies += product.policies(riskId)
                        componentData['additionalData'] = {
                            'risks': product.risks(),
                            'policies': policies,
                            'applications': product.applications()
                        }
                    elif cType == 2:  # Riskpool
                        riskpool = contract_from_address(
                            AyiiRiskpool, cAddress)
                        componentData['additionalData'] = {
                            'bundles': riskpool.bundles()
                        }
                except Exception as e:
                    componentData['error'] = str(e)

                result.append(componentData)

        self.components = result
        return result

    def getComponents(self, type=None, reload=False):
        if reload or not hasattr(self, 'components'):
            self.loadComponents()
        if type is not None:
            return list(filter(lambda x: x['type'] == type, self.components))
        return self.components
