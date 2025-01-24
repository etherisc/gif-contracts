from brownie import (
    AyiiProduct,
    AyiiOracle,
    AyiiRiskpool,
    GenericOracle,
    GenericRiskpool,
    GenericProduct
)

from scripts.deploy_ayii import (verify_deploy)
from scripts.util import (contract_from_address, decodeEnum, b2s, s2b, utcStr)
from scripts.context import Context
from scripts.prompt import prompt

context = Context()
a = context.accounts


def listComponents():
    components = context.getComponents()
    for componentIndex, componentData in enumerate(components):
        info = (
            f'{componentIndex:>3} : '
            f'{componentData["typeStr"].ljust(12)}\n'
            f'      Address:      {componentData["address"]}\n'
            f'      Status:       {componentData["stateStr"].ljust(12)}'
        )
        if componentData["type"] == 0:  # Oracle
            pass
        elif componentData["type"] == 1:  # Product
            info += (
                '\n'
                f'      Risks:        {componentData["additionalData"]["risks"]}\n'
                f'      Policies:     {componentData["additionalData"]["policies"]}\n'
                f'      Applications: {componentData["additionalData"]["applications"]}'
            )
        elif componentData["type"] == 2:  # Riskpool
            info += (
                '\n'
                f'      Bundles:      {componentData["additionalData"]["bundles"]}'
            )

        print(info)


def selectComponent(type):
    components = context.getComponents(type)
    options = [
        f"{i:>3}: {component['address']}" for i, component in enumerate(components, 1)
    ]
    options.append('Cancel')
    print(f'Select {decodeEnum("ComponentType", type)}:')
    selection = options.index(prompt.menu(options))
    if selection == len(options) - 1:
        return None
    return components[selection]


def selectComponentType():
    options = [
        f"{i}: {decodeEnum('ComponentType', i)}" for i in range(3)
    ]
    options.append('Cancel')
    print('Select Component Type:')
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
    print((
        f'Selected: {decodeEnum("ComponentType", component[1])} '
        f'Address: {component[0]} '
        f'State: {decodeEnum("ComponentState", component[2])}'
    ))
    if component[1] == 0:
        context.oracle = contract_from_address(GenericOracle, component[0])
    elif component[1] == 1:
        context.product = contract_from_address(AyiiProduct, component[0])
    elif component[1] == 2:
        context.riskpool = contract_from_address(AyiiRiskpool, component[0])


def setRiskpool(address):
    context.riskpool = contract_from_address(AyiiRiskpool, address)


def setOracle(address):
    context.oracle = contract_from_address(AyiiOracle, address)


def setProduct(address):
    context.product = contract_from_address(AyiiProduct, address)


def verifyDeploy():
    verify_deploy(
        context.accounts,
        context.usdc,
        context.registry,
        context.riskpoolId.getId(),
        context.oracle.getId(),
        context.product.getId()
    )


def setFeeCapital():

    instanceOperatorService = context.instanceOperatorService
    feeRiskpool = instanceOperatorService.createFeeSpecification(
        context.riskpool.getId(),
        context.feeCapitalFix,
        context.feeCapitalPercentage,
        b''
    )
    instanceOperatorService.setCapitalFees(
        feeRiskpool, {'from': context.instanceOperator})


def setFeePremium():

    instanceOperatorService = context.instanceOperatorService
    feeProduct = instanceOperatorService.createFeeSpecification(
        context.product.getId(),
        context.feePremiumFix,
        context.feePremiumPercentage,
        b''
    )

    instanceOperatorService.setPremiumFees(
        feeProduct, {'from': context.instanceOperator})


def getFeeSpecification():
    print(dict(context.treasury.getFeeSpecification(context.riskpoolId)))
    print(dict(context.treasury.getFeeSpecification(context.productId)))


def getComponent(componentId):
    address = context.instanceService.getComponent(componentId)
    type = context.instanceService.getComponentType(componentId)
    contract = [GenericOracle, GenericRiskpool, GenericProduct][type]
    return contract_from_address(contract, address)


def createRisk():
    insurer = a['insurer']
    projectId = prompt.enterString("Enter the project ID:", r'^\d{1,10}$')
    uaiId = prompt.enterString("Enter the UAI ID:", r'^\d{1,10}$')
    cropId = prompt.enterString("Enter the crop ID:", r'^[a-zA-Z]+$')
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
        s2b(projectId), s2b(uaiId), s2b(cropId),
        trigger, exit, tsi, aph,
        {'from': insurer}
    )
    riskId = dict(tx.events['LogAyiiRiskDataCreated'])['riskId']
    print(f"Risk created with ID: {riskId}")


def listRisks():
    product = context.product
    riskCount = product.risks()
    for riskIndex in range(0, riskCount):
        riskId = product.getRiskId(riskIndex)
        risk = product.getRisk(riskId)
        mul = product.getPercentageMultiplier()
        print((
            f'Index:       {riskIndex}\n'
            f'RiskId:      {riskId}\n'
            f'ProjectId:   {b2s(risk["projectId"]).ljust(10)}\n'
            f'UAI:         {b2s(risk["uaiId"]).ljust(10)}\n'
            f'CropId:      {b2s(risk["cropId"]).ljust(10)}\n'
            f'Trigger:     {risk["trigger"]/mul:.5f}\n'
            f'Exit:        {risk["exit"]/mul:.5f}\n'
            f'TSI:         {risk["tsi"]/mul:.5f}\n'
            f'APH:         {risk["aph"]/mul:.5f}\n'
            f'AAAY:        {risk["aaay"]/mul:.5f}\n'
            f'Payout Pct:  {risk["payoutPercentage"]/mul:.5f}\n'
            f'Triggered:   {risk["requestTriggered"]}\n'
            f'RequestId:   {risk["requestId"]}\n'
            f'Response at: {utcStr(risk["responseAt"])}\n'
            f'Created:     {utcStr(risk["createdAt"])}\n'
            f'Updated:     {utcStr(risk["updatedAt"])}\n'
        ))
