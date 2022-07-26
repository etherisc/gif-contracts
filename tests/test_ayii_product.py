import brownie
import pytest

from brownie.network.account import Account

from brownie import (
    interface,
    AreaYieldIndexOracle,
    AyiiProduct,
)

from scripts.area_yield_index import (
    GifAreaYieldIndexOracle,
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


def test_sanity_flow(
    instance: GifInstance, 
    owner, 
    gifAyiiProduct: GifAyiiProduct,
    capitalOwner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
    customer,
    customer2
):
    instanceService = instance.getInstanceService()

    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    riskpool = gifAyiiProduct.getRiskpool().getContract()

    riskpoolWallet = capitalOwner
    investor = riskpoolKeeper # investor=bundleOwner
    insurer = productOwner # role required by area yield index product

    clOperator = gifAyiiProduct.getOracle().getClOperator()

    print('--- test setup funding riskpool --------------------------')
    token = gifAyiiProduct.getToken()
    riskpoolFunding = 200000
    fund_riskpool(
        instance, 
        owner, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)

    print('--- test setup risks -------------------------------------')

    UNIT_MULTIPLIER = 10**10

    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = [s2b32('1234'), s2b32('2345')]
    cropId = s2b32('mixed')
    
    triggerFloat = 0.75
    exitFloat = 0.1
    tsiFloat = 0.9
    aphFloat = [2.0, 1.8]
    
    trigger = UNIT_MULTIPLIER * triggerFloat
    exit = UNIT_MULTIPLIER * exitFloat
    tsi = UNIT_MULTIPLIER * tsiFloat
    aph = [UNIT_MULTIPLIER * aphFloat[0], UNIT_MULTIPLIER * aphFloat[1]]

    tx = [None, None]
    tx[0] = product.createRisk(projectId, uaiId[0], cropId, trigger, exit, tsi, aph[0])
    tx[1] = product.createRisk(projectId, uaiId[1], cropId, trigger, exit, tsi, aph[1])

    riskId = [None, None]
    riskId = [tx[0].return_value, tx[1].return_value]
    print('riskId {}'.format(riskId))
    assert riskId[0] != riskId[1]
    assert riskId[0] == product.getRiskId(projectId, uaiId[0], cropId)
    assert riskId[1] == product.getRiskId(projectId, uaiId[1], cropId)
    
    print('--- test setup funding customers -------------------------')
    customerFunding = 500
    fund_customer(instance, owner, customer, token, customerFunding)
    fund_customer(instance, owner, customer2, token, customerFunding)

    print('--- test create policies ---------------------------------')

    premium = [200, 300]
    sumInsured = [2200, 3300]

    tx[0] = product.applyForPolicy(customer, premium[0], sumInsured[0], riskId[0])
    tx[1] = product.applyForPolicy(customer2, premium[1], sumInsured[1], riskId[1])

    policyId = [None, None]
    policyId = [tx[0].return_value, tx[1].return_value]
    print('policyId {}'.format(policyId))
    assert policyId[0] != policyId[1]

    meta = [None, None]
    meta[0] = instanceService.getMetadata(policyId[0]).dict()
    meta[1] = instanceService.getMetadata(policyId[1]).dict()
    print('meta {}'.format(meta))

    application = [None, None]
    application[0] = instanceService.getApplication(policyId[0]).dict()
    application[1] = instanceService.getApplication(policyId[1]).dict()
    print('application {}'.format(application))

    policy = [None, None]
    policy[0] = instanceService.getPolicy(policyId[0]).dict()
    policy[1] = instanceService.getPolicy(policyId[1]).dict()
    print('policy {}'.format(policy))
 
    # check policy 1
    assert meta[0]['state'] == 0
    assert meta[0]['owner'] == customer
    assert meta[0]['productId'] == product.getId()
    assert application[0]['state'] == 2
    assert application[0]['premiumAmount'] == premium[0]
    assert application[0]['sumInsuredAmount'] == sumInsured[0]
    assert application[0]['data'] == riskId[0]
    assert policy[0]['state'] == 0
    assert policy[0]['premiumExpectedAmount'] == premium[0]
    assert policy[0]['premiumPaidAmount'] == premium[0]
 
    # check policy 2
    assert meta[1]['state'] == 0
    assert meta[1]['owner'] == customer
    assert meta[1]['productId'] == product.getId()
    assert application[1]['state'] == 2
    assert application[1]['premiumAmount'] == premium[1]
    assert application[1]['sumInsuredAmount'] == sumInsured[1]
    assert application[1]['data'] == riskId[1]
    assert policy[1]['state'] == 0
    assert policy[1]['premiumExpectedAmount'] == premium[1]
    assert policy[1]['premiumPaidAmount'] == premium[1]

    assert product.policies(riskId[0]) == 1
    assert product.policies(riskId[1]) == 1
    assert product.policies(s2b32('dummyRiskId')) == 0

    assert product.getPolicyId(riskId[0], 0) == policyId[0]
    assert product.getPolicyId(riskId[1], 0) == policyId[1]
 
    print('--- step trigger oracle (call chainlin node) -------------')

    tx[0] = product.triggerOracle(riskId[0])
    tx[1] = product.triggerOracle(riskId[1])
    requestId = [tx[0].return_value, tx[1].return_value]

    # ensure event emitted as chainlink client
    assert 'OracleRequest' in tx[0].events
    assert len(tx[0].events['OracleRequest']) == 1

    # check event attributes
    clRequestEvent = tx[0].events['OracleRequest'][0]
    print('chainlink requestEvent {}'.format(clRequestEvent))
    assert clRequestEvent['requester'] == oracle.address
    assert clRequestEvent['requester'] == clRequestEvent['callbackAddr']

    # check that gif request id corresponds to expected chainlink request id
    assert 'LogAyiiRiskDataRequested' in tx[0].events
    assert len(tx[0].events['LogAyiiRiskDataRequested']) == 1

    requestEvent = tx[0].events['LogAyiiRiskDataRequested'][0]
    print('ayii requestEvent {}'.format(requestEvent))
    assert requestEvent['requestId'] == requestId[0]
    assert requestEvent['projectId'] == projectId
    assert requestEvent['riskId'] == riskId[0]
    assert requestEvent['uaiId'] == uaiId[0]
    assert requestEvent['cropId'] == cropId

    print('--- step test oracle response ----------------------------')

    risk = product.getRisk(riskId[0]).dict()
    assert risk['id'] == riskId[0]
    assert risk['createdAt'] > 0
    assert risk['responseAt'] == 0
    assert risk['aaay'] == 0

    # simulate callback from oracle node
    aaayFloat = 1.1
    aaay = UNIT_MULTIPLIER * aaayFloat

    data = oracle.encodeFulfillParameters(
        clRequestEvent['requestId'], 
        projectId, 
        uaiId[0], 
        cropId, 
        aaay
    )

    tx = clOperator.fulfillOracleRequest2(
        clRequestEvent['requestId'],
        clRequestEvent['payment'],
        clRequestEvent['callbackAddr'],
        clRequestEvent['callbackFunctionId'],
        clRequestEvent['cancelExpiration'],
        data
    )

    print(tx.info())

    # verify in log entry that aaay data properly arrives in ayii product cotract
    assert 'LogAyiiRiskDataReceived' in tx.events
    assert len(tx.events['LogAyiiRiskDataReceived']) == 1

    receivedEvent = tx.events['LogAyiiRiskDataReceived'][0]
    print('ayii requestEvent {}'.format(receivedEvent))
    assert receivedEvent['requestId'] == requestId[0]
    assert receivedEvent['riskId'] == riskId[0]
    assert receivedEvent['aaay'] == aaay

    # verify in risk that aaay data properly arrives in ayii product cotract
    risk = product.getRisk(riskId[0]).dict()
    print('risk {}'.format(risk))
    assert risk['id'] == riskId[0]
    assert risk['responseAt'] > risk['createdAt']
    assert risk['aaay'] == aaay

    # TODO test payoutFactor

    print('--- step test process policies ---------------------------')
    # TODO add setup and assertions

    print('--- step test close bundle -------------------------------')
    # TODO add setup and assertions
    


def create_peril(
    id:str, 
    cropId:int, 
    premium:int, 
    sumInsured:int, 
    customer: Account
):
    UAI = 100;
    AAAY = 1;
    APH = 2;
    precisionMultiplier = 10 ** 6
    trigger = 0.75 * precisionMultiplier;
    exit = 0.10 * precisionMultiplier;
    TSI = 0.90 * precisionMultiplier;

    return [
        id, 
        UAI, 
        cropId, 
        trigger, 
        exit, 
        TSI, 
        APH, 
        sumInsured, 
        premium, 
        customer
    ]
