import json
import os

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
    network
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

    def __init__(
        self, 
        owner: Account,
        publishSource: bool = False
    ):
        controller = RegistryController.deploy(
            s2h(GIF_RELEASE), 
            {'from': owner},
            publish_source=publishSource)

        storage = Registry.deploy(
            controller.address, 
            s2h(GIF_RELEASE), 
            {'from': owner},
            publish_source=publishSource)

        self.owner = owner
        self.registry = contractFromAddress(RegistryController, storage.address)
        self.registry.register(storage.NAME.call(), storage.address, {'from': owner})
        self.registry.register(controller.NAME.call(), controller.address, {'from': owner})

    def getOwner(self) -> Account:
        return self.owner

    def getRegistry(self) -> RegistryController:
        return self.registry


class GifInstance(GifRegistry):

    def __init__(
        self, 
        owner: Account = None, 
        registryAddress = None,
        publishSource: bool = False
    ):
        if owner:
            super().__init__(
                owner, 
                publishSource)
            
            self.deployWithRegistry(
                self.registry, 
                owner,
                publishSource)
            
        elif registryAddress:
            self.fromRegistryAddress(registryAddress)

        else:
            raise ValueError('either owner or registry_address need to be provided')

    def deployWithRegistry(
        self, 
        registry: GifRegistry, 
        owner: Account,
        publishSource: bool
    ):
        self.licence = deployGifModule(LicenseController, License, registry, owner, publishSource)
        self.policy = deployGifModule(PolicyController, Policy, registry, owner, publishSource)
        self.query = deployGifModule(QueryController, Query, registry, owner, publishSource)
        self.policyFlow = deployGifService(PolicyFlowDefault, registry, owner, publishSource)
        self.productService = deployGifService(ProductService, registry, owner, publishSource)
        self.oracleOwnerService = deployGifService(OracleOwnerService, registry, owner, publishSource)
        self.oracleService = deployGifService(OracleService, registry, owner, publishSource)
        self.instanceOperatorService = deployGifService(InstanceOperatorService, registry, owner, publishSource)

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


def dump_single(contract, instance=None) -> str:

    info = contract.get_verification_info()
    netw = network.show_active()
    compiler = info['compiler_version']
    optimizer = info['optimizer_enabled']
    runs = info['optimizer_runs']
    licence = info['license_identifier']
    address = 'no_address'
    name = info['contract_name']

    if instance:
        nameB32 = s2b32(contract._name)
        address = instance.registry.getContract(nameB32)

    dump_sources_contract_file = './dump_sources/{}/{}.json'.format(netw, name)
    with open(dump_sources_contract_file,'w') as f: 
        f.write(json.dumps(contract.get_verification_info()['standard_json_input']))

    return '{} {} {} {} {} {} {}'.format(netw, compiler, optimizer, runs, licence, address, name)


def dump_sources(registryAddress=None):

    dump_sources_summary_dir = './dump_sources/{}'.format(network.show_active())
    dump_sources_summary_file = '{}/contracts.txt'.format(dump_sources_summary_dir)

    # create parent dir
    try:
        os.mkdir('./dump_sources')
    except OSError:
        pass

    # create network specific sub dir
    try:
        os.mkdir(dump_sources_summary_dir)
    except OSError:
        pass
    
    instance = None
        
    if registryAddress:
        instance = GifInstance(registryAddress=registryAddress)
        
    contracts = []
    contracts.append(dump_single(Registry, instance))
    contracts.append(dump_single(RegistryController, instance))

    contracts.append(dump_single(License, instance))
    contracts.append(dump_single(LicenseController, instance))
    contracts.append(dump_single(Policy, instance))
    contracts.append(dump_single(PolicyController, instance))
    contracts.append(dump_single(Query, instance))
    contracts.append(dump_single(QueryController, instance))

    contracts.append(dump_single(PolicyFlowDefault, instance))
    contracts.append(dump_single(ProductService, instance))
    contracts.append(dump_single(OracleOwnerService, instance))
    contracts.append(dump_single(OracleService, instance))
    contracts.append(dump_single(InstanceOperatorService, instance))

    with open(dump_sources_summary_file,'w') as f: 
        f.write('\n'.join(contracts))
        f.write('\n')

    print('\n'.join(contracts))
    print('\nfor contract json files see directory {}'.format(dump_sources_summary_dir))
