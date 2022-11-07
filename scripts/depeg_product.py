from web3 import Web3

from brownie import Contract
from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    Wei,
    Contract, 
    PolicyController,
    ComponentOwnerService,
    InstanceOperatorService,
    DepegProduct,
    DepegRiskpool,
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


RISKPOOL_NAME = 'DepgeRiskpool'
PRODUCT_NAME = 'DepegProduct'

class GifDepegRiskpool(object):

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

        sumOfSumInsuredCap = 1000000
        self.riskpool = DepegRiskpool.deploy(
            s2b32(name),
            sumOfSumInsuredCap,
            erc20Token,
            riskpoolWallet,
            instance.getRegistry(),
            {'from': riskpoolKeeper},
            publish_source=publishSource)
        
        print('3) riskpool {} proposing to instance by riskpool keeper {}'.format(
            self.riskpool, riskpoolKeeper))
        
        componentOwnerService.propose(
            self.riskpool,
            {'from': riskpoolKeeper})

        print('4) approval of riskpool id {} by instance operator {}'.format(
            self.riskpool.getId(), instance.getOwner()))
        
        instanceOperatorService.approve(
            self.riskpool.getId(),
            {'from': instance.getOwner()})

        maxActiveBundles = 10
        print('5) set max number of bundles to {} by riskpool keeper {}'.format(
            maxActiveBundles, riskpoolKeeper))
        
        self.riskpool.setMaximumNumberOfActiveBundles(
            maxActiveBundles,
            {'from': riskpoolKeeper})

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
    
    def getContract(self) -> DepegRiskpool:
        return self.riskpool


# TODO adapt after building product contract
class GifDepegProduct(object):

    def __init__(self, 
        instance: GifInstance, 
        erc20Token, 
        productOwner: Account, 
        riskpool: GifDepegRiskpool, 
        name=PRODUCT_NAME, 
        publishSource=False
    ):
        self.policy = instance.getPolicy()
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
        
        self.product = DepegProduct.deploy(
            s2b32(name),
            registry,
            erc20Token.address,
            riskpool.getId(),
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

    def getRiskpool(self) -> GifDepegRiskpool:
        return self.riskpool
    
    def getContract(self) -> DepegProduct:
        return self.product

    def getPolicy(self, policyId: str):
        return self.policy.getPolicy(policyId)


class GifDepegProductComplete(object):

    def __init__(self, 
        instance: GifInstance, 
        productOwner: Account, 
        investor: Account,
        erc20Token: Account,
        riskpoolKeeper: Account,
        riskpoolWallet: Account,
        baseName='Depeg', 
        publishSource=False
    ):
        instanceService = instance.getInstanceService()
        instanceOperatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        registry = instance.getRegistry()

        self.token = erc20Token

        self.riskpool = GifDepegRiskpool(
            instance, 
            erc20Token, 
            riskpoolKeeper, 
            riskpoolWallet, 
            investor, 
            instanceService.getFullCollateralizationLevel(),
            '{}Riskpool'.format(baseName),
            publishSource)

        self.product = GifDepegProduct(
            instance, 
            erc20Token, 
            productOwner, 
            self.riskpool,
            '{}Product'.format(baseName),
            publishSource)

    def getToken(self):
        return self.token

    def getRiskpool(self) -> GifDepegRiskpool:
        return self.riskpool

    def getProduct(self) -> GifDepegProduct:
        return self.product
