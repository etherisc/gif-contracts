from datetime import datetime

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
    INSURER:           REQUIRED_FUNDS_M,
    ORACLE_PROVIDER:   int(1.2 * REQUIRED_FUNDS_M),
    RISKPOOL_KEEPER:   REQUIRED_FUNDS_M,
    RISKPOOL_WALLET:   REQUIRED_FUNDS_S,
    INVESTOR:          REQUIRED_FUNDS_S,
    CUSTOMER1:         REQUIRED_FUNDS_S,
    CUSTOMER2:         REQUIRED_FUNDS_S,
}


def help():
    print('from scripts.util import s2b, b2s, contract_from_address')
    print('from scripts.deploy_ayii import stakeholders_accounts_ganache, check_funds, amend_funds, deploy, deploy_product_riskpool, from_registry, from_component, verify_deploy')
    print()
    print('#--- deploy ganache setup ---------------------------------------#')
    print('a = stakeholders_accounts_ganache()')
    print("instance_operator = a['instanceOperator']")
    print("token = TestCoin.deploy({'from': instance_operator})")
    print()
    print('check_funds(a, token)')
    print('# amend_funds(a)')
    print('d = deploy(a, token, False)')
    print()
    print("(instance, product, oracle, riskpool) = from_registry(d['instance'].getRegistry())")
    print("verify_deploy(a, token, instance.getRegistry())")
    print()
    print('#--- deploy to existing instance --------------------------------#')
    print('check_funds(a, token)')
    print("registry_address = d['instance'].getRegistry()")
    print("registry_address = instance.getRegistry().address")
    print('collateralization_level = 0')
    print()
    print('product_old = product')
    print('oracle_old = oracle')
    print('riskpool_old = riskpool')
    print()
    print('(instance, product, oracle, riskpool) = deploy_product_riskpool(registry_address, a, token, collateralization_level)')



def stakeholders_accounts_ganache():
    # define stakeholder accounts
    instanceOperator = accounts[0]
    instanceWallet = accounts[1]
    oracleProvider = accounts[2]
    chainlinkNodeOperator = accounts[3]
    riskpoolKeeper = accounts[4]
    riskpoolWallet = accounts[5]
    investor = accounts[6]
    productOwner = accounts[7]
    insurer = accounts[8]
    customer = accounts[9]
    customer2 = accounts[10]

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


def check_funds(stakeholders_accounts, erc20_token):
    _print_constants()

    a = stakeholders_accounts

    native_token_success = True
    fundsMissing = 0
    for accountName, requiredAmount in REQUIRED_FUNDS.items():
        if a[accountName].balance() >= REQUIRED_FUNDS[accountName]:
            print('{} funding ok'.format(accountName))
        else:
            fundsMissing += REQUIRED_FUNDS[accountName] - \
                a[accountName].balance()
            print('{} needs {} but has {}'.format(
                accountName,
                REQUIRED_FUNDS[accountName],
                a[accountName].balance()
            ))

    if fundsMissing > 0:
        native_token_success = False

        if a[INSTANCE_OPERATOR].balance() >= REQUIRED_FUNDS[INSTANCE_OPERATOR] + fundsMissing:
            print('{} sufficiently funded with native token to cover missing funds'.format(
                INSTANCE_OPERATOR))
        else:
            additionalFunds = REQUIRED_FUNDS[INSTANCE_OPERATOR] + \
                fundsMissing - a[INSTANCE_OPERATOR].balance()
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
            missingAmount = REQUIRED_FUNDS[accountName] - \
                a[accountName].balance()
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
    balance_delta = {'total': 0}

    for accountName, account in balances_before.items():
        balance_delta[accountName] = balances_before[accountName] - \
            balances_after[accountName]
        balance_delta['total'] += balance_delta[accountName]

    return balance_delta


