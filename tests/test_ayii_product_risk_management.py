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
def test_risk_creation_happy_case(
    instance: GifInstance, 
    gifAyiiProduct: GifAyiiProduct,
    insurer,
):
    product = gifAyiiProduct.getContract()
    multiplier = product.getPercentageMultiplier()

    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = s2b32('1234')
    cropId = s2b32('mixed')

    trigger = 0.75
    exit = 0.1
    tsi = 0.9
    aph = 1.9

    riskId = create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi, aph)
    risk = product.getRisk(riskId)

    assert risk[0] == riskId
    assert risk[1] == projectId
    assert risk[2] == uaiId
    assert risk[3] == cropId
    assert risk[4] == multiplier * trigger
    assert risk[5] == multiplier * exit
    assert risk[6] == multiplier * tsi
    assert risk[7] == multiplier * aph

    # attempt to modify risk
    with brownie.reverts('ERROR:AYI-001:RISK_ALREADY_EXISTS'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi, aph * 0.9)


def test_risk_creation_validation(
    instance: GifInstance, 
    gifAyiiProduct: GifAyiiProduct,
    insurer,
):
    product = gifAyiiProduct.getContract()
    multiplier = product.getPercentageMultiplier()

    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = s2b32('1234')
    cropId = s2b32('mixed')

    # valid parameters
    trigger = 0.75
    exit = 0.1
    tsi = 0.9
    aph = 1.9

    # check trigger validation: trigger <= 1.0
    valid_trigger = 1.0
    bad_trigger = 1.1

    create_risk(product, insurer, multiplier, s2b32('1'), uaiId, cropId, valid_trigger, exit, tsi, aph)

    with brownie.reverts('ERROR:AYI-040:RISK_TRIGGER_TOO_LARGE'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, bad_trigger, exit, tsi, aph)

    # check trigger validation: trigger > exit
    bad_trigger1 = exit
    bad_trigger2 = exit - 0.1

    with brownie.reverts('ERROR:AYI-041:RISK_TRIGGER_NOT_LARGER_THAN_EXIT'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, bad_trigger1, exit, tsi, aph)

    with brownie.reverts('ERROR:AYI-041:RISK_TRIGGER_NOT_LARGER_THAN_EXIT'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, bad_trigger2, exit, tsi, aph)

    # check exit validation: 0 <= exit <= 0.2
    valid_exit = 0
    bad_exit = 0.2 + 0.001

    create_risk(product, insurer, multiplier, s2b32('2'), uaiId, cropId, trigger, valid_exit, tsi, aph)

    with brownie.reverts('ERROR:AYI-042:RISK_EXIT_TOO_LARGE'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, bad_exit, tsi, aph)

    # check tsi validation: 0.5 <= tsi
    valid_tsi = 0.5
    bad_tsi = 0.49

    create_risk(product, insurer, multiplier, s2b32('3'), uaiId, cropId, trigger, exit, valid_tsi, aph)

    with brownie.reverts('ERROR:AYI-043:RISK_TSI_TOO_SMALL'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, bad_tsi, aph)

    # check tsi validation: tsi <= 1.0
    exit_modified = 0.0
    valid_tsi = 1.0
    bad_tsi = 1.1

    create_risk(product, insurer, multiplier, s2b32('4'), uaiId, cropId, trigger, exit_modified, valid_tsi, aph)

    with brownie.reverts('ERROR:AYI-044:RISK_TSI_TOO_LARGE'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit_modified, bad_tsi, aph)

    # check tsi validation: tsi + exit <= 1.0
    exit_modified = 0.15
    valid_tsi = 0.85
    bad_tsi = 0.9

    create_risk(product, insurer, multiplier, s2b32('5'), uaiId, cropId, trigger, exit_modified, valid_tsi, aph)

    with brownie.reverts('ERROR:AYI-045:RISK_TSI_EXIT_SUM_TOO_LARGE'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit_modified, bad_tsi, aph)

    # check tsi validation: tsi + exit <= 1.0
    valid_aph_1 = 0.0001
    valid_aph_2 = 15.0
    bad_aph_1 = 0.0
    bad_aph_2 = 15.1

    create_risk(product, insurer, multiplier, s2b32('6'), uaiId, cropId, trigger, exit, tsi, valid_aph_1)
    create_risk(product, insurer, multiplier, s2b32('7'), uaiId, cropId, trigger, exit, tsi, valid_aph_2)

    with brownie.reverts('ERROR:AYI-046:RISK_APH_ZERO_INVALID'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi, bad_aph_1)

    with brownie.reverts('ERROR:AYI-047:RISK_APH_TOO_LARGE'):
        create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi, bad_aph_2)


def test_risk_adjustment_happy_case(
    instance: GifInstance, 
    gifAyiiProduct: GifAyiiProduct,
    insurer,
):
    product = gifAyiiProduct.getContract()
    multiplier = product.getPercentageMultiplier()

    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = s2b32('1234')
    cropId = s2b32('mixed')

    trigger = 0.75
    exit = 0.1
    tsi = 0.9
    aph = 1.9

    riskId = create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi, aph)

    trigger_new = 0.765 * multiplier
    exit_new = 0.123 * multiplier
    tsi_new = 0.876 * multiplier
    aph_new = 1.123 * multiplier

    tx = product.adjustRisk(riskId, trigger_new, exit_new, tsi_new, aph_new, {'from': insurer})
    print(tx.info())

    risk = product.getRisk(riskId)
    assert risk[0] == riskId
    assert risk[1] == projectId
    assert risk[2] == uaiId
    assert risk[3] == cropId
    assert risk[4] == trigger_new
    assert risk[5] == exit_new
    assert risk[6] == tsi_new
    assert risk[7] == aph_new


def test_risk_adjustment_with_policy(
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

    customerFunding = 500
    fund_customer(instance, instanceOperator, customer, token, customerFunding)

    multiplier = product.getPercentageMultiplier()
    projectId = s2b32('2022.kenya.wfp.ayii')
    uaiId = s2b32('1234')
    cropId = s2b32('mixed')

    trigger = 0.75
    exit = 0.1
    tsi = 0.9
    aph = 1.9
    riskId = create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi, aph)

    premium = 300
    sumInsured = 2000
    tx = product.applyForPolicy(customer, premium, sumInsured, riskId, {'from': insurer})
    processId = tx.return_value

    assert product.policies(riskId) == 1
    assert product.getPolicyId(riskId, 0) == processId

    trigger_new = 0.765 * multiplier
    exit_new = 0.123 * multiplier
    tsi_new = 0.876 * multiplier
    aph_new = 1.123 * multiplier

    with brownie.reverts('ERROR:AYI-003:RISK_WITH_POLICIES_NOT_ADJUSTABLE'):
        product.adjustRisk(riskId, trigger_new, exit_new, tsi_new, aph_new, {'from': insurer})


def create_risk(product, insurer, multiplier, projectId, uaiId, cropId, trigger, exit, tsi_at_exit, aph):

    tx = product.createRisk(
        projectId,
        uaiId,
        cropId,
        trigger * multiplier,
        exit * multiplier,
        tsi_at_exit * multiplier,
        aph * multiplier,
        {'from': insurer }
    )

    return tx.return_value
