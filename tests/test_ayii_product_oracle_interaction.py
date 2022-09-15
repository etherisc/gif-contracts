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


def test_trigger_and_cancel_oracle_requests(
    instance: GifInstance, 
    instanceOperator, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet,
    investor,
    productOwner,
    insurer,
    oracleProvider,
    riskpoolKeeper,
    customer,
    customer2
):
    instanceService = instance.getInstanceService()
    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    clOperator = gifAyiiProduct.getOracle().getClOperator()
    riskpool = gifAyiiProduct.getRiskpool().getContract()

    token = gifAyiiProduct.getToken()
    riskpoolFunding = 200000
    fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)

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
    riskId = tx.return_value

    customerFunding = 500
    fund_customer(instance, instanceOperator, customer, token, customerFunding)

    premium = 300
    sumInsured = 2000
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    processId = tx.return_value

    print('--- step trigger oracle (call chainlin node) -------------')

    tx = product.triggerOracle(processId, {'from': insurer})
    requestId = tx.return_value
    clRequestEvent = tx.events['OracleRequest'][0]

    print('oracle request triggered'.format(tx.info()))
    assert requestId == 0

    # check if existing request can be cancelled 
    tx = product.cancelOracleRequest(processId, {'from': insurer})
    print('oracle request cancelled'.format(tx.info()))

    print('--- oracle node answers to cancelled request ----------------------------')

    risk = product.getRisk(riskId).dict()

    # create aaay data for oracle response
    # aaay value selected triggers a payout
    aaayFloat = 1.1
    aaay = product.getPercentageMultiplier() * aaayFloat

    data = oracle.encodeFulfillParameters(
        clRequestEvent['requestId'],
        projectId, 
        uaiId, 
        cropId, 
        aaay
    )

    # simulate callback from oracle node with call to chainlink operator contract
    tx = clOperator.fulfillOracleRequest2(
        clRequestEvent['requestId'],
        clRequestEvent['payment'],
        clRequestEvent['callbackAddr'],
        clRequestEvent['callbackFunctionId'],
        clRequestEvent['cancelExpiration'],
        data
    )

    success = tx.return_value
    assert success == False
    print('fulfill on cancelled request: {}'.format(tx.info()))
    print('fulfill on cancelled request. return_value: {}'.format(tx.return_value))

    print('--- oracle node triggering for 2nd time ----------------------------')

    # check if processId (risk) can now be triggered a second time
    tx = product.triggerOracle(processId, {'from': insurer})
    requestId2 = tx.return_value
    clRequestEvent2 = tx.events['OracleRequest'][0]

    print('oracle request triggered again'.format(tx.info()))
    assert requestId2 == 1

    print('--- oracle node answers to repeated request ----------------------------')

    data2 = oracle.encodeFulfillParameters(
        clRequestEvent2['requestId'],
        projectId, 
        uaiId, 
        cropId, 
        aaay
    )

    # simulate callback from oracle node with call to chainlink operator contract
    tx2 = clOperator.fulfillOracleRequest2(
        clRequestEvent2['requestId'],
        clRequestEvent2['payment'],
        clRequestEvent2['callbackAddr'],
        clRequestEvent2['callbackFunctionId'],
        clRequestEvent2['cancelExpiration'],
        data2
    )

    print('fulfill on repeated request: {}'.format(tx2.info()))
    print('fulfill on repeated request. return_value: {}'.format(tx2.return_value))

    success = tx2.return_value
    assert success == True

    risk = product.getRisk(riskId).dict()
    print('risk {}'.format(risk))
    assert risk['id'] == riskId
    assert risk['requestId'] == requestId2
    assert risk['responseAt'] > risk['createdAt']
    assert risk['aaay'] == aaay

    # check if triggering the same risk twice works
    with brownie.reverts('ERROR:AYI-011:ORACLE_ALREADY_RESPONDED'):
        product.triggerOracle(processId, {'from': insurer})



def test_oracle_responds_with_invalid_aaay(
    instance: GifInstance, 
    instanceOperator, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet,
    investor,
    productOwner,
    insurer,
    oracleProvider,
    riskpoolKeeper,
    customer,
    customer2
):
    instanceService = instance.getInstanceService()
    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    clOperator = gifAyiiProduct.getOracle().getClOperator()
    riskpool = gifAyiiProduct.getRiskpool().getContract()

    token = gifAyiiProduct.getToken()
    riskpoolFunding = 200000
    fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)

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
    riskId = tx.return_value

    customerFunding = 500
    fund_customer(instance, instanceOperator, customer, token, customerFunding)

    premium = 300
    sumInsured = 2000
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    processId = tx.return_value

    print('--- step trigger oracle (call chainlin node) -------------')

    risk = product.getRisk(riskId).dict()
    print('risk before triggering oracle call {}'.format(risk))
    assert risk['requestTriggered'] == False
    assert risk['requestId'] == 0
    assert risk['responseAt'] == 0

    tx = product.triggerOracle(processId, {'from': insurer})
    requestId = tx.return_value
    clRequestEvent = tx.events['OracleRequest'][0]

    print('oracle request triggered'.format(tx.info()))
    assert requestId == 0

    print('--- oracle node answers with invalid aaay ----------------------------')

    risk = product.getRisk(riskId).dict()
    print('risk after triggering oracle call before oracle callback {}'.format(risk))
    assert risk['requestTriggered'] == True
    assert risk['responseAt'] == 0

    # create oracle response with aaay value out of range
    # aaay value selected triggers a payout
    aaayFloat = 17.9 
    aaay = product.getPercentageMultiplier() * aaayFloat

    data = oracle.encodeFulfillParameters(
        clRequestEvent['requestId'],
        projectId, 
        uaiId, 
        cropId, 
        aaay
    )

    # simulate callback from oracle node with call to chainlink operator contract
    tx = clOperator.fulfillOracleRequest2(
        clRequestEvent['requestId'],
        clRequestEvent['payment'],
        clRequestEvent['callbackAddr'],
        clRequestEvent['callbackFunctionId'],
        clRequestEvent['cancelExpiration'],
        data
    )

    success = tx.return_value
    assert success == False

    risk = product.getRisk(riskId).dict()
    print('risk after oracle call {}'.format(risk))
    assert risk['requestTriggered'] == True
    assert risk['responseAt'] == 0

    print('--- repeat trigger/response with valid aaaay ----------------------------')

    tx = product.triggerOracle(processId, {'from': insurer})
    requestId = tx.return_value
    clRequestEvent = tx.events['OracleRequest'][0]

    print('oracle request triggered'.format(tx.info()))
    assert requestId == 1

    risk = product.getRisk(riskId).dict()
    print('risk before triggering oracle call {}'.format(risk))
    assert risk['requestTriggered'] == True
    assert risk['requestId'] == 1
    assert risk['responseAt'] == 0

    validAaayFloat = 10.0 
    validAaay = product.getPercentageMultiplier() * validAaayFloat

    validData = oracle.encodeFulfillParameters(
        clRequestEvent['requestId'],
        projectId, 
        uaiId, 
        cropId, 
        validAaay
    )

    # simulate callback from oracle node with call to chainlink operator contract
    tx = clOperator.fulfillOracleRequest2(
        clRequestEvent['requestId'],
        clRequestEvent['payment'],
        clRequestEvent['callbackAddr'],
        clRequestEvent['callbackFunctionId'],
        clRequestEvent['cancelExpiration'],
        validData
    )

    success = tx.return_value
    assert success == True

    risk = product.getRisk(riskId).dict()
    print('risk after valid oracle callback {}'.format(risk))
    assert risk['requestTriggered'] == True
    assert risk['requestId'] == 1
    assert risk['responseAt'] > 0
    assert risk['aaay'] == validAaay

    print('--- attempt to repeat trigger once more ----------------------------')

    with brownie.reverts('ERROR:AYI-011:ORACLE_ALREADY_RESPONDED'):
        product.triggerOracle(processId, {'from': insurer})


def test_oracle_getters(gifAyiiProduct: GifAyiiProduct):

    ayiiOracle = gifAyiiProduct.getOracle()
    oracle = ayiiOracle.getContract()

    assert oracle.getChainlinkToken() == ayiiOracle.chainlinkToken
    assert oracle.getChainlinkOperator() == ayiiOracle.chainlinkOperator
    assert oracle.getChainlinkJobId() == s2b32('1')
    assert oracle.getChainlinkPayment() == 0
