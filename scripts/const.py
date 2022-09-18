from brownie import accounts

# === GIF platform ========================================================== #

# GIF release
GIF_RELEASE = '2.0.0'

# GIF modules
ACCESS_NAME = 'Access'
BUNDLE_NAME = 'Bundle'
COMPONENT_NAME = 'Component'

REGISTRY_CONTROLLER_NAME = 'RegistryController'
REGISTRY_NAME = 'Registry'

ACCESS_CONTROLLER_NAME = 'AccessController'
ACCESS_NAME = 'Access'

LICENSE_CONTROLLER_NAME = 'LicenseController'
LICENSE_NAME = 'License'

POLICY_CONTROLLER_NAME = 'PolicyController'
POLICY_NAME = 'Policy'

POLICY_DEFAULT_FLOW_NAME = 'PolicyDefaultFlow'
POOL_NAME = 'Pool'

QUERY_NAME = 'Query'

RISKPOOL_CONTROLLER_NAME = 'RiskpoolController'
RISKPOOL_NAME = 'Riskpool'
TREASURY_NAME = 'Treasury'

# GIF services
COMPONENT_OWNER_SERVICE_NAME = 'ComponentOwnerService'
PRODUCT_SERVICE_NAME = 'ProductService'
RISKPOOL_SERVICE_NAME = 'RiskpoolService'
ORACLE_SERVICE_NAME = 'OracleService'
INSTANCE_OPERATOR_SERVICE_NAME = 'InstanceOperatorService'
INSTANCE_SERVICE_NAME = 'InstanceService'

# === GIF testing =========================================================== #

# ZERO_ADDRESS = accounts.at('0x0000000000000000000000000000000000000000')
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
COMPROMISED_ADDRESS = '0x0000000000000000000000000000000000000013'

# TEST account values
ACCOUNTS_MNEMONIC = 'candy maple cake sugar pudding cream honey rich smooth crumble sweet treat'

# TEST oracle/rikspool/product values
PRODUCT_NAME = 'Test.Product'
RISKPOOL_NAME = 'Test.Riskpool'
ORACLE_NAME = 'Test.Oracle'
ORACLE_INPUT_FORMAT = '(bytes input)'
ORACLE_OUTPUT_FORMAT = '(bool output)'
