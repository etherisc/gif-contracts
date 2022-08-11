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
        erc20Token: Account,
        riskpoolWallet: Account,
        riskpoolKeeper: Account,
        investor: Account,
        collateralization:int,
        name=RISKPOOL_NAME, 
        publishSource=False,
        gasLimit:int=None
    ):
        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        riskpoolService = instance.getRiskpoolService()

        deployInstanceOperatorDict = {'from': instance.getOwner(), 'gas_limit': gasLimit} if gasLimit else {'from': instance.getOwner()}
        deployRiskpoolKeeperDict = {'from': riskpoolKeeper, 'gas_limit': gasLimit} if gasLimit else {'from': riskpoolKeeper}

        # 1) add role to keeper
        keeperRole = instanceService.getRiskpoolKeeperRole()
        operatorService.grantRole(
            keeperRole, 
            riskpoolKeeper, 
            deployInstanceOperatorDict)

        # 2) keeper deploys riskpool
        self.riskpool = AyiiRiskpool.deploy(
            s2b32(name),
            collateralization,
            erc20Token,
            riskpoolWallet,
            instance.getRegistry(),
            deployRiskpoolKeeperDict,
            publish_source=publishSource)
        
        # 3) set up rikspool keeper as investor (createBundle restricted to this role)
        self.riskpool.grantInvestorRole(
            investor,
            deployRiskpoolKeeperDict,
        )

        # 4) riskpool keeperproposes oracle to instance
        componentOwnerService.propose(
            self.riskpool,
            deployRiskpoolKeeperDict)

        # 5) instance operator approves riskpool
        operatorService.approve(
            self.riskpool.getId(),
            deployInstanceOperatorDict)

        # 6) instance operator assigns riskpool wallet
        operatorService.setRiskpoolWallet(
            self.riskpool.getId(),
            riskpoolWallet,
            deployInstanceOperatorDict)

        # 7) setup capital fees
        fixedFee = 42
        fractionalFee = instanceService.getFeeFractionFullUnit() / 20 # corresponds to 5%
        feeSpec = operatorService.createFeeSpecification(
            self.riskpool.getId(),
            fixedFee,
            fractionalFee,
            b'',
            deployInstanceOperatorDict) 

        operatorService.setCapitalFees(
            feeSpec,
            deployInstanceOperatorDict) 
    
    def getId(self) -> int:
        return self.riskpool.getId()
    
    def getContract(self) -> AyiiRiskpool:
        return self.riskpool


class GifAyiiOracle(object):

    def __init__(self, 
        instance: GifInstance, 
        oracleProvider: Account, 
        publishSource=False,
        gasLimit:int=None
    ):

        deployInstanceOperatorDict = {'from': instance.getOwner(), 'gas_limit': gasLimit} if gasLimit else {'from': instance.getOwner()}
        deployOracleProviderDict = {'from': oracleProvider, 'gas_limit': gasLimit} if gasLimit else {'from': oracleProvider}

        instanceService = instance.getInstanceService()
        operatorService = instance.getInstanceOperatorService()
        componentOwnerService = instance.getComponentOwnerService()
        oracleService = instance.getOracleService()

        # 1) add oracle provider role to owner
        providerRole = instanceService.getOracleProviderRole()
        operatorService.grantRole(
            providerRole, 
            oracleProvider, 
            deployInstanceOperatorDict)

        # 2a) chainlink dummy token deploy
        clTokenOwner = oracleProvider
        clTokenSupply = 10**20
        self.clToken = ClToken.deploy(
            clTokenOwner,
            clTokenSupply,
            deployOracleProviderDict,
            publish_source=publishSource)

        # 2b) chainlink operator deploy
        self.chainlinkOperator = ClOperator.deploy(
            self.clToken,
            oracleProvider,
            deployOracleProviderDict,
            publish_source=publishSource)

        # set oracleProvider as authorized to call fullfill on operator
        self.chainlinkOperator.setAuthorizedSenders(
            [oracleProvider],
            deployOracleProviderDict)

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
            deployOracleProviderDict,
            publish_source=publishSource)

        # 3) oracle owner proposes oracle to instance
        componentOwnerService.propose(
            self.oracle,
            deployOracleProviderDict)

        # 4) instance operator approves oracle
        operatorService.approve(
            self.oracle.getId(),
            deployInstanceOperatorDict)
    
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
        productOwner: Account, 
        insurer: Account,
        oracle: GifAyiiOracle, 
        riskpool: GifAyiiRiskpool, 
        publishSource=False,
        gasLimit:int=None
    ):
        deployInstanceOperatorDict = {'from': instance.getOwner(), 'gas_limit': gasLimit} if gasLimit else {'from': instance.getOwner()}
        deployProductOwnerDict = {'from': productOwner, 'gas_limit': gasLimit} if gasLimit else {'from': productOwner}

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
            deployInstanceOperatorDict)

        # 2) product owner creates product
        self.product = AyiiProduct.deploy(
            s2b32('AyiiProduct'),
            registry,
            token.address,
            oracle.getId(),
            riskpool.getId(),
            insurer,
            deployProductOwnerDict,
            publish_source=publishSource)

        # 3) product owner proposes product to instance
        componentOwnerService.propose(
            self.product,
            deployProductOwnerDict)

        # 4) instance operator approves product
        operatorService.approve(
            self.product.getId(),
            deployInstanceOperatorDict)

        # 5) instance owner sets token in treasury
        operatorService.setProductToken(
            self.product.getId(), 
            token,
            deployInstanceOperatorDict) 

        # 5) instance owner creates and sets product fee spec
        fixedFee = 3
        fractionalFee = instanceService.getFeeFractionFullUnit() / 10 # corresponds to 10%
        feeSpec = operatorService.createFeeSpecification(
            self.product.getId(),
            fixedFee,
            fractionalFee,
            b'',
            deployInstanceOperatorDict) 

        operatorService.setPremiumFees(
            feeSpec,
            deployInstanceOperatorDict) 

    
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
