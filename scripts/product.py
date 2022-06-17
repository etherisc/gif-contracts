from web3 import Web3

from brownie import Contract
from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    Wei,
    Contract, 
    # Registry,
    # RegistryController,
    License,
    LicenseController,
    Policy,
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

    def __init__(self, instance: GifInstance, oracleOwner: Account):
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        oracleService = instance.getOracleService()

        # 1) add oracle provider role to owner
        opRole = operatorService.oracleProviderRole()
        operatorService.addRoleToAccount(oracleOwner, opRole)

        # 2) oracle owner creates oracle
        self.oracle = TestOracle.deploy(
            s2b32(ORACLE_NAME),
            instance.getRegistry(),
            {'from': oracleOwner})

        # 3) oracle owner proposes oracle to instance
        componentOwnerService.propose(
            self.oracle,
            {'from': oracleOwner})

        # 4) instance operator approves oracle
        operatorService.approveOracle(
            self.oracle.getId(),
            {'from': instance.getOwner()})
    
    def getOracleId(self) -> int:
        return self.oracle.getId()
    
    def getOracleContract(self) -> TestOracle:
        return self.oracle


class GifTestProduct(object):

    def __init__(self, instance: GifInstance, oracle: GifTestOracle, productOwner: Account):
        self.policyController = instance.getPolicyController()

        operatorService = instance.getInstanceOperatorService()
        productService = instance.getProductService()

        self.product = TestProduct.deploy(
            productService,
            s2b32(PRODUCT_NAME),
            oracle.getOracleId(),
            {'from': productOwner})

        operatorService.approveProduct(
            self.product.getId(),
            {'from': instance.getOwner()})
    
    def getProductId(self) -> int:
        return self.product.getId()
    
    def getProductContract(self) -> TestProduct:
        return self.product

    def getPolicy(self, policyId: str):
        return self.policyController.getPolicy(policyId)