from brownie import web3

from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    interface,
    network,
    TestCoin,
    InstanceService,
    InstanceOperatorService,
    ComponentOwnerService,
    DepegProduct,
    DepegRiskpool
)

from scripts.depeg_product import GifDepegProductComplete
from scripts.instance import GifInstance
from scripts.util import contract_from_address, s2b32

INSTANCE_OPERATOR = 'instanceOperator'
INSTANCE_WALLET = 'instanceWallet'
RISKPOOL_KEEPER = 'riskpoolKeeper'
RISKPOOL_WALLET = 'riskpoolWallet'
INVESTOR = 'investor'
PRODUCT_OWNER = 'productOwner'
CUSTOMER1 = 'customer1'
CUSTOMER2 = 'customer2'

ERC20_TOKEM = 'erc20Token'
INSTANCE = 'instance'
INSTANCE_SERVICE = 'instanceService'
INSTANCE_OPERATOR_SERVICE = 'instanceOperatorService'
COMPONENT_OWNER_SERVICE = 'componentOwnerService'
PRODUCT = 'product'
RISKPOOL = 'riskpool'

PROCESS_ID1 = 'processId1'
PROCESS_ID2 = 'processId2'

GAS_PRICE = web3.eth.gas_price
GAS_PRICE_SAFETY_FACTOR = 1.25

GAS_S = 2000000
GAS_M = 3 * GAS_S
GAS_L = 10 * GAS_M

REQUIRED_FUNDS_S = int(GAS_PRICE * GAS_PRICE_SAFETY_FACTOR * GAS_S)
REQUIRED_FUNDS_M = int(GAS_PRICE * GAS_PRICE_SAFETY_FACTOR * GAS_M)
REQUIRED_FUNDS_L = int(GAS_PRICE * GAS_PRICE_SAFETY_FACTOR * GAS_L)

INITIAL_ERC20_BUNDLE_FUNDING = 100000

REQUIRED_FUNDS = {
    INSTANCE_OPERATOR: REQUIRED_FUNDS_L,
    INSTANCE_WALLET:   REQUIRED_FUNDS_S,
    PRODUCT_OWNER:     REQUIRED_FUNDS_M,
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
    riskpoolKeeper=accounts[2]
    riskpoolWallet=accounts[3]
    investor=accounts[4]
    productOwner=accounts[5]
    customer=accounts[6]
    customer2=accounts[7]

    return {
        INSTANCE_OPERATOR: instanceOperator,
        INSTANCE_WALLET: instanceWallet,
        RISKPOOL_KEEPER: riskpoolKeeper,
        RISKPOOL_WALLET: riskpoolWallet,
        INVESTOR: investor,
        PRODUCT_OWNER: productOwner,
        CUSTOMER1: customer,
        CUSTOMER2: customer2,
    }


def check_funds(stakeholders_accounts, erc20_token):
    _print_constants()

    a = stakeholders_accounts

    native_token_success = True
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
        native_token_success = False

        if a[INSTANCE_OPERATOR].balance() >= REQUIRED_FUNDS[INSTANCE_OPERATOR] + fundsMissing:
            print('{} sufficiently funded with native token to cover missing funds'.format(INSTANCE_OPERATOR))
        else:
            additionalFunds = REQUIRED_FUNDS[INSTANCE_OPERATOR] + fundsMissing - a[INSTANCE_OPERATOR].balance()
            print('{} needs additional funding of {} ({} ETH) with native token to cover missing funds'.format(
                INSTANCE_OPERATOR,
                additionalFunds,
                additionalFunds/10**18
            ))
    else:
        native_token_success = True

    erc20_success = False
    if erc20_token:
        erc20_success = check_erc20_funds(a, erc20_token)
    else:
        print('WARNING: no erc20 token defined, skipping erc20 funds checking')
    
    return native_token_success & erc20_success


def check_erc20_funds(a, erc20_token):
    if erc20_token.balanceOf(a[INSTANCE_OPERATOR]) >= INITIAL_ERC20_BUNDLE_FUNDING:
        print('{} ERC20 funding ok'.format(INSTANCE_OPERATOR))
        return True
    else:
        print('{} needs additional ERC20 funding of {} to cover missing funds'.format(
            INSTANCE_OPERATOR,
            INITIAL_ERC20_BUNDLE_FUNDING - erc20_token.balanceOf(a[INSTANCE_OPERATOR])))
        print('IMPORTANT: manual transfer needed to ensure ERC20 funding')
        return False


def amend_funds(stakeholders_accounts):
    a = stakeholders_accounts
    for accountName, requiredAmount in REQUIRED_FUNDS.items():
        if a[accountName].balance() < REQUIRED_FUNDS[accountName]:
            missingAmount = REQUIRED_FUNDS[accountName] - a[accountName].balance()
            print('funding {} with {}'.format(accountName, missingAmount))
            a[INSTANCE_OPERATOR].transfer(a[accountName], missingAmount)

    print('re-run check_funds() to verify funding before deploy')


def _print_constants():
    print('chain id: {}'.format(web3.eth.chain_id))
    print('gas price [Mwei]: {}'.format(GAS_PRICE/10**6))
    print('gas price safety factor: {}'.format(GAS_PRICE_SAFETY_FACTOR))

    print('gas S: {}'.format(GAS_S))
    print('gas M: {}'.format(GAS_M))
    print('gas L: {}'.format(GAS_L))

    print('required S [ETH]: {}'.format(REQUIRED_FUNDS_S / 10**18))
    print('required M [ETH]: {}'.format(REQUIRED_FUNDS_M / 10**18))
    print('required L [ETH]: {}'.format(REQUIRED_FUNDS_L / 10**18))


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
    erc20_token,
):
    return deploy(stakeholders_accounts, erc20_token, None)


