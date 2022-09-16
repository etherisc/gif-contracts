from re import A
import brownie
import pytest

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


# underwrite the policy after the apply_for_policy has failed due to low riskpool balance
def test_underwrite_after_apply_with_riskpool_empty(
    instance: GifInstance, 
    instanceOperator, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet,
    riskpoolKeeper: Account,    
    investor,
    insurer,
    customer,
):
    instanceService = instance.getInstanceService()

    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    riskpool = gifAyiiProduct.getRiskpool().getContract()

    clOperator = gifAyiiProduct.getOracle().getClOperator()

    print('--- test setup underfunded riskpool --------------------------')

    token = gifAyiiProduct.getToken()
    assert token.balanceOf(riskpoolWallet) == 0


    riskpoolBalanceBeforeFunding = token.balanceOf(riskpoolWallet)
    assert 0 == riskpoolBalanceBeforeFunding
    
    riskId = prepare_risk(product, insurer)

    premium = 300
    sumInsured = 2000

        # ensure the riskpool is funded, but too low for insurance
    riskpoolFunding = 1000
    fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)
    riskpoolBalanceAfterFunding = token.balanceOf(riskpoolWallet)
    assert riskpoolBalanceAfterFunding > 0

    print('--- test setup customer --------------------------')

    customerFunding = 5000
    fund_customer(instance, instanceOperator, customer, token, customerFunding)

    print('--- apply for policy on underfunded riskpool --------------------------')
    # ensure application works for policy with underfunded riskpool
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    process_id = tx.return_value
    events = tx.events
    print(events)

    assert 'LogAyiiPolicyApplicationCreated' in events
    assert 'LogRiskpoolCollateralizationFailed' in events

    assert 'LogAyiiPolicyCreated' not in events
    
    # ensure application exists and has state Applied
    application = instanceService.getApplication(process_id)
    assert 0 == application[0] # ApplicationState.Applied

    assert 1 == product.applications()
    assert 0 == product.policies(riskId)

    assert process_id == product.getApplicationId(0)

    # ensure that explicity underwriting still fails
    tx = product.underwrite(process_id, {'from': insurer})
    assert False == tx.return_value
    
    events = tx.events
    print(events)
    assert 'LogRiskpoolCollateralizationFailed' in events

    print('--- fully fund riskpool --------------------------')
    # ensure the riskpool is fully funded
    riskpool.setMaximumNumberOfActiveBundles(2, {'from': riskpoolKeeper})
    riskpoolFunding = 20000
    fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)

    # check riskpool funds and book keeping after funding
    riskpoolBalanceAfter2ndFunding = token.balanceOf(riskpoolWallet)
    assert riskpoolBalanceAfter2ndFunding > riskpoolBalanceAfterFunding
    assert riskpool.bundles() == 2
    
    print('--- underwrite application --------------------------')
    # now underwrite the policy as the riskpool is now funded
    tx = product.underwrite(process_id, {'from': insurer})
    assert True == tx.return_value

    events = tx.events
    print(events)
    assert 'LogAyiiPolicyCreated' in events

    # ensure application exists and has state Applied
    application = instanceService.getApplication(process_id)
    assert 2 == application[0] # ApplicationState.Underwritten

def test_underwrite_invalid_policy_id(
    gifAyiiProduct: GifAyiiProduct,
    insurer,
):
    product = gifAyiiProduct.getContract()

    with brownie.reverts("ERROR:POC-101:APPLICATION_DOES_NOT_EXIST"):
        tx = product.underwrite(s2b32('does_not_exist'), {'from': insurer})



def prepare_risk(product, insurer):
    print('--- test setup risks -------------------------------------')

    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = [s2b32('1234'), s2b32('2345')]
    cropId = s2b32('mixed')
    
    triggerFloat = 0.75
    exitFloat = 0.1
    tsiFloat = 0.9
    aphFloat = [2.0, 1.8]
    
    multiplier = product.getPercentageMultiplier()
    trigger = multiplier * triggerFloat
    exit = multiplier * exitFloat
    tsi = multiplier * tsiFloat
    aph = [multiplier * aphFloat[0], multiplier * aphFloat[1]]

    tx = product.createRisk(projectId, uaiId[0], cropId, trigger, exit, tsi, aph[0], {'from': insurer})
    return tx.return_value
