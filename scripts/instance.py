import json
import os

from web3 import Web3

from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

# pylint: disable-msg=E0611
from brownie import (
    Wei,
    Contract, 
    BundleToken,
    RiskpoolToken,
    CoreProxy,
    AccessController,
    RegistryController,
    LicenseController,
    PolicyController,
    QueryModule,
    PoolController,
    BundleController,
    PoolController,
    TreasuryModule,
    ProductService,
    OracleService,
    RiskpoolService,
    ComponentController,
    ComponentOwnerService,
    PolicyDefaultFlow,
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
    deployGifToken,
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
        instanceWallet: Account = None, 
        registryAddress = None,
        publishSource: bool = False,
        setInstanceWallet: bool = True
    ):
        if registryAddress:
            self.fromRegistryAddress(registryAddress)
            self.owner=self.instanceService.getInstanceOperator()
        
        elif owner:
            super().__init__(
                owner, 
                publishSource)
            
            self.deployWithRegistry(
                self.registry, 
                owner,
                publishSource)
        
            if setInstanceWallet:
                self.instanceOperatorService.setInstanceWallet(
                    instanceWallet,
                    {'from': owner})
            
        else:
            raise ValueError('either owner or registry_address need to be provided')


    def deployWithRegistry(
        self, 
        registry: GifRegistry, 
        owner: Account,
        publishSource: bool
    ):
        # gif instance tokens
        self.bundleToken = deployGifToken("BundleToken", BundleToken, registry, owner, publishSource)
        self.riskpoolToken = deployGifToken("RiskpoolToken", RiskpoolToken, registry, owner, publishSource)

        # modules (need to be deployed first)
        # deploy order needs to respect module dependencies
        self.access = deployGifModuleV2("Access", AccessController, registry, owner, publishSource)
        self.component = deployGifModuleV2("Component", ComponentController, registry, owner, publishSource)
        self.query = deployGifModuleV2("Query", QueryModule, registry, owner, publishSource)
        self.license = deployGifModuleV2("License", LicenseController, registry, owner, publishSource)
        self.policy = deployGifModuleV2("Policy", PolicyController, registry, owner, publishSource)
        self.bundle = deployGifModuleV2("Bundle", BundleController, registry, owner, publishSource)
        self.pool = deployGifModuleV2("Pool", PoolController, registry, owner, publishSource)
        self.treasury = deployGifModuleV2("Treasury", TreasuryModule, registry, owner, publishSource)

        # TODO these contracts do not work with proxy pattern
        self.policyFlow = deployGifService(PolicyDefaultFlow, registry, owner, publishSource)

        # services
        self.instanceService = deployGifModuleV2("InstanceService", InstanceService, registry, owner, publishSource)
        self.componentOwnerService = deployGifModuleV2("ComponentOwnerService", ComponentOwnerService, registry, owner, publishSource)
        self.oracleService = deployGifModuleV2("OracleService", OracleService, registry, owner, publishSource)
        self.riskpoolService = deployGifModuleV2("RiskpoolService", RiskpoolService, registry, owner, publishSource)

        # TODO these contracts do not work with proxy pattern
        self.productService = deployGifService(ProductService, registry, owner, publishSource)

        # needs to be the last module to register as it will 
        # perform some post deploy wirings and changes the address 
        # of the instance operator service to its true address
        self.instanceOperatorService = deployGifModuleV2("InstanceOperatorService", InstanceOperatorService, registry, owner, publishSource)

        # post deploy wiring steps
        # self.bundleToken.setBundleModule(self.bundle)

        # ensure that the instance has 32 contracts when freshly deployed
        assert 32 == registry.contracts()


    def fromRegistryAddress(self, registry_address):
        self.registry = contractFromAddress(RegistryController, registry_address)
        self.access = self.contractFromGifRegistry(AccessController, "Access")
        self.component = self.contractFromGifRegistry(AccessController, "Component")

        self.query = self.contractFromGifRegistry(QueryModule, "Query")
        self.license = self.contractFromGifRegistry(LicenseController, "License")
        self.policy = self.contractFromGifRegistry(PolicyController, "Policy")
        self.bundle = self.contractFromGifRegistry(BundleController, "Bundle")
        self.pool = self.contractFromGifRegistry(PoolController, "Pool")
        self.treasury = self.contractFromGifRegistry(TreasuryModule, "Treasury")

        self.instanceService = self.contractFromGifRegistry(InstanceService, "InstanceService")
        self.oracleService = self.contractFromGifRegistry(OracleService, "OracleService")
        self.riskpoolService = self.contractFromGifRegistry(RiskpoolService, "RiskpoolService")
        self.productService = self.contractFromGifRegistry(ProductService, "ProductService")

        self.policyFlow = self.contractFromGifRegistry(PolicyDefaultFlow, "PolicyDefaultFlow")
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

    def getAccess(self) -> AccessController:
        return self.access

    def getBundle(self) -> BundleController:
        return self.bundle

    def getBundleToken(self) -> BundleToken:
        return self.bundleToken

    def getComponent(self) -> ComponentController:
        return self.component

    def getLicense(self) -> LicenseController:
        return self.license

    def getPolicy(self) -> PolicyController:
        return self.policy
    
    def getPolicyDefaultFlow(self) -> PolicyDefaultFlow:
        return self.policyFlow

    def getPool(self) -> PoolController:
        return self.pool

    def getTreasury(self) -> TreasuryModule:
        return self.treasury

    def getQuery(self) -> QueryModule:
        return self.query

    def getInstanceOperatorService(self) -> InstanceOperatorService:
        return self.instanceOperatorService

    def getInstanceService(self) -> InstanceService:
        return self.instanceService
    
    def getRiskpoolService(self) -> RiskpoolService:
        return self.riskpoolService
    
    def getProductService(self) -> ProductService:
        return self.productService
    
    def getComponentOwnerService(self) -> ComponentOwnerService:
        return self.componentOwnerService
    
    def getOracleService(self) -> OracleService:
        return self.oracleService


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
    contracts.append(dump_single(CoreProxy, "Registry", instance))
    contracts.append(dump_single(RegistryController, "RegistryController", instance))

    contracts.append(dump_single(BundleToken, "BundleToken", instance))
    contracts.append(dump_single(RiskpoolToken, "RiskpoolToken", instance))

    contracts.append(dump_single(CoreProxy, "Access", instance))
    contracts.append(dump_single(AccessController, "AccessController", instance))

    contracts.append(dump_single(CoreProxy, "Component", instance))
    contracts.append(dump_single(ComponentController, "ComponentController", instance))

    contracts.append(dump_single(CoreProxy, "Query", instance))
    contracts.append(dump_single(QueryModule, "QueryModule", instance))

    contracts.append(dump_single(CoreProxy, "License", instance))
    contracts.append(dump_single(LicenseController, "LicenseController", instance))

    contracts.append(dump_single(CoreProxy, "Policy", instance))
    contracts.append(dump_single(PolicyController, "PolicyController", instance))

    contracts.append(dump_single(CoreProxy, "Bundle", instance))
    contracts.append(dump_single(BundleController, "BundleController", instance))

    contracts.append(dump_single(CoreProxy, "Pool", instance))
    contracts.append(dump_single(PoolController, "PoolController", instance))

    contracts.append(dump_single(CoreProxy, "Treasury", instance))
    contracts.append(dump_single(TreasuryModule, "TreasuryModule", instance))

    contracts.append(dump_single(PolicyDefaultFlow, "PolicyDefaultFlow", instance))

    contracts.append(dump_single(CoreProxy, "InstanceService", instance))
    contracts.append(dump_single(InstanceService, "InstanceServiceController", instance))

    contracts.append(dump_single(CoreProxy, "ComponentOwnerService", instance))
    contracts.append(dump_single(ComponentOwnerService, "ComponentOwnerServiceController", instance))

    contracts.append(dump_single(CoreProxy, "OracleService", instance))
    contracts.append(dump_single(OracleService, "OracleServiceController", instance))

    contracts.append(dump_single(CoreProxy, "RiskpoolService", instance))
    contracts.append(dump_single(RiskpoolService, "RiskpoolServiceController", instance))

    contracts.append(dump_single(ProductService, "ProductService", instance))

    contracts.append(dump_single(CoreProxy, "InstanceOperatorService", instance))
    contracts.append(dump_single(InstanceOperatorService, "InstanceOperatorServiceController", instance))

    with open(dump_sources_summary_file,'w') as f: 
        f.write('\n'.join(contracts))
        f.write('\n')

    print('\n'.join(contracts))
    print('\nfor contract json files see directory {}'.format(dump_sources_summary_dir))


def dump_single(contract, registryName, instance=None) -> str:

    info = contract.get_verification_info()
    netw = network.show_active()
    compiler = info['compiler_version']
    optimizer = info['optimizer_enabled']
    runs = info['optimizer_runs']
    license = info['license_identifier']
    address = 'no_address'
    name = info['contract_name']

    if instance:
        nameB32 = s2b32(registryName)
        address = instance.registry.getContract(nameB32)

    dump_sources_contract_file = './dump_sources/{}/{}.json'.format(netw, name)
    with open(dump_sources_contract_file,'w') as f: 
        f.write(json.dumps(contract.get_verification_info()['standard_json_input']))

    return '{} {} {} {} {} {} {}'.format(netw, compiler, optimizer, runs, license, address, name)
