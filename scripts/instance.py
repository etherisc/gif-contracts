import json
import os

from web3 import Web3

from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    Wei,
    Contract, 
    CoreProxy,
    AccessController,
    RegistryController,
    LicenseController,
    PolicyController,
    QueryController,
    ProductService,
    OracleService,
    ComponentController,
    ComponentOwnerService,
    PolicyFlowDefault,
    InstanceOperatorService,
    InstanceService,
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
    deployGifModuleV2,
    deployGifServiceV2,
    contractFromAddress,
)

class GifRegistry(object):

    def __init__(
        self, 
        owner: Account,
        publishSource: bool = False
    ):
        controller = RegistryController.deploy(
            {'from': owner},
            publish_source=publishSource)

        encoded_initializer = encode_function_data(
            s2b32(GIF_RELEASE),
            initializer=controller.initializeRegistry)

        proxy = CoreProxy.deploy(
            controller.address,
            encoded_initializer, 
            {'from': owner},
            publish_source=publishSource)

        self.owner = owner
        self.registry = contractFromAddress(RegistryController, proxy.address)

        print('owner {}'.format(owner))
        print('controller.address {}'.format(controller.address))
        print('proxy.address {}'.format(proxy.address))
        print('registry.address {}'.format(self.registry.address))
        print('registry.getContract(InstanceOperatorService) {}'.format(self.registry.getContract(s2h("InstanceOperatorService"))))

        self.registry.register(s2b32("Registry"), proxy.address, {'from': owner})
        self.registry.register(s2b32("RegistryController"), controller.address, {'from': owner})

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
        if registryAddress:
            self.fromRegistryAddress(registryAddress)
            self.owner=owner
        
        elif owner:
            super().__init__(
                owner, 
                publishSource)
            
            self.deployWithRegistry(
                self.registry, 
                owner,
                publishSource)

        else:
            raise ValueError('either owner or registry_address need to be provided')


    def deployWithRegistry(
        self, 
        registry: GifRegistry, 
        owner: Account,
        publishSource: bool
    ):
        # modules
        self.access = deployGifModuleV2("Access", AccessController, registry, owner, publishSource)
        self.component = deployGifModuleV2("Component", ComponentController, registry, owner, publishSource)
        self.query = deployGifModuleV2("Query", QueryController, registry, owner, publishSource)
        self.licence = deployGifModuleV2("License", LicenseController, registry, owner, publishSource)
        self.policy = deployGifModuleV2("Policy", PolicyController, registry, owner, publishSource)

        # services
        self.componentOwnerService = deployGifModuleV2("ComponentOwnerService", ComponentOwnerService, registry, owner, publishSource)
        self.instanceService = deployGifModuleV2("InstanceService", InstanceService, registry, owner, publishSource)
        self.oracleService = deployGifModuleV2("OracleService", OracleService, registry, owner, publishSource)

        # self.productService = deployGifModuleV2("ProductService", ProductService, registry, owner, publishSource)
        # self.policyFlow = deployGifModuleV2("PolicyFlowDefault", PolicyFlowDefault, registry, owner, publishSource)
        # TODO these contracts do not work with proxy pattern
        self.policyFlow = deployGifService(PolicyFlowDefault, registry, owner, publishSource)
        self.productService = deployGifService(ProductService, registry, owner, publishSource)

        # needs to be the last module to register as it will change
        # the address of the instance operator service to its true address
        self.instanceOperatorService = deployGifModuleV2("InstanceOperatorService", InstanceOperatorService, registry, owner, publishSource)

        # needs to be called during instance setup
        self.access.setDefaultAdminRole(self.instanceOperatorService.address, {'from': owner})


    def fromRegistryAddress(self, registry_address):
        self.registry = contractFromAddress(RegistryController, registry_address)

        self.query = self.contractFromGifRegistry(QueryController, "Query")
        self.licence = self.contractFromGifRegistry(LicenseController, "License")
        self.policy = self.contractFromGifRegistry(PolicyController, "Policy")

        self.instanceService = self.contractFromGifRegistry(InstanceService, "InstanceService")
        self.oracleService = self.contractFromGifRegistry(OracleService, "OracleService")
        self.productService = self.contractFromGifRegistry(ProductService, "ProductService")

        self.policyFlow = self.contractFromGifRegistry(PolicyFlowDefault, "PolicyFlowDefault")
        self.componentOwnerService = self.contractFromGifRegistry(ComponentOwnerService)
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

    def getInstanceService(self) -> InstanceService:
        return self.instanceService
    
    def getProductService(self) -> ProductService:
        return self.productService
    
    def getPolicyFlowDefault(self) -> PolicyFlowDefault:
        return self.policyFlow
    
    def getComponentOwnerService(self) -> ComponentOwnerService:
        return self.componentOwnerService
    
    def getOracleService(self) -> OracleService:
        return self.oracleService

    def getPolicyController(self) -> PolicyController:
        return self.policy


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