def _pretty_print_delta(title, balances_delta):

    print('--- {} ---'.format(title))

    gasPrice = network.gas_price()
    print('gas price: {}'.format(gasPrice))

    for accountName, amount in balances_delta.items():
        if accountName != 'total':
            if gasPrice != 'auto':
                print('account {}: gas {}'.format(
                    accountName, amount / gasPrice))
            else:
                print('account {}: amount {}'.format(accountName, amount))

    print('-----------------------------')
    if gasPrice != 'auto':
        print('account total: gas {}'.format(
            balances_delta['total'] / gasPrice))
    else:
        print('account total: amount {}'.format(balances_delta['total']))
    print('=============================')


def deploy_setup_including_token(
    stakeholders_accounts,
    erc20_token,
    publishSource=False
):
    return deploy(stakeholders_accounts, erc20_token, None)


def verify_deploy(
    stakeholders_accounts,
    erc20_token,
    registry_address
):
    # define stakeholder accounts
    a = stakeholders_accounts
    instanceOperator = a[INSTANCE_OPERATOR]
    instanceWallet = a[INSTANCE_WALLET]
    oracleProvider = a[ORACLE_PROVIDER]
    chainlinkNodeOperator = a[NODE_OPERATOR]
    riskpoolKeeper = a[RISKPOOL_KEEPER]
    riskpoolWallet = a[RISKPOOL_WALLET]
    investor = a[INVESTOR]
    productOwner = a[PRODUCT_OWNER]
    insurer = a[INSURER]
    customer = a[CUSTOMER1]
    customer2 = a[CUSTOMER2]

    (
        instance,
        product,
        oracle,
        riskpool
    ) = from_registry(registry_address)

    instanceService = instance.getInstanceService()
    riskpoolId = 1
    oracleId = 2
    productId = 3

    verify_element('Registry', instanceService.getRegistry(), registry_address)
    verify_element('InstanceOperator',
                   instanceService.getInstanceOperator(), instanceOperator)
    verify_element('InstanceWallet',
                   instanceService.getInstanceWallet(), instanceWallet)

    verify_element('RiskpoolId', riskpool.getId(), riskpoolId)
    verify_element(
        'RiskpoolType', instanceService.getComponentType(riskpoolId), 2)
    verify_element('RiskpoolState',
                   instanceService.getComponentState(riskpoolId), 3)
    verify_element('RiskpoolKeeper', riskpool.owner(), riskpoolKeeper)
    verify_element('RiskpoolWallet', instanceService.getRiskpoolWallet(
        riskpoolId), riskpoolWallet)
    verify_element('RiskpoolBalance', instanceService.getBalance(
        riskpoolId), erc20_token.balanceOf(riskpoolWallet))
    verify_element('RiskpoolToken', riskpool.getErc20Token(),
                   erc20_token.address)

    verify_element('OracleId', oracle.getId(), oracleId)
    verify_element('OracleType', instanceService.getComponentType(oracleId), 0)
    verify_element(
        'OracleState', instanceService.getComponentState(oracleId), 3)
    verify_element('OracleProvider', oracle.owner(), oracleProvider)

    verify_element('ProductId', product.getId(), productId)
    verify_element(
        'ProductType', instanceService.getComponentType(productId), 1)
    verify_element(
        'ProductState', instanceService.getComponentState(productId), 3)
    verify_element('ProductOwner', product.owner(), productOwner)
    verify_element('ProductToken', product.getToken(), erc20_token.address)
    verify_element('ProductRiskpool', product.getRiskpoolId(), riskpoolId)

    print('InstanceWalletBalance {:.2f}'.format(erc20_token.balanceOf(
        instanceService.getInstanceWallet())/10**erc20_token.decimals()))
    print('RiskpoolWalletTVL {:.2f}'.format(
        instanceService.getTotalValueLocked(riskpoolId)/10**erc20_token.decimals()))
    print('RiskpoolWalletCapacity {:.2f}'.format(
        instanceService.getCapacity(riskpoolId)/10**erc20_token.decimals()))
    print('RiskpoolWalletBalance {:.2f}'.format(erc20_token.balanceOf(
        instanceService.getRiskpoolWallet(riskpoolId))/10**erc20_token.decimals()))
    print('RiskpoolBundles {}'.format(riskpool.bundles()))

    bundle_id = riskpool.getBundleId(0)
    print('RiskpoolBundle[0] {}'.format(instanceService.getBundle(bundle_id).dict()))
    print('ProductRisks {}'.format(product.risks()))
    print('ProductApplications {}'.format(product.applications()))