def deploy(
    stakeholders_accounts, 
    erc20_token,
    publishSource=False
):

    # define stakeholder accounts
    a = stakeholders_accounts
    instanceOperator=a[INSTANCE_OPERATOR]
    instanceWallet=a[INSTANCE_WALLET]
    riskpoolKeeper=a[RISKPOOL_KEEPER]
    riskpoolWallet=a[RISKPOOL_WALLET]
    investor=a[INVESTOR]
    productOwner=a[PRODUCT_OWNER]
    customer=a[CUSTOMER1]
    customer2=a[CUSTOMER2]

    if not check_funds(a, erc20_token):
        print('ERROR: insufficient funding, aborting deploy')
        return

    # assess balances at beginning of deploy
    balances_before = _get_balances(stakeholders_accounts)

    if not erc20_token:
        print('ERROR: no erc20 defined, aborting deploy')
        return

    print('====== setting erc20 token to {} ======'.format(erc20_token))
    erc20Token = erc20_token

    print('====== deploy gif instance ======')
    instance = GifInstance(instanceOperator, instanceWallet=instanceWallet, publishSource=publishSource)
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    print('====== deploy depeg product ======')
    depegDeploy = GifDepegProductComplete(instance, productOwner, investor, erc20Token, riskpoolKeeper, riskpoolWallet, publishSource=publishSource)

    # assess balances at beginning of deploy
    balances_after_deploy = _get_balances(stakeholders_accounts)

    depegProduct = depegDeploy.getProduct()
    depegRiskpool = depegDeploy.getRiskpool()

    product = depegProduct.getContract()
    riskpool = depegRiskpool.getContract()

    print('====== create initial setup ======')

    bundleInitialFunding = INITIAL_ERC20_BUNDLE_FUNDING
    print('1) investor {} funding (transfer/approve) with {} token for erc20 {}'.format(
        investor, bundleInitialFunding, erc20Token))
    
    erc20Token.transfer(investor, bundleInitialFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), bundleInitialFunding, {'from': investor})

    print('2) riskpool wallet {} approval for instance treasury {}'.format(
        riskpoolWallet, instance.getTreasury()))
    
    erc20Token.approve(instance.getTreasury(), bundleInitialFunding, {'from': riskpoolWallet})

    print('3) riskpool bundle creation by investor {}'.format(
        investor))

    policyMinSumInsured =  1000
    policyMaxSumInsured = 50000
    policyMinDuration = 30 * 24 * 3600
    policyMaxDuration = 90 * 24 * 3600
    annualPercentageReturn = riskpool.getApr100PercentLevel() / 20;
    applicationFilter = bytes(0)
    riskpool.createBundle(
            policyMinSumInsured,
            policyMaxSumInsured,
            policyMinDuration,
            policyMaxDuration,
            annualPercentageReturn,
            bundleInitialFunding, 
            {'from': investor})

    customerFunding=1000
    print('5) customer {} funding (transfer/approve) with {} token for erc20 {}'.format(
        customer, customerFunding, erc20Token))

    erc20Token.transfer(customer, customerFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), customerFunding, {'from': customer})

    # policy creation
    premium = [300, 400]
    sumInsured = [2000, 3000]
    print('6) policy creation (2x) for customers {}, {}'.format(
        customer, customer2))

    tx = [None, None]
    tx[0] = product.applyForPolicy(premium[0], sumInsured[0], {'from': customer})
    tx[1] = product.applyForPolicy(premium[1], sumInsured[1], {'from': customer2})

    processId1 = tx[0].events['LogDepegPolicyCreated']['policyId']
    processId2 = tx[1].events['LogDepegPolicyCreated']['policyId']

    deploy_result = {
        INSTANCE_OPERATOR: instanceOperator,
        INSTANCE_WALLET: instanceWallet,
        RISKPOOL_KEEPER: riskpoolKeeper,
        RISKPOOL_WALLET: riskpoolWallet,
        INVESTOR: investor,
        PRODUCT_OWNER: productOwner,
        CUSTOMER1: customer,
        CUSTOMER2: customer2,
        ERC20_TOKEM: contract_from_address(interface.ERC20, erc20Token),
        INSTANCE: instance,
        INSTANCE_SERVICE: contract_from_address(InstanceService, instanceService),
        INSTANCE_OPERATOR_SERVICE: contract_from_address(InstanceOperatorService, instanceOperatorService),
        COMPONENT_OWNER_SERVICE: contract_from_address(ComponentOwnerService, componentOwnerService),
        PRODUCT: contract_from_address(DepegProduct, product),
        RISKPOOL: contract_from_address(DepegRiskpool, riskpool),
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


def help():
    print('from scripts.deploy_depeg import allIn1, inspect_bundle')
    print('(customer, product, riskpool, riskpoolWallet, usd1, instanceService, d) = allIn1()')
    print('inspect_bundle(d, 1)')


def allIn1():
    a = stakeholders_accounts_ganache()
    usd1 = TestCoin.deploy({'from':a[INSTANCE_OPERATOR]})
    d = deploy_setup_including_token(a, usd1)

    customer = d[CUSTOMER1]
    instanceService = d[INSTANCE_SERVICE]
    product = d[PRODUCT]
    riskpool = d[RISKPOOL]
    riskpoolWallet = d[RISKPOOL_WALLET]

    return (customer, product, riskpool, riskpoolWallet, usd1, instanceService, d)


def inspect_bundle(d, bundleId):
    instanceService = d[INSTANCE_SERVICE]
    riskpool = d[RISKPOOL]

    bundle = instanceService.getBundle(bundleId)
    filter = bundle[4]
    (
        minSumInsured,
        maxSumInsured,
        minDuration,
        maxDuration,
        annualPercentageReturn

    ) = riskpool.decodeBundleParamsFromFilter(filter)

    sPerD = 24 * 3600
    print('bundle {} riskpool {}'.format(bundleId, bundle[1]))
    print('- nft {}'.format(bundle[2]))
    print('- state {}'.format(bundle[3]))
    print('- filter')
    print('  + sum insured {}-{} [USD1]'.format(minSumInsured, maxSumInsured))
    print('  + coverage duration {}-{} [days]'.format(minDuration/sPerD, maxDuration/sPerD))
    print('  + apr {} [%]'.format(100 * annualPercentageReturn/riskpool.getApr100PercentLevel()))
    print('- financials')
    print('  + capital {}'.format(bundle[5]))
    print('  + locked {}'.format(bundle[6]))
    print('  + capacity {}'.format(bundle[5]-bundle[6]))
    print('  + balance {}'.format(bundle[7]))

def from_component(componentAddress):
    component = contract_from_address(interface.IComponent, componentAddress)
    return from_registry(component.getRegistry())


def from_registry(
    registryAddress,
    productId=0,
    riskpoolId=0
):
    instance = GifInstance(registryAddress=registryAddress)
    instanceService = instance.getInstanceService()

    products = instanceService.products()
    riskpools = instanceService.riskpools()

    product = None
    riskpool = None

    if products >= 1:
        if productId > 0:
            componentId = productId
        else:
            componentId = instanceService.getProductId(products-1)

            if products > 1:
                print('1 product expected, {} products available'.format(products))
                print('returning last product available')
        
        componentAddress = instanceService.getComponent(componentId)
        product = contract_from_address(AyiiProduct, componentAddress)

        if product.getType() != 1:
            product = None
            print('component (type={}) with id {} is not product'.format(product.getType(), componentId))
            print('no product returned (None)')
    else:
        print('1 product expected, no product available')
        print('no product returned (None)')

    if riskpools >= 1:
        if riskpoolId > 0:
            componentId = riskpoolId
        else:
            componentId = instanceService.getRiskpoolId(riskpools-1)

            if riskpools > 1:
                print('1 riskpool expected, {} riskpools available'.format(riskpools))
                print('returning last riskpool available')
        
        componentAddress = instanceService.getComponent(componentId)
        riskpool = contract_from_address(AyiiRiskpool, componentAddress)

        if riskpool.getType() != 2:
            riskpool = None
            print('component (type={}) with id {} is not riskpool'.format(component.getType(), componentId))
            print('no riskpool returned (None)')
    else:
        print('1 riskpool expected, no riskpools available')
        print('no riskpool returned (None)')

    return (instance, product, riskpool)
