import pytest
import web3

from typing import Dict

from brownie import (
    Wei,
    Contract, 
    CoreProxy,
    BundleToken,
    RiskpoolToken,
    AccessController,
    BundleController,
    BundleToken,
    RegistryController,
    LicenseController,
    PolicyController,
    QueryController,
    PoolController,
    ProductService,
    OracleService,
    RiskpoolService,
    ComponentOwnerService,
    PolicyDefaultFlow,
    InstanceOperatorService,
    InstanceService,
    TestCoin,
    TestCoinAlternativeImplementation,
    TestCoinX,
    TestRiskpool,
    TestOracle,
    TestProduct,
    TestRiskpool,
    TestRegistryControllerUpdated,
    TestRegistryCompromisedController,
    AyiiProduct,
    AyiiOracle,
    AyiiRiskpool,
)

from brownie.network import accounts
from brownie.network.account import Account

from scripts.const import (
    GIF_RELEASE,
    ACCOUNTS_MNEMONIC, 
)

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestRiskpool,
    GifTestOracle,
    GifTestProduct,
)

from scripts.ayii_product import (
    GifAyiiProduct,
    GifAyiiOracle,
    GifAyiiRiskpool,
    GifAyiiProductComplete,
)

from scripts.util import (
    get_account,
    encode_function_data,
    s2h,
    s2b32,
    deployGifModule,
    deployGifModuleV2,
    deployGifService,
)

PUBLISH_SOURCE = False

# @pytest.fixture(scope="function", autouse=True)
# def isolate(fn_isolation):
#     # perform a chain rewind after completing each test, to ensure proper isolation
#     # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
#     pass

# -- comments below may be used /w 'brownie console'
# mnemonic = 'candy maple cake sugar pudding cream honey rich smooth crumble sweet treat'
# owner = accounts.from_mnemonic(mnemonic, count=1, offset=0)
def get_filled_account(accounts, account_no, funding) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, account_no)
    accounts[account_no].transfer(owner, funding)
    return owner

# fixtures with `yield` execute the code that is placed before the `yield` as setup code
# and code after `yield` is teardown code. 
# See https://docs.pytest.org/en/7.1.x/how-to/fixtures.html#yield-fixtures-recommended
@pytest.fixture(autouse=True)
def run_around_tests():
    try:
        yield
        # after each test has finished, execute one trx and wait for it to finish. 
        # this is to ensure that the last transaction of the test is finished correctly. 
    finally:
        accounts[8].transfer(accounts[9], 1)
        # dummy_account = get_account(ACCOUNTS_MNEMONIC, 999)
        # execute_simple_incrementer_trx(dummy_account)

# DEPRECATED: use erc20Token instead
@pytest.fixture(scope="module")
def testCoin(erc20Token) -> TestCoin:
    return erc20Token

# DEPRECATED: use instanceOperator instead
@pytest.fixture(scope="module")
def owner(instanceOperator) -> Account:
    return instanceOperator

# DEPRECATED: use instanceWallet instead
@pytest.fixture(scope="module")
def feeOwner(instanceWallet) -> Account:
    return instanceWallet

# DEPRECATED: use riskpoolWallet instead
@pytest.fixture(scope="module")
def capitalOwner(riskpoolWallet) -> Account:
    return riskpoolWallet

@pytest.fixture(scope="module")
def instanceOperator(accounts) -> Account:
    return get_filled_account(accounts, 0, "1 ether")

@pytest.fixture(scope="module")
def instanceWallet(accounts) -> Account:
    return get_filled_account(accounts, 1, "1 ether")

@pytest.fixture(scope="module")
def oracleProvider(accounts) -> Account:
    return get_filled_account(accounts, 2, "1 ether")

@pytest.fixture(scope="module")
def chainlinkNodeOperator(accounts) -> Account:
    return get_filled_account(accounts, 3, "1 ether")

@pytest.fixture(scope="module")
def riskpoolKeeper(accounts) -> Account:
    return get_filled_account(accounts, 4, "1 ether")

@pytest.fixture(scope="module")
def riskpoolWallet(accounts) -> Account:
    return get_filled_account(accounts, 5, "1 ether")

@pytest.fixture(scope="module")
def investor(accounts) -> Account:
    return get_filled_account(accounts, 6, "1 ether")

@pytest.fixture(scope="module")
def productOwner(accounts) -> Account:
    return get_filled_account(accounts, 7, "1 ether")

@pytest.fixture(scope="module")
def insurer(accounts) -> Account:
    return get_filled_account(accounts, 8, "1 ether")

@pytest.fixture(scope="module")
def customer(accounts) -> Account:
    return get_filled_account(accounts, 9, "1 ether")

@pytest.fixture(scope="module")
def customer2(accounts) -> Account:
    return get_filled_account(accounts, 10, "1 ether")

