import pytest
import web3

from typing import Dict

from brownie import (
    Wei,
    Contract, 
    CoreProxy,
    DummyCoin,
    AccessController,
    RegistryController,
    LicenseController,
    PolicyController,
    QueryController,
    UnderwritingController,
    ClaimsController,
    ProductService,
    OracleService,
    ComponentOwnerService,
    PolicyFlowDefault,
    InstanceOperatorService,
    InstanceService,
    TestRiskpool,
    TestOracle,
    TestProduct,
    TestRegistryControllerUpdated
)

from brownie.network import accounts
from brownie.network.account import Account

from scripts.const import (
    GIF_RELEASE,
    ACCOUNTS_MNEMONIC, 
    INSTANCE_OPERATOR_ACCOUNT_NO,
    RISKPOOL_KEEPER_ACCOUNT_NO,
    ORACLE_PROVIDER_ACCOUNT_NO,
    PRODUCT_OWNER_ACCOUNT_NO,
    CUSTOMER_ACCOUNT_NO,
    CAPITAL_ACCOUNT_NO,
    FEE_ACCOUNT_NO,
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

@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass

# -- comments below may be used /w 'brownie console'
# mnemonic = 'candy maple cake sugar pudding cream honey rich smooth crumble sweet treat'
# owner = accounts.from_mnemonic(mnemonic, count=1, offset=0)
@pytest.fixture(scope="module")
def owner(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, INSTANCE_OPERATOR_ACCOUNT_NO)
    accounts[0].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def riskpoolKeeper(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, RISKPOOL_KEEPER_ACCOUNT_NO)
    accounts[1].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def oracleProvider(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, ORACLE_PROVIDER_ACCOUNT_NO)
    accounts[2].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def productOwner(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, PRODUCT_OWNER_ACCOUNT_NO)
    accounts[3].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def customer(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, CUSTOMER_ACCOUNT_NO)
    accounts[4].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def capitalOwner(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, CAPITAL_ACCOUNT_NO)
    accounts[5].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def feeOwner(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, FEE_ACCOUNT_NO)
    accounts[6].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def instance(owner) -> GifInstance:
    return GifInstance(owner)


@pytest.fixture(scope="module")
def gifTestOracle(instance: GifInstance, oracleProvider: Account) -> GifTestOracle:
    oracle = GifTestOracle(instance, oracleProvider)
    return oracle


@pytest.fixture(scope="module")
def gifTestRiskpool(instance: GifInstance, riskpoolKeeper: Account, capitalOwner: Account) -> GifTestRiskpool:
    capitalization = 10000
    riskpool = GifTestRiskpool(instance, riskpoolKeeper, capitalOwner, capitalization)
    return riskpool


@pytest.fixture(scope="module")
def gifTestProduct(
    instance: GifInstance, 
    dummyCoinSetup: Account, 
    capitalOwner: Account, 
    feeOwner: Account, 
    productOwner: Account,
    gifTestOracle: GifTestOracle,
    gifTestRiskpool: GifTestRiskpool
) -> GifTestProduct:
    product = GifTestProduct(
        instance, 
        dummyCoinSetup, 
        capitalOwner,
        feeOwner,
        productOwner,
        gifTestOracle,
        gifTestRiskpool)
    return product


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
def access(AccessController, registry, owner) -> AccessController:
    return deployGifModuleV2("Access", AccessController, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def policy(PolicyController, registry, owner) -> PolicyController:
    return deployGifModuleV2("Policy", PolicyController, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def license(LicenseController, registry, owner) -> LicenseController:
    return deployGifModuleV2("License", LicenseController, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def underwriting(UnderwritingController, registry, owner) -> UnderwritingController:
    return deployGifModuleV2("Underwriting", UnderwritingController, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def query(QueryController, registry, owner) -> QueryController:
    return deployGifModuleV2("Query", QueryController, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def productService(ProductService, registry, owner) -> ProductService:
    return deployGifService(ProductService, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def oracleService(OracleService, registry, owner) -> OracleService:
    return deployGifModuleV2("OracleService", OracleService, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def componentOwnerService(ComponentOwnerService, registry, owner) -> ComponentOwnerService:
    return deployGifModuleV2("ComponentOwnerService", ComponentOwnerService, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def policyFlowDefault(PolicyFlowDefault, registry, owner) -> PolicyFlowDefault:
    return deployGifService(PolicyFlowDefault, registry, owner, PUBLISH_SOURCE)
    # return deployGifModuleV2("PolicyFlowDefault", PolicyFlowDefault, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def instanceOperatorService(InstanceOperatorService, registry, owner) -> InstanceOperatorService:
    return deployGifModuleV2("InstanceOperatorService", InstanceOperatorService, registry, owner, PUBLISH_SOURCE)

@pytest.fixture(scope="module")
def instanceService(instance) -> InstanceService:
    return instance.getInstanceService()

@pytest.fixture(scope="module")
def dummyCoin(owner) -> DummyCoin:
    return DummyCoin.deploy({'from': owner})

@pytest.fixture(scope="module")
def dummyCoinSetup(dummyCoin, owner, customer) -> DummyCoin:
    dummyCoin.transfer(customer, 10**6, {'from': owner})
    return dummyCoin

def contractFromAddress(contractClass, contractAddress):
    return Contract.from_abi(contractClass._name, contractAddress, contractClass.abi)

def encode_function_data(*args, initializer=None):
    if not len(args): args = b''

    if initializer:
        return initializer.encode_input(*args)

    return b''