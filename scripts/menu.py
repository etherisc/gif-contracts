from scripts.prompt import prompt
from scripts.interactive import (
    context,
    listComponents,
    createRisk,
    listRisks,
    selectTypeAndComponent
)

from scripts.deploy_ayii import (
    check_funds,
    amend_funds,
    deploy,
    deploy_product_with_oracle_riskpool,
    verify_deploy
)


def menu():
    run = True
    while run:
        options = {
            'Check Funds': {
                'function': check_funds,
                'args': [context.accounts, context.usdc]
            },
            'Amend Funds': {
                'function': amend_funds,
                'args': [context.accounts]
            },
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
            'Create Risk': createRisk,
            'List Risks': listRisks,
            'Select Type and Component': selectTypeAndComponent,
            'Exit': None
        }
        selection = prompt.dictMenu(options)
        run = selection != 'Exit'


menu()
