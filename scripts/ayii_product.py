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
    ChainlinkOperator, 
    ChainlinkToken, 
)

from scripts.util import (
    get_account,
    encode_function_data,
    # s2h,
    s2b32,
    deployGifModule,
    deployGifService,
)

from scripts.instance import GifInstance


RISKPOOL_NAME = 'AyiiRiskpool'
ORACLE_NAME = 'AyiiOracle'
PRODUCT_NAME = 'AyiiProduct'

class GifAyiiRiskpool(object):

    def __init__(self, 
        instance: GifInstance, 
        erc20Token: Account,
        riskpoolKeeper: Account, 
        riskpoolWallet: Account,
        investor: Account,
        collateralization:int,
        name=RISKPOOL_NAME, 
        publishSource=False
    ):
        instanceService = instance.getInstanceService()
        instanceOperatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        riskpoolService = instance.getRiskpoolService()

        # 1) add role to keeper
        riskpoolKeeperRole = instanceService.getRiskpoolKeeperRole()
        instanceOperatorService.grantRole(
            riskpoolKeeperRole, 
            riskpoolKeeper, 
            {'from': instance.getOwner()})

        # 2) keeper deploys riskpool
        self.riskpool = AyiiRiskpool.deploy(
            s2b32(name),
            collateralization,
            erc20Token,
            riskpoolWallet,
            instance.getRegistry(),
            {'from': riskpoolKeeper},
            publish_source=publishSource)
        
        # 3) set up rikspool keeper as investor (createBundle restricted to this role)
        self.riskpool.grantInvestorRole(
            investor,
            {'from': riskpoolKeeper},
        )

        # 4) riskpool keeperproposes oracle to instance
        componentOwnerService.propose(
            self.riskpool,
            {'from': riskpoolKeeper})

        # 5) instance operator approves riskpool
        instanceOperatorService.approve(
            self.riskpool.getId(),
            {'from': instance.getOwner()})

        # 6) instance operator assigns riskpool wallet
        instanceOperatorService.setRiskpoolWallet(
            self.riskpool.getId(),
            riskpoolWallet,
            {'from': instance.getOwner()})

        # 7) setup capital fees
        fixedFee = 42
        fractionalFee = instanceService.getFeeFractionFullUnit() / 20 # corresponds to 5%
        feeSpec = instanceOperatorService.createFeeSpecification(
            self.riskpool.getId(),
            fixedFee,
            fractionalFee,
            b'',
            {'from': instance.getOwner()}) 

        instanceOperatorService.setCapitalFees(
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
        chainlinkNodeOperator: Account,
        name=ORACLE_NAME, 
        publishSource=False
    ):
        instanceService = instance.getInstanceService()
        instanceOperatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        oracleService = instance.getOracleService()

        # 1) add oracle provider role to owner
        providerRole = instanceService.getOracleProviderRole()
        instanceOperatorService.grantRole(
            providerRole, 
            oracleProvider, 
            {'from': instance.getOwner()})

        # 2a) chainlink dummy token deploy
        clTokenOwner = oracleProvider
        clTokenSupply = 10**20
        self.chainlinkToken = ChainlinkToken.deploy(
            clTokenOwner,
            clTokenSupply,
            {'from': oracleProvider},
            publish_source=publishSource)

        # 2b) chainlink operator deploy

        self.chainlinkOperator = ChainlinkOperator.deploy(
            {'from': oracleProvider},
            publish_source=publishSource)

        # set oracleProvider as authorized to call fullfill on operator
        self.chainlinkOperator.setAuthorizedSenders([chainlinkNodeOperator])

        # 2c) oracle provider creates oracle
        chainLinkTokenAddress = self.chainlinkToken.address
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
            {'from': oracleProvider},
            publish_source=publishSource)

        # 3) oracle owner proposes oracle to instance
        componentOwnerService.propose(
            self.oracle,
            {'from': oracleProvider})

        # 4) instance operator approves oracle
        instanceOperatorService.approve(
            self.oracle.getId(),
            {'from': instance.getOwner()})
    
    def getId(self) -> int:
        return self.oracle.getId()
    
    def getClOperator(self) -> ChainlinkOperator:
        return self.chainlinkOperator
    
    def getContract(self) -> AyiiOracle:
        return self.oracle


class GifAyiiProduct(object):

    def __init__(self, 
        instance: GifInstance, 
        erc20Token, 
        productOwner: Account, 
        insurer: Account, 
        oracle: GifAyiiOracle, 
        riskpool: GifAyiiRiskpool, 
        name=PRODUCT_NAME, 
        publishSource=False
    ):
        self.policy = instance.getPolicy()
        self.oracle = oracle
        self.riskpool = riskpool
        self.token = erc20Token

        instanceService = instance.getInstanceService()
        instanceOperatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        registry = instance.getRegistry()

        # 1) add product owner role to owner
        productOwnerRole = instanceService.getProductOwnerRole()
        instanceOperatorService.grantRole(
            productOwnerRole,
            productOwner, 
            {'from': instance.getOwner()})

        # 2) product owner creates product
        self.product = AyiiProduct.deploy(
            s2b32('AyiiProduct'),
            registry,
            erc20Token.address,
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
        instanceOperatorService.approve(
            self.product.getId(),
            {'from': instance.getOwner()})

        # 5) instance owner sets token in treasury
        instanceOperatorService.setProductToken(
            self.product.getId(), 
            erc20Token,
            {'from': instance.getOwner()}) 

        # 5) instance owner creates and sets product fee spec
        fixedFee = 3
        fractionalFee = instanceService.getFeeFractionFullUnit() / 10 # corresponds to 10%
        feeSpec = instanceOperatorService.createFeeSpecification(
            self.product.getId(),
            fixedFee,
            fractionalFee,
            b'',
            {'from': instance.getOwner()}) 

        instanceOperatorService.setPremiumFees(
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


class GifAyiiProductComplete(object):

    def __init__(self, 
        instance: GifInstance, 
        productOwner: Account, 
        insurer: Account,
        oracleProvider: Account, 
        chainlinkNodeOperator: Account,
        riskpoolKeeper: Account, 
        investor: Account,
        erc20Token: Account,
        riskpoolWallet: Account,
        baseName='Ayii', 
        publishSource=False
    ):
        instanceService = instance.getInstanceService()
        instanceOperatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        registry = instance.getRegistry()

        self.token = erc20Token

        self.riskpool = GifAyiiRiskpool(
            instance, 
            erc20Token, 
            riskpoolKeeper, 
            riskpoolWallet, 
            investor, 
            instanceService.getFullCollateralizationLevel(),
            '{}Riskpool'.format(baseName),
            publishSource)

        self.oracle = GifAyiiOracle(
            instance, 
            oracleProvider,
            oracleProvider,
            # TODO analyze how to set a separate chainlink operator node account
            # chainlinkNodeOperator,
            '{}Oracle'.format(baseName),
            publishSource)

        self.product = GifAyiiProduct(
            instance, 
            erc20Token, 
            productOwner, 
            insurer, 
            self.oracle, 
            self.riskpool,
            '{}Product'.format(baseName),
            publishSource)

    def getToken(self):
        return self.token

    def getRiskpool(self) -> GifAyiiRiskpool:
        return self.riskpool

    def getOracle(self) -> GifAyiiOracle:
        return self.oracle

    def getProduct(self) -> GifAyiiProduct:
        return self.product
