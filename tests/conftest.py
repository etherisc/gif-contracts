import pytest
import web3

from typing import Dict

from brownie import (
    Wei,
    Contract, 
    Registry,
    RegistryController,
    License,
    LicenseController,
    Policy,
    PolicyController,
    Query,
    QueryController,
    ProductService,
    OracleService,
    OracleOwnerService,
    PolicyFlowDefault,
    InstanceOperatorService,
    TestOracle,
    TestProduct
)

from brownie.network import accounts
from brownie.network.account import Account

from scripts.const import (
    GIF_RELEASE,
    ACCOUNTS_MNEMONIC, 
    INSTANCE_OPERATOR_ACCOUNT_NO,
    ORACLE_OWNER_ACCOUNT_NO,
    PRODUCT_OWNER_ACCOUNT_NO,
    CUSTOMER_ACCOUNT_NO,
    ORACLE_TYPE_NAME,
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
    GifTestOracle,
    GifTestProduct,
)

from scripts.util import (
    get_account,
    encode_function_data,
    s2h,
    deployGifModule,
    deployGifService,
)

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
def oracleOwner(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, ORACLE_OWNER_ACCOUNT_NO)
    accounts[1].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def productOwner(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, PRODUCT_OWNER_ACCOUNT_NO)
    accounts[2].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def customer(accounts) -> Account:
    owner = get_account(ACCOUNTS_MNEMONIC, CUSTOMER_ACCOUNT_NO)
    accounts[3].transfer(owner, "100 ether")
    return owner

@pytest.fixture(scope="module")
def instance(owner) -> GifInstance:
    return GifInstance(owner)

@pytest.fixture(scope="module")
def testProduct(instance: GifInstance, oracleOwner: Account, productOwner: Account) -> TestProduct:
    oracle = GifTestOracle(instance, oracleOwner)
    product = GifTestProduct(instance, oracle, productOwner)

    return product.getProductContract()

# rel = '1.2.0'
# relHex = Web3.toHex(rel.encode('ascii'))
# controller = RegistryController.deploy(relHex, {'from': owner})
@pytest.fixture(scope="module")
def registryController(RegistryController, owner) -> RegistryController:
    return RegistryController.deploy(s2h(GIF_RELEASE), {'from': owner})

# storage = Registry.deploy(controller.address, relHex, {'from': owner})
@pytest.fixture(scope="module")
def registryStorage(Registry, registryController, owner) -> Registry:
    return Registry.deploy(registryController.address, s2h(GIF_RELEASE), {'from': owner})

# controller.assignStorage(storage.address, {'from': owner})
# registry = Contract.from_abi(RegistryController._name, storage.address, RegistryController.abi)
# registry.register(storage.NAME.call(), storage.address, {'from': owner})
# registry.register(controller.NAME.call(), controller.address, {'from': owner})
@pytest.fixture(scope="module")
def registry(RegistryController, registryController, registryStorage, owner) -> Registry:
    registryController.assignStorage(registryStorage.address, {'from': owner})
    # TODO check: registryStorage.assignController missing ?
    registry = Contract.from_abi(RegistryController._name, registryStorage.address, RegistryController.abi)

    registry.register(registryStorage.NAME.call(), registryStorage.address, {'from': owner})
    registry.register(registryController.NAME.call(), registryController.address, {'from': owner})

    return registry

@pytest.fixture(scope="module")
def license(LicenseController, License, registry, owner) -> License:
    return deployGifModule(LicenseController, License, registry, owner)

@pytest.fixture(scope="module")
def policy(PolicyController, Policy, registry, owner) -> Policy:
    return deployGifModule(PolicyController, Policy, registry, owner)

@pytest.fixture(scope="module")
def query(QueryController, Query, registry, owner) -> Query:
    return deployGifModule(QueryController, Query, registry, owner)

@pytest.fixture(scope="module")
def productService(ProductService, registry, owner) -> ProductService:
    return deployGifService(ProductService, registry, owner)

@pytest.fixture(scope="module")
def oracleService(OracleService, registry, owner) -> OracleService:
    return deployGifService(OracleService, registry, owner)

@pytest.fixture(scope="module")
def oracleOwnerService(OracleOwnerService, registry, owner) -> OracleOwnerService:
    return deployGifService(OracleOwnerService, registry, owner)

@pytest.fixture(scope="module")
def policyFlowDefault(PolicyFlowDefault, registry, owner) -> PolicyFlowDefault:
    return deployGifService(PolicyFlowDefault, registry, owner)

@pytest.fixture(scope="module")
def instanceOperatorService(InstanceOperatorService, registry, owner) -> InstanceOperatorService:
    return deployGifService(InstanceOperatorService, registry, owner)