@pytest.fixture(scope="module")
def instance(owner, feeOwner) -> GifInstance:
    return GifInstance(owner, feeOwner)

@pytest.fixture(scope="module")
def instanceNoInstanceWallet(owner, feeOwner) -> GifInstance:
    return GifInstance(owner, feeOwner, setInstanceWallet=False)

@pytest.fixture(scope="module")
def gifTestOracle(instance: GifInstance, oracleProvider: Account) -> GifTestOracle:
    return GifTestOracle(instance, oracleProvider)

@pytest.fixture(scope="module")
def gifTestRiskpool(instance: GifInstance, riskpoolKeeper: Account, testCoin: Account, capitalOwner: Account, owner: Account) -> GifTestRiskpool:
    capitalization = 10**18
    return GifTestRiskpool(instance, riskpoolKeeper, testCoin, capitalOwner, capitalization)

@pytest.fixture(scope="module")
def gifTestProduct(
    instance: GifInstance, 
    testCoin,
    capitalOwner: Account, 
    productOwner: Account,
    gifTestOracle: GifTestOracle,
    gifTestRiskpool: GifTestRiskpool,
    owner
) -> GifTestProduct:
    return GifTestProduct(
        instance, 
        testCoin,
        capitalOwner,
        productOwner,
        gifTestOracle,
        gifTestRiskpool)

@pytest.fixture(scope="module")
def gifAyiiDeploy(
    instance: GifInstance, 
    productOwner: Account, 
    insurer: Account, 
    oracleProvider: Account, 
    chainlinkNodeOperator: Account, 
    riskpoolKeeper: Account, 
    investor: Account, 
    testCoin,
    riskpoolWallet: Account
) -> GifAyiiProductComplete:
    return GifAyiiProductComplete(
        instance, 
        productOwner, 
        insurer, 
        oracleProvider, 
        chainlinkNodeOperator, 
        riskpoolKeeper, 
        investor, 
        testCoin, 
        riskpoolWallet)

@pytest.fixture(scope="module")
def gifAyiiProduct(gifAyiiDeploy) -> GifAyiiProduct:
    return gifAyiiDeploy.getProduct()

@pytest.fixture(scope="module")
def gifAyiiOracle(gifAyiiDeploy) -> GifAyiiOracle:
    return gifAyiiDeploy.getOracle()

@pytest.fixture(scope="module")
def gifAyiiRiskpool(gifAyiiDeploy) -> GifAyiiRiskpool:
    return gifAyiiDeploy.getRiskpool()

@pytest.fixture(scope="module")
def testProduct(gifTestProduct: GifTestProduct):
    return gifTestProduct.getContract()

@pytest.fixture(scope="module")
def registryController(RegistryController, owner) -> RegistryController:
    return RegistryController.deploy({'from': owner})

@pytest.fixture(scope="module")
def registryControllerV2Test(TestRegistryControllerUpdated, owner) -> TestRegistryControllerUpdated:
    return TestRegistryControllerUpdated.deploy({'from': owner})

@pytest.fixture(scope="module")
def registryCompromisedControllerV2Test(TestRegistryCompromisedController, customer) -> TestRegistryCompromisedController:
    return TestRegistryCompromisedController.deploy({'from': customer})

@pytest.fixture(scope="module")
def registry(registryController, owner) -> RegistryController:
    encoded_initializer = encode_function_data(
        s2b32(GIF_RELEASE),
        initializer=registryController.initializeRegistry)

    proxy = CoreProxy.deploy(
        registryController.address, 
        encoded_initializer, 
        {'from': owner})

    registry = contractFromAddress(RegistryController, proxy.address)
    registry.register(s2b32("Registry"), proxy.address, {'from': owner})
    registry.register(s2b32("RegistryController"), registryController.address, {'from': owner})

    return registry

@pytest.fixture(scope="module")
def erc20Token(instanceOperator) -> TestCoin:
    return TestCoin.deploy({'from': instanceOperator})

@pytest.fixture(scope="module")
def erc20TokenAlternative(instanceOperator) -> TestCoin:
    return TestCoinAlternativeImplementation.deploy({'from': instanceOperator})

@pytest.fixture(scope="module")
def testCoinX(owner) -> TestCoinX:
    return TestCoinX.deploy({'from': owner})

@pytest.fixture(scope="module")
def bundleToken(owner) -> BundleToken:
    return BundleToken.deploy({'from': owner})

@pytest.fixture(scope="module")
def testCoinSetup(testCoin, owner, customer) -> TestCoin:
    testCoin.transfer(customer, 10**6, {'from': owner})
    return testCoin

def contractFromAddress(contractClass, contractAddress):
    return Contract.from_abi(contractClass._name, contractAddress, contractClass.abi)

def encode_function_data(*args, initializer=None):
    if not len(args): args = b''

    if initializer:
        return initializer.encode_input(*args)

    return b''
