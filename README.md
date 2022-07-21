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
# --- imports ---
import uuid
from scripts.product import GifInstance, GifTestOracle, GifTestProduct, GifTestRiskpool
from scripts.util import s2b, b2s

# --- create instance and accounts setup ---
owner=accounts[0]
riskpoolKeeper=accounts[1]
oracleProvider=accounts[2]
productOwner=accounts[3]
customer=accounts[4]
customer2=accounts[5]
capitalOwner=accounts[6]
feeOwner=accounts[7]

# --- dummy coin setup ---
testCoin = TestCoin.deploy({'from': owner})
testCoin.transfer(riskpoolKeeper, 10**6, {'from': owner})
testCoin.transfer(customer, 10**6, {'from': owner})

# --- create instance setup ---
# instance=GifInstance(registryAddress='0xe7D6c54cf8Bd798edA9E9A3Aa094Fb01EF34C251', owner=owner)
instance = GifInstance(owner, feeOwner)
service = instance.getInstanceService()

instance.getRegistry()

# --- deploy product (and oracle) ---
capitalization = 10**18
gifRiskpool = GifTestRiskpool(instance, riskpoolKeeper, capitalOwner, capitalization)
gifOracle = GifTestOracle(instance, oracleProvider, name=str(uuid.uuid4())[:8])
gifProduct = GifTestProduct(
  instance,
  testCoin,
  capitalOwner,
  feeOwner,
  productOwner,
  gifOracle,
  gifRiskpool,
  name=str(uuid.uuid4())[:8])

riskpool = gifRiskpool.getContract()
oracle = gifOracle.getContract()
product = gifProduct.getContract()
treasury = instance.getTreasury()

# --- fund riskpool ---
testCoin.approve(treasury, 3000, {'from': riskpoolKeeper})
riskpool.createBundle(bytes(0), 1000, {'from':riskpoolKeeper})
riskpool.createBundle(bytes(0), 2000, {'from':riskpoolKeeper})

# --- policy application spec  ---
premium = 100
sumInsured = 1000
metaData = s2b('')
applicationData = s2b('')

# --- premium funding setup
treasuryAddress = instance.getTreasury().address
testCoin.transfer(customer, premium, {'from': owner})
testCoin.approve(treasuryAddress, premium, {'from': customer})

# --- create policies ---
txPolicy1 = product.applyForPolicy(premium, sumInsured, metaData, applicationData, {'from':customer})
txPolicy2 = product.applyForPolicy(premium, sumInsured, metaData, applicationData, {'from':customer})
```

```shell
from scripts.area_yield_index import GifAreaYieldIndexOracle, GifAreaYieldIndexProduct

#--- area yield product
collateralization = 10**18
gifTestRiskpool = GifTestRiskpool(
  instance, 
  riskpoolKeeper, 
  capitalOwner, 
  collateralization)

gifAreaYieldIndexOracle = GifAreaYieldIndexOracle(
  instance, 
  oracleProvider, 
  testCoin)

gifAreaYieldIndexProduct = GifAreaYieldIndexProduct(
  instance, 
  testCoin,
  capitalOwner,
  feeOwner,
  productOwner,
  riskpoolKeeper,
  customer,
  gifAreaYieldIndexOracle,
  gifTestRiskpool)


riskpool = gifTestRiskpool.getContract()
oracle = gifAreaYieldIndexOracle.getContract()
product = gifAreaYieldIndexProduct.getContract()

# funding of riskpool and customers
riskpoolWallet = capitalOwner
investor = riskpoolKeeper # investor=bundleOwner
insurer = productOwner # role required by area yield index product

token = gifAreaYieldIndexProduct.getToken()
riskpoolFunding = 200000
fund_riskpool(
    instance, 
    owner, 
    riskpoolWallet, 
    riskpool, 
    investor, 
    token, 
    riskpoolFunding)

customerFunding = 500
fund_customer(instance, owner, customer, token, customerFunding)
fund_customer(instance, owner, customer2, token, customerFunding)

uai1 = '1'
uai2 = '2'
cropId1 = 1001
cropId2 = 1002
premium1 = 200
premium2 = 300
sumInsured = 60000

token.allowance(customer, instance.getTreasury()) == customerFunding
token.allowance(customer2, instance.getTreasury()) == customerFunding

product.applyForPolicy(
    [
        create_peril(uai1, cropId1, premium1, sumInsured, customer),
        # create_peril(uai2, cropId2, premium2, sumInsured, customer2),
    ],
    {'from': insurer})

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
