from web3 import Web3

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
    s2b32,
    deployGifModule,
    deployGifService,
    contractFromAddress,
)

class GifRegistry(object):

    def __init__(self, owner: Account):
        controller = RegistryController.deploy(s2h(GIF_RELEASE), {'from': owner})
        storage = Registry.deploy(controller.address, s2h(GIF_RELEASE), {'from': owner})

        self.owner = owner
        self.registry = contractFromAddress(RegistryController, storage.address)
        self.registry.register(storage.NAME.call(), storage.address, {'from': owner})
        self.registry.register(controller.NAME.call(), controller.address, {'from': owner})

    def getOwner(self) -> Account:
        return self.owner

    def getRegistry(self) -> RegistryController:
        return self.registry


class GifInstance(GifRegistry):

    def __init__(self, owner:Account=None, registry_address=None):
        if owner:
            super().__init__(owner)
            self.deployWithRegistry(self.registry, owner)
        elif registry_address:
            self.fromRegistryAddress(registry_address)
        else:
            raise ValueError('either owner or registry_address need to be provided')

    def deployWithRegistry(self, registry: GifRegistry, owner: Account):
        self.licence = deployGifModule(LicenseController, License, registry, owner)
        self.policy = deployGifModule(PolicyController, Policy, registry, owner)
        self.query = deployGifModule(QueryController, Query, registry, owner)
        self.policyFlow = deployGifService(PolicyFlowDefault, registry, owner)
        self.productService = deployGifService(ProductService, registry, owner)
        self.oracleOwnerService = deployGifService(OracleOwnerService, registry, owner)
        self.oracleService = deployGifService(OracleService, registry, owner)
        self.instanceOperatorService = deployGifService(InstanceOperatorService, registry, owner)

    def fromRegistryAddress(self, registry_address):
        self.registry = contractFromAddress(RegistryController, registry_address)

        self.licence = self.contractFromGifRegistry(LicenseController, License._name)
        self.policy = self.contractFromGifRegistry(PolicyController, Policy._name)
        self.query = self.contractFromGifRegistry(QueryController, Query._name)

        self.policyFlow = self.contractFromGifRegistry(PolicyFlowDefault)
        self.productService = self.contractFromGifRegistry(ProductService)
        self.oracleOwnerService = self.contractFromGifRegistry(OracleOwnerService)
        self.oracleService = self.contractFromGifRegistry(OracleService)
        self.instanceOperatorService = self.contractFromGifRegistry(InstanceOperatorService)

    def contractFromGifRegistry(self, contractClass, name=None):
        if not name:
            nameB32 = s2b32(contractClass._name)
        else:
            nameB32 = s2b32(name)
        
        address = self.registry.getContract(nameB32)
        return contractFromAddress(contractClass, address)

    def getRegistry(self) -> GifRegistry:
        return self.registry

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