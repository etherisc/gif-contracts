from brownie import accounts

# === GIF platform ========================================================== #

# GIF release
GIF_RELEASE = '1.6.0'

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

POLICY_FLOW_DEFAULT_NAME = 'PolicyFlowDefault'
POOL_NAME = 'Pool'

QUERY_CONTROLLER_NAME = 'QueryController'
QUERY_NAME = 'Query'

RISKPOOL_CONTROLLER_NAME = 'RiskpoolController'
RISKPOOL_NAME = 'Riskpool'
TREASURY_NAME = 'Treasury'

# GIF services
COMPONENT_OWNER_SERVICE_NAME = 'ComponentOwnerService'
PRODUCT_SERVICE_NAME = 'ProductService'
RISKPOOL_SERVICE_NAME = 'RiskpoolService'
ORACLE_SERVICE_NAME = 'OracleService'
POLICY_FLOW_DEFAULT_NAME = 'PolicyFlowDefault'
INSTANCE_OPERATOR_SERVICE_NAME = 'InstanceOperatorService'
INSTANCE_SERVICE_NAME = 'InstanceService'

# === GIF testing =========================================================== #

# ZERO_ADDRESS = accounts.at('0x0000000000000000000000000000000000000000')
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

# TEST account values
ACCOUNTS_MNEMONIC = 'candy maple cake sugar pudding cream honey rich smooth crumble sweet treat'
INSTANCE_OPERATOR_ACCOUNT_NO = 0
RISKPOOL_KEEPER_ACCOUNT_NO = 1
ORACLE_PROVIDER_ACCOUNT_NO = 2
PRODUCT_OWNER_ACCOUNT_NO = 3
CUSTOMER_ACCOUNT_NO = 4
CAPITAL_ACCOUNT_NO = 5
FEE_ACCOUNT_NO = 6

# TEST oracle/rikspool/product values
RISKPOOL_NAME = 'Test.Riskpool'
RIKSPOOL_ID = 0

ORACLE_NAME = 'Test.Oracle'
ORACLE_INPUT_FORMAT = '(bytes input)'
ORACLE_OUTPUT_FORMAT = '(bool output)'
ORACLE_ID = 1

PRODUCT_NAME = 'Test.Product'
PRODUCT_ID = 2
