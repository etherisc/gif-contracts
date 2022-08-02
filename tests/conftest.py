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
    TestRiskpool,
    TestOracle,
    TestProduct,
    TestRiskpool,
    TestRegistryControllerUpdated,
    TestRegistryCompromisedController,
    ClOperator,
    AyiiProduct,
    AyiiOracle,
)

from brownie.network import accounts
from brownie.network.account import Account

from scripts.const import (
    GIF_RELEASE,
    ACCOUNTS_MNEMONIC, 
    RISKPOOL_NAME,
    RIKSPOOL_ID,
    ORACLE_NAME,
    ORACLE_INPUT_FORMAT,
    ORACLE_OUTPUT_FORMAT,
    ORACLE_ID,
    PRODUCT_NAME,
    PRODUCT_ID,
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

@pytest.fixture(scope="module")
def owner(accounts) -> Account:
    return get_filled_account(accounts, 0, "1 ether")

@pytest.fixture(scope="module")
def riskpoolKeeper(accounts) -> Account:
    return get_filled_account(accounts, 1, "1 ether")

@pytest.fixture(scope="module")
def oracleProvider(accounts) -> Account:
    return get_filled_account(accounts, 2, "1 ether")

@pytest.fixture(scope="module")
def productOwner(accounts) -> Account:
    return get_filled_account(accounts, 3, "1 ether")

@pytest.fixture(scope="module")
def customer(accounts) -> Account:
    return get_filled_account(accounts, 4, "1 ether")

@pytest.fixture(scope="module")
def customer2(accounts) -> Account:
    return get_filled_account(accounts, 5, "1 ether")

@pytest.fixture(scope="module")
def capitalOwner(accounts) -> Account:
    return get_filled_account(accounts, 6, "1 ether")

@pytest.fixture(scope="module")
def feeOwner(accounts) -> Account:
    return get_filled_account(accounts, 7, "1 ether")

@pytest.fixture(scope="module")
def instance(owner, feeOwner) -> GifInstance:
    return GifInstance(owner, feeOwner)


@pytest.fixture(scope="module")
def gifTestOracle(instance: GifInstance, oracleProvider: Account) -> GifTestOracle:
    return GifTestOracle(instance, oracleProvider)


@pytest.fixture(scope="module")
def gifTestRiskpool(instance: GifInstance, riskpoolKeeper: Account, capitalOwner: Account, owner: Account) -> GifTestRiskpool:
    capitalization = 10**18
    return GifTestRiskpool(instance, riskpoolKeeper, capitalOwner, capitalization)


@pytest.fixture(scope="module")
def gifTestProduct(
    instance: GifInstance, 
    testCoin,
    capitalOwner: Account, 
    feeOwner: Account, 
    productOwner: Account,
    gifTestOracle: GifTestOracle,
    gifTestRiskpool: GifTestRiskpool,
    owner
) -> GifTestProduct:
    return GifTestProduct(
        instance, 
        testCoin,
        capitalOwner,
        feeOwner,
        productOwner,
        gifTestOracle,
        gifTestRiskpool)


@pytest.fixture(scope="module")
def gifAyiiOracle(
    instance: GifInstance, 
    oracleProvider: Account, 
    testCoin
) -> GifAyiiOracle:
    return GifAyiiOracle(
        instance, 
        oracleProvider, 
        testCoin)


@pytest.fixture(scope="module")
def gifAyiiProduct(
    instance: GifInstance, 
    testCoin,
    capitalOwner: Account, 
    feeOwner: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    customer: Account,
    gifAyiiOracle: GifAyiiOracle,
    gifTestRiskpool: GifTestRiskpool,
    owner
) -> GifAyiiProduct:
    return GifAyiiProduct(
        instance, 
        testCoin,
        capitalOwner,
        feeOwner,
        productOwner,
        riskpoolKeeper,
        customer,
        gifAyiiOracle,
        gifTestRiskpool)


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
def testCoin(owner) -> TestCoin:
    return TestCoin.deploy({'from': owner})

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