from brownie import (
    AyiiProduct,
    AyiiOracle,
    AyiiRiskpool,
    GenericOracle,
    GenericRiskpool,
    GenericProduct,
)

from scripts.deploy_ayii import verify_deploy, printBundle
from scripts.util import contract_from_address, decodeEnum, b2s, s2b, utcStr, fromWei
from scripts.context import Context
from scripts.prompt import prompt

context = Context()
a = context.accounts


def listComponents():
    components = context.getComponents()
    for componentIndex, componentData in enumerate(components):
        info = (
            f"{componentIndex:>3} : "
            f'{componentData["typeStr"].ljust(12)}\n'
            f'      Address:      {componentData["address"]}\n'
            f'      Status:       {componentData["stateStr"].ljust(12)}'
        )
        if componentData["type"] == 0:  # Oracle
            pass
        elif componentData["type"] == 1:  # Product
            info += (
                "\n"
                f'      Risks:        {componentData["additionalData"]["risks"]}\n'
                f'      RiskpoolId:   {componentData["additionalData"]["riskpoolId"]}\n'
                f'      Token:        {componentData["additionalData"]["erc20Token"]}\n'
                f'      Policies:     {componentData["additionalData"]["policies"]}\n'
                f'      Applications: {componentData["additionalData"]["applications"]}'
            )
        elif componentData["type"] == 2:  # Riskpool
            info += (
                "\n"
                f'      Token:        {componentData["additionalData"]["erc20Token"]}\n'
                f'      Capital(wei): {componentData["additionalData"]["capital"]}\n'
                f'      Bundles:      {componentData["additionalData"]["bundles"]}'
            )

        print(info)


def selectComponent(type):
    components = context.getComponents(type)
    ct = [context.oracle.address, context.product.address, context.riskpool.address]
    options = [
        f"{i:>3}: {component['address']} {'< in context' if component['address'] in ct else ''}"
        for i, component in enumerate(components, 1)
    ]
    options.append("Cancel")
    print(f'Select {decodeEnum("ComponentType", type)}:')
    selection = options.index(prompt.menu(options))
    if selection == len(options) - 1:
        return None
    return components[selection]


def selectComponentType():
    options = [f"{i}: {decodeEnum('ComponentType', i)}" for i in range(3)]
    options.append("Cancel")
    print("Select Component Type:")
    selection = options.index(prompt.menu(options))
    if selection == len(options) - 1:
        return None
    return selection


def selectTypeAndComponent():
    type = selectComponentType()
    if type is None:
        return
    component = selectComponent(type)
    if component is None:
        return
    print(
        (
            f'Selected: {component["typeStr"]} '
            f'Address: {component["address"]} '
            f'State: {component["stateStr"]}'
        )
    )
    if component["type"] == 0:  # Oracle
        context.oracle = contract_from_address(GenericOracle, component["address"])
    elif component["type"] == 1:  # Product
        context.product = contract_from_address(AyiiProduct, component["address"])
    elif component["type"] == 2:  # Riskpool
        context.riskpool = contract_from_address(AyiiRiskpool, component["address"])


def verifyDeploy():
    verify_deploy(
        context.accounts,
        context.usdc,
        context.registry,
        context.riskpoolId.getId(),
        context.oracle.getId(),
        context.product.getId(),
    )


def setFeeCapital():

    instanceOperatorService = context.instanceOperatorService
    feeRiskpool = instanceOperatorService.createFeeSpecification(
        context.riskpool.getId(),
        context.feeCapitalFix,
        context.feeCapitalPercentage,
        b"",
    )
    instanceOperatorService.setCapitalFees(
        feeRiskpool, {"from": context.instanceOperator}
    )


def setFeePremium():

    instanceOperatorService = context.instanceOperatorService
    feeProduct = instanceOperatorService.createFeeSpecification(
        context.product.getId(),
        context.feePremiumFix,
        context.feePremiumPercentage,
        b"",
    )

    instanceOperatorService.setPremiumFees(
        feeProduct, {"from": context.instanceOperator}
    )


def getFeeSpecification():
    print(dict(context.treasury.getFeeSpecification(context.riskpoolId)))
    print(dict(context.treasury.getFeeSpecification(context.productId)))


def getComponent(componentId):
    address = context.instanceService.getComponent(componentId)
    type = context.instanceService.getComponentType(componentId)
    contract = [GenericOracle, GenericRiskpool, GenericProduct][type]
    return contract_from_address(contract, address)


def createRisk():
    insurer = a["insurer"]
    projectId = prompt.enterString("Enter the project ID:", r"^\d{1,10}$")
    uaiId = prompt.enterString("Enter the UAI ID:", r"^\d{1,10}$")
    cropId = prompt.enterString("Enter the crop ID:", r"^[a-zA-Z]+$")
    trigger = prompt.enterFloat("Enter the trigger:", 0, 1)
    exit = prompt.enterFloat("Enter the exit:", 0, 1)
    tsi = prompt.enterFloat("Enter the TSI:", 0, 1)
    aph = prompt.enterFloat("Enter the APH:", 0, 1)
    print("Creating risk:")
    print(f"projectId: {projectId}")
    print(f"uaiId    : {uaiId}")
    print(f"cropId   : {cropId}")
    print(f"Trigger  : {trigger}")
    print(f"Exit     : {exit}")
    print(f"TSI      : {tsi}")
    print(f"APH      : {aph}")
    if not prompt.confirm("create risk"):
        return

    mul = context.product.getPercentageMultiplier()
    (trigger, exit, tsi, aph) = (mul * trigger, mul * exit, mul * tsi, mul * aph)
    tx = context.product.createRisk(
        s2b(projectId),
        s2b(uaiId),
        s2b(cropId),
        trigger,
        exit,
        tsi,
        aph,
        {"from": insurer},
    )
    riskId = dict(tx.events["LogAyiiRiskDataCreated"])["riskId"]
    print(f"Risk created with ID: {riskId}")


def getRisks():
    product = context.product
    riskCount = product.risks()
    result = []
    for riskIndex in range(0, riskCount):
        riskId = product.getRiskId(riskIndex)
        risk = product.getRisk(riskId)
        mul = product.getPercentageMultiplier()
        result.append(
            {
                "riskId": riskId,
                "risk": risk,
                "mul": mul,
                "trigger": risk["trigger"] / mul,
                "exit": risk["exit"] / mul,
                "tsi": risk["tsi"] / mul,
                "aph": risk["aph"] / mul,
                "aaay": risk["aaay"] / mul,
                "payoutPercentage": risk["payoutPercentage"] / mul,
            }
        )
    return result


def listRisks():
    riskData = getRisks()
    riskCount = len(riskData)
    for riskIndex in range(0, riskCount):
        data = riskData[riskIndex]
        risk = data["risk"]
        print(
            (
                f"Index:       {riskIndex}\n"
                f'RiskId:      {data["riskId"]}\n'
                f'ProjectId:   {b2s(risk["projectId"]).ljust(10)}\n'
                f'UAI:         {b2s(risk["uaiId"]).ljust(10)}\n'
                f'CropId:      {b2s(risk["cropId"]).ljust(10)}\n'
                f'Trigger:     {data["trigger"]:.5f}\n'
                f'Exit:        {data["exit"]:.5f}\n'
                f'TSI:         {data["tsi"]:.5f}\n'
                f'APH:         {data["aph"]:.5f}\n'
                f'AAAY:        {data["aaay"]:.5f}\n'
                f'Payout Pct:  {data["payoutPercentage"]:.5f}\n'
                f'Triggered:   {risk["requestTriggered"]}\n'
                f'RequestId:   {risk["requestId"]}\n'
                f'Response at: {utcStr(risk["responseAt"])}\n'
                f'Created:     {utcStr(risk["createdAt"])}\n'
                f'Updated:     {utcStr(risk["updatedAt"])}\n'
            )
        )


def listRiskShort():
    riskData = getRisks()
    return [
        f"{i:>3}: "
        f'{b2s(risk["risk"]["projectId"]).ljust(10)} '
        f'{b2s(risk["risk"]["uaiId"]).ljust(10)} '
        f'{b2s(risk["risk"]["cropId"]).ljust(10)} '
        f'{risk["trigger"]:.5f} '
        f'{risk["exit"]:.5f} '
        f'{risk["tsi"]:.5f} '
        f'{risk["aph"]:.5f} '
        for i, risk in enumerate(riskData)
    ]


def getPolicies():
    product = context.product
    riskCount = product.risks()
    result = []
    for riskIndex in range(0, riskCount):
        riskId = product.getRiskId(riskIndex)
        policyCount = product.policies(riskId)
        for policyIndex in range(0, policyCount):
            policyId = product.getPolicyId(riskId, policyIndex)
            policy = context.instanceService.getPolicy(policyId)
            result.append({"policyId": policyId, "policy": policy, "riskId": riskId})
    return result


