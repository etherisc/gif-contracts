import asyncio
import os
from prompt_toolkit.shortcuts.progress_bar import ProgressBar

from brownie import (
    network,
    accounts,
    UsdcAccounting,
    AyiiProduct,
    AyiiRiskpool,
    ProtectedMulticall,
    Wei,
)

from scripts.onepassword import signIn, getItem, getSecret
from scripts.deploy_ayii import from_registry
from scripts.util import contract_from_address, decodeEnum


class Context:

    networkName = network.show_active()
    vault = os.getenv("OP_VAULT")
    stakeholders = [
        "fundsOwner",
        "instanceOperator",
        "instanceWallet",
        "oracleProvider",
        "chainlinkNodeOperator",
        "riskpoolKeeper",
        "riskpoolWallet",
        "investor",
        "productOwner",
        "insurer",
        "customer1",
        "customer2",
        "escrow",
    ]
    feeCapitalFix = 0
    feeCapitalPercentage = 0
    feePremiumFix = 0
    feePremiumPercentage = 0

    def __init__(self):
        self.initialize()

    def initialize(self):
        print("Initializing context, please wait...")
        self.secretsItem = f"{self.networkName} secrets"

        asyncio.run(signIn())
        asyncio.run(getItem(self.vault, self.secretsItem))

        self.registry = getSecret("Addresses", "registry")
        self.usdcAccountingToken = getSecret("Addresses", "usdc_accounting_token")
        self.clfConsumer = getSecret("Addresses", "clf_consumer")
        self.multicallAddress = getSecret("Addresses", "multicall")
        self.usdc = contract_from_address(UsdcAccounting, self.usdcAccountingToken)
        self.multicall = contract_from_address(
            ProtectedMulticall, self.multicallAddress
        )
        self.decimals = self.usdc.decimals()

        self.accounts = {
            s: accounts.from_mnemonic(getSecret("Mnemonics", s))
            for s in self.stakeholders
        }
        self.instanceOperator = self.accounts["instanceOperator"]
        self.insurer = self.accounts["insurer"]
        self.escrow = self.accounts["escrow"]
        self.farmer_hd_base = "insurer"

        (instance, product, oracle, riskpool, componentController) = from_registry(
            self.registry
        )
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

        assert self.instanceService.getInstanceOperator() == self.instanceOperator
        assert self.riskpool.getFullCollateralizationLevel() == 1000000000000000000
        self.fullCollateralizationLevel = self.riskpool.getFullCollateralizationLevel()
        self.noPrint = ["accounts", "stakeholders", "noPrint", "components"]
        self.components = []

    def setContext(self, key, value):
        setattr(self, key, value)

    def getHdWallet(self, name, index):
        return accounts.from_mnemonic(getSecret("Mnemonics", name), 1, index)

    def printContext(self):
        print("Context:")
        for k, v in self.__dict__.items():
            if k not in self.noPrint:
                print(f"{k.ljust(30)}: {v}")

    def printAccounts(self):
        print("Accounts:")
        for k, v in self.accounts.items():
            print(
                (
                    f"{k.ljust(30)}: "
                    f"{v.address[:8]} "
                    f'{str(Wei(v.balance()).to("ether"))[-22:-16].rjust(8)} '
                    f"{str(round(self.usdc.balanceOf(v)/10**self.decimals,2)).rjust(12)}"
                )
            )

    def loadComponents(self):
        componentController = self.componentController
        components = componentController.components()
        result = []
        with ProgressBar() as pb:
            for componentIndex in pb(
                range(1, components + 1), label="Fetching components..."
            ):
                cAddress = componentController.getComponent(componentIndex)
                cType = componentController.getComponentType(componentIndex)
                cState = componentController.getComponentState(componentIndex)
                componentData = {
                    "index": componentIndex,
                    "address": cAddress,
                    "type": cType,
                    "state": cState,
                    "typeStr": decodeEnum("ComponentType", cType),
                    "stateStr": decodeEnum("ComponentState", cState),
                }
                try:
                    if cType == 0:  # Oracle
                        componentData["additionalData"] = {}
                    elif cType == 1:  # Product
                        product = contract_from_address(AyiiProduct, cAddress)
                        risks = product.risks()
                        policies = 0
                        for riskIndex in range(0, risks):
                            riskId = product.getRiskId(riskIndex)
                            policies += product.policies(riskId)
                        componentData["additionalData"] = {
                            "erc20Token": product.getToken(),
                            "riskpoolId": product.getRiskpoolId(),
                            "risks": product.risks(),
                            "policies": policies,
                            "applications": product.applications(),
                        }
                    elif cType == 2:  # Riskpool
                        riskpool = contract_from_address(AyiiRiskpool, cAddress)
                        componentData["additionalData"] = {
                            "erc20Token": riskpool.getErc20Token(),
                            "capital": riskpool.getCapital(),
                            "bundles": riskpool.bundles(),
                        }
                except Exception as e:
                    componentData["error"] = str(e)

                result.append(componentData)

        self.components = result
        return result

    def getComponents(self, type=None, reload=False):
        if reload or not hasattr(self, "components") or len(self.components) == 0:
            self.loadComponents()
        if type is not None:
            return list(filter(lambda x: x["type"] == type, self.components))
        return self.components


context = Context()

# Convenience:

usdc = context.usdc
a = context.accounts
iop = context.instanceOperator
insurer = context.insurer
escrow = context.escrow
getHdWallet = context.getHdWallet
multicall = context.multicall
