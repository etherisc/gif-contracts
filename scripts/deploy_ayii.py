from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    interface,
    network,
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

INSTANCE_OPERATOR = 'instanceOperator'
INSTANCE_WALLET = 'instanceWallet'
ORACLE_PROVIDER = 'oracleProvider'
NODE_OPERATOR = 'chainlinkNodeOperator'
RISKPOOL_KEEPER = 'riskpoolKeeper'
RISKPOOL_WALLET = 'riskpoolWallet'
INVESTOR = 'investor'
PRODUCT_OWNER = 'productOwner'
INSURER = 'insurer'
CUSTOMER1 = 'customer1'
CUSTOMER2 = 'customer2'

ERC20_TOKEM = 'erc20Token'
INSTANCE = 'instance'
INSTANCE_SERVICE = 'instanceService'
INSTANCE_OPERATOR_SERVICE = 'instanceOperatorService'
COMPONENT_OWNER_SERVICE = 'componentOwnerService'
PRODUCT = 'product'
ORACLE = 'oracle'
RISKPOOL = 'riskpool'

RISK_ID1 = 'riskId1'
RISK_ID2 = 'riskId2'
PROCESS_ID1 = 'processId1'
PROCESS_ID2 = 'processId2'

REQUIRED_FUNDS_S =   50000000000000000
REQUIRED_FUNDS_M =  150000000000000000
REQUIRED_FUNDS_L = 1500000000000000000

REQUIRED_FUNDS = {
    INSTANCE_OPERATOR: REQUIRED_FUNDS_L,
    INSTANCE_WALLET:   REQUIRED_FUNDS_S,
    PRODUCT_OWNER:     REQUIRED_FUNDS_M,
    INSURER:           REQUIRED_FUNDS_M,
    ORACLE_PROVIDER:   REQUIRED_FUNDS_M,
    RISKPOOL_KEEPER:   REQUIRED_FUNDS_M,
    RISKPOOL_WALLET:   REQUIRED_FUNDS_S,
    INVESTOR:          REQUIRED_FUNDS_S,
    CUSTOMER1:         REQUIRED_FUNDS_S,
    CUSTOMER2:         REQUIRED_FUNDS_S,
}

def stakeholders_accounts_ganache():
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

    return {
        INSTANCE_OPERATOR: instanceOperator,
        INSTANCE_WALLET: instanceWallet,
        ORACLE_PROVIDER: oracleProvider,
        NODE_OPERATOR: chainlinkNodeOperator,
        RISKPOOL_KEEPER: riskpoolKeeper,
        RISKPOOL_WALLET: riskpoolWallet,
        INVESTOR: investor,
        PRODUCT_OWNER: productOwner,
        INSURER: insurer,
        CUSTOMER1: customer,
        CUSTOMER2: customer2,
    }


def check_funds(stakeholders_accounts):
    a = stakeholders_accounts
    fundsMissing = 0
    for accountName, requiredAmount in REQUIRED_FUNDS.items():
        if a[accountName].balance() >= REQUIRED_FUNDS[accountName]:
            print('{} funding ok'.format(accountName))
        else:
            fundsMissing += REQUIRED_FUNDS[accountName] - a[accountName].balance()
            print('{} needs {} but has {}'.format(
                accountName,
                REQUIRED_FUNDS[accountName],
                a[accountName].balance()
            ))
    
    if fundsMissing > 0:
        if a[INSTANCE_OPERATOR].balance() >= REQUIRED_FUNDS[INSTANCE_OPERATOR] + fundsMissing:
            print('{} sufficiently funded to cover missing funds'.format(INSTANCE_OPERATOR))
        else:
            print('{} needs additional funding of {} to cover missing funds'.format(
                INSTANCE_OPERATOR,
                REQUIRED_FUNDS[INSTANCE_OPERATOR] + fundsMissing - a[INSTANCE_OPERATOR].balance()
            ))


def amend_funds(stakeholders_accounts):
    a = stakeholders_accounts
    for accountName, requiredAmount in REQUIRED_FUNDS.items():
        if a[accountName].balance() < REQUIRED_FUNDS[accountName]:
            missingAmount = REQUIRED_FUNDS[accountName] - a[accountName].balance()
            print('funding {} with {}'.format(accountName, missingAmount))
            a[INSTANCE_OPERATOR].transfer(a[accountName], missingAmount)


def _get_balances(stakeholders_accounts):
    balance = {}

    for accountName, account in stakeholders_accounts.items():
        balance[accountName] = account.balance()

    return balance


def _get_balances_delta(balances_before, balances_after):
    balance_delta = { 'total': 0 }

    for accountName, account in balances_before.items():
        balance_delta[accountName] = balances_before[accountName] - balances_after[accountName]
        balance_delta['total'] += balance_delta[accountName]
    
    return balance_delta