def selectPolicy():
    policies = getPolicies()
    if len(policies) == 0:
        print("No policies available")
        return None
    options = [f"{i:>3}: {p['policyId']}" for i, p in enumerate(policies)]
    options.append("Cancel")
    print("Select Policy:")
    selection = options.index(prompt.menu(options))
    if selection == len(options) - 1:
        return None
    return policies[selection]


def selectBundle():
    bundles = context.riskpool.bundles()
    if bundles == 0:
        print("No bundles available")
        return None
    elif bundles == 1:
        print("Only one bundle available - selecting it")
        return 0
    options = [f"{i:>3}: {context.riskpool.getBundle(i)}" for i in range(bundles)]
    options.append("Cancel")
    print("Select Bundle:")
    selection = options.index(prompt.menu(options))
    if selection == len(options) - 1:
        return None
    return selection


def selectRisk():
    risks = context.product.risks()
    if risks == 0:
        print("No risks available")
        return None
    elif risks == 1:
        print("Only one risk available - selecting it")
        return 0
    options = listRiskShort()
    options.append("Cancel")
    print("Select Risk:")
    selection = options.index(prompt.menu(options))
    if selection == len(options) - 1:
        return None
    return context.product.getRiskId(selection)


def fundBundle():
    bundleId = selectBundle()
    if bundleId is None:
        return
    printBundle(context.riskpool, bundleId)

    bundle = context.riskpool.getBundle(bundleId)
    if bundle["state"] != 0:
        print("Bundle is not active - aborting")
        return

    funding = prompt.enterCurrency(
        "Enter the funding amount:", context.usdc.decimals(), lowerBound=0
    )

    if funding == 0:
        return
    if not prompt.confirm(
        f"Fund bundle with {fromWei(funding, context.usdc.decimals())} USDC"
    ):
        return

    investor = context.accounts["investor"]
    if context.usdc.balanceOf(investor) < funding:
        print("Insufficient funds at investor - supplying more")
        context.usdc.transfer(investor, funding, {"from": context.instanceOperator})
    if (
        context.usdc.allowance(investor, context.instanceService.getTreasuryAddress())
        < funding
    ):
        print("Approving USDC transfer from investor to treasury")
        context.usdc.approve(
            context.instanceService.getTreasuryAddress(), funding, {"from": investor}
        )

    context.riskpool.fundBundle(bundle["id"], funding, {"from": investor})
    print("Bundle successfully funded:")
    printBundle(context.riskpool, bundleId)


def createPolicy():

    riskId = selectRisk()
    if riskId is None:
        return

    premium = prompt.enterCurrency(
        "Enter the premium amount:", context.usdc.decimals(), lowerBound=0
    )
    if premium == 0:
        return

    sumInsured = prompt.enterCurrency(
        "Enter the sum insured amount:", context.usdc.decimals(), lowerBound=0
    )
    if sumInsured == 0:
        return

    customer = context.accounts["customer1"]
    insurer = context.accounts["insurer"]

    if context.usdc.balanceOf(customer) < premium:
        print("Insufficient funds at customer - supplying more")
        context.usdc.transfer(customer, premium, {"from": context.instanceOperator})
    if (
        context.usdc.allowance(customer, context.instanceService.getTreasuryAddress())
        < premium
    ):
        print("Approving USDC transfer from customer to treasury")
        context.usdc.approve(
            context.instanceService.getTreasuryAddress(), premium, {"from": customer}
        )

    print(f"Creating policy for riskId: {riskId}")
    tx = context.product.applyForPolicy(
        customer, premium, sumInsured, riskId, {"from": insurer}
    )
    policyId = dict(tx.events["LogAyiiPolicyCreated"])["policyId"]
    print(f"Policy created with ID: {policyId}")


def triggerOracle():
    policy = selectPolicy()
    if policy is None:
        return
    policyId = policy["policyId"]
    insurer = context.accounts["insurer"]
    if not prompt.confirm(f"Trigger oracle request for policyId: {policyId}"):
        return
    print(f"Triggering oracle request for policyId: {policyId}")
    tx = context.product.triggerOracle(policyId, {"from": insurer})
    requestId = dict(tx.events["LogAyiiRiskDataRequested"])["requestId"]
    print(f"Oracle request triggered with requestId: {requestId}")
