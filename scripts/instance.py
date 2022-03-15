from web3 import Web3

from brownie import Contract
from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    Wei,
    Contract, 
    Registry,
    RegistryController,
    License,
    LicenseController,
    Policy,
    PolicyController,
    Query,
    QueryController,
    ProductService,
    OracleService,
    OracleOwnerService,
    PolicyFlowDefault,
    InstanceOperatorService,
)

from scripts.const import (
    GIF_RELEASE,
)

from scripts.util import (
    get_account,
    encode_function_data,
    s2h,
    deployGifModule,
    deployGifService,
)

class GifRegistry(object):

    def __init__(self, owner: Account):
        controller = RegistryController.deploy(s2h(GIF_RELEASE), {'from': owner})
        storage = Registry.deploy(controller.address, s2h(GIF_RELEASE), {'from': owner})

        self.owner = owner
        self.registry = Contract.from_abi(RegistryController._name, storage.address, RegistryController.abi)
        self.registry.register(storage.NAME.call(), storage.address, {'from': owner})
        self.registry.register(controller.NAME.call(), controller.address, {'from': owner})

    def getOwner(self) -> Account:
        return self.owner

    def getRegistry(self) -> RegistryController:
        return self.registry


class GifInstance(GifRegistry):

    def __init__(self, owner: Account):
        super().__init__(owner)

        registry = self.registry
        self.licence = deployGifModule(LicenseController, License, registry, owner)
        self.policy = deployGifModule(PolicyController, Policy, registry, owner)
        self.query = deployGifModule(QueryController, Query, registry, owner)

        self.policyFlow = deployGifService(PolicyFlowDefault, registry, owner)

        self.productService = deployGifService(ProductService, registry, owner)
        self.oracleOwnerService = deployGifService(OracleOwnerService, registry, owner)
        self.oracleService = deployGifService(OracleService, registry, owner)
        self.instanceOperatorService = deployGifService(InstanceOperatorService, registry, owner)

    def getInstanceOperatorService(self) -> InstanceOperatorService:
        return self.instanceOperatorService
    
    def getProductService(self) -> ProductService:
        return self.productService
    
    def getOracleOwnerService(self) -> OracleOwnerService:
        return self.oracleOwnerService
    
    def getOracleService(self) -> OracleService:
        return self.oracleService

    def getPolicyController(self) -> PolicyController:
        return self.policy