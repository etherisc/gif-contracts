import brownie
import pytest

from brownie import (
    TestOracle,
    TestProduct,
    TestCompromisedProduct,
)

from scripts.instance import GifInstance

from scripts.product import (
    GifTestOracle,
    GifTestProduct,
    GifTestRiskpool,
)

from scripts.setup import (
    fund_riskpool,
    apply_for_policy,
)

from scripts.util import s2b32


# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_use_compromised_product(
    instance: GifInstance, 
    owner,
    gifTestProduct: GifTestProduct, 
    testCoin,
    productOwner, 
    capitalOwner, 
    riskpoolKeeper,
    customer
):
    instanceService = instance.getInstanceService()

    assert instanceService.oracles() == 1
    assert instanceService.products() == 1
    assert instanceService.riskpools() == 1

    product = gifTestProduct.getContract()
    assert product.getId() == 3
    assert product.getState() == 3

    riskpool = gifTestProduct.getRiskpool().getContract()
    assert riskpool.getId() == 2
    assert riskpool.getState() == 3

    # asssertions for initialized product
    assert instanceService.getComponentToken(product.getId()) == testCoin
    assert instanceService.getRiskpoolWallet(riskpool.getId()) == capitalOwner

    # fund riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # fund customer and apply for policy
    premium = 100
    sumInsured = 5000
    policyId = apply_for_policy(instance, owner, product, customer, testCoin, premium, sumInsured)

    policy = instanceService.getPolicy(policyId)
    print(policy)

    # deploy compromised product
    compromisedProduct = TestCompromisedProduct.deploy(
        product.getName(), 
        product.getToken(),
        product.getId(),
        riskpool.getId(),
        instance.getRegistry(),
        {'from': customer})

    # assert name, id and state match with the target product
    assert compromisedProduct.getName() == product.getName()
    assert compromisedProduct.getId() == product.getId()
    assert compromisedProduct.getState() == product.getState()

    # attempt to create a new policy with the compromised product
    with brownie.reverts("ERROR:CCR-007:COMPONENT_UNKNOWN"):
        apply_for_policy(instance, owner, compromisedProduct, customer, testCoin, premium, sumInsured)

    # attempt to create a new claim for an existing policy with the compromised product
    with brownie.reverts("ERROR:CCR-007:COMPONENT_UNKNOWN"):
        claimAmount = 5000
        compromisedProduct.submitClaim(policyId, claimAmount, {'from': customer}) 