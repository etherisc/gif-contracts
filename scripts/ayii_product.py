from web3 import Web3

from brownie import Contract
from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    Wei,
    Contract, 
    PolicyController,
    OracleService,
    ComponentOwnerService,
    InstanceOperatorService,
    AyiiRiskpool,
    AyiiProduct,
    AyiiOracle,
    ClOperator,
    ClToken,
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

class GifAyiiRiskpool(object):

    def __init__(self, 
        instance: GifInstance, 
        riskpoolKeeper: Account, 
        erc20Token: Account,
        capitalOwner: Account,
        investor: Account,
        collateralization:int,
        name=RISKPOOL_NAME, 
        publishSource=False
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
        self.riskpool = AyiiRiskpool.deploy(
            s2b32(name),
            collateralization,
            erc20Token,
            capitalOwner,
            instance.getRegistry(),
            {'from': riskpoolKeeper},
            publish_source=publishSource)
        
        # 3) set up rikspool keeper as investor (createBundle restricted to this role)
        self.riskpool.grantInvestorRole(
            riskpoolKeeper,
            {'from': riskpoolKeeper},
        )

        # 4) riskpool keeperproposes oracle to instance
        componentOwnerService.propose(
            self.riskpool,
            {'from': riskpoolKeeper})

        # 5) instance operator approves riskpool
        operatorService.approve(
            self.riskpool.getId(),
            {'from': instance.getOwner()})

        # 6) instance operator assigns riskpool wallet
        operatorService.setRiskpoolWallet(
            self.riskpool.getId(),
            capitalOwner,
            {'from': instance.getOwner()})

        # 7) setup capital fees
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
    
    def getContract(self) -> AyiiRiskpool:
        return self.riskpool


class GifAyiiOracle(object):

    def __init__(self, 
        instance: GifInstance, 
        oracleProvider: Account, 
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
            oracleProvider, 
            {'from': instance.getOwner()})

        # 2a) chainlink dummy token deploy
        clTokenOwner = oracleProvider
        clTokenSupply = 10**20
        self.clToken = ClToken.deploy(
            clTokenOwner,
            clTokenSupply,
            {'from': oracleProvider})

        # 2b) chainlink operator deploy
        self.chainlinkOperator = ClOperator.deploy(
            self.clToken,
            oracleProvider,
            {'from': oracleProvider})

        # set oracleProvider as authorized to call fullfill on operator
        self.chainlinkOperator.setAuthorizedSenders([oracleProvider])

        # 2c) oracle provider creates oracle
        chainLinkTokenAddress = self.clToken.address
        chainLinkOracleAddress = self.chainlinkOperator.address
        chainLinkJobId = s2b32('1')
        chainLinkPaymentAmount = 0
        
        self.oracle = AyiiOracle.deploy(
            s2b32('AyiiOracle'),
            instance.getRegistry(),
            chainLinkTokenAddress,
            chainLinkOracleAddress,
            chainLinkJobId,
            chainLinkPaymentAmount,
            {'from': oracleProvider})
            # {'from': oracleProvider},
            # publish_source=publishSource)

        # 3) oracle owner proposes oracle to instance
        componentOwnerService.propose(
            self.oracle,
            {'from': oracleProvider})

        # 4) instance operator approves oracle
        operatorService.approve(
            self.oracle.getId(),
            {'from': instance.getOwner()})
    
    def getId(self) -> int:
        return self.oracle.getId()
    
    def getClOperator(self) -> ClOperator:
        return self.chainlinkOperator
    
    def getContract(self) -> AyiiOracle:
        return self.oracle


class GifAyiiProduct(object):

    def __init__(self, 
        instance: GifInstance, 
        token, 
        capitalOwner: Account, 
        productOwner: Account, 
        riskpoolKeeper: Account,
        customer: Account,
        oracle: GifAyiiOracle, 
        riskpool: GifAyiiRiskpool, 
        publishSource=False
    ):
        self.policy = instance.getPolicy()
        self.oracle = oracle
        self.riskpool = riskpool
        self.token = token

        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        registry = instance.getRegistry()

        # 1) add product owner role to owner
        ownerRole = instanceService.getProductOwnerRole()
        operatorService.grantRole(
            ownerRole,
            productOwner, 
            {'from': instance.getOwner()})

        # 2) product owner creates product
        investor = riskpoolKeeper
        insurer = productOwner
        self.product = AyiiProduct.deploy(
            s2b32('AyiiProduct'),
            registry,
            token.address,
            oracle.getId(),
            riskpool.getId(),
            insurer,
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

    def getToken(self):
        return self.token

    def getOracle(self) -> GifAyiiOracle:
        return self.oracle

    def getRiskpool(self) -> GifAyiiRiskpool:
        return self.riskpool
    
    def getContract(self) -> AyiiProduct:
        return self.product

    def getPolicy(self, policyId: str):
        return self.policy.getPolicy(policyId)
