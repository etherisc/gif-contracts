import brownie
import pytest

from scripts.const import ZERO_ADDRESS

def test_setup(bundleToken, owner):
    assert bundleToken.symbol() == "BTK"
    assert bundleToken.totalSupply() == 0

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_setup_with_instance(instance, owner):
    bundleToken = instance.bundleToken
    bundleModule = instance.bundle

    # check after intance deployment bundle module is already set
    with brownie.reverts('ERROR:BTK-003:BUNDLE_MODULE_ALREADY_DEFINED'):
        bundleToken.setBundleModule(owner)

    # check that initial wiring corresponds to expectation
    assert bundleToken.getBundleModuleAddress() == bundleModule.address


# check initialization process then happy path with mint/burn
def test_initialize(bundleToken, owner, riskpoolKeeper, customer):

    # check uninitialized case
    bundleId = 3
    with brownie.reverts('ERROR:BTK-001:NOT_INITIALIZED'):
        bundleToken.mint(
            bundleId, 
            customer, 
            {'from': owner})

    # check setting of minter
    with brownie.reverts('ERROR:BTK-004:INVALID_BUNDLE_MODULE_ADDRESS'):
        bundleToken.setBundleModule(ZERO_ADDRESS)

    # use riskpool keeper as surrogate bundle module
    bundleToken.setBundleModule(riskpoolKeeper)

    # check that minter can only be set once
    with brownie.reverts('ERROR:BTK-003:BUNDLE_MODULE_ALREADY_DEFINED'):
        bundleToken.setBundleModule(customer)

    # check that minting/burning now works
    bundleId = 3
    tokenId = 1
    assert bundleToken.totalSupply() == 0
    assert bundleToken.exists(tokenId) == False
    assert bundleToken.burned(tokenId) == False
    
    # check minting works for 'bundle module'
    tx = bundleToken.mint(
        bundleId, 
        customer, 
        {'from': riskpoolKeeper})

    tokenId = tx.return_value

    assert bundleToken.totalSupply() == 1
    assert tokenId == 1
    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False

    # check that burning does work for non-minter (eg customer)
    bundleToken.burn(
        tokenId, 
        {'from': riskpoolKeeper})

    assert bundleToken.totalSupply() == 1
    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == True


def test_mint(bundleToken, owner, riskpoolKeeper, customer):

    # use riskpool keeper as surrogate bundle module
    bundleToken.setBundleModule(riskpoolKeeper)

    assert bundleToken.totalSupply() == 0
    assert bundleToken.balanceOf(customer) == 0

    bundleId = 3
    tx = bundleToken.mint(
        bundleId, 
        customer, 
        {'from': riskpoolKeeper})

    assert bundleToken.totalSupply() == 1
    assert bundleToken.balanceOf(customer) == 1

    tokenId = tx.return_value

    assert tokenId == 1
    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False
    assert bundleToken.ownerOf(tokenId) == customer
    assert bundleToken.getBundleId(tokenId) == bundleId


def test_burn(bundleToken, owner, riskpoolKeeper, customer):

    # use riskpool keeper as surrogate bundle module
    bundleToken.setBundleModule(riskpoolKeeper)
    bundleId = 3
    tx = bundleToken.mint(
        bundleId, 
        customer, 
        {'from': riskpoolKeeper})

    tokenId = tx.return_value

    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False

    nonExistingId = 13
    with brownie.reverts('ERROR:BTK-005:TOKEN_ID_INVALID'):
        bundleToken.burn(
            nonExistingId,
            {'from': riskpoolKeeper})

    bundleToken.burn(
        tokenId,
        {'from': riskpoolKeeper})

    assert bundleToken.totalSupply() == 1
    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == True


def test_mint_only_bundle_module(bundleToken, owner, riskpoolKeeper, customer):

    # use riskpool keeper as surrogate bundle module
    bundleToken.setBundleModule(riskpoolKeeper)

    # customer must not be able to mint herself a nft
    bundleId = 3
    with brownie.reverts('ERROR:BTK-002:NOT_BUNDLE_MODULE'):
        bundleToken.mint(
            bundleId, 
            customer, 
            {'from': customer})

    assert bundleToken.totalSupply() == 0

    # owner must be able to mint customer a nft
    tx = bundleToken.mint(
        bundleId, 
        customer, 
        {'from': riskpoolKeeper})

    assert bundleToken.totalSupply() == 1


def test_burn_only_bundle_module(bundleToken, owner, riskpoolKeeper, customer):

    # use riskpool keeper as surrogate bundle module
    bundleToken.setBundleModule(riskpoolKeeper)

    # customer must not be able to mint herself a nft
    bundleId = 3

    tx = bundleToken.mint(
        bundleId, 
        customer, 
        {'from': riskpoolKeeper})

    tokenId = tx.return_value

    # check that burning does not work for non-minter (eg customer)
    with brownie.reverts('ERROR:BTK-002:NOT_BUNDLE_MODULE'):
        bundleToken.burn(
            tokenId, 
            {'from': customer})

    assert bundleToken.totalSupply() == 1
    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == False

    # check that burning does work for non-minter (eg customer)
    bundleToken.burn(
        tokenId, 
        {'from': riskpoolKeeper})

    assert bundleToken.totalSupply() == 1
    assert bundleToken.exists(tokenId) == True
    assert bundleToken.burned(tokenId) == True
