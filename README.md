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
instanceOperator=accounts[0]
instanceWallet=accounts[1]
oracleProvider=accounts[2]
chainlinkNodeOperator=accounts[3]
riskpoolKeeper=accounts[4]
riskpoolWallet=accounts[5]
investor=accounts[6]
productOwner=accounts[7]
insurer=accounts[8]
customer=accounts[9]
customer2=accounts[10]

# --- dummy coin setup ---
testCoin = TestCoin.deploy({'from': instanceOperator})
testCoin.transfer(investor, 10**6, {'from': instanceOperator})
testCoin.transfer(customer, 10**6, {'from': instanceOperator})

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

Brownie console commands to deploy/use the example product

```shell
from scripts.area_yield_index import GifAreaYieldIndexOracle, GifAreaYieldIndexProduct

from scripts.setup import fund_riskpool, fund_customer
from tests.test_area_yield import create_peril 

#--- area yield product
collateralization = 10**18
gifTestRiskpool = GifTestRiskpool(
  instance, 
  riskpoolKeeper, 
  capitalOwner, 
  collateralization)

gifAreaYieldIndexOracle = GifAreaYieldIndexOracle(
  instance, 
  oracleProvider)

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

# batched policy creation
perils = [
        create_peril(uai1, cropId1, premium1, sumInsured, customer),
        create_peril(uai2, cropId2, premium2, sumInsured, customer2),
    ]

tx = product.applyForPolicy(perils, {'from': insurer})

# returns tuple for created process ids
processIds = tx.return_value

product.triggerResolutions(uai1, {'from': insurer})

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

## Full Deployment with Example Product

```bash
# --- ganache accounts setup -------------
instanceOperator=accounts[0]
instanceWallet=accounts[1]
oracleProvider=accounts[2]
chainlinkNodeOperator=accounts[3]
riskpoolKeeper=accounts[4]
riskpoolWallet=accounts[5]
investor=accounts[6]
productOwner=accounts[7]
insurer=accounts[8]
customer=accounts[9]
customer2=accounts[10]

# --- test net accounts setup -------------
instanceOperator=accounts.add()
instanceWallet=accounts.add()
oracleProvider=accounts.add()
chainlinkNodeOperator=accounts.add()
riskpoolKeeper=accounts.add()
riskpoolWallet=accounts.add()
investor=accounts.add()
productOwner=accounts.add()
insurer=accounts.add()
customer=accounts.add()
customer2=accounts.add()

# --- optional erc20 token deploy  -------------
# skip this if the value token for the product and
# riskpool is already deployed

erc20Token = TestCoin.deploy({'from': instanceOperator})

# --- gif instance deploy deploy  -------------
# if the gif instance is already deployed replace
# the command below with the following line
# instance = GifInstance(registryAddress='0x...')
from scripts.instance import GifInstance

instance = GifInstance(instanceOperator, instanceWallet=instanceWallet)
instanceService = instance.getInstanceService()

instance.getRegistry()

# --- example product deploy deploy  -------------
from scripts.ayii_product import GifAyiiProductComplete

ayiiDeploy = GifAyiiProductComplete(instance, productOwner, insurer, oracleProvider, chainlinkNodeOperator, riskpoolKeeper, investor, erc20Token, riskpoolWallet)

ayiiProduct = ayiiDeploy.getProduct()
ayiiOracle = ayiiProduct.getOracle()
ayiiRiskpool = ayiiProduct.getRiskpool()

product = ayiiProduct.getContract()
oracle = ayiiOracle.getContract()
riskpool = ayiiRiskpool.getContract()
```

## Interact with Example Product

```bash
from scripts.util import s2b32

#--- setup risk (group policy) definition -----------------
projectId = s2b32('test-project')
uaiId = s2b32('some-region-id')
cropId = s2b32('maize')

multiplier = product.getPercentageMultiplier()
trigger = 0.75 * multiplier
exit_ = 0.1 * multiplier # exit is needed to exit the console
tsi = 0.9 * multiplier
aph = 2.0 * multiplier

tx = product.createRisk(projectId, uaiId, cropId, trigger, exit_, tsi, aph,
  {'from': insurer})
riskId = tx.return_value

#--- fund investor which in turn creates a risk bundle ---
bundleInitialFunding=1000000
erc20Token.transfer(investor, bundleInitialFunding, {'from': instanceOperator})
erc20Token.approve(instance.getTreasury(), bundleInitialFunding, {'from': investor})

applicationFilter = bytes(0)
riskpool.createBundle(applicationFilter, bundleInitialFunding, {'from': investor})

instanceService.getBundle(1)
erc20Token.balanceOf(riskpoolWallet.address)
erc20Token.balanceOf(instanceWallet.address)

# approvel for payouts/defunding
maxUint256 = 2**256-1
erc20Token.approve(instance.getTreasury(), maxUint256, {'from': riskpoolWallet})

#--- fund customer which in turn applies for a policy ---
customerFunding=1000
erc20Token.transfer(customer, customerFunding, {'from': instanceOperator})

premium = 100
sumInsured = 20000

tx = product.applyForPolicy(customer, premium, sumInsured, riskId, 
  {'from': insurer})
policyId = tx.return_value

# print data for bundle and newly created policy
riskpool.getTotalValueLocked() # shows the 20000 of locked capital to cover the sum insurance
instanceService.getBundle(1) # bundle state, locked capital (20000 to cover sum insured)
instanceService.getMetadata(policyId) # policy owner and product id
instanceService.getApplication(policyId) # premium, sum insurec, risk id
instanceService.getPolicy(policyId) # policy state, premium payed (=0 for now)

# premium payment in bits, allowance set for full premium
erc20Token.approve(instance.getTreasury(), 100, {'from': customer})

# first installment
product.collectPremium(policyId, 40, {'from':insurer})
instanceService.getPolicy(policyId)

# second installment
product.collectPremium(policyId, 60, {'from':insurer})
instanceService.getPolicy(policyId)

# TODO add:
# - oracle call
# - policy processing
# - payout to customer
# - definding back to inverster
```