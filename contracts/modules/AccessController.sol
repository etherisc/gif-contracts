// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IAccess.sol";

import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";

/**
 * @dev The provided smart contract is called "AccessController" and is written in Solidity. It implements the "IAccess" interface and inherits from the "CoreController" contract and the "AccessControlEnumerable" contract. The contract provides functionalities for access control and role management.
 *
 * Roles:
 *
 * The contract defines three role identifiers as bytes32 constants:
 * 1. PRODUCT_OWNER_ROLE: Represents the role of a product owner.
 * 2. ORACLE_PROVIDER_ROLE: Represents the role of an oracle provider.
 * 3. RISKPOOL_KEEPER_ROLE: Represents the role of a risk pool keeper.
 *
 * State Variables:
 *
 * - `validRole`: A mapping that stores the validity of each role. It maps a role identifier (bytes32) to a boolean value indicating whether the role is valid.
 * - `_defaultAdminSet`: A boolean flag indicating whether the default admin role has been set.
 *
 * Functions:
 *
 * - `_afterInitialize()`: Internal function called after contract initialization, which adds the product owner, oracle provider, and risk pool keeper roles. It calls the `_populateValidRoles()` function.
 * - `_getName()`: Internal pure function that returns the name of the contract as a bytes32 value.
 * - `setDefaultAdminRole(address defaultAdmin)`: Sets the default admin role for the Access Control List (ACL) by granting the DEFAULT_ADMIN_ROLE to the specified address. It can only be called once, and emits a `RoleGranted` event.
 * - `grantRole(bytes32 role, address principal)`: Grants a specific role to a principal (address). The caller must be an instance operator. It checks the validity of the role and calls the `grantRole()` function from the `AccessControl` contract.
 * - `revokeRole(bytes32 role, address principal)`: Revokes a specific role from a principal. The caller must be an instance operator. It calls the `revokeRole()` function from the `AccessControl` contract.
 * - `renounceRole(bytes32 role, address principal)`: Removes a principal from a specific role in the access control list (ACL) of the contract. It calls the `renounceRole()` function from the `AccessControl` contract.
 * - `addRole(bytes32 role)`: Adds a new role to the Access Control List. The caller must be an instance operator. It checks if the role is already valid and adds it to the `validRole` mapping.
 * - `invalidateRole(bytes32 role)`: Invalidates a role by marking it as not valid. The caller must be an instance operator. It checks if the role is valid and updates the `validRole` mapping.
 * - `hasRole(bytes32 role, address principal)`: Checks if a given principal has a specific role. It returns a boolean value indicating whether the principal has the specified role.
 * - `getDefaultAdminRole()`: Returns the bytes32 value of the DEFAULT_ADMIN_ROLE.
 * - `getProductOwnerRole()`: Returns the bytes32 value of the PRODUCT_OWNER_ROLE.
 * - `getOracleProviderRole()`: Returns the bytes32 value of the ORACLE_PROVIDER_ROLE.
 * - `getRiskpoolKeeperRole()`: Returns the bytes32 value of the RISKPOOL_KEEPER_ROLE.
 * - `_populateValidRoles()`: Internal function that populates the `validRole` mapping with the roles considered valid for the contract. It sets the validity of the predefined roles to true.
 *
 * Modifiers:
 *
 * - `onlyInstanceOperator`: A modifier that restricts access to functions to only instance operators.
 *
 * Overall, the contract provides a flexible access control mechanism by defining roles and
 * allowing the assignment, revocation, and validation of roles by instance operators.
 * It also sets a default admin role and manages the validity of roles through the `validRole` mapping.
 */

contract AccessController is IAccess, CoreController, AccessControlEnumerable {
    // 0xe984cfd1d1fa34f80e24ddb2a60c8300359d79eee44555bc35c106eb020394cd
    bytes32 public constant PRODUCT_OWNER_ROLE =
        keccak256("PRODUCT_OWNER_ROLE");

    // 0xd26b4cd59ffa91e4599f3d18b02fcd5ffb06e03216f3ee5f25f68dc75cbbbaa2
    bytes32 public constant ORACLE_PROVIDER_ROLE =
        keccak256("ORACLE_PROVIDER_ROLE");

    // 0x3c4cdb47519f2f89924ebeb1ee7a8a43b8b00120826915726460bb24576012fd
    bytes32 public constant RISKPOOL_KEEPER_ROLE =
        keccak256("RISKPOOL_KEEPER_ROLE");

    mapping(bytes32 => bool) public validRole;

    bool private _defaultAdminSet;

    function _afterInitialize() internal override {
        // add product owner, oracle provider and riskpool keeper roles
        _populateValidRoles();
    }

    function _getName() internal pure override returns (bytes32) {
        return "Access";
    }

    // IMPORTANT check the setting of the default admin role
    // after the deployment of a GIF instance.
    // this method is called in the deployment of
    // the instance operator proxy/controller
    function setDefaultAdminRole(address defaultAdmin) external {
        require(!_defaultAdminSet, "ERROR:ACL-001:ADMIN_ROLE_ALREADY_SET");
        _defaultAdminSet = true;

        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
    }

    //--- manage role ownership ---------------------------------------------//
    function grantRole(
        bytes32 role,
        address principal
    ) public override(IAccessControl, IAccess) onlyInstanceOperator {
        require(validRole[role], "ERROR:ACL-002:ROLE_UNKNOWN_OR_INVALID");
        AccessControl.grantRole(role, principal);
    }

    function revokeRole(
        bytes32 role,
        address principal
    ) public override(IAccessControl, IAccess) onlyInstanceOperator {
        AccessControl.revokeRole(role, principal);
    }

    function renounceRole(
        bytes32 role,
        address principal
    ) public override(IAccessControl, IAccess) {
        AccessControl.renounceRole(role, principal);
    }

    //--- manage roles ------------------------------------------------------//
    function addRole(bytes32 role) public override onlyInstanceOperator {
        require(!validRole[role], "ERROR:ACL-003:ROLE_EXISTING_AND_VALID");
        validRole[role] = true;
    }

    function invalidateRole(bytes32 role) public override onlyInstanceOperator {
        require(validRole[role], "ERROR:ACL-004:ROLE_UNKNOWN_OR_INVALID");
        validRole[role] = false;
    }

    function hasRole(
        bytes32 role,
        address principal
    ) public view override(IAccessControl, IAccess) returns (bool) {
        return super.hasRole(role, principal);
    }

    function getDefaultAdminRole() public pure override returns (bytes32) {
        return DEFAULT_ADMIN_ROLE;
    }

    function getProductOwnerRole() public pure override returns (bytes32) {
        return PRODUCT_OWNER_ROLE;
    }

    function getOracleProviderRole() public pure override returns (bytes32) {
        return ORACLE_PROVIDER_ROLE;
    }

    function getRiskpoolKeeperRole() public pure override returns (bytes32) {
        return RISKPOOL_KEEPER_ROLE;
    }

    function _populateValidRoles() private {
        validRole[PRODUCT_OWNER_ROLE] = true;
        validRole[ORACLE_PROVIDER_ROLE] = true;
        validRole[RISKPOOL_KEEPER_ROLE] = true;
    }
}