def verify_element(
    element,
    value,
    expected_value
):
    if value == expected_value:
        print('{} OK {}'.format(element, value))
    else:
        print('{} ERROR {} expected {}'.format(element, value, expected_value))


def deploy_product_riskpool(
    registry_address,
    stakeholders_accounts,
    erc20_token,
    collateralizaionLevel,
    publishSource=False
):
    # define stakeholder accounts
    a = stakeholders_accounts
    instanceOperator = a[INSTANCE_OPERATOR]
    instanceWallet = a[INSTANCE_WALLET]
    oracleProvider = a[ORACLE_PROVIDER]
    chainlinkNodeOperator = a[NODE_OPERATOR]
    riskpoolKeeper = a[RISKPOOL_KEEPER]
    riskpoolWallet = a[RISKPOOL_WALLET]
    investor = a[INVESTOR]
    productOwner = a[PRODUCT_OWNER]
    insurer = a[INSURER]
    customer = a[CUSTOMER1]
    customer2 = a[CUSTOMER2]

    # create basename including unix timestamp
    baseName = 'Ayii_{}_'.format(int(datetime.now().timestamp()))

    if not check_funds(a, erc20_token):
        print('ERROR: insufficient funding, aborting deploy')
        return

    if not erc20_token:
        print('ERROR: no erc20 defined, aborting deploy')
        return

    print('====== setting erc20 token to {} ======'.format(erc20_token))
    erc20Token = erc20_token

    print('====== getting instance from registry address {} ======'.format(registry_address))
    (instance, product, oracle, riskpool) = from_registry(registry_address)


    print("====== deploy ayii product /w base name '{}' and riskpool collateralization level {} ======".format(baseName, collateralizaionLevel))
    ayiiDeploy = GifAyiiProductComplete(
        instance, productOwner, insurer, oracleProvider, chainlinkNodeOperator,
        riskpoolKeeper, investor, erc20Token, riskpoolWallet, collateralizaionLevel, 
        baseName=baseName, publishSource=publishSource)

    ayiiProduct = ayiiDeploy.getProduct()
    ayiiOracle = ayiiProduct.getOracle()
    ayiiRiskpool = ayiiProduct.getRiskpool()

    product = ayiiProduct.getContract()
    oracle = ayiiOracle.getContract()
    riskpool = ayiiRiskpool.getContract()

    print("====== create bundle for investor {} ======".format(investor))
    initial_funding = 10**erc20Token.decimals()
    bundle_filter = b''
    erc20Token.transfer(investor, initial_funding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury().address, initial_funding, {'from': investor})
    riskpool.createBundle(bundle_filter, initial_funding, {'from': investor})

    return (
        instance,
        product,
        oracle,
        riskpool
    )


