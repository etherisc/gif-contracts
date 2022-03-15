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
    TestOracle,
    TestProduct,
)

from scripts.const import (
    ORACLE_TYPE_NAME,
    ORACLE_INPUT_FORMAT,
    ORACLE_OUTPUT_FORMAT,
    ORACLE_NAME,
    ORACLE_ID,
    PRODUCT_NAME,
    PRODUCT_ID,
)

from scripts.util import (
    get_account,
    encode_function_data,
    s2h,
    deployGifModule,
    deployGifService,
)

from scripts.instance import (
    GifInstance,
)

class GifTestOracle(object):

    def __init__(self, instance: GifInstance, oracleOwner: Account):
        operatorService = instance.getInstanceOperatorService()
        oracleOwnerService = instance.getOracleOwnerService()
        oracleService = instance.getOracleService()

        # 1) oracle owner proposes oracle type 
        oracleOwnerService.proposeOracleType(
            s2h(ORACLE_TYPE_NAME), 
            ORACLE_INPUT_FORMAT,
            ORACLE_OUTPUT_FORMAT,
            {'from': oracleOwner})

        # 2) instance operator approves oracle type
        operatorService.approveOracleType(
            s2h(ORACLE_TYPE_NAME),
            {'from': instance.getOwner()})

        # 3) oracle owner proposes oracle
        self.oracle = TestOracle.deploy(
            oracleService,
            oracleOwnerService,
            s2h(ORACLE_TYPE_NAME),
            s2h(ORACLE_NAME),
            {'from': oracleOwner})

        # 4) instance operator approves oracle
        operatorService.approveOracle(
            ORACLE_ID,
            {'from': instance.getOwner()})

        # 5) instance operator approves oracle
        operatorService.assignOracleToOracleType(
            s2h(ORACLE_TYPE_NAME), 
            ORACLE_ID,
            {'from': instance.getOwner()})

    def getOracleTypeName(self) -> str:
        return s2h(ORACLE_TYPE_NAME)
    
    def getOracleId(self) -> int:
        return ORACLE_ID
    
    def getOracleContract(self) -> TestOracle:
        return self.oracle


class GifTestProduct(object):

    def __init__(self, instance: GifInstance, oracle: GifTestOracle, productOwner: Account):
        self.policyController = instance.getPolicyController()

        operatorService = instance.getInstanceOperatorService()
        productService = instance.getProductService()

        self.product = TestProduct.deploy(
            productService,
            s2h(PRODUCT_NAME),
            oracle.getOracleTypeName(),
            oracle.getOracleId(),
            {'from': productOwner})

        operatorService.approveProduct(PRODUCT_ID)
    
    def getProductId(self) -> int:
        return PRODUCT_ID
    
    def getProductContract(self) -> TestProduct:
        return self.product

    def getPolicy(self, policyId: str):
        return self.policyController.getPolicy(policyId)