from web3 import Web3

from brownie import Contract
from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    Wei,
    Contract, 
    LicenseController,
    PolicyController,
    QueryController,
    ProductService,
    OracleService,
    ComponentOwnerService,
    PolicyFlowDefault,
    InstanceOperatorService,
    TestOracle,
    TestProduct,
)

from scripts.const import (
    ORACLE_INPUT_FORMAT,
    ORACLE_OUTPUT_FORMAT,
    ORACLE_NAME,
    PRODUCT_NAME,
)

from scripts.util import (
    get_account,
    encode_function_data,
    # s2h,
    s2b32,
    deployGifModule,
    deployGifService,
)

from scripts.instance import (
    GifInstance,
)

class GifTestOracle(object):

    def __init__(self, 
        instance: GifInstance, 
        oracleOwner: Account, 
        name=ORACLE_NAME, 
        publishSource=False
    ):
        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        oracleService = instance.getOracleService()

        # 1) add oracle provider role to owner
        providerRole = instanceService.oracleProviderRole()
        operatorService.grantRole(
            providerRole, 
            oracleOwner, 
            {'from': instance.getOwner()})

        # 2) oracle provider creates oracle
        self.oracle = TestOracle.deploy(
            s2b32(name),
            instance.getRegistry(),
            {'from': oracleOwner},
            publish_source=publishSource)

        # 3) oracle owner proposes oracle to instance
        componentOwnerService.propose(
            self.oracle,
            {'from': oracleOwner})

        # 4) instance operator approves oracle
        operatorService.approve(
            self.oracle.getId(),
            {'from': instance.getOwner()})
    
    def getOracleId(self) -> int:
        return self.oracle.getId()
    
    def getOracleContract(self) -> TestOracle:
        return self.oracle


class GifTestProduct(object):

    def __init__(self, 
        instance: GifInstance, 
        oracle: GifTestOracle, 
        productOwner: Account, 
        name=PRODUCT_NAME, 
        publishSource=False
    ):
        self.policyController = instance.getPolicyController()

        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        registry = instance.getRegistry()

        # 1) add oracle provider role to owner
        ownerRole = instanceService.productOwnerRole()
        operatorService.grantRole(
            ownerRole,
            productOwner, 
            {'from': instance.getOwner()})

        # 2) product owner creates product
        self.product = TestProduct.deploy(
            s2b32(name),
            instance.getRegistry(),
            oracle.getOracleId(),
            {'from': productOwner},
            publish_source=publishSource)

        print('prod id {} (before propose)'.format(self.product.getId()))
        # 3) oracle owner proposes oracle to instance
        componentOwnerService.propose(
            self.product,
            {'from': productOwner})

        print('prod id {} (after propose)'.format(self.product.getId()))
        # 4) instance operator approves oracle
        operatorService.approve(
            self.product.getId(),
            {'from': instance.getOwner()})
    
    def getProductId(self) -> int:
        return self.product.getId()
    
    def getProductContract(self) -> TestProduct:
        return self.product

    def getPolicy(self, policyId: str):
        return self.policyController.getPolicy(policyId)