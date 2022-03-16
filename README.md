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
```bash
from scripts.instance import GifInstance
from scripts.product import GifTestOracle
from scripts.product import GifTestProduct

print('accounts setup')
owner = accounts[0]
oracleOwner = accounts[1]
productOwner = accounts[2]
consumer1 = accounts[3]
consumer2 = accounts[4]

print('deploy gif instance')
instance = GifInstance(owner)

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

## Start a Local Ganache Chain

As the brownie image contains an embedded [Ganache](https://trufflesuite.com/ganache/index.html) chain we can also use this image to create Ganache container as shown below.

```bash
docker run -d -p 7545:7545 --name ganache brownie ganache-cli \
    --mnemonic "candy maple cake sugar pudding cream honey rich smooth crumble sweet treat" \
    --chainId 1234 \
    --port 7545 \
    -h "0.0.0.0"

```

A Metamask wallet can then connect to this local Ganache chain by adding a new network via Metamask "Settings", "Networks", "Add Network" and specifying its property values as shown below

* Network Name: `ganache` (just about any name will do)
* New RPC URL: `http://localhost:7545` (port number needs to match with docker/ganache "port" command line paramters above)
* Chain ID: `1234` (id needs to match with ganache commande line paramter "chainId" above)
* Currency Symbol: `ETH` (just about any symbol you like)



## Deploy GIF to Local Ganache

Add ganache to the networks available to Brownie.
Then, start Brownie console using the ganache network.
See Brownie [Network Managment](https://eth-brownie.readthedocs.io/en/stable/network-management.html) for details.

```bash
brownie networks add Local ganache host=http://host.docker.internal:7545 chainid=1234
brownie console --network ganache
```

Brownie recognizes the network and provides access to its accounts. 
We can use `accounts[0]` as the owner of the GIF instance to be deployed.
```bash
print('network {} is_connected {}'.format(network.show_active(), network.is_connected()))
print('\n'.join(['{} {:.4f} ETH'.format(acc.address, Wei(acc.balance()).to('ether')) for acc in accounts]))
owner = accounts[0]
```

An owner account may also be directly created from a seed phrase
```bash
owner = accounts.from_mnemonic('candy maple cake sugar pudding cream honey rich smooth crumble sweet treat')
```

A new GIF Instance can be deployed in the Brownie console.
```bash
from scripts.instance import GifInstance
instance = GifInstance(owner)
```

To deploy your own oracle and insurance product contracts to this new GIF instance you will need to record the following contract addresses.
```bash
instance.getOracleOwnerService().address
instance.getOracleService().address
instance.getProductService().address
```

For a known registry address a GIF instance object may be created as shown below.
```bash
>>> instance.getRegistry().address
'0xcfeD223fAb2A41b5a5a5F9AaAe2D1e882cb6Fe2D'

>>> myInstance = GifInstance(registry_address='0xcfeD223fAb2A41b5a5a5F9AaAe2D1e882cb6Fe2D')
```
