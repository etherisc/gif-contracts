import json
from web3 import Web3

from brownie import (
    web3,
    network, 
    Contract, 
    CoreProxy,
)

from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

CHAIN_ID_MUMBAI = 80001
CHAIN_ID_FUJI = 43113
CHAIN_ID_GOERLI = 5

CHAIN_ID_AVAX = 43114
CHAIN_ID_MAINNET = 1

CHAIN_IDS_REQUIRING_CONFIRMATIONS = [CHAIN_ID_MUMBAI, CHAIN_ID_FUJI, CHAIN_ID_GOERLI, CHAIN_ID_AVAX, CHAIN_ID_MAINNET]


def s2h(text: str) -> str:
    return Web3.toHex(text.encode('ascii'))

def h2s(hex: str) -> str:
    return Web3.toText(hex).split('\x00')[-1]

def h2sLeft(hex: str) -> str:
    return Web3.toText(hex).split('\x00')[0]

def s2b32(text: str):
    return '{:0<66}'.format(Web3.toHex(text.encode('ascii')))[:66]

def b322s(b32: bytes):
    return b32.decode().split('\x00')[0]

def s2b(text:str):
    return s2b32(text)

def b2s(b32: bytes):
    return b322s(b32)

def keccak256(text:str):
    return Web3.solidityKeccak(['string'], [text]).hex()

def get_account(mnemonic: str, account_offset: int) -> Account:
    return accounts.from_mnemonic(
        mnemonic,
        count=1,
        offset=account_offset)


def wait_for_confirmations(tx):
    if web3.chain_id in CHAIN_IDS_REQUIRING_CONFIRMATIONS:
        if not is_forked_network():
            print('waiting for confirmations ...')
            tx.wait(2)
        else:
            print('not waiting for confirmations in a forked network...')


def is_forked_network():
    return 'fork' in network.show_active()


# source: https://github.com/brownie-mix/upgrades-mix/blob/main/scripts/helpful_scripts.py 
def encode_function_data(*args, initializer=None):
    """Encodes the function call so we can work with an initializer.
    Args:
        initializer ([brownie.network.contract.ContractTx], optional):
        The initializer function we want to call. Example: `box.store`.
        Defaults to None.
        args (Any, optional):
        The arguments to pass to the initializer function
    Returns:
        [bytes]: Return the encoded bytes.
    """
    if not len(args): args = b''

    if initializer: return initializer.encode_input(*args)

    return b''

# generic upgradable gif module deployment
def deployGifModule(
    controllerClass, 
    storageClass, 
    registry, 
    owner,
    publishSource
):
    controller = controllerClass.deploy(
        registry.address, 
        {'from': owner},
        publish_source=publishSource)
    
    storage = storageClass.deploy(
        registry.address, 
        {'from': owner},
        publish_source=publishSource)

    controller.assignStorage(storage.address, {'from': owner})
    storage.assignController(controller.address, {'from': owner})

    registry.register(controller.NAME.call(), controller.address, {'from': owner})
    registry.register(storage.NAME.call(), storage.address, {'from': owner})

    return contractFromAddress(controllerClass, storage.address)

# gif token deployment
def deployGifToken(
    tokenName,
    tokenClass,
    registry,
    owner,
    publishSource
):
    print('token {} deploy'.format(tokenName))
    token = tokenClass.deploy(
        {'from': owner},
        publish_source=publishSource)

    tokenNameB32 = s2b32(tokenName)
    print('token {} register'.format(tokenName))
    registry.register(tokenNameB32, token.address, {'from': owner})

    return token


# generic open zeppelin upgradable gif module deployment
def deployGifModuleV2(
    moduleName,
    controllerClass, 
    registry, 
    owner,
    publishSource
):
    print('module {} deploy controller'.format(moduleName))
    controller = controllerClass.deploy(
        {'from': owner},
        publish_source=publishSource)

    encoded_initializer = encode_function_data(
        registry.address,
        initializer=controller.initialize)

    print('module {} deploy proxy'.format(moduleName))
    proxy = CoreProxy.deploy(
        controller.address, 
        encoded_initializer, 
        {'from': owner},
        publish_source=publishSource)

    moduleNameB32 = s2b32(moduleName)
    controllerNameB32 = s2b32('{}Controller'.format(moduleName))[:32]

    print('module {} ({}) register controller'.format(moduleName, controllerNameB32))
    registry.register(controllerNameB32, controller.address, {'from': owner})
    print('module {} ({}) register proxy'.format(moduleName, moduleNameB32))
    registry.register(moduleNameB32, proxy.address, {'from': owner})

    return contractFromAddress(controllerClass, proxy.address)


# generic upgradable gif service deployment
def deployGifService(
    serviceClass, 
    registry, 
    owner,
    publishSource
):
    service = serviceClass.deploy(
        registry.address, 
        {'from': owner},
        publish_source=publishSource)

    registry.register(service.NAME.call(), service.address, {'from': owner})

    return service

def deployGifServiceV2(
    serviceName,
    serviceClass, 
    registry, 
    owner,
    publishSource
):
    service = serviceClass.deploy(
        registry.address, 
        {'from': owner},
        publish_source=publishSource)

    registry.register(s2b32(serviceName), service.address, {'from': owner})

    return service

def contractFromAddress(contractClass, contractAddress):
    return contract_from_address(contractClass, contractAddress)

def contract_from_address(contractClass, contractAddress):
    return Contract.from_abi(contractClass._name, contractAddress, contractClass.abi)

def save_json(contract_class, file_name=None):
    vi = contract_class.get_verification_info()
    sji = vi['standard_json_input']

    if not file_name or len(file_name) == 0:
        file_name = './{}.json'.format(contract_class._name)

    print('writing standard json input file {}'.format(file_name))
    with open(file_name, "w") as json_file:
        json.dump(sji, json_file)
