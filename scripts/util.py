from web3 import Web3

from brownie import Contract
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
    return '{:0<66}'.format(Web3.toHex(text.encode('ascii')))

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
def deployGifModule(controllerClass, storageClass, registry, owner):
    controller = controllerClass.deploy(registry.address, {'from': owner})
    storage = storageClass.deploy(registry.address, {'from': owner})

    controller.assignStorage(storage.address, {'from': owner})
    storage.assignController(controller.address, {'from': owner})

    registry.register(controller.NAME.call(), controller.address, {'from': owner})
    registry.register(storage.NAME.call(), storage.address, {'from': owner})

    return Contract.from_abi(controllerClass._name, storage.address, controllerClass.abi)

# generic upgradable gif module deployment
def deployGifService(serviceClass, registry, owner):
    service = serviceClass.deploy(registry.address, {'from': owner})

    registry.register(service.NAME.call(), service.address, {'from': owner})

    return service
