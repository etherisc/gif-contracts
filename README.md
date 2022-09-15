![Build](https://github.com/etherisc/gif-contracts/actions/workflows/runtests.yml/badge.svg)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![](https://dcbadge.vercel.app/api/server/Qb6ZjgE8?style=flat)](https://discord.gg/Qb6ZjgE8)

https://discord.gg/

# GIF Core Contracts

This repository holds the GIF core contracts and tools to develop, test and deploy GIF instances.

## Clone Repository

```bash
git clone https://github.com/etherisc/gif-contracts.git
cd gif-contracts
```

## Fully configure IDE 

To use our fully configured IDE see the instructions at [https://github.com/etherisc/gif-sandbox/blob/master/docs/development_environment.md](https://github.com/etherisc/gif-sandbox/blob/master/docs/development_environment.md). 
In this case you can skip the next two steps as the _devcontainer_ is based on the (updated) _brownie_ image. 

## Create Brownie Docker Image

[Brownie](https://eth-brownie.readthedocs.io/en/stable) is used for development of the contracts in this repository.

Alternatively to installing a python development environment and the brownie framework, wokring with Brownie is also possible via Docker.

For building the `brownie` docker image used in the samples below, follow the instructions in [gif-brownie](https://github.com/etherisc/gif-brownie).


## Run Brownie Container

```bash
docker run -it --rm -v $PWD:/projects brownie
```

## Compile the GIF Core Contracts

Inside the Brownie container compile the contracts/interfaces

```bash
brownie compile --all
```

## Run GIF Unit Tests

Run the unit tests
```bash
brownie test
```

or to execute the tests in parallel

```
brownie test -n auto
```

_Note_: Should the tests fail when running them in parallel, the test execution probably creates too much load on the system. 
In this case replace the `auto` keyword in the command with the number of executors (use at most the number of CPU cores available on your system). 

## Deployment to Live Networks

Deployments to live networks can be done with brownie console as well.

Example for the deployment to Polygon test

```bash
brownie console --network polygon-test

# in console
owner = accounts.add()
# will generate a new account and prints the mnemonic here

owner.address
# will print the owner address that you will need to fund first
```

Use Polygon test [faucet](https://faucet.polygon.technology/) to fund the owner address
```python
from scripts.instance import GifInstance

# publishes source code to the network
instance = GifInstance(owner, publishSource=True)

# after the deploy print the registry address
instance.getRegistry().address
```

After a successful deploy check the registry contract in the Polygon [testnet explorer](https://mumbai.polygonscan.com/).

To check all contract addresses you may use the instance python script inside the brownie container as follows.
```bash
# 0x2852593b21796b549555d09873155B25257F6C38 is the registry contract address
brownie run scripts/instance.py dump_sources 0x2852593b21796b549555d09873155B25257F6C38 --network polygon-test
```

## Full Deployment with Example Product

Before attempting to deploy the setup on a life chain ensure that the
`instanceOperator` has sufficient funds to cover the setup.

For testnets faucet funds may be used

* [avax-test (Fuji (C-Chain))](https://faucet.avax.network/)
* [polygon-test](https://faucet.polygon.technology/)

Using the ganache scenario shown below ensures that all addresses used are sufficiently funded.

```python
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

# for ganche the command below may be used
# for other chains, use accounts.add() and record the mnemonics
a = stakeholders_accounts_ganache()

# check_funds checks which stakeholder accounts need funding for the deploy
# also, it checks if the instanceOperator has a balance that allows to provided
# the missing funds for the other accounts
check_funds(a)

# amend_funds transfers missing funds to stakeholder addresses using the
# avaulable balance of the instanceOperator
amend_funds(a)

d = deploy_setup_including_token(a)

(
componentOwnerService,customer1,customer2,erc20Token,instance,instanceOperator,instanceOperatorService,instanceService,
instanceWallet,insurer,investor,oracle,oracleProvider,processId1,processId2,product,productOwner,riskId1,riskId2,
riskpool,riskpoolKeeper,riskpoolWallet
)=(
d['componentOwnerService'],d['customer1'],d['customer2'],d['erc20Token'],d['instance'],d['instanceOperator'],d['instanceOperatorService'],d['instanceService'],
d['instanceWallet'],d['insurer'],d['investor'],d['oracle'],d['oracleProvider'],d['processId1'],d['processId2'],d['product'],d['productOwner'],d['riskId1'],d['riskId2'],
d['riskpool'],d['riskpoolKeeper'],d['riskpoolWallet']
)

# the deployed setup can now be used
# example usage
instanceOperator
instance.getRegistry()

instanceService.getChainName()
instanceService.getInstanceId()

product.getId()
b2s(product.getName())

customer1
instanceService.getMetadata(processId1)
instanceService.getApplication(processId1)
instanceService.getPolicy(processId1)

tx = product.triggerOracle(processId1, {'from': insurer})
```

For a first time setup on a live chain the setup below can be used.

IMPORTANT: Make sure to write down the generated mnemonics for the
stakeholder accounts. To reuse the same accounts replace `accounts.add` 
with `accounts.from_mnemonic` using the recorded mnemonics.

```python
instanceOperator=accounts.add()
instanceWallet=accounts.add()
oracleProvider=accounts.add()
chainlinkNodeOperator=accounts.add()
riskpoolKeeper=accounts.add()
riskpoolWallet=accounts.add()
investor=accounts.add()
productOwner=accounts.add()
insurer=accounts.add()
customer1=accounts.add()
customer2=accounts.add()

a = {
  'instanceOperator': instanceOperator,
  'instanceWallet': instanceWallet,
  'oracleProvider': oracleProvider,
  'chainlinkNodeOperator': chainlinkNodeOperator,
  'riskpoolKeeper': riskpoolKeeper,
  'riskpoolWallet': riskpoolWallet,
  'investor': investor,
  'productOwner': productOwner,
  'insurer': insurer,
  'customer1': customer1,
  'customer2': customer2,
}
```

To interact with an existing setup use the following helper methods as shown below.

```python
from scripts.deploy_ayii import (
    from_registry,
    from_component,
)

from scripts.instance import (
  GifInstance, 
)

from scripts.util import (
  s2b, 
  b2s, 
  contract_from_address,
)

# for the case of a known registry address, 
# eg '0xE7eD6747FaC5360f88a2EFC03E00d25789F69291'
(instance, product, oracle, riskpool) = from_registry('0xE7eD6747FaC5360f88a2EFC03E00d25789F69291')

# or for a known address of a component, eg
# eg product address '0xF039D8acecbB47763c67937D66A254DB48c87757'
(instance, product, oracle, riskpool) = from_component('0xF039D8acecbB47763c67937D66A254DB48c87757')
```

## Run linter

Linter findings are shown automatically in vscode. To execute it manually, run the following command:

```bash
solhint contracts/**/*.sol
```
and including _prettier_ formatting 

```bash
solhint --config .solhint.prettier.json contracts/**/*.sol
```

