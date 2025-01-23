from brownie import (
    AyiiProduct,
    AyiiOracle,
    AyiiRiskpool,
    GenericOracle,
    GenericRiskpool,
    GenericProduct
)

from scripts.deploy_ayii import (
    check_funds,
    amend_funds,
    deploy,
    deploy_product_with_oracle_riskpool,
    verify_deploy
)
from scripts.util import (contract_from_address, decodeEnum)

from scripts.prompt import Prompt
from scripts.context import Context

prompt = Prompt()

context = Context()


def menu():
    run = True
    while run:
        options = {
            'Check Funds': {'function': check_funds, 'args': [context.accounts, context.usdc]},
            'Amend Funds': {'function': amend_funds, 'args': [context.accounts]},
            'Deploy': {
                'function': deploy,
                'args': [
                    context.accounts,
                    context.usdc
                ]},
            'Deploy Product, Oracle and Riskpool': {
                'function': deploy_product_with_oracle_riskpool,
                'args': [
                    context.registry,
                    context.accounts,
                    context.usdc,
                    context.fullCollateralizationLevel
                ]},
            'Verify Deploy': {
                'function': verify_deploy,
                'args': [
                    context.accounts,
                    context.usdc,
                    context.registry,
                    context.riskpoolId,
                    context.oracleId,
                    context.productId
                ]
            },
            'Context': context.printContext,
            'List Components': listComponents,
            'Exit': lambda: False
        }
        selection = prompt.dict_menu(options)
        run = selection != 'Exit'


def listComponents():
    componentController = context.componentController
    components = componentController.components()
    for componentIndex in range(1, components+1):
        componentAddress = componentController.getComponent(componentIndex)
        componentType = componentController.getComponentType(componentIndex)
        print(
            f'{componentIndex:>3}: {componentAddress} : {decodeEnum("ComponentType", componentType)}')


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


menu()
