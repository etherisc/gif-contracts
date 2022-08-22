import brownie
import pytest

from brownie.network.account import Account
from brownie import (
    interface,
    Wei,
    TestProduct,
    TestRiskpool,
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

def test_request_for_inactive_oracle(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner,
    oracleProvider,
    riskpoolKeeper: Account,
    owner: Account,
    customer: Account,
    feeOwner: Account,
    capitalOwner: Account
):
    componentOwnerService = instance.getComponentOwnerService()
    instanceService = instance.getInstanceService()

    product = gifTestProduct.getContract()
    oracle = gifTestProduct.getOracle().getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    initialFunding = 10000
    bundleOwner = riskpoolKeeper
    fund_riskpool(instance, owner, capitalOwner, riskpool, bundleOwner, testCoin, initialFunding)
    
    # transfer premium funds to customer and create allowance
    premium = 200
    testCoin.transfer(customer, premium, {'from': owner})
    testCoin.approve(instance.getTreasury(), premium, {'from': customer})

    # create test policy before oracle is paused
    sumInsured = 3000
    tx = product.applyForPolicy(
        premium,
        sumInsured,
        bytes(0),
        bytes(0),
        {'from': customer})
    
    # returns policy id
    policyId = tx.return_value

    # check claim subission work for active oracle
    oracleId = oracle.getId()
    assert instanceService.getComponentState(oracleId) == 3

    # check normal claim submission works
    claimAmount = 50
    product.submitClaim(
        policyId,
        claimAmount,
        {'from': customer})

    # check claim submission with deferred response works
    tx = product.submitClaimWithDeferredResponse(
        policyId,
        claimAmount,
        {'from': customer})

    print(tx.info())
    (claimId, requestId) = tx.return_value

    # pause oracle (oracle no longer active)
    componentOwnerService.pause(
        oracleId, 
        {'from': oracleProvider})

    # assert oracle is paused
    assert instanceService.getComponentState(oracleId) == 4

    # check creating new claim no longer works
    with brownie.reverts("ERROR:QUC-042:ORACLE_NOT_ACTIVE"):
        product.submitClaim(
            policyId,
            claimAmount,
            {'from': customer})

    # check oracle no longer accepts response
    with brownie.reverts("ERROR:QUC-042:ORACLE_NOT_ACTIVE"):
        isLossEvent = True
        oracle.respond(requestId, isLossEvent)

    # unpause oracle (oracle active again)
    componentOwnerService.unpause(
        oracleId, 
        {'from': oracleProvider})

    # assert oracle is active agains
    assert instanceService.getComponentState(oracleId) == 3

    # check oracle accepts response in active state
    tx = oracle.respond(requestId, isLossEvent)
    print(tx.info())

