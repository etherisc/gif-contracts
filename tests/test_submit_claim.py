import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    Wei,
    TestProduct,
)

from scripts.util import (
    s2h,
    s2b32,
)

from scripts.setup import (
    fund_riskpool,
    apply_for_policy,
)

from scripts.instance import (
    GifInstance,
)

from scripts.product import (
    GifTestProduct,
    GifTestRiskpool,
)

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_claim_submission(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()
    product = gifTestProduct.getContract()
    riskpoolWallet = capitalOwner
    investor = riskpoolKeeper

    policy_id = create_policy(
        instance, owner, gifTestProduct, riskpoolWallet, investor, customer, 
        testCoin, funding=10000, premium=100, sumInsured=5000)

    # ensure successful policy creation
    assert product.policies() == 1
    assert product.claims() == 0

    # only policy holder may sumit a claim
    claimAmount = 300
    with brownie.reverts():
        product.submitClaim(
            policy_id, 
            claimAmount, 
            {'from': riskpoolKeeper})

    # submit claim
    claim_tx = product.submitClaim(
        policy_id, 
        claimAmount, 
        {'from': customer})
    
    # expected id for new claim
    claim_id = claim_tx.return_value
    assert product.claims() == 1
    assert product.getClaimId(policy_id) == claim_id

    # check claim info
    claim = instanceService.getClaim(policy_id, claim_id)
    print(claim)


def test_claim_submission_for_expired_policy(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    premium = 100
    sumInsured = 5000
    policy_id = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    assert policy_id is not None 
    
    # only product owner may expire a policy
    product.expire(policy_id, {'from': productOwner})

    # attempt to submit a claim and verify attempt reverts
    claimAmount = 300
    with brownie.reverts():
        product.submitClaim(policy_id, claimAmount, {'from': customer})


def test_multiple_claim_submission(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 20000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    premium = 100
    sumInsured = 5000
    policy1_id = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    assert policy1_id is not None 

    # ensure successful policy creation
    assert product.applications() == 1
    assert product.policies() == 1
    assert product.claims() == 0

    # TODO add assertions to check coin balance

    # create 2nd policy
    policy2_id = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    assert policy2_id is not None 
    assert policy1_id != policy2_id
    
    # TODO add assertions to check coin balance

    # ensure successful policy creation
    assert product.applications() == 2
    assert product.policies() == 2
    assert product.claims() == 0

    # assertions via instance service
    instanceService = instance.getInstanceService()

    assert instanceService.claims(policy1_id) == 0
    assert instanceService.payouts(policy1_id) == 0
    assert instanceService.claims(policy2_id) == 0
    assert instanceService.payouts(policy2_id) == 0
    
    # submit claim for 1st policy
    product.submitClaim(policy1_id, 2*premium, {'from': customer})
    assert product.claims() == 1
    assert product.getClaimId(policy1_id) == 0

    assert instanceService.claims(policy1_id) == 1
    assert instanceService.payouts(policy1_id) == 1
    assert instanceService.claims(policy2_id) == 0
    assert instanceService.payouts(policy2_id) == 0
    
    # submit claim for 1st policy (every 2nd claim does not have any payout)
    product.submitClaim(policy2_id, premium/2, {'from': customer})
    assert product.claims() == 2
    assert product.getClaimId(policy2_id) == 0

    assert instanceService.claims(policy1_id) == 1
    assert instanceService.payouts(policy1_id) == 1
    assert instanceService.claims(policy2_id) == 1
    assert instanceService.payouts(policy2_id) == 0
    
    # submit 2nd claim for 1st policy
    product.submitClaim(policy1_id, premium/2, {'from': customer})
    assert product.claims() == 3
    assert product.getClaimId(policy1_id) == 1

    assert instanceService.claims(policy1_id) == 2
    assert instanceService.payouts(policy1_id) == 2
    assert instanceService.claims(policy2_id) == 1
    assert instanceService.payouts(policy2_id) == 0


def test_payout_creation_for_declined_claim(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()

    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    claimAmount = 2*premium
    tx = product.submitClaimWithDeferredResponse(policyId, claimAmount, {'from': customer})
    (claimId, requestId) = tx.return_value
    claim = instanceService.getClaim(policyId, claimId).dict()
    print(claim)

    assert claim["state"] ==  0 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    # check that it's not possible to create payout for claim in applied state
    payoutAmount = premium / 2
    with brownie.reverts("ERROR:POC-082:CLAIM_NOT_CONFIRMED"):
        product.createPayout(policyId, claimId, payoutAmount, {'from': productOwner})

    product.declineClaim(policyId, claimId, {'from': productOwner})

    claim = instanceService.getClaim(policyId, claimId).dict()
    assert claim["state"] ==  2 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    # check that it's not possible to create payout for claim in declined state
    with brownie.reverts("ERROR:POC-082:CLAIM_NOT_CONFIRMED"):
        product.createPayout(policyId, claimId, payoutAmount, {'from': productOwner})

def test_close_policy_with_declined_claim(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()

    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    claimAmount = 2*premium
    tx = product.submitClaimWithDeferredResponse(policyId, claimAmount, {'from': customer})
    (claimId, requestId) = tx.return_value
    claim = instanceService.getClaim(policyId, claimId).dict()
    print(claim)

    assert claim["state"] ==  0 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    product.declineClaim(policyId, claimId, {'from': productOwner})

    claim = instanceService.getClaim(policyId, claimId).dict()
    assert claim["state"] ==  2 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    product.closeClaim(policyId, claimId, {'from': productOwner})

    product.expire(policyId, {'from': productOwner})

    product.close(policyId, {'from': productOwner})


def test_payout_creation_for_confirmed_claim(
    instance: GifInstance, 
    gifTestProduct: GifTestProduct, 
    testCoin,
    owner: Account,
    customer: Account, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account
):
    instanceService = instance.getInstanceService()

    # prepare funded riskpool
    riskpool = gifTestProduct.getRiskpool().getContract()
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # build and use policy application
    product = gifTestProduct.getContract()
    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)
    
    claimAmount = 2*premium
    tx = product.submitClaimWithDeferredResponse(policyId, claimAmount, {'from': customer})
    (claimId, requestId) = tx.return_value
    claim = instanceService.getClaim(policyId, claimId).dict()
    print(claim)

    assert claim["state"] ==  0 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    product.confirmClaim(policyId, claimId, claimAmount, {'from': productOwner})

    claim = instanceService.getClaim(policyId, claimId).dict()
    assert claim["state"] ==  1 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    # check that it's possible to create payout for claim in confirmed state
    payoutAmount = claimAmount
    tx = product.createPayout(policyId, claimId, payoutAmount, {'from': productOwner})

    payoutId = tx.return_value
    payout = instanceService.getPayout(policyId, payoutId).dict()
    assert payout["state"] == 1 # enum PayoutState {Expected, PaidOut}
    assert payout["amount"] == payoutAmount

    claim = instanceService.getClaim(policyId, claimId).dict()
    assert claim["state"] ==  3 # enum ClaimState {Applied, Confirmed, Declined, Closed}

    # check that it's not possible to create payout for claim in closed state
    with brownie.reverts("ERROR:POC-082:CLAIM_NOT_CONFIRMED"):
        product.createPayout(policyId, claimId, payoutAmount, {'from': productOwner})


def create_policy(
    instance: GifInstance, 
    instanceOperator: Account,
    testProduct: GifTestProduct, 
    riskpoolWallet: Account,
    investor: Account,
    customer: Account, 
    coin,
    funding:int=10000,
    premium:int=100,
    sumInsured:int=5000 
):
    # prepare funded riskpool
    riskpool = testProduct.getRiskpool().getContract()
    fund_riskpool(instance, instanceOperator, riskpoolWallet, riskpool, investor, coin, funding)

    # build and use application to create policy
    product = testProduct.getContract()
    policy_id = apply_for_policy(instance, instanceOperator, product, customer, coin, premium, sumInsured)

    return policy_id