def _pretty_print_delta(title, balances_delta):

    print('--- {} ---'.format(title))
    
    gasPrice = network.gas_price()
    print('gas price: {}'.format(gasPrice))

    for accountName, amount in balances_delta.items():
        if accountName != 'total':
            if gasPrice != 'auto':
                print('account {}: gas {}'.format(accountName, amount / gasPrice))
            else:
                print('account {}: amount {}'.format(accountName, amount))
    
    print('-----------------------------')
    if gasPrice != 'auto':
        print('account total: gas {}'.format(balances_delta['total'] / gasPrice))
    else:
        print('account total: amount {}'.format(balances_delta['total']))
    print('=============================')


def deploy_setup_including_token(
    stakeholders_accounts, 
    publishSource=False
):
    return deploy(stakeholders_accounts, None)


def deploy(
    stakeholders_accounts, 
    erc20_token,
    publishSource=False
):

    # define stakeholder accounts
    a = stakeholders_accounts
    instanceOperator=a[INSTANCE_OPERATOR]
    instanceWallet=a[INSTANCE_WALLET]
    oracleProvider=a[ORACLE_PROVIDER]
    chainlinkNodeOperator=a[NODE_OPERATOR]
    riskpoolKeeper=a[RISKPOOL_KEEPER]
    riskpoolWallet=a[RISKPOOL_WALLET]
    investor=a[INVESTOR]
    productOwner=a[PRODUCT_OWNER]
    insurer=a[INSURER]
    customer=a[CUSTOMER1]
    customer2=a[CUSTOMER2]

    # assess balances at beginning of deploy
    balances_before = _get_balances(stakeholders_accounts)

    if not erc20_token:
        print('====== deploy erc20 test token ======')
        erc20Token = TestCoin.deploy({'from': instanceOperator})
    else:
        print('====== setting erc20 token to {} ======'.format(erc20_token))
        erc20Token = erc20_token


    print('====== deploy gif instance ======')
    instance = GifInstance(instanceOperator, instanceWallet=instanceWallet)
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    print('====== deploy ayii product ======')
    ayiiDeploy = GifAyiiProductComplete(instance, productOwner, insurer, oracleProvider, chainlinkNodeOperator, riskpoolKeeper, investor, erc20Token, riskpoolWallet)

    # assess balances at beginning of deploy
    balances_after_deploy = _get_balances(stakeholders_accounts)

    ayiiProduct = ayiiDeploy.getProduct()
    ayiiOracle = ayiiProduct.getOracle()
    ayiiRiskpool = ayiiProduct.getRiskpool()

    product = ayiiProduct.getContract()
    oracle = ayiiOracle.getContract()
    riskpool = ayiiRiskpool.getContract()

    print('====== create initial setup ======')

    bundleInitialFunding=1000000
    print('1) investor {} funding (transfer/approve) with {} token for erc20 {}'.format(
        investor, bundleInitialFunding, erc20Token))
    
    erc20Token.transfer(investor, bundleInitialFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), bundleInitialFunding, {'from': investor})

    maxUint256 = 2**256-1
    print('2) riskpool wallet {} approval for instance treasury {}'.format(
        riskpoolWallet, instance.getTreasury()))
    
    erc20Token.approve(instance.getTreasury(), maxUint256, {'from': riskpoolWallet})

    print('3) riskpool bundle creation by investor {}'.format(
        investor))

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

    print('4) risk creation (2x) by insurer {}'.format(
        insurer))

    tx = [None, None]
    tx[0] = product.createRisk(projectId, uaiId[0], cropId, trigger, exit_, tsi, aph[0], {'from': insurer})
    tx[1] = product.createRisk(projectId, uaiId[1], cropId, trigger, exit_, tsi, aph[1], {'from': insurer})

    riskId1 = tx[0].events['LogAyiiRiskDataCreated']['riskId']
    riskId2 = tx[1].events['LogAyiiRiskDataCreated']['riskId']

    customerFunding=1000
    print('5) customer {} funding (transfer/approve) with {} token for erc20 {}'.format(
        investor, customerFunding, erc20Token))

    erc20Token.transfer(customer, customerFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), customerFunding, {'from': customer})

    # policy creation
    premium = [300, 400]
    sumInsured = [2000, 3000]
    print('6) policy creation (2x) for customers {}, {} by insurer {}'.format(
        customer, customer2, insurer))

    tx[0] = product.applyForPolicy(customer, premium[0], sumInsured[0], riskId1, {'from': insurer})
    tx[1] = product.applyForPolicy(customer2, premium[1], sumInsured[1], riskId2, {'from': insurer})

    processId1 = tx[0].events['LogAyiiPolicyCreated']['policyId']
    processId2 = tx[1].events['LogAyiiPolicyCreated']['policyId']

    deploy_result = {
        INSTANCE_OPERATOR: instanceOperator,
        INSTANCE_WALLET: instanceWallet,
        ORACLE_PROVIDER: oracleProvider,
        NODE_OPERATOR: chainlinkNodeOperator,
        RISKPOOL_KEEPER: riskpoolKeeper,
        RISKPOOL_WALLET: riskpoolWallet,
        INVESTOR: investor,
        PRODUCT_OWNER: productOwner,
        INSURER: insurer,
        CUSTOMER1: customer,
        CUSTOMER2: customer2,
        ERC20_TOKEM: contract_from_address(TestCoin, erc20Token),
        INSTANCE: instance,
        INSTANCE_SERVICE: contract_from_address(InstanceService, instanceService),
        INSTANCE_OPERATOR_SERVICE: contract_from_address(InstanceOperatorService, instanceOperatorService),
        COMPONENT_OWNER_SERVICE: contract_from_address(ComponentOwnerService, componentOwnerService),
        PRODUCT: contract_from_address(AyiiProduct, product),
        ORACLE: contract_from_address(AyiiOracle, oracle),
        RISKPOOL: contract_from_address(AyiiRiskpool, riskpool),
        RISK_ID1: riskId1,
        RISK_ID2: riskId2,
        PROCESS_ID1: processId1,
        PROCESS_ID2: processId2,
    }

    print('deploy_result: {}'.format(deploy_result))

    print('====== deploy and setup creation complete ======')
    print('')

    # check balances at end of setup
    balances_after_setup = _get_balances(stakeholders_accounts)

    print('--------------------------------------------------------------------')
    print('inital balances: {}'.format(balances_before))
    print('after deploy balances: {}'.format(balances_after_deploy))
    print('end of setup balances: {}'.format(balances_after_setup))

    delta_deploy = _get_balances_delta(balances_before, balances_after_deploy)
    delta_setup = _get_balances_delta(balances_after_deploy, balances_after_setup)
    delta_total = _get_balances_delta(balances_before, balances_after_setup)

    print('--------------------------------------------------------------------')
    print('total deploy {}'.format(delta_deploy['total']))
    print('deploy {}'.format(delta_deploy))

    print('--------------------------------------------------------------------')
    print('total setup after deploy {}'.format(delta_setup['total']))
    print('setup after deploy {}'.format(delta_setup))

    print('--------------------------------------------------------------------')
    print('total deploy + setup{}'.format(delta_total['total']))
    print('deploy + setup{}'.format(delta_total))

    print('--------------------------------------------------------------------')

    _pretty_print_delta('gas usage deploy', delta_deploy)
    _pretty_print_delta('gas usage total', delta_total)

    return deploy_result


