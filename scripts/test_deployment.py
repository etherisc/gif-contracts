from scripts.deploy_ayii import (
    stakeholders_accounts_ganache,
    check_funds,
    amend_funds,
    deploy,
    deploy_setup_including_token,
    from_registry,
    from_component,
)

from scripts.instance import (
    GifInstance, 
    dump_sources
)

from scripts.util import (
    s2b, 
    b2s, 
    contract_from_address,
)

from brownie import (
    TestCoin
)

def main():
    # for ganche the command below may be used
    # for other chains, use accounts.add() and record the mnemonics
    a = stakeholders_accounts_ganache()

    # deploy TestCoin with instanceOperator 
    usdc = TestCoin.deploy({'from': a['instanceOperator']})

    # check_funds checks which stakeholder accounts need funding for the deploy
    # also, it checks if the instanceOperator has a balance that allows to provided
    # the missing funds for the other accounts
    check_funds(a, usdc)

    # amend_funds transfers missing funds to stakeholder addresses using the
    # avaulable balance of the instanceOperator
    amend_funds(a)

    d = deploy_setup_including_token(a, usdc)

    instance = d['instance']
    registry = instance.getRegistry()

    for i in range(registry.contracts()):
        print(b2s(registry.contractName(i)))

    # assert number of contracts and some contract names 
    assert 32 == registry.contracts()
    assert 'InstanceOperatorService' == b2s(registry.contractName(0))
    assert 'Registry' == b2s(registry.contractName(1))
    assert 'RegistryController' == b2s(registry.contractName(2))
    assert 'BundleToken' == b2s(registry.contractName(3))
    assert 'RiskpoolToken' == b2s(registry.contractName(4))
    assert 'AccessController' == b2s(registry.contractName(5))
    assert 'Access' == b2s(registry.contractName(6))
    assert 'PolicyDefaultFlow' == b2s(registry.contractName(21))
    assert 'InstanceOperatorServiceControlle' == b2s(registry.contractName(31))

