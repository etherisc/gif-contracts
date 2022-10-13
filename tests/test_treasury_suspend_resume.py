import brownie
import pytest

from brownie.network.account import Account

from scripts.instance import GifInstance
from scripts.util import b2s

from scripts.setup import (
    fund_riskpool,
    apply_for_policy,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_events(
    instance: GifInstance,
    instanceOperator: Account
):
    instanceOperatorService = instance.getInstanceOperatorService()
    ioDict = {'from': instanceOperator }

    tx1 = instanceOperatorService.suspendTreasury(ioDict)
    print('suspend {}'.format(tx1.events))

    assert 'Paused' in tx1.events
    assert 'LogTreasurySuspended' in tx1.events

    tx2 = instanceOperatorService.resumeTreasury(ioDict)
    print('resume {}'.format(tx2.events))

    assert 'Unpaused' in tx2.events
    assert 'LogTreasuryResumed' in tx2.events


def test_token_wallet_and_fee_functions(
    instance: GifInstance,
    instanceWallet,
    instanceOperator: Account,
    customer,
    erc20Token,
    testCoinX,
    riskpoolWallet,
    gifTestProduct,
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    treasury = instance.getTreasury()
    ioDict = {'from': instanceOperator }

    product = gifTestProduct.getContract()
    productId = product.getId()
    riskpoolId = gifTestProduct.getRiskpool().getId()

    hundredPercent = instanceService.getFeeFractionFullUnit()
    productFeeSpec = instanceOperatorService.createFeeSpecification(
        productId, 10, hundredPercent / 100, bytes(0))
    riskpoolFeeSpec = instanceOperatorService.createFeeSpecification(
        riskpoolId, 2, hundredPercent / 200, bytes(0))

    # try to suspend with non-instanceOperator
    with brownie.reverts('ERROR:IOS-001:NOT_INSTANCE_OPERATOR'):
        instanceOperatorService.suspendTreasury({'from': customer })

    # suspend with instanceOperator
    instanceOperatorService.suspendTreasury(ioDict)

    # check that all wallet and fee actions are suspened
    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        instanceOperatorService.setProductToken(productId, testCoinX, ioDict)

    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        instanceOperatorService.setInstanceWallet(riskpoolWallet, ioDict)

    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        instanceOperatorService.setRiskpoolWallet(riskpoolId, instanceWallet, ioDict)

    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        instanceOperatorService.setPremiumFees(productFeeSpec, ioDict)

    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        instanceOperatorService.setCapitalFees(riskpoolFeeSpec, ioDict)

    # try to resume with non-instanceOperator
    with brownie.reverts('ERROR:IOS-001:NOT_INSTANCE_OPERATOR'):
        instanceOperatorService.resumeTreasury({'from': customer })

    # resume with instanceOperator
    instanceOperatorService.resumeTreasury(ioDict)

    # check that all wallet and fee actions are suspended
    with brownie.reverts('ERROR:TRS-012:PRODUCT_TOKEN_ALREADY_SET'):
        instanceOperatorService.setProductToken(productId, testCoinX, ioDict)
    
    instanceOperatorService.setInstanceWallet(riskpoolWallet, ioDict)
    instanceOperatorService.setRiskpoolWallet(riskpoolId, instanceWallet, ioDict)
    instanceOperatorService.setPremiumFees(productFeeSpec, ioDict)
    instanceOperatorService.setCapitalFees(riskpoolFeeSpec, ioDict)


def test_process_premium(
    instance: GifInstance,
    instanceWallet,
    instanceOperator: Account,
    investor,
    customer,
    erc20Token,
    riskpoolWallet,
    gifTestProduct
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    product = gifTestProduct.getContract()
    ioDict = {'from': instanceOperator }

    # prepare funded riskpool
    riskpoolFunding = 10000
    riskpool = gifTestProduct.getRiskpool().getContract()
    fund_riskpool(instance, instanceOperator, riskpoolWallet, riskpool, investor, erc20Token, riskpoolFunding)

    # prepare funded customer
    customerFunding = 300
    fund_customer(instance, instanceOperator, customer, customerFunding, erc20Token)
    customerBalanceBeforePolicy = erc20Token.balanceOf(customer)
    instanceBalanceBeforePolicy = erc20Token.balanceOf(instanceWallet)
    riskpoolBalanceBeforePolicy = erc20Token.balanceOf(riskpoolWallet)
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # suspend treasury
    instanceOperatorService.suspendTreasury(ioDict)

    # build and use application to create policy
    premium = 150
    sumInsured = 2000

    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        tx = product.applyForPolicy(
            premium,
            sumInsured,
            bytes(0),
            bytes(0),
            {'from': customer})

    assert customerBalanceBeforePolicy == erc20Token.balanceOf(customer)
    assert instanceBalanceBeforePolicy == erc20Token.balanceOf(instanceWallet)
    assert riskpoolBalanceBeforePolicy == erc20Token.balanceOf(riskpoolWallet)
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # suspend treasury
    instanceOperatorService.resumeTreasury(ioDict)

    # build and use application to create policy
    product.applyForPolicy(
        premium,
        sumInsured,
        bytes(0),
        bytes(0),
        {'from': customer})

    assert erc20Token.balanceOf(customer) == customerBalanceBeforePolicy - premium
    deltaRiskpoolWallet = erc20Token.balanceOf(riskpoolWallet) - riskpoolBalanceBeforePolicy
    deltaInstanceWallet = erc20Token.balanceOf(instanceWallet) - instanceBalanceBeforePolicy
    assert deltaRiskpoolWallet + deltaInstanceWallet == premium
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)


def test_process_payout(
    instance: GifInstance,
    instanceWallet,
    instanceOperator: Account,
    productOwner,
    investor,
    customer,
    erc20Token,
    riskpoolWallet,
    gifTestProduct
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()
    ioDict = {'from': instanceOperator }

    # prepare setup
    riskpoolFunding = 10000
    customerFunding = 300
    premium = 150
    sumInsured = 2000
    claimAmount = 500

    fund_riskpool(instance, instanceOperator, riskpoolWallet, riskpool, investor, erc20Token, riskpoolFunding)
    fund_customer(instance, instanceOperator, customer, customerFunding, erc20Token)
    policyId = create_policy(product, customer, premium, sumInsured, erc20Token)
    claimId = create_claim(product, policyId, claimAmount, customer, productOwner)

    claim = instanceService.getClaim(policyId, claimId).dict()
    print(claim)

    customerBalanceBeforePayout = erc20Token.balanceOf(customer)
    riskpoolBalanceBeforePayout = erc20Token.balanceOf(riskpoolWallet)
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # suspend treasury
    instanceOperatorService.suspendTreasury(ioDict)

    # attempt to trigger payout
    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        product.createPayout(policyId, claimId, claimAmount, {'from': productOwner})

    # check that no funds have moved
    assert customerBalanceBeforePayout == erc20Token.balanceOf(customer)
    assert riskpoolBalanceBeforePayout == erc20Token.balanceOf(riskpoolWallet)
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # resume treasury
    instanceOperatorService.resumeTreasury(ioDict)

    # check that no funds have moved
    assert customerBalanceBeforePayout == erc20Token.balanceOf(customer)
    assert riskpoolBalanceBeforePayout == erc20Token.balanceOf(riskpoolWallet)
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)

    # trigger payout
    product.createPayout(policyId, claimId, claimAmount, {'from': productOwner})

    # check that no funds have moved as expected for the payout (claimAmount)
    assert erc20Token.balanceOf(customer) == customerBalanceBeforePayout + claimAmount
    assert erc20Token.balanceOf(riskpoolWallet) == riskpoolBalanceBeforePayout - claimAmount
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)
    

def test_process_capital(
    instance: GifInstance,
    instanceWallet,
    instanceOperator: Account,
    riskpoolWallet,
    investor,
    gifTestProduct,
    erc20Token,
    funding:int=10000
):
    instanceOperatorService = instance.getInstanceOperatorService()
    ioDict = {'from': instanceOperator }

    riskpool = gifTestProduct.getRiskpool().getContract()
    assert riskpool.getBalance() == 0
    assert erc20Token.balanceOf(riskpoolWallet) == 0
    assert erc20Token.balanceOf(instanceWallet) == 0

    # suspend treasury
    instanceOperatorService.suspendTreasury(ioDict)

    # try to move capital into riskpoolWallet
    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        fund_riskpool(
            instance, 
            instanceOperator, 
            riskpoolWallet, 
            riskpool, 
            investor, 
            erc20Token, 
            funding)
    
    assert riskpool.getBalance() == 0
    assert erc20Token.balanceOf(riskpoolWallet) == 0
    assert erc20Token.balanceOf(instanceWallet) == 0

    # resume treasury
    instanceOperatorService.resumeTreasury(ioDict)

    # try again
    fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        erc20Token, 
        funding)
    
    assert riskpool.getBalance() == 9458
    assert riskpool.getBalance() == erc20Token.balanceOf(riskpoolWallet)
    assert erc20Token.balanceOf(riskpoolWallet) + erc20Token.balanceOf(instanceWallet) == funding


