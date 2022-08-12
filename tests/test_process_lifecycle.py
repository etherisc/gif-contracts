import brownie
import pytest

from web3 import Web3

from brownie.network.account import Account
from brownie import (
    interface,
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

def test_process_apply(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()

    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create application
    premium = 50
    sumInsured = 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin)

    metadata = policyController.getMetadata(processId).dict()
    application = policyController.getApplication(processId).dict()

    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        policy = policyController.getPolicy(processId).dict()

    assert metadata is not None
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 1
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 0
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    claimAmount = 42
    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer})


def test_process_apply_revoke(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account
):
    policyController = instance.getPolicy()

    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create application
    premium = 50
    sumInsured = 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin)

    with brownie.reverts('ERROR:PRD-001:INVALID_POLICY_OR_HOLDER_INVALID'):
        product.revoke(processId, {'from': riskpoolKeeper})

    product.revoke(processId, {'from': customer})

    metadata = policyController.getMetadata(processId).dict()
    application = policyController.getApplication(processId).dict()

    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        policy = policyController.getPolicy(processId).dict()

    assert metadata is not None
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 2
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 1
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    claimAmount = 42
    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer})


def test_process_apply_decline(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account,
):
    policyController = instance.getPolicy()

    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create application
    premium = 50
    sumInsured = 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin)

    with brownie.reverts('Ownable: caller is not the owner'):
        product.decline(processId, {'from': customer})

    product.decline(processId, {'from': productOwner})

    metadata = policyController.getMetadata(processId).dict()
    application = policyController.getApplication(processId).dict()

    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        policy = policyController.getPolicy(processId).dict()

    assert metadata is not None
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 2
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 3
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    claimAmount = 42
    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer})


def test_process_apply_underwrite_expire_close(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account,
):
    policyController = instance.getPolicy()

    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create application
    premium = 50
    sumInsured = 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin)

    #--- underwrite ----------------------------------------------------------#
    with brownie.reverts('Ownable: caller is not the owner'):
        product.underwrite(processId, {'from': customer})

    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        product.expire(processId, {'from': productOwner})

    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        product.close(processId, {'from': productOwner})

    product.underwrite(processId, {'from': productOwner})

    metadata = policyController.getMetadata(processId).dict()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert metadata is not None
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 1
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 2
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    assert policy is not None
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 0
    assert policy['createdAt'] >= application['createdAt']
    assert policy['updatedAt'] >= policy['createdAt']

    #--- expire --------------------------------------------------------------#
    with brownie.reverts('Ownable: caller is not the owner'):
        product.expire(processId, {'from': customer})

    with brownie.reverts('ERROR:POL-020:APPLICATION_STATE_INVALID'):
        product.underwrite(processId, {'from': productOwner})

    with brownie.reverts('ERROR:POC-019:APPLICATION_STATE_INVALID'):
        product.decline(processId, {'from': productOwner})

    with brownie.reverts('ERROR:PFD-001:POLICY_NOT_EXPIRED'):
        product.close(processId, {'from': productOwner})

    product.expire(processId, {'from': productOwner})

    metadata = policyController.getMetadata(processId).dict()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert metadata is not None
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 1
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 2
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    assert policy is not None
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 1
    assert policy['createdAt'] >= application['createdAt']
    assert policy['updatedAt'] >= policy['createdAt']

    #--- close ---------------------------------------------------------------#
    with brownie.reverts('Ownable: caller is not the owner'):
        product.close(processId, {'from': customer})

    with brownie.reverts('ERROR:POL-020:APPLICATION_STATE_INVALID'):
        product.underwrite(processId, {'from': productOwner})

    with brownie.reverts('ERROR:POC-019:APPLICATION_STATE_INVALID'):
        product.decline(processId, {'from': productOwner})

    with brownie.reverts('ERROR:PFD-001:POLICY_NOT_ACTIVE'):
        product.expire(processId, {'from': productOwner})

    product.close(processId, {'from': productOwner})

    metadata = policyController.getMetadata(processId).dict()
    application = policyController.getApplication(processId).dict()
    policy = policyController.getPolicy(processId).dict()

    assert metadata is not None
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 2
    assert metadata['createdAt'] > 0
    assert metadata['updatedAt'] >= metadata['createdAt']

    assert application is not None
    # ApplicationState {Applied, Revoked, Underwritten, Declined}
    assert application['state'] == 2
    assert application['createdAt'] >= metadata['createdAt']
    assert application['updatedAt'] >= application['createdAt']

    assert policy is not None
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 2
    assert policy['createdAt'] >= application['createdAt']
    assert policy['updatedAt'] >= policy['createdAt']


def test_process_policy_create_claims(
    instance: GifInstance, 
    testCoin,
    gifTestProduct: GifTestProduct, 
    productOwner: Account,
    riskpoolKeeper: Account,
    capitalOwner: Account,
    owner: Account,
    customer: Account,
):
    policyController = instance.getPolicy()

    product = gifTestProduct.getContract()
    riskpool = gifTestProduct.getRiskpool().getContract()

    # prepare funded riskpool
    initialFunding = 10000
    fund_riskpool(instance, owner, capitalOwner, riskpool, riskpoolKeeper, testCoin, initialFunding)

    # create application
    premium = 50
    sumInsured = 1000
    processId = create_application(customer, premium, sumInsured, instance, owner, product, testCoin)

    claimAmount = 20
    with brownie.reverts('ERROR:POC-052:POLICY_DOES_NOT_EXIST'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer}) 

    #--- underwrite + open claim ---------------------------------------------#
    product.underwrite(processId, {'from': productOwner})

    with brownie.reverts('ERROR:PRD-001:INVALID_POLICY_OR_HOLDER_INVALID'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': productOwner}) 

    tx = product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer})
    claimId = tx.return_value[0]
    print('processid:{}, claimid:{}, claimamount:{}'.format(processId, claimId, claimAmount))

    with brownie.reverts('Ownable: caller is not the owner'):
        product.confirmClaim(processId, claimId, claimAmount, {'from': customer})

    product.confirmClaim(processId, claimId, claimAmount, {'from': productOwner})

    metadata = policyController.getMetadata(processId).dict()
    policy = policyController.getPolicy(processId).dict()
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 1
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 0

    #--- expire --------------------------------------------------------------#
    product.expire(processId, {'from': productOwner})

    with brownie.reverts('ERROR:PFD-001:POLICY_NOT_ACTIVE'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer})

    metadata = policyController.getMetadata(processId).dict()
    policy = policyController.getPolicy(processId).dict()
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 1
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 1

    #--- process claims and close policy --------------------------------------#
    with brownie.reverts('ERROR:POC-028:POLICY_HAS_OPEN_CLAIMS'):
        product.close(processId, {'from': productOwner})
    
    with brownie.reverts('Ownable: caller is not the owner'):
        product.createPayout(processId, claimId, claimAmount, {'from': customer})

    product.createPayout(processId, claimId, claimAmount, {'from': productOwner})

    metadata = policyController.getMetadata(processId).dict()
    policy = policyController.getPolicy(processId).dict()
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 1
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 1

    product.close(processId, {'from': productOwner})

    with brownie.reverts('ERROR:PFD-001:POLICY_NOT_ACTIVE'):
        product.submitClaimWithDeferredResponse(processId, claimAmount, {'from': customer})

    metadata = policyController.getMetadata(processId).dict()
    policy = policyController.getPolicy(processId).dict()
    # IPolicy.PolicyFlowState {Started, Active, Finished}
    assert metadata['state'] == 2
    # PolicyState {Active, Expired, Closed}
    assert policy['state'] == 2


def create_application(customer, premium, sumInsured, instance, owner, product, erc20token):
    erc20token.transfer(customer, premium, {'from': owner})
    erc20token.approve(instance.getTreasury(), premium, {'from': customer})

    # create policy
    sumInsured = 1000
    policy_tx = product.newAppliation(
        premium,
        sumInsured,
        bytes(0),
        bytes(0),
        {'from': customer})

    processId = policy_tx.return_value
    return processId
