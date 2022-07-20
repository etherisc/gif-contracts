import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    Wei,
    TestProduct,
)

from scripts.const import (
    PRODUCT_NAME,
    PRODUCT_ID,
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

    # TODO verify balance after application

    # ensure successful policy creation
    assert product.policies() == 1
    assert product.claims() == 0

    # only policy holder may sumit a claim
    claimAmount = 300
    with brownie.reverts():
        product.submitClaim(
            policy_id, 
            claimAmount, 
            {'from': productOwner})

    # submit claim
    claim_tx = product.submitClaim(
        policy_id, 
        claimAmount, 
        {'from': customer})
    
    assert product.claims() == 1
    assert product.getClaimId(policy_id) == 0


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


def _create_policy(
    instance: GifInstance, 
    owner: Account,
    gifTestProduct: GifTestProduct, 
    customer: Account, 
    testCoin,
    funding: int,
    premium: int,
    sumInsured: int 
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

    return policy_id
