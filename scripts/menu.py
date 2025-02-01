from scripts.prompt import prompt
from scripts.interactive import (
    context,
    listComponents,
    createRiskInteractive,
    listRisks,
    listRiskShort,
    selectTypeAndComponent,
    fundBundle,
    getFeeSpecification,
    createPolicyInteractive,
    triggerOracleInteractive,
    cancelOracleRequestInteractive,
    doSetClfConsumer,
    fullCycle,
    initializeContext,
)

from scripts.deploy_ayii import (
    check_funds,
    amend_funds,
    deploy,
    deploy_product_with_oracle_riskpool,
    verify_deploy,
)


def executeFunctionOrObject(param):
    if callable(param):
        # If param is a function, call it without parameters
        return param()
    elif isinstance(param, dict) and "function" in param and "args" in param:
        # If param is a dictionary with 'function' and 'args', execute the function with arguments
        func = param["function"]
        args = param["args"]

        if not callable(func):
            raise ValueError("'function' in the dictionary must be callable")
        if not isinstance(args, (list, tuple)):
            raise ValueError("'args' in the dictionary must be a list or tuple")

        return func(*args)


def menu():
    run = True
    while run:
        options = {
            "Check Funds": {
                "function": check_funds,
                "args": [context.accounts, context.usdc],
            },
            "Amend Funds": {"function": amend_funds, "args": [context.accounts]},
            "Deploy": {"function": deploy, "args": [context.accounts, context.usdc]},
            "Deploy Product, Oracle and Riskpool": {
                "function": deploy_product_with_oracle_riskpool,
                "args": [
                    context.registry,
                    context.accounts,
                    context.usdc,
                    context.fullCollateralizationLevel,
                ],
            },
            "Verify Deploy": {
                "function": verify_deploy,
                "args": [
                    context.accounts,
                    context.usdc,
                    context.registry,
                    context.riskpoolId,
                    context.oracleId,
                    context.productId,
                ],
            },
            "Context": context.printContext,
            "Initialize Context": initializeContext,
            "Accounts": context.printAccounts,
            "List Components": listComponents,
            "Create Risk": createRiskInteractive,
            "List Risks": listRisks,
            "List Risk Short": listRiskShort,
            "Select Type and Component": selectTypeAndComponent,
            "Fund Bundle": fundBundle,
            "Create Policy": createPolicyInteractive,
            "Trigger Oracle": triggerOracleInteractive,
            "Cancel Oracle Request": cancelOracleRequestInteractive,
            "Show Fee Specification": getFeeSpecification,
            "Set Clf Consumer": doSetClfConsumer,
            "Full Cycle": fullCycle,
            "Exit": None,
        }
        selection = prompt.dictMenu(options)
        if selection is None:
            run = False
        else:
            executeFunctionOrObject(selection)


menu()
