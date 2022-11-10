from web3 import Web3

from brownie import Contract
from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

# pylint: disable-msg=E0611
from brownie import (
    Wei,
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

        print('------ setting up riskpool ------')

        riskpoolKeeperRole = instanceService.getRiskpoolKeeperRole()
        print('1) grant riskpool keeper role {} to riskpool keeper {}'.format(
            riskpoolKeeperRole, riskpoolKeeper))

        instanceOperatorService.grantRole(
            riskpoolKeeperRole, 
            riskpoolKeeper, 
            {'from': instance.getOwner()})

        print('2) deploy riskpool by riskpool keeper {}'.format(
            riskpoolKeeper))

        self.riskpool = AyiiRiskpool.deploy(
            s2b32(name),
            collateralization,
            erc20Token,
            riskpoolWallet,
            instance.getRegistry(),
            {'from': riskpoolKeeper},
            publish_source=publishSource)
        
        print('3) investor role granting to investor {} by riskpool keeper {}'.format(
            investor, riskpoolKeeper))

        self.riskpool.grantInvestorRole(
            investor,
            {'from': riskpoolKeeper},
        )

        print('4) riskpool {} proposing to instance by riskpool keeper {}'.format(
            self.riskpool, riskpoolKeeper))
        
        componentOwnerService.propose(
            self.riskpool,
            {'from': riskpoolKeeper})

        print('5) approval of riskpool id {} by instance operator {}'.format(
            self.riskpool.getId(), instance.getOwner()))
        
        instanceOperatorService.approve(
            self.riskpool.getId(),
            {'from': instance.getOwner()})

        print('6) riskpool wallet {} set for riskpool id {} by instance operator {}'.format(
            riskpoolWallet, self.riskpool.getId(), instance.getOwner()))
        
        instanceOperatorService.setRiskpoolWallet(
            self.riskpool.getId(),
            riskpoolWallet,
            {'from': instance.getOwner()})

        # 7) setup capital fees
        fixedFee = 42
        fractionalFee = instanceService.getFeeFractionFullUnit() / 20 # corresponds to 5%
        print('7) creating capital fee spec (fixed: {}, fractional: {}) for riskpool id {} by instance operator {}'.format(
            fixedFee, fractionalFee, self.riskpool.getId(), instance.getOwner()))
        
        feeSpec = instanceOperatorService.createFeeSpecification(
            self.riskpool.getId(),
            fixedFee,
            fractionalFee,
            b'',
            {'from': instance.getOwner()}) 

        print('8) setting capital fee spec by instance operator {}'.format(
            instance.getOwner()))
        
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

        print('------ setting up oracle ------')

        providerRole = instanceService.getOracleProviderRole()
        print('1) grant oracle provider role {} to oracle provider {}'.format(
            providerRole, oracleProvider))

        instanceOperatorService.grantRole(
            providerRole, 
            oracleProvider, 
            {'from': instance.getOwner()})


        clTokenOwner = oracleProvider
        clTokenSupply = 10**20
        print('2) deploy chainlink (mock) token with token owner (=oracle provider) {} by oracle provider {}'.format(
            clTokenOwner, oracleProvider))
        
        self.chainlinkToken = ChainlinkToken.deploy(
            clTokenOwner,
            clTokenSupply,
            {'from': oracleProvider},
            publish_source=publishSource)

        print('3) deploy chainlink (mock) operator by oracle provider {}'.format(
            oracleProvider))

        self.chainlinkOperator = ChainlinkOperator.deploy(
            {'from': oracleProvider},
            publish_source=publishSource)

        print('4) set node operator list [{}] as authorized sender by oracle provider {}'.format(
            chainlinkNodeOperator, oracleProvider))
        
        self.chainlinkOperator.setAuthorizedSenders([chainlinkNodeOperator])

        # 2c) oracle provider creates oracle
        chainLinkTokenAddress = self.chainlinkToken.address
        chainLinkOracleAddress = self.chainlinkOperator.address
        chainLinkJobId = s2b32('1')
        chainLinkPaymentAmount = 0
        print('5) deploy oracle by oracle provider {}'.format(
            oracleProvider))
        
        self.oracle = AyiiOracle.deploy(
            s2b32(name),
            instance.getRegistry(),
            chainLinkTokenAddress,
            chainLinkOracleAddress,
            chainLinkJobId,
            chainLinkPaymentAmount,
            {'from': oracleProvider},
            publish_source=publishSource)

        print('6) oracle {} proposing to instance by oracle provider {}'.format(
            self.oracle, oracleProvider))

        componentOwnerService.propose(
            self.oracle,
            {'from': oracleProvider})

        print('7) approval of oracle id {} by instance operator {}'.format(
            self.oracle.getId(), instance.getOwner()))

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

        print('------ setting up product ------')

        productOwnerRole = instanceService.getProductOwnerRole()
        print('1) grant product owner role {} to product owner {}'.format(
            productOwnerRole, productOwner))

        instanceOperatorService.grantRole(
            productOwnerRole,
            productOwner, 
            {'from': instance.getOwner()})

        print('2) deploy product by product owner {}'.format(
            productOwner))
        
        self.product = AyiiProduct.deploy(
            s2b32(name),
            registry,
            erc20Token.address,
            oracle.getId(),
            riskpool.getId(),
            insurer,
            {'from': productOwner},
            publish_source=publishSource)

        print('3) product {} proposing to instance by product owner {}'.format(
            self.product, productOwner))
        
        componentOwnerService.propose(
            self.product,
            {'from': productOwner})

        print('4) approval of product id {} by instance operator {}'.format(
            self.product.getId(), instance.getOwner()))
        
        instanceOperatorService.approve(
            self.product.getId(),
            {'from': instance.getOwner()})

        print('5) setting erc20 product token {} for product id {} by instance operator {}'.format(
            erc20Token, self.product.getId(), instance.getOwner()))

        instanceOperatorService.setProductToken(
            self.product.getId(), 
            erc20Token,
            {'from': instance.getOwner()}) 

        fixedFee = 3
        fractionalFee = instanceService.getFeeFractionFullUnit() / 10 # corresponds to 10%
        print('6) creating premium fee spec (fixed: {}, fractional: {}) for product id {} by instance operator {}'.format(
            fixedFee, fractionalFee, self.product.getId(), instance.getOwner()))
        
        feeSpec = instanceOperatorService.createFeeSpecification(
            self.product.getId(),
            fixedFee,
            fractionalFee,
            b'',
            {'from': instance.getOwner()}) 

        print('7) setting premium fee spec by instance operator {}'.format(
            instance.getOwner()))

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