def from_component(componentAddress):
    component = contract_from_address(interface.IComponent, componentAddress)
    return from_registry(component.getRegistry())


def from_registry(registryAddress):
    instance = GifInstance(registryAddress=registryAddress)
    instanceService = instance.getInstanceService()

    products = instanceService.products()
    oracles = instanceService.oracles()
    riskpools = instanceService.riskpools()

    product = None
    oracle = None
    riskpool = None

    if products >= 1:
        if products > 1:
            print('1 product expected, {} product available'.format(products))
            print('returning last product available')
        
        componentId = instanceService.getProductId(products-1)
        component = instanceService.getComponent(componentId)
        product = contract_from_address(AyiiProduct, component)
    else:
        print('1 product expected, no producta available')
        print('no product returned (None)')

    if oracles >= 1:
        if oracles > 1:
            print('1 oracle expected, {} oracles available'.format(oracles))
            print('returning last oracle available')
        
        componentId = instanceService.getOracleId(oracles-1)
        component = instanceService.getComponent(componentId)        
        oracle = contract_from_address(AyiiOracle, component)
    else:
        print('1 oracle expected, no oracles available')
        print('no oracle returned (None)')

    if riskpools >= 1:
        if riskpools > 1:
            print('1 riskpool expected, {} riskpools available'.format(riskpools))
            print('returning last riskpool available')
        
        componentId = instanceService.getRiskpoolId(riskpools-1)
        component = instanceService.getComponent(componentId)        
        riskpool = contract_from_address(AyiiRiskpool, component)
    else:
        print('1 riskpool expected, no riskpools available')
        print('no riskpool returned (None)')

    return (instance, product, oracle, riskpool)


def dry_run_create_risks(product, insurer):
    project = '2022.kenya.wfp.ayii'
    crop = 'maize'

    trigger = 0.75
    tsi = 0.9
    exit_ = 0.1 

    aez = [
        22,
        23,
        26,
        29,
        30,
        32,
        34,
        38,
        39,
        40]

    aph = [
        2.28,
        2.42,
        2.14,
        2.01,
        3.03,
        3.05,
        2.38,
        1.84,
        2.60,
        2.30]
    
    print("project, aez, crop, trigger, exit, tsi, aph, riskId")
    for i in range(len(aez)):
        riskId = create_risk(product, insurer, project, aez[i], crop, trigger, exit_, tsi, aph[i])
        print(project, aez[i], crop, trigger, exit_, tsi, aph[i], riskId)


def create_risk(product, insurer, project, uai, crop, trigger, exit_, tsi, aph):
    
    multiplier = product.getPercentageMultiplier()
    triggerInt = multiplier * trigger
    exitInt = multiplier * exit_
    tsiInt = multiplier * tsi
    aphInt = multiplier * aph

    tx = product.createRisk(
        s2b32(project),
        s2b32(str(uai)),
        s2b32(crop),
        triggerInt, 
        exitInt, 
        tsiInt, 
        aphInt,
        {'from': insurer}
    )

    return tx.events['LogAyiiRiskDataCreated']['riskId']