def test_process_withdrawal(
    instance: GifInstance,
    instanceWallet,
    instanceOperator: Account,
    investor,
    riskpoolWallet,
    gifTestProduct,
    erc20Token,
    funding:int=10000
):
    instanceService = instance.getInstanceService()
    instanceOperatorService = instance.getInstanceOperatorService()
    ioDict = {'from': instanceOperator }
    inDict = {'from': investor }

    riskpool = gifTestProduct.getRiskpool().getContract()
    bundleId = fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        erc20Token, 
        funding)

    assert instanceService.bundles() == 1
    bundle = instanceService.getBundle(bundleId)
    print('bundleId {}, bundle {}'.format(bundleId, bundle))

    riskpoolBalanceBeforeDefunding = erc20Token.balanceOf(riskpoolWallet)
    investorBalanceBeforeDefunding = erc20Token.balanceOf(investor)

    assert riskpool.getBalance() == 9458
    assert erc20Token.balanceOf(riskpoolWallet) == 9458
    assert riskpoolBalanceBeforeDefunding == 9458

    # suspend treasury
    instanceOperatorService.suspendTreasury(ioDict)

    # attempt to defund bundle
    defundingAmount = funding/2
    with brownie.reverts('ERROR:TRS-004:TREASURY_SUSPENDED'):
        riskpool.defundBundle(bundleId, defundingAmount, inDict)

    # check that no funds are transferred
    assert erc20Token.balanceOf(riskpoolWallet) == riskpoolBalanceBeforeDefunding
    assert erc20Token.balanceOf(investor) == investorBalanceBeforeDefunding

    # resume treasury
    instanceOperatorService.resumeTreasury(ioDict)

    # try again to defund
    riskpool.defundBundle(bundleId, defundingAmount, inDict)

    # verify balances after defunding
    assert erc20Token.balanceOf(riskpoolWallet) + defundingAmount == riskpoolBalanceBeforeDefunding
    assert erc20Token.balanceOf(investor) - defundingAmount == investorBalanceBeforeDefunding


def fund_customer(
    instance,
    instanceOperator,
    customer,
    funding,
    erc20Token
):
    # transfer premium funds to customer and create allowance
    erc20Token.transfer(customer, funding, {'from': instanceOperator})
    erc20Token.approve(instance.getTreasury(), funding, {'from': customer})


def create_policy(
    product,
    customer,
    premium,
    sumInsured,
    erc20Token
):
    # create minimal policy application
    metaData = bytes(0)
    applicationData = bytes(0)

    tx = product.applyForPolicy(
        premium,
        sumInsured,
        metaData,
        applicationData,
        {'from': customer})
    
    # returns policy id
    return tx.return_value


def create_claim(
    product,
    policyId,
    claimAmount,
    customer,
    productOwner
):
    tx = product.submitClaimWithDeferredResponse(policyId, claimAmount, {'from': customer})
    (claimId, requestId) = tx.return_value

    product.confirmClaim(policyId, claimId, claimAmount, {'from': productOwner})

    return claimId
