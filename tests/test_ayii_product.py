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


def test_happy_path(
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
    riskpool = gifAyiiProduct.getRiskpool().getContract()

    clOperator = gifAyiiProduct.getOracle().getClOperator()

    print('--- test setup funding riskpool --------------------------')

    token = gifAyiiProduct.getToken()
    assert token.balanceOf(riskpoolWallet) == 0

    riskpoolFunding = 200000
    fund_riskpool(
        instance, 
        instanceOperator, 
        riskpoolWallet, 
        riskpool, 
        investor, 
        token, 
        riskpoolFunding)

    # check riskpool funds and book keeping after funding
    riskpoolBalanceAfterFunding = token.balanceOf(riskpoolWallet)
    riskpoolExpectedBalance = 0.95 * riskpoolFunding - 42
    assert riskpoolBalanceAfterFunding == riskpoolExpectedBalance
    assert riskpool.bundles() == 1
    assert riskpool.getCapital() == riskpoolExpectedBalance
    assert riskpool.getTotalValueLocked() == 0
    assert riskpool.getCapacity() == riskpoolExpectedBalance
    assert riskpool.getBalance() == riskpoolExpectedBalance

    # check risk bundle in riskpool and book keeping after funding
    bundleIdx = 0
    bundleAfterFunding = riskpool.getBundle(bundleIdx).dict()
    bundleId = bundleAfterFunding['id']

    assert bundleAfterFunding['id'] == 1
    assert bundleAfterFunding['riskpoolId'] == riskpool.getId()
    assert bundleAfterFunding['state'] == 0
    assert bundleAfterFunding['capital'] == riskpoolExpectedBalance
    assert bundleAfterFunding['lockedCapital'] == 0
    assert bundleAfterFunding['balance'] == riskpoolExpectedBalance

    # cheeck bundle token (nft)
    bundleNftId = bundleAfterFunding['tokenId']
    bundleToken = contractFromAddress(BundleToken, instanceService.getBundleToken())
    assert bundleToken.exists(bundleNftId) == True
    assert bundleToken.burned(bundleNftId) == False
    assert bundleToken.getBundleId(bundleNftId) == bundleId
    assert bundleToken.balanceOf(investor) == 1
    assert bundleToken.ownerOf(bundleNftId) == investor

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

    tx = [None, None]
    tx[0] = product.createRisk(projectId, uaiId[0], cropId, trigger, exit, tsi, aph[0], {'from': insurer})
    tx[1] = product.createRisk(projectId, uaiId[1], cropId, trigger, exit, tsi, aph[1], {'from': insurer})

    riskId = [None, None]
    riskId = [tx[0].return_value, tx[1].return_value]
    print('riskId {}'.format(riskId))
    assert riskId[0] != riskId[1]
    assert riskId[0] == product.getRiskId(projectId, uaiId[0], cropId)
    assert riskId[1] == product.getRiskId(projectId, uaiId[1], cropId)
    

    print('--- test setup funding customers -------------------------')

    assert token.balanceOf(customer) == 0
    assert token.balanceOf(customer2) == 0

    customerFunding = 500
    fund_customer(instance, instanceOperator, customer, token, customerFunding)
    fund_customer(instance, instanceOperator, customer2, token, customerFunding)

    # check customer funds after funding
    customerBalanceAfterFunding = token.balanceOf(customer)
    customer2BalanceAfterFunding = token.balanceOf(customer2)
    assert customerBalanceAfterFunding == customerFunding
    assert customer2BalanceAfterFunding == customerFunding


    print('--- test create policies ---------------------------------')

    premium = [300, 400]
    sumInsured = [2000, 3000]

    tx[0] = product.applyForPolicy(customer, premium[0], sumInsured[0], riskId[0], {'from': insurer})
    tx[1] = product.applyForPolicy(customer2, premium[1], sumInsured[1], riskId[1], {'from': insurer})

    # check customer funds after application/paying premium
    customerBalanceAfterPremium = token.balanceOf(customer)
    customer2BalanceAfterPremium = token.balanceOf(customer2)
    assert premium[0] + customerBalanceAfterPremium == customerBalanceAfterFunding 
    assert premium[1] + customer2BalanceAfterPremium == customer2BalanceAfterFunding 

    # check riskpool funds after application/paying premium
    netPremium = [0.9 * premium[0] - 3, 0.9 * premium[1] - 3]
    riskpoolBalanceAfterPremiums = token.balanceOf(riskpoolWallet)
    assert riskpoolBalanceAfterPremiums == riskpoolBalanceAfterFunding + netPremium[0] + netPremium[1]

    # check risk bundle after premium
    bundleAfterPremium = riskpool.getBundle(bundleIdx).dict()
    assert bundleAfterPremium['id'] == 1
    assert bundleAfterPremium['riskpoolId'] == riskpool.getId()
    assert bundleAfterPremium['state'] == 0
    assert bundleAfterPremium['capital'] == riskpoolExpectedBalance
    assert bundleAfterPremium['lockedCapital'] == sumInsured[0] + sumInsured[1]
    assert bundleAfterPremium['balance'] == riskpoolExpectedBalance + netPremium[0] + netPremium[1]

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
    assert meta[0]['state'] == 1
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
    assert meta[1]['state'] == 1
    assert meta[1]['owner'] == customer2
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

    tx[0] = product.triggerOracle(riskId[0], {'from': insurer})
    tx[1] = product.triggerOracle(riskId[1], {'from': insurer})
    requestId = [tx[0].return_value, tx[1].return_value]

    # ensure event emitted as chainlink client
    assert 'OracleRequest' in tx[0].events
    assert len(tx[0].events['OracleRequest']) == 1

    # check event attributes
    clRequestEvent = tx[0].events['OracleRequest'][0]
    clRequestEvent1 = tx[1].events['OracleRequest'][0]
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

    # create aaay data for oracle response
    # aaay value selected triggers a payout
    aaayFloat = 1.1
    aaay = product.getPercentageMultiplier() * aaayFloat

    data = [None, None]
    data[0] = oracle.encodeFulfillParameters(
        clRequestEvent['requestId'], 
        projectId, 
        uaiId[0], 
        cropId, 
        aaay
    )

    # simulate callback from oracle node with call to chainlink operator contract
    tx[0] = clOperator.fulfillOracleRequest2(
        clRequestEvent['requestId'],
        clRequestEvent['payment'],
        clRequestEvent['callbackAddr'],
        clRequestEvent['callbackFunctionId'],
        clRequestEvent['cancelExpiration'],
        data[0]
    )

    print(tx[0].info())

    # simulate callback for 2nd risk
    data[1] = oracle.encodeFulfillParameters(
        clRequestEvent1['requestId'],
        projectId, 
        uaiId[1], 
        cropId, 
        aph[1] # setting aaay to aph will result in a 0 payout
    )

    # simulate callback from oracle node with call to chainlink operator contract
    tx[1] = clOperator.fulfillOracleRequest2(
        clRequestEvent1['requestId'],
        clRequestEvent1['payment'],
        clRequestEvent1['callbackAddr'],
        clRequestEvent1['callbackFunctionId'],
        clRequestEvent1['cancelExpiration'],
        data[1]
    )

    # focus checks on oracle 1 response
    # verify in log entry that aaay data properly arrives in ayii product cotract
    assert 'LogAyiiRiskDataReceived' in tx[0].events
    assert len(tx[0].events['LogAyiiRiskDataReceived']) == 1

    receivedEvent = tx[0].events['LogAyiiRiskDataReceived'][0]
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


    print('--- step test process policies (risk[0]) -----------------')

    print('balanceOf(riskpoolWallet): {}'.format(token.balanceOf(riskpoolWallet)))
    print('sumInsured[0]: {}'.format(sumInsured[0]))
    
    assert token.balanceOf(riskpoolWallet) == riskpoolBalanceAfterPremiums
    assert riskpoolBalanceAfterPremiums >= sumInsured[0]

    # record riskpool state before processing
    balanceBeforeProcessing = riskpool.getBalance()
    valueLockedBeforeProcessing = riskpool.getTotalValueLocked()
    capacityBeforeProcessing = riskpool.getCapacity()

    # claim processing for policies associated with the specified risk
    # batch size=0 triggers processing of all policies for this risk
    tx = product.processPoliciesForRisk(riskId[0], 0, {'from': insurer})
    policyIds = tx.return_value

    assert len(policyIds) == 1
    assert policyIds[0] == policyId[0]

    assert instanceService.claims(policyId[1]) == 0 # not triggered -> no claim
    assert instanceService.claims(policyId[0]) == 1 # triggered -> claim

    policy = instanceService.getPolicy(policyId[0]).dict()
    print('policy {}'.format(policy))
    assert policy['state'] == 2 # enum PolicyState {Active, Expired, Closed}
    assert policy['claimsCount'] == 1
    assert policy['openClaimsCount'] == 0
    assert policy['createdAt'] > 0
    assert policy['updatedAt'] >= policy['createdAt']

    expectedClaimPercentage = product.calculatePayoutPercentage(
        risk['tsi'],
        risk['trigger'],
        risk['exit'],
        risk['aph'],
        risk['aaay'],
    )

    expectedPayoutAmount = int(expectedClaimPercentage * sumInsured[0] / product.getPercentageMultiplier())
    assert expectedPayoutAmount > 0
    assert expectedPayoutAmount <= sumInsured[0]

    claim = instanceService.getClaim(policyId[0], 0).dict()
    print('claim {}'.format(claim))
    assert claim['state'] == 3 # ClaimState {Applied, Confirmed, Declined, Closed}
    assert claim['claimAmount'] == expectedPayoutAmount
    assert claim['createdAt'] >= policy['createdAt']
    assert claim['updatedAt'] == claim['createdAt']

    assert instanceService.payouts(policyId[0]) == 1 

    payout = instanceService.getPayout(policyId[0], 0).dict()
    print('payout {}'.format(payout))
    assert payout['claimId'] == 0
    assert payout['state'] == 1 # PayoutState {Expected, PaidOut}
    assert payout['amount'] == expectedPayoutAmount
    assert payout['createdAt'] == claim['createdAt']
    assert payout['updatedAt'] == payout['createdAt']

    print(tx.info())

    # tests token balances for actual payout
    # riskpool wallet decrease of balance by payout amount
    assert token.balanceOf(riskpoolWallet) == riskpoolBalanceAfterPremiums - expectedPayoutAmount

    # check customer increase of balance by payout amount (and no increase for customer2)
    assert token.balanceOf(customer) == customerBalanceAfterPremium + expectedPayoutAmount 
    assert token.balanceOf(customer2) == customer2BalanceAfterPremium

    # check risk bundle after payout
    bundleAfterPayout = riskpool.getBundle(bundleIdx).dict()
    assert bundleAfterPayout['id'] == 1
    assert bundleAfterPayout['riskpoolId'] == riskpool.getId()
    assert bundleAfterPayout['state'] == 0
    assert bundleAfterPayout['capital'] == riskpoolExpectedBalance
    assert bundleAfterPayout['lockedCapital'] == sumInsured[1]
    assert bundleAfterPayout['balance'] == riskpoolExpectedBalance + netPremium[0] + netPremium[1] - expectedPayoutAmount

    # record riskpool state after processing
    balanceAfterProcessing = riskpool.getBalance()
    valueLockedAfterProcessing = riskpool.getTotalValueLocked()
    capacityAfterProcessing = riskpool.getCapacity()

    # check book keeping on riskpool level
    assert valueLockedAfterProcessing == valueLockedBeforeProcessing - sumInsured[0]
    assert capacityAfterProcessing == capacityBeforeProcessing + sumInsured[0]
    assert balanceAfterProcessing == balanceBeforeProcessing - expectedPayoutAmount

    print('--- step test process policies (risk[1]) -----------------')

    # process 2nd policy to have all policies closed
    tx = product.processPoliciesForRisk(riskId[1], 0, {'from': insurer})
    policyIds = tx.return_value
    assert len(policyIds) == 1
    assert policyIds[0] == policyId[1]

    # high level checs
    policy = instanceService.getPolicy(policyId[1]).dict()
    assert policy['state'] == 2 # enum PolicyState {Active, Expired, Closed}
    assert policy['claimsCount'] == 1
    assert policy['openClaimsCount'] == 0

    assert instanceService.payouts(policyId[1]) == 0

    claim = instanceService.getClaim(policyId[1], 0).dict()
    print('claim {}'.format(claim))
    assert claim['state'] == 3 # ClaimState {Applied, Confirmed, Declined, Closed}
    assert claim['claimAmount'] == 0

    # check bundle state
    bundleAfter2ndPayout = riskpool.getBundle(bundleIdx).dict()
    assert bundleAfter2ndPayout['capital'] == riskpoolExpectedBalance
    assert bundleAfter2ndPayout['lockedCapital'] == 0
    assert bundleAfter2ndPayout['balance'] == riskpoolExpectedBalance + netPremium[0] + netPremium[1] - expectedPayoutAmount

    # check riskpool state
    assert riskpool.getTotalValueLocked() == 0
    assert riskpool.getBalance() == bundleAfter2ndPayout['balance']

    print('--- step test close bundle -------------------------------')

    investorBalanceBeforeBundleClose = token.balanceOf(investor)

    riskpool.closeBundle(bundleId, {'from': investor})

    investorBalanceBeforeTokenBurn = token.balanceOf(investor)    
    assert investorBalanceBeforeBundleClose == investorBalanceBeforeTokenBurn

    bundleBeforeBurn = riskpool.getBundle(bundleIdx).dict()
    assert bundleBeforeBurn['state'] == 2 # enum BundleState { Active, Locked, Closed, Burned }

    # cheeck bundle token (nft)
    bundleNftId = bundleBeforeBurn['tokenId']
    assert bundleToken.exists(bundleNftId) == True
    assert bundleToken.burned(bundleNftId) == False
    assert bundleToken.ownerOf(bundleNftId) == investor

    tx = riskpool.burnBundle(bundleId, {'from': investor})
    print(tx.info())

    # verify bundle is burned and has 0 balance
    bundleAfterBurn = riskpool.getBundle(bundleIdx).dict()
    assert bundleAfterBurn['state'] == 3 # enum BundleState { Active, Locked, Closed, Burned }
    assert bundleAfterBurn['balance'] == 0

    # verify bundle funds are now with investor
    assert bundleToken.exists(bundleNftId) == True
    assert bundleToken.burned(bundleNftId) == True
    with brownie.reverts('ERC721: invalid token ID'):
        assert bundleToken.ownerOf(bundleNftId) == investor
    
    assert token.balanceOf(investor) == investorBalanceBeforeTokenBurn + bundleBeforeBurn['balance']


def test_create_bundle_investor_restriction(
    instance: GifInstance, 
    instanceOperator: Account, 
    gifAyiiProduct: GifAyiiProduct,
    riskpoolWallet: Account,
    productOwner: Account,
    oracleProvider: Account,
    riskpoolKeeper: Account,
    investor: Account,
    customer: Account,
):
    instanceService = instance.getInstanceService()

    product = gifAyiiProduct.getContract()
    oracle = gifAyiiProduct.getOracle().getContract()
    riskpool = gifAyiiProduct.getRiskpool().getContract()

    amount = 5000
    token = gifAyiiProduct.getToken()
    token.transfer(investor, amount, {'from': instanceOperator})
    token.approve(instance.getTreasury(), amount, {'from': investor})

    # check that investor can create a bundle
    applicationFilter = bytes(0)
    tx = riskpool.createBundle(
            applicationFilter, 
            amount, 
            {'from': investor})
    
    bundleId = tx.return_value
    assert bundleId > 0

    # check that customer is not allowed to create bundle
    with brownie.reverts("AccessControl: account 0x5aeda56215b167893e80b4fe645ba6d5bab767de is missing role 0x5614e11ca6d7673c9c8dcec913465d676494aad1151bb2c1cf40b9d99be4d935"):
        riskpool.createBundle(
                applicationFilter, 
                amount, 
                {'from': customer})

    # check that customer cannot assign investor role to herself
    with brownie.reverts("Ownable: caller is not the owner"):
        riskpool.grantInvestorRole(customer, {'from': customer})

    # assign investor role to customer
    riskpool.grantInvestorRole(customer, {'from': riskpoolKeeper})

    # fund customer
    customerAmount = 2000
    token.transfer(customer, customerAmount, {'from': instanceOperator})
    token.approve(instance.getTreasury(), customerAmount, {'from': customer})

    # check that customer now can create a bundle
    tx = riskpool.createBundle(
            applicationFilter, 
            customerAmount, 
            {'from': customer})
    
    bundleIdCustomer = tx.return_value
    assert bundleIdCustomer == bundleId + 1


def test_payout_percentage_calculation(gifAyiiProduct: GifAyiiProduct):

    product = gifAyiiProduct.getContract()
    multiplier = product.getPercentageMultiplier()

    # product example values
    tsi = 0.9
    trigger = 0.75
    exit = 0.1

    # random example values
    # expected payout = 0.091093117, aph = 1.9, aaay = 1.3
    assert get_payout_delta(0.091093117, 1.9, 1.3, tsi, trigger, exit, product, multiplier) < 0.00000001

    # run through product example table
    # harvest ratio >= trigger (75%) give 0 payout 
    assert get_payout_delta(0, 100.0, 110.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0, 100.0, 100.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0, 100.0,  95.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0, 100.0,  90.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0, 100.0,  85.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0, 100.0,  80.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0, 100.0,  75.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.06923073, 100.0,  70.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.13846153, 100.0,  65.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.20769232, 100.0,  60.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.27692312, 100.0,  55.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.34615379, 100.0,  50.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.41538459, 100.0,  45.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.48461532, 100.0,  40.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.55384612, 100.0,  35.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.62307691, 100.0,  30.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.69230759, 100.0,  25.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.76153838, 100.0,  20.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.83076918, 100.0,  15.0, tsi, trigger, exit, product, multiplier) < 0.00000001
    assert get_payout_delta(0.9, 100.0,  10.0, tsi, trigger, exit, product, multiplier) < 0.0000001
    assert get_payout_delta(0.9, 100.0,   5.0, tsi, trigger, exit, product, multiplier) < 0.0000001
    assert get_payout_delta(0.9, 100.0,   0.0, tsi, trigger, exit, product, multiplier) < 0.0000001


def test_payout_percentage_calculation(gifAyiiProduct: GifAyiiProduct):

    product = gifAyiiProduct.getContract()
    multiplier = product.getPercentageMultiplier()

    # product example values
    tsi = 0.9
    trigger = 0.75
    exit = 0.1

    expected_payout_percentage = 0.091093117 * multiplier
    aph = 1.9
    aaay = 1.3

    payout_percentage = product.calculatePayoutPercentage(
        tsi * multiplier,
        trigger * multiplier,
        exit * multiplier,
        aph * multiplier,
        aaay * multiplier
    )
    assert int(expected_payout_percentage + 0.5) == payout_percentage

    sumInsuredAmount = 2200
    expected_payout = int(expected_payout_percentage * sumInsuredAmount / multiplier)
    assert expected_payout == product.calculatePayout(expected_payout_percentage, sumInsuredAmount)


def get_payout_delta(
    expectedPayoutPercentage,
    aph, aaay, 
    tsi, trigger, exit, 
    product, multiplier
):
    calculatedPayout = product.calculatePayoutPercentage(
        tsi * multiplier,
        trigger * multiplier,
        exit * multiplier,
        aph * multiplier,
        aaay * multiplier
    )

    return abs(expectedPayoutPercentage * multiplier - calculatedPayout) / multiplier
