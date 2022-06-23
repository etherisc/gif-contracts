from brownie import accounts

# === GIF platform ========================================================== #

# GIF release
GIF_RELEASE = '1.2.0'

# GIF modules
ACCESS_NAME = 'Access'

REGISTRY_CONTROLLER_NAME = 'RegistryController'
REGISTRY_NAME = 'Registry'

ACCESS_CONTROLLER_NAME = 'AccessController'
ACCESS_NAME = 'Access'

LICENSE_CONTROLLER_NAME = 'LicenseController'
LICENSE_NAME = 'License'

POLICY_CONTROLLER_NAME = 'PolicyController'
POLICY_NAME = 'Policy'

QUERY_CONTROLLER_NAME = 'QueryController'
QUERY_NAME = 'Query'

# GIF services
COMPONENT_OWNER_SERVICE_NAME = 'ComponentOwnerService'
PRODUCT_SERVICE_NAME = 'ProductService'
ORACLE_SERVICE_NAME = 'OracleService'
ORACLE_OWNER_SERVICE_NAME = 'OracleOwnerService'
POLICY_FLOW_DEFAULT_NAME = 'PolicyFlowDefault'
INSTANCE_OPERATOR_SERVICE_NAME = 'InstanceOperatorService'
INSTANCE_SERVICE_NAME = 'InstanceService'

# === GIF testing =========================================================== #

# ZERO_ADDRESS = accounts.at('0x0000000000000000000000000000000000000000')
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

# TEST account values
ACCOUNTS_MNEMONIC = 'candy maple cake sugar pudding cream honey rich smooth crumble sweet treat'
INSTANCE_OPERATOR_ACCOUNT_NO = 0
ORACLE_OWNER_ACCOUNT_NO = 1
PRODUCT_OWNER_ACCOUNT_NO = 2
CUSTOMER_ACCOUNT_NO = 3
CUSTOMER2_ACCOUNT_NO = 4

# TEST oracle/product values
ORACLE_NAME = 'Test.Oracle'
ORACLE_INPUT_FORMAT = '(bytes input)'
ORACLE_OUTPUT_FORMAT = '(bool output)'
ORACLE_ID = 1

PRODUCT_NAME = 'Test.Product'
PRODUCT_ID = 1
