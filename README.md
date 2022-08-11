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

Examples below

* Polygon Testnet
* Celo Testnet
* Avalanche Testnet

### Polygon Testnet

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

### Celo Testnet

Some resources regarding Celo

* [Forno Hosted Node Service](https://docs.celo.org/developer-guide/forno)
* [Choosing a Celo Network](https://docs.celo.org/getting-started/choosing-a-network)
* [Alfajores Testnet Explorer](https://alfajores-blockscout.celo-testnet.org/)
* [Testnet Faucet](https://celo.org/developers/faucet)

Brownie add network setup for Celo
```bash
brownie networks add Celo celo-test name=Testnet host=https://alfajores-forno.celo-testnet.org chainid=44787
brownie networks add Celo celo-main name=Mainnet host=https://forno.celo.org chainid=42220
```

GIF Instance Deploy on Alfajores using Brownie console
```bash
brownie console --network=celo-test
>>>
```

Console commands
```bash
from scripts.instance import GifInstance

instanceOperator = accounts.add()
wallet = accounts.add()

instance=GifInstance(instanceOperator, instanceWallet=wallet, gasLimit=10000000)

instance.getRegistry()
```

Creating accounts with `accounts.add()` prints the mnemonic `'<mnemonic words>'` on the console. 
To recreate the same account use `accounts.from_mnemonic('<mnemonic words>')`.

Using the registry address `'<0xYouraddress>'` printed by `instance.getRegistry()` may be used to recreate the instance using GifInstance.

```bash
from scripts.instance import GifInstance
from scripts.util import s2b32

instance = GifInstance(owner, registryAddress='<0xYouraddress>')

instanceService = instance.getInstanceService()
instanceService.getInstanceId()
instanceService.getTreasuryAddress()
instanceService.getInstanceOperator()
instanceService.getInstanceWallet()

registry = instance.getRegistry()
registry.getContract(s2b32('Registry'))
registry.getContract(s2b32('InstanceService'))

>>> registry
<RegistryController Contract '0x3448A3f8c9541234AaFDf549d95698AF336D861c'>
```

Deploying the product

```bash
from scripts.ayii_product import GifAyiiRiskpool, GifAyiiOracle, GifAyiiProduct

erc20Token = TestCoin.deploy({'from': instanceOperator, 'gas_limit':10000000})
collateralization = instanceService.getFullCollateralizationLevel()

gifAyiiRiskpool = GifAyiiRiskpool(instance,erc20Token,riskpoolWallet,riskpoolKeeper,investor,collateralization,gasLimit=10000000)
gifAyiiOracle = GifAyiiOracle(instance,oracleProvider,gasLimit=10000000)
gifAyiiProduct = GifAyiiProduct(instance,erc20Token,productOwner,insurer,gifAyiiOracle,gifAyiiRiskpool,gasLimit=10000000)

product = gifAyiiProduct.getContract()
oracle = gifAyiiProduct.getOracle().getContract()
riskpool = gifAyiiProduct.getRiskpool().getContract()

product.getId()
oracle.getId()
riskpool.getId()

>>> product
<AyiiProduct Contract '0x6f9bF8D82A4934C7263909B701678742a136D733'>
>>> oracle
<AyiiOracle Contract '0x18021D1f791c018F8906C4FFe2185bAAC8099F34'>
>>> riskpool
<AyiiRiskpool Contract '0xf3e35154310CEC78c0AC70Ce5aFf3aa274056ADf'>
```
