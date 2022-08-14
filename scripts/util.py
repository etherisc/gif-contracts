from web3 import Web3

from brownie import (
    Contract, 
    CoreProxy,
)

from brownie.convert import to_bytes
from brownie.network import accounts
from brownie.network.account import Account

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

def get_account(mnemonic: str, account_offset: int) -> Account:
    return accounts.from_mnemonic(
        mnemonic,
        count=1,
        offset=account_offset)

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
    publishSource,
    gasLimit
):
    deployDict = {'from': owner, 'gas_limit': gasLimit} if gasLimit else {'from': owner}

    controller = controllerClass.deploy(
        registry.address, 
        deployDict,
        publish_source=publishSource)
    
    storage = storageClass.deploy(
        registry.address, 
        deployDict,
        publish_source=publishSource)

    controller.assignStorage(storage.address, deployDict)
    storage.assignController(controller.address, deployDict)

    registry.register(controller.NAME.call(), controller.address, deployDict)
    registry.register(storage.NAME.call(), storage.address, deployDict)

    return contractFromAddress(controllerClass, storage.address)



# gif token deployment
def deployGifToken(
    tokenName,
    tokenClass,
    registry,
    owner,
    publishSource,
    gasLimit
):
    deployDict = {'from': owner, 'gas_limit': gasLimit} if gasLimit else {'from': owner}

    print('token {} deploy'.format(tokenName))
    token = tokenClass.deploy(deployDict, publish_source=publishSource)

    print('token {} register'.format(tokenName))
    registry.register(s2b32(tokenName), token.address, deployDict)

    return token


# generic open zeppelin upgradable gif module deployment
def deployGifModuleV2(
    moduleName,
    controllerClass, 
    registry, 
    owner,
    publishSource,
    gasLimit
):
    deployDict = {'from': owner, 'gas_limit': gasLimit} if gasLimit else {'from': owner}

    print('module {} deploy controller'.format(moduleName))
    controller = controllerClass.deploy(
        deployDict,
        publish_source=publishSource)

    encoded_initializer = encode_function_data(
        registry.address,
        initializer=controller.initialize)

    print('module {} deploy proxy'.format(moduleName))
    proxy = CoreProxy.deploy(
        controller.address, 
        encoded_initializer, 
        deployDict,
        publish_source=publishSource)

    moduleNameB32 = s2b32(moduleName)
    controllerNameB32 = s2b32('{}Controller'.format(moduleName))

    registry.register(controllerNameB32, controller.address, deployDict)
    registry.register(moduleNameB32, proxy.address, deployDict)

    return contractFromAddress(controllerClass, proxy.address)


# generic upgradable gif service deployment
def deployGifService(
    serviceClass, 
    registry, 
    owner,
    publishSource,
    gasLimit
):
    deployDict = {'from': owner, 'gas_limit': gasLimit} if gasLimit else {'from': owner}

    service = serviceClass.deploy(
        registry.address, 
        deployDict,
        publish_source=publishSource)

    registry.register(
        service.NAME.call(), 
        service.address, 
        deployDict)

    return service

def deployGifServiceV2(
    serviceName,
    serviceClass, 
    registry, 
    owner,
    publishSource,
    gasLimit
):
    deployDict = {'from': owner, 'gas_limit': gasLimit} if gasLimit else {'from': owner}

    service = serviceClass.deploy(
        registry.address, 
        deployDict,
        publish_source=publishSource)

    registry.register(
        s2b32(serviceName), 
        service.address, 
        deployDict)

    return service


def contractFromAddress(contractClass, contractAddress):
    return Contract.from_abi(contractClass._name, contractAddress, contractClass.abi)
