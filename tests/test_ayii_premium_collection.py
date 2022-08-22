import brownie
import pytest

from brownie.network import accounts
from brownie.network.account import Account

from brownie import (
    interface,
    AyiiProduct,
    BundleToken
)

from scripts.ayii_product import (
    GifAyiiProduct
)

from scripts.setup import (
    fund_riskpool,
    fund_customer,
)

from scripts.instance import GifInstance
from scripts.util import s2b32, contractFromAddress

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_late_premium_payment(
    instance: GifInstance, 
    instanceOperator, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet,
    investor,
    productOwner,
    insurer,
    riskpoolKeeper,
    customer
):
    instanceService = instance.getInstanceService()

    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    riskpool = gifAyiiProduct.getRiskpool().getContract()
    erc20Token = gifAyiiProduct.getToken()
    
    riskpoolFunding = 200000
    fund_riskpool(instance, instanceOperator, riskpoolWallet, riskpool, investor, erc20Token, riskpoolFunding)

    # check riskpool funds and book keeping after funding
    riskpoolExpectedBalance = 0.95 * riskpoolFunding - 42
    assert riskpool.getBalance() == riskpoolExpectedBalance
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # create risk
    riskId = create_risk(product, insurer)

    # create policy
    premium = 300
    sumInsured = 2000
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    processId = tx.return_value

    # check riskpool funds remain unchanged as no premium has been collected
    assert riskpool.getBalance() == riskpoolExpectedBalance
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    metadata = instanceService.getMetadata(processId).dict()
    application = instanceService.getApplication(processId).dict()
    policy = instanceService.getPolicy(processId).dict()

    print('metadata {}'.format(metadata))
    print('application {}'.format(application))
    print('policy {}'.format(policy))

    # check underwritten application and policy for customer
    assert metadata['owner'] == customer
    assert metadata['productId'] == product.getId()
    # enum ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 2
    # enum PolicyState {Active, Expired, Closed}
    assert policy['state'] == 0

    # check premium expected and paid (nothing so far)
    policy = instanceService.getPolicy(processId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == 0

    # fund customer to pay premium now
    fund_customer(instance, instanceOperator, customer, erc20Token, premium)
    assert erc20Token.balanceOf(customer) == premium
    assert erc20Token.allowance(customer, instance.getTreasury()) == premium

    tx = product.collectPremium(processId, customer, premium, {'from': insurer})
    (success, fee, netPremium) = tx.return_value
    print('success: {}, fee: {}, netPremium: {}'.format(success, fee, netPremium))

    assert riskpool.getBalance() == riskpoolExpectedBalance + netPremium
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # check premium expected and paid (full amount)
    policy = instanceService.getPolicy(processId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premium


def test_partial_premium_payment_attempt(
    instance: GifInstance, 
    instanceOperator, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet,
    investor,
    productOwner,
    insurer,
    riskpoolKeeper,
    customer
):
    instanceService = instance.getInstanceService()

    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    riskpool = gifAyiiProduct.getRiskpool().getContract()
    erc20Token = gifAyiiProduct.getToken()
    
    riskpoolFunding = 200000
    fund_riskpool(instance, instanceOperator, riskpoolWallet, riskpool, investor, erc20Token, riskpoolFunding)

    # check riskpool funds and book keeping after funding
    riskpoolExpectedBalance = 0.95 * riskpoolFunding - 42
    assert riskpool.getBalance() == riskpoolExpectedBalance
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # create risk
    riskId = create_risk(product, insurer)

    # create policy
    premium = 300
    sumInsured = 2000
    fund_customer(instance, instanceOperator, customer, erc20Token, premium / 2)
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    processId = tx.return_value

    # applyForPolicy attempts to transfer the full premium amount
    # if not possible no premium is collected even if some funds would be available
    # check riskpool funds remain unchanged as no premium has been collected
    assert riskpool.getBalance() == riskpoolExpectedBalance
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # check premium expected and paid (nothing so far)
    policy = instanceService.getPolicy(processId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == 0


def test_premium_payment_by_subsidies(
    instance: GifInstance, 
    instanceOperator, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet,
    investor,
    productOwner,
    insurer,
    riskpoolKeeper,
    customer
):
    instanceService = instance.getInstanceService()

    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    riskpool = gifAyiiProduct.getRiskpool().getContract()
    erc20Token = gifAyiiProduct.getToken()
    
    riskpoolFunding = 200000
    fund_riskpool(instance, instanceOperator, riskpoolWallet, riskpool, investor, erc20Token, riskpoolFunding)

    # check riskpool funds and book keeping after funding
    riskpoolExpectedBalance = 0.95 * riskpoolFunding - 42
    assert riskpool.getBalance() == riskpoolExpectedBalance
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # create risk
    riskId = create_risk(product, insurer)

    # create policy
    premium = 300
    sumInsured = 2000
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    processId = tx.return_value

    # 20% premium payment by policy holder
    premiumPolicyHolder = premium / 5
    premiumSubsidies = premium - premiumPolicyHolder

    fund_customer(instance, instanceOperator, customer, erc20Token, premiumPolicyHolder)
    assert erc20Token.balanceOf(customer) == premiumPolicyHolder

    tx = product.collectPremium(processId, customer, premiumPolicyHolder, {'from': insurer})
    (success, fee, netPremium) = tx.return_value

    assert success
    assert fee + netPremium == premiumPolicyHolder
    assert erc20Token.balanceOf(customer) == 0

    policy = instanceService.getPolicy(processId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premiumPolicyHolder

    # 80% premium subidies payment
    donor = accounts.add()
    accounts[9].transfer(donor, 100000000)
    erc20Token.transfer(donor, premiumSubsidies, {'from': instanceOperator})
    erc20Token.approve(product, premiumSubsidies, {'from': donor})

    assert erc20Token.balanceOf(donor) == premiumSubsidies
    riskpoolBeforeDonation = erc20Token.balanceOf(riskpoolWallet)

    # collect premium from 1st ransfers amount from donor to customer then performs
    # standard premium collection. therefore, customer needs to have sufficient allowance
    erc20Token.approve(instance.getTreasury(), premiumSubsidies, {'from': customer})
    tx = product.collectPremium(processId, donor, premiumSubsidies, {'from': insurer})
    (success, fee, netPremium) = tx.return_value

    assert success
    assert fee + netPremium == premiumSubsidies
    assert erc20Token.balanceOf(donor) == 0
    assert erc20Token.balanceOf(riskpoolWallet) == riskpoolBeforeDonation + netPremium

    policy = instanceService.getPolicy(processId).dict()
    assert policy['premiumExpectedAmount'] == premium
    assert policy['premiumPaidAmount'] == premium


def create_risk(
    product,
    insurer
):
    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = s2b32('1234')
    cropId = s2b32('mixed')
    
    triggerFloat = 0.75
    exitFloat = 0.1
    tsiFloat = 0.9
    aphFloat = 2.0
    
    multiplier = product.getPercentageMultiplier()
    trigger = multiplier * triggerFloat
    exit = multiplier * exitFloat
    tsi = multiplier * tsiFloat
    aph = multiplier * aphFloat

    tx = product.createRisk(projectId, uaiId, cropId, trigger, exit, tsi, aph, {'from': insurer})

    # return riskId
    return tx.return_value
