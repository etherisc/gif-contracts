import asyncio
import os

from brownie import (
    interface,
    network,
    accounts,
    InstanceService,
    InstanceOperatorService,
    ComponentOwnerService,
    AyiiProduct,
    AyiiOracle,
    AyiiRiskpool,
    ComponentController,
    UsdcAccounting,
)

from scripts.onepassword import signIn, getItem, getSecret, getLastItem
from scripts.deploy_ayii import (
    confirm,
    stakeholders_accounts_ganache,
    check_funds,
    amend_funds,
    deploy,
    from_registry,
    from_component,
    deploy_product_riskpool,
    verify_deploy,
)
from scripts.util import s2b, b2s, h2sLeft, contract_from_address, decodeEnum

#################################################################################
#
# Step 6 - avax-test end-to-end testing
#
#
# Step 6.1 - setup stakeholders + amounts
#
""" instanceOperator = a['instanceOperator']
investor = a['investor']
funding = 1000 * 10 ** usdc.decimals()  # 1000$

insurer = a['insurer']
customer = a['customer1']
"""
#
# Step 6. 2 - create risk (see https://lccc.etherisc.com/risks for risk data)
#
""" 
projectId = s2b('5413')
uaiId = s2b('125')
cropId = s2b('greengrams')

mul = product.getPercentageMultiplier()
(trigger, exit, tsi, aph) = (mul * 0.7, mul * 0, mul * 0.7, mul * 0.17)
tx = product.createRisk(projectId, uaiId, cropId, trigger,
                        exit, tsi, aph, {'from': insurer})
riskId = dict(tx.events['LogAyiiRiskDataCreated'])['riskId']
"""
#
# Step 6.3 - fund riskpool (bundle)
#
""" 
usdc.transfer(investor, funding, {'from': instanceOperator})
usdc.approve(instanceService.getTreasuryAddress(), funding, {'from': investor})

bundleId = riskpool.getActiveBundleId(0)
riskpool.fundBundle(bundleId, funding, {'from': investor})
"""
#
# Step 6.4 - create policy
#
""" 
usdc.transfer(customer, premium, {'from': instanceOperator})
usdc.approve(instanceService.getTreasuryAddress(), premium, {'from': customer})

tx = product.applyForPolicy(
    customer, premium, sumInsured, riskId, {'from': insurer})
policyId = dict(tx.events['LogAyiiPolicyCreated'])['policyId']
"""
#
# Step 6.5 - trigger oracle request
#
""" 
tx = product.triggerOracle(policyId, {'from': insurer})
requestId = dict(tx.events['LogAyiiRiskDataRequested'])['requestId']
"""
#
# Step 6.6 - check risk (aaay value according to expectations, responseAt > 0)
#
""" 
product.getRisk(riskId).dict()

"""
# Step 6.6 - check policies linked to risk
#

product.policies(riskId)
product.getPolicyId(riskId, 0)
instanceService.getPolicy(product.getPolicyId(riskId, 0)).dict()

#
# Step 6.7 - check riskpool funds and allowance
#

rpw = instanceService.getRiskpoolWallet(riskpool.getId())
usdc.balanceOf(rpw) / 10 ** usdc.decimals()
usdc.allowance(rpw, instanceService.getTreasuryAddress()) / 10 ** usdc.decimals()

#
# Step 6.8 - set/increase allowance for treasury if necessary
#

usdc.approve(instanceService.getTreasuryAddress(), sumInsured, {"from": rpw})

#
# Step 6.9 - process policies for risk (bach size = 1)
#


product.processPoliciesForRisk(riskId, 1, {"from": insurer})

#
# Step 6.10 - check payout
#

policyId = dict(history[-1].events["LogAyiiPolicyProcessed"])["policyId"]
instanceService.getApplication(policyId).dict()
instanceService.getPolicy(policyId).dict()
usdc.balanceOf(customer) / 10 ** usdc.decimals()
