from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    TestCoin,
    InstanceService,
    InstanceOperatorService,
    ComponentOwnerService,
    AyiiProduct,
    AyiiOracle,
    AyiiRiskpool
)

from scripts.ayii_product import GifAyiiProductComplete
from scripts.instance import GifInstance
from scripts.util import contract_from_address, s2b32

def deploy_ganache():

    # define stakeholder accounts    
    instanceOperator=accounts[0]
    instanceWallet=accounts[1]
    oracleProvider=accounts[2]
    chainlinkNodeOperator=accounts[3]
    riskpoolKeeper=accounts[4]
    riskpoolWallet=accounts[5]
    investor=accounts[6]
    productOwner=accounts[7]
    insurer=accounts[8]
    customer=accounts[9]
    customer2=accounts[10]

    # token definition, funding of investor and customer
    erc20Token = TestCoin.deploy({'from': instanceOperator})

    # gif instance deployment
    instance = GifInstance(instanceOperator, instanceWallet=instanceWallet)
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    # ayii deployment
    ayiiDeploy = GifAyiiProductComplete(instance, productOwner, insurer, oracleProvider, chainlinkNodeOperator, riskpoolKeeper, investor, erc20Token, riskpoolWallet)

    ayiiProduct = ayiiDeploy.getProduct()
    ayiiOracle = ayiiProduct.getOracle()
    ayiiRiskpool = ayiiProduct.getRiskpool()

    product = ayiiProduct.getContract()
    oracle = ayiiOracle.getContract()
    riskpool = ayiiRiskpool.getContract()

    # investor funding and bundle creation
    bundleInitialFunding=1000000
    erc20Token.transfer(investor, bundleInitialFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), bundleInitialFunding, {'from': investor})

    maxUint256 = 2**256-1
    erc20Token.approve(instance.getTreasury(), maxUint256, {'from': riskpoolWallet})

    # create bundle for investor
    applicationFilter = bytes(0)
    riskpool.createBundle(
            applicationFilter, 
            bundleInitialFunding, 
            {'from': investor})

    # create risks
    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = [s2b32('1234'), s2b32('2345')]
    cropId = s2b32('mixed')
    
    triggerFloat = 0.75
    exitFloat = 0.1
    tsiFloat = 0.9
    aphFloat = [2.0, 1.8]
    
    multiplier = product.getPercentageMultiplier()
    trigger = multiplier * triggerFloat
    exit_ = multiplier * exitFloat
    tsi = multiplier * tsiFloat
    aph = [multiplier * aphFloat[0], multiplier * aphFloat[1]]

    tx = [None, None]
    tx[0] = product.createRisk(projectId, uaiId[0], cropId, trigger, exit_, tsi, aph[0], {'from': insurer})
    tx[1] = product.createRisk(projectId, uaiId[1], cropId, trigger, exit_, tsi, aph[1], {'from': insurer})

    riskId1 = tx[0].return_value
    riskId2 = tx[1].return_value

    # customer funding
    customerFunding=1000
    erc20Token.transfer(customer, customerFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), customerFunding, {'from': customer})

    # policy creation
    premium = [300, 400]
    sumInsured = [2000, 3000]

    tx[0] = product.applyForPolicy(customer, premium[0], sumInsured[0], riskId1, {'from': insurer})
    tx[1] = product.applyForPolicy(customer2, premium[1], sumInsured[1], riskId2, {'from': insurer})

    processId1 = tx[0].return_value
    processId2 = tx[1].return_value

    return {
        'instanceOperator': instanceOperator,
        'instanceWallet': instanceWallet,
        'oracleProvider': oracleProvider,
        'chainlinkNodeOperator': chainlinkNodeOperator,
        'riskpoolKeeper': riskpoolKeeper,
        'riskpoolWallet': riskpoolWallet,
        'investor': investor,
        'productOwner': productOwner,
        'insurer': insurer,
        'customer1': customer,
        'customer2': customer2,
        'erc20Token': contract_from_address(TestCoin, erc20Token),
        'instance': instance,
        'instanceService': contract_from_address(InstanceService, instanceService),
        'instanceOperatorService': contract_from_address(InstanceOperatorService, instanceOperatorService),
        'componentOwnerService': contract_from_address(ComponentOwnerService, componentOwnerService),
        'product': contract_from_address(AyiiProduct, product),
        'oracle': contract_from_address(AyiiOracle, oracle),
        'riskpool': contract_from_address(AyiiRiskpool, riskpool),
        'riskId1': riskId1,
        'riskId2': riskId2,
        'processId1': processId1,
        'processId2': processId2,
    }

