# GIF Core Contracts

This repository holds the GIF core contracts and tools to develop, test and deploy GIF instances.

## Clone Repository

```bash
git clone https://github.com/etherisc/gif-contracts.git
cd gif-contracts
```

## Create Brownie Docker Image

[Brownie](https://eth-brownie.readthedocs.io/en/stable) is used for development of the contracts in this repository.

Alternatively to installing a python development environment and the brownie framework, wokring with Brownie is also possible via Docker.
For this, build the brownie Docker image as shown below.
The Dockerfile in this repository is a trimmed down version from [Brownie Github]((https://github.com/eth-brownie/brownie))

```bash
docker build -t brownie .
```

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

## Deploy and Use GIF Interactively

Start the Brownie console that shows the `>>>` console prompt.
```bash
brownie console
```

Example session inside the Brownie console

* Deployment of a GIF instance
* Deployment and usage of Test oracle and product

```bash
from scripts.instance import GifInstance
from scripts.product import GifTestOracle
from scripts.product import GifTestProduct
from scripts.util import s2b32

print('instance deployment')
owner = accounts[0]
instance = GifInstance(owner)

print('accounts setup')
oracleOwner = accounts[1]
productOwner = accounts[2]
consumer1 = accounts[3]
consumer2 = accounts[4]

print('deploy gif test oracle and product')
oracle = GifTestOracle(instance, oracleOwner)
product = GifTestProduct(instance, oracle, productOwner)
productContract = product.getProductContract()

print('check balances')
Wei(consumer1.balance()).to('ether')
Wei(productContract.balance()).to('ether')

print('create policies')
premium = Wei('0.5 ether')
tx1 = productContract.applyForPolicy({'from': consumer1, 'amount': premium})
tx2 = productContract.applyForPolicy({'from': consumer1, 'amount': premium})
policyId1 = tx1.return_value
policyId2 = tx2.return_value
print('ids of created policies:\n{}\n{}'.format(policyId1, policyId2))

print('balances after policy creation')
Wei(consumer1.balance()).to('ether')
Wei(productContract.balance()).to('ether')

print('show events and subcalls for policy creation')
tx1.events
tx1.subcalls

print('submit claims')
tx_claim1 = productContract.submitClaim(policyId1, {'from': consumer1})
tx_claim2 = productContract.submitClaim(policyId2, {'from': consumer1})

print('show events for claim submission')
tx_claim1.events
tx_claim2.events

pc = instance.getPolicyController()
pc.getPolicy(policyId1)
pc.getPolicy(policyId2)
pc.getClaim(policyId1, 0)
pc.getClaim(policyId2, 0)
```

In case things go wrong you can information regarding the last transaction via history.

```bash
history[-1].info()
```

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
```bash
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
