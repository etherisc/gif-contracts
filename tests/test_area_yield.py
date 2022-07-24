import brownie
import pytest

from brownie.network.account import Account

from brownie import (
    interface,
    AreaYieldIndexOracle,
    AreaYieldIndexProduct,
)

from scripts.area_yield_index import (
    GifAreaYieldIndexOracle,
    GifAreaYieldIndexProduct
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
    gifAreaYieldIndexProduct: GifAreaYieldIndexProduct,
    capitalOwner,
    productOwner,
    oracleProvider,
    riskpoolKeeper,
    customer,
    customer2
):
    instanceService = instance.getInstanceService()

    product = gifAreaYieldIndexProduct.getContract()
    oracle = gifAreaYieldIndexProduct.getOracle().getContract()
    riskpool = gifAreaYieldIndexProduct.getRiskpool().getContract()

    riskpoolWallet = capitalOwner
    investor = riskpoolKeeper # investor=bundleOwner
    insurer = productOwner # role required by area yield index product

    clOperator = gifAreaYieldIndexProduct.getOracle().getClOperator()

    print('--- test setup funding riskpool --------------------------')
    token = gifAreaYieldIndexProduct.getToken()
    riskpoolFunding = 200000
    fund_riskpool(
        instance, 
        owner, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)
    
    print('--- test setup funding customers -------------------------')
    customerFunding = 500
    fund_customer(instance, owner, customer, token, customerFunding)
    fund_customer(instance, owner, customer2, token, customerFunding)

    print('--- test step apply for policy ---------------------------')
    uai1 = '1'
    uai2 = '2'
    cropId1 = 1001
    cropId2 = 1002
    premium1 = 200
    premium2 = 300
    sumInsured = 60000

    # batched policy creation
    perils = [
            create_peril(uai1, cropId1, premium1, sumInsured, customer),
            create_peril(uai2, cropId2, premium2, sumInsured, customer2),
        ]
    
    tx = product.applyForPolicy(perils, {'from': insurer})

    # returns tuple for created process ids
    processIds = tx.return_value

    # ensure policies are created as expected
    assert len(processIds) == 2
    meta1 = instanceService.getMetadata(processIds[0]).dict()
    meta2 = instanceService.getMetadata(processIds[1]).dict()
    application1 = instanceService.getApplication(processIds[0]).dict()
    application2 = instanceService.getApplication(processIds[1]).dict()
 
    assert meta1['owner'] == customer
    assert meta1['productId'] == product.getId()
    assert application1['premiumAmount'] == premium1
    assert application1['sumInsuredAmount'] == sumInsured
    assert application1['state'] == 2
 
    assert meta2['owner'] == customer2
    assert meta2['productId'] == product.getId()
    assert application2['premiumAmount'] == premium2
    assert application2['sumInsuredAmount'] == sumInsured
    assert application2['state'] == 2

    print('--- step trigger resolutions (call chainlin oracle) ------')
    txTrigger = product.triggerResolutions(uai1, {'from': insurer})
    requestId = txTrigger.return_value

    # ensure event emitted as chainlink client
    assert 'OracleRequest' in txTrigger.events
    assert len(txTrigger.events['OracleRequest']) == 1

    # check event attributes
    clRequestEvent = txTrigger.events['OracleRequest'][0]
    print('chainlink requestEvent {}'.format(clRequestEvent))
    assert clRequestEvent['requester'] == oracle.address
    assert clRequestEvent['requester'] == clRequestEvent['callbackAddr']

    # check that gif request id corresponds to expected chainlink request id
    assert 'LogAYIRequest' in txTrigger.events
    assert len(txTrigger.events['LogAYIRequest']) == 1

    requestEvent = txTrigger.events['LogAYIRequest'][0]
    print('ayi requestEvent {}'.format(requestEvent))
    assert requestEvent['requestId'] == requestId
    assert requestEvent['chainlinkRequestId'] == clRequestEvent['requestId']

    # TODO fix call setup below
    # brownie.exceptions.VirtualMachineError: revert: Response must be > 32 bytes

    # payment = 0
    # txOperator = clOperator.fulfillOracleRequest2(
    #     clRequestEvent['requestId'],
    #     clRequestEvent['payment'],
    #     clRequestEvent['callbackAddr'],
    #     clRequestEvent['callbackFunctionId'],
    #     clRequestEvent['cancelExpiration'],
    #     clRequestEvent['data'],
    #     {'from': oracleProvider }
    # )

    # success = txOperator.return_value
    # assert success


    print('--- step trigger resolutions -----------------------------')
    # TODO it("trigger resolutions processing", async function () { ...

    print('--- step withdraw reminder -------------------------------')
    # TODO it("withdraw remainder", async function () { ...
    


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