def deploy(
    stakeholders_accounts,
    erc20_token,
    publishSource=False
):

    # define stakeholder accounts
    a = stakeholders_accounts
    instanceOperator = a[INSTANCE_OPERATOR]
    instanceWallet = a[INSTANCE_WALLET]
    oracleProvider = a[ORACLE_PROVIDER]
    chainlinkNodeOperator = a[NODE_OPERATOR]
    riskpoolKeeper = a[RISKPOOL_KEEPER]
    riskpoolWallet = a[RISKPOOL_WALLET]
    investor = a[INVESTOR]
    productOwner = a[PRODUCT_OWNER]
    insurer = a[INSURER]
    customer = a[CUSTOMER1]
    customer2 = a[CUSTOMER2]

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
    instance = GifInstance(
        instanceOperator, instanceWallet=instanceWallet, publishSource=publishSource)
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    componentOwnerService = instance.getComponentOwnerService()

    print('====== deploy ayii product ======')
    collateralizationLevel = instanceService.getFullCollateralizationLevel()
    ayiiDeploy = GifAyiiProductComplete(instance, productOwner, insurer, oracleProvider, chainlinkNodeOperator,
        riskpoolKeeper, investor, erc20Token, riskpoolWallet, collateralizationLevel, 
        publishSource=publishSource)

    # assess balances at beginning of deploy
    balances_after_deploy = _get_balances(stakeholders_accounts)

    ayiiProduct = ayiiDeploy.getProduct()
    ayiiOracle = ayiiProduct.getOracle()
    ayiiRiskpool = ayiiProduct.getRiskpool()

    product = ayiiProduct.getContract()
    oracle = ayiiOracle.getContract()
    riskpool = ayiiRiskpool.getContract()

    print('====== create initial setup ======')

    bundleInitialFunding = INITIAL_ERC20_BUNDLE_FUNDING
    print('1) investor {} funding (transfer/approve) with {} token for erc20 {}'.format(
        investor, bundleInitialFunding, erc20Token))

    erc20Token.transfer(investor, bundleInitialFunding,
                        {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(),
                       bundleInitialFunding, {'from': investor})

    print('2) riskpool wallet {} approval for instance treasury {}'.format(
        riskpoolWallet, instance.getTreasury()))

    erc20Token.approve(instance.getTreasury(), bundleInitialFunding, {
                       'from': riskpoolWallet})

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
    tx[0] = product.createRisk(
        projectId, uaiId[0], cropId, trigger, exit_, tsi, aph[0], {'from': insurer})
    tx[1] = product.createRisk(
        projectId, uaiId[1], cropId, trigger, exit_, tsi, aph[1], {'from': insurer})

    riskId1 = tx[0].events['LogAyiiRiskDataCreated']['riskId']
    riskId2 = tx[1].events['LogAyiiRiskDataCreated']['riskId']

    customerFunding = 1000
    print('5) customer {} funding (transfer/approve) with {} token for erc20 {}'.format(
        customer, customerFunding, erc20Token))

    erc20Token.transfer(customer, customerFunding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(),
                       customerFunding, {'from': customer})

    # policy creation
    premium = [300, 400]
    sumInsured = [2000, 3000]
    print('6) policy creation (2x) for customers {}, {} by insurer {}'.format(
        customer, customer2, insurer))

    tx[0] = product.applyForPolicy(
        customer, premium[0], sumInsured[0], riskId1, {'from': insurer})
    tx[1] = product.applyForPolicy(
        customer2, premium[1], sumInsured[1], riskId2, {'from': insurer})

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
        ERC20_TOKEM: contract_from_address(interface.ERC20, erc20Token),
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
    delta_setup = _get_balances_delta(
        balances_after_deploy, balances_after_setup)
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


def from_registry(
    registryAddress,
    productId=0,
    oracleId=0,
    riskpoolId=0
):
    instance = GifInstance(registryAddress=registryAddress)
    instanceService = instance.getInstanceService()

    products = instanceService.products()
    oracles = instanceService.oracles()
    riskpools = instanceService.riskpools()

    product = None
    oracle = None
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
            print('component (type={}) with id {} is not product'.format(
                product.getType(), componentId))
            print('no product returned (None)')
    else:
        print('1 product expected, no product available')
        print('no product returned (None)')

    if oracles >= 1:
        if oracleId > 0:
            componentId = oracleId
        else:
            componentId = instanceService.getOracleId(oracles-1)

            if oracles > 1:
                print('1 oracle expected, {} oracles available'.format(oracles))
                print('returning last oracle available')

        componentAddress = instanceService.getComponent(componentId)
        oracle = contract_from_address(AyiiOracle, componentAddress)

        if oracle.getType() != 0:
            oracle = None
            print('component (type={}) with id {} is not oracle'.format(
                component.getType(), componentId))
            print('no oracle returned (None)')
    else:
        print('1 oracle expected, no oracles available')
        print('no oracle returned (None)')

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
            print('component (type={}) with id {} is not riskpool'.format(
                component.getType(), componentId))
            print('no riskpool returned (None)')
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
        riskId = create_risk(product, insurer, project,
                             aez[i], crop, trigger, exit_, tsi, aph[i])
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
