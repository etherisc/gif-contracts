from web3 import Web3

from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

# pylint: disable-msg=E0611
from brownie import (
    Wei,
    Contract, 
    PolicyController,
    OracleService,
    ComponentOwnerService,
    InstanceOperatorService,
    TestRiskpool,
    TestOracle,
    TestProduct,
)

from scripts.const import (
    RISKPOOL_NAME,
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


class GifTestRiskpool(object):

    def __init__(self, 
        instance: GifInstance, 
        riskpoolKeeper: Account, 
        erc20Token: Account,
        riskpoolWallet: Account, 
        collateralization:int,
        name=RISKPOOL_NAME, 
        publishSource=False,
        setRiskpoolWallet=True
    ):
        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        riskpoolService = instance.getRiskpoolService()

        # 1) add role to keeper
        keeperRole = instanceService.getRiskpoolKeeperRole()
        operatorService.grantRole(
            keeperRole, 
            riskpoolKeeper, 
            {'from': instance.getOwner()})

        # 2) keeper deploys riskpool
        if not setRiskpoolWallet:
            name += '_NO_WALLET'
        
        self.riskpool = TestRiskpool.deploy(
            s2b32(name),
            collateralization,
            erc20Token,
            riskpoolWallet,
            instance.getRegistry(),
            {'from': riskpoolKeeper},
            publish_source=publishSource)

        # 3) riskpool keeperproposes oracle to instance
        componentOwnerService.propose(
            self.riskpool,
            {'from': riskpoolKeeper})

        # 4) instance operator approves riskpool
        operatorService.approve(
            self.riskpool.getId(),
            {'from': instance.getOwner()})

        # 5) instance operator assigns riskpool wallet
        if setRiskpoolWallet:
            operatorService.setRiskpoolWallet(
                self.riskpool.getId(),
                riskpoolWallet,
                {'from': instance.getOwner()})

        # 6) setup capital fees
        fixedFee = 42
        fractionalFee = instanceService.getFeeFractionFullUnit() / 20 # corresponds to 5%
        feeSpec = operatorService.createFeeSpecification(
            self.riskpool.getId(),
            fixedFee,
            fractionalFee,
            b'',
            {'from': instance.getOwner()}) 

        operatorService.setCapitalFees(
            feeSpec,
            {'from': instance.getOwner()}) 
    
    def getId(self) -> int:
        return self.riskpool.getId()
    
    def getContract(self) -> TestRiskpool:
        return self.riskpool


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
        providerRole = instanceService.getOracleProviderRole()
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
    
    def getId(self) -> int:
        return self.oracle.getId()
    
    def getContract(self) -> TestOracle:
        return self.oracle


class GifTestProduct(object):

    def __init__(self, 
        instance: GifInstance, 
        token: Account, 
        capitalOwner: Account, 
        productOwner: Account, 
        oracle: GifTestOracle, 
        riskpool: GifTestRiskpool, 
        name=PRODUCT_NAME, 
        publishSource=False
    ):
        self.policy = instance.getPolicy()
        self.oracle = oracle
        self.riskpool = riskpool

        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        registry = instance.getRegistry()

        # 1) add oracle provider role to owner
        ownerRole = instanceService.getProductOwnerRole()
        operatorService.grantRole(
            ownerRole,
            productOwner, 
            {'from': instance.getOwner()})

        # 2) product owner creates product
        self.product = TestProduct.deploy(
            s2b32(name),
            token.address,
            capitalOwner,
            oracle.getId(),
            riskpool.getId(),
            instance.getRegistry(),
            {'from': productOwner},
            publish_source=publishSource)

        # 3) product owner proposes product to instance
        componentOwnerService.propose(
            self.product,
            {'from': productOwner})

        # 4) instance operator approves product
        operatorService.approve(
            self.product.getId(),
            {'from': instance.getOwner()})

        # 5) instance owner sets token in treasury
        operatorService.setProductToken(
            self.product.getId(), 
            token,
            {'from': instance.getOwner()}) 

        # 5) instance owner creates and sets product fee spec
        fixedFee = 3
        fractionalFee = instanceService.getFeeFractionFullUnit() / 10 # corresponds to 10%
        feeSpec = operatorService.createFeeSpecification(
            self.product.getId(),
            fixedFee,
            fractionalFee,
            b'',
            {'from': instance.getOwner()}) 

        operatorService.setPremiumFees(
            feeSpec,
            {'from': instance.getOwner()}) 

    
    def getId(self) -> int:
        return self.product.getId()

    def getOracle(self) -> GifTestOracle:
        return self.oracle

    def getRiskpool(self) -> GifTestRiskpool:
        return self.riskpool
    
    def getContract(self) -> TestProduct:
        return self.product

    def getPolicy(self, policyId: str):
        return self.policy.getPolicy(policyId)
