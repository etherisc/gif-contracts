// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IAccess.sol";

import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";


contract AccessController is 
    IAccess, 
    CoreController,
    AccessControlEnumerable
 {

    // 0xe984cfd1d1fa34f80e24ddb2a60c8300359d79eee44555bc35c106eb020394cd
    bytes32 public constant PRODUCT_OWNER_ROLE = keccak256("PRODUCT_OWNER_ROLE");

    // 0xd26b4cd59ffa91e4599f3d18b02fcd5ffb06e03216f3ee5f25f68dc75cbbbaa2
    bytes32 public constant ORACLE_PROVIDER_ROLE = keccak256("ORACLE_PROVIDER_ROLE");

    // 0x3c4cdb47519f2f89924ebeb1ee7a8a43b8b00120826915726460bb24576012fd
    bytes32 public constant RISKPOOL_KEEPER_ROLE = keccak256("RISKPOOL_KEEPER_ROLE");

    mapping(bytes32 => bool) public validRole;

    bool private _defaultAdminSet;

    /**
     * @dev This function is called after contract initialization and adds the product owner, oracle provider, and riskpool keeper roles.
     */
    function _afterInitialize() internal override {
        // add product owner, oracle provider and riskpool keeper roles
        _populateValidRoles();
    }

    /**
     * @dev Returns the name of the contract.
     * @return The name of the contract as a bytes32 value.
     */
    function _getName() internal override pure returns(bytes32) { return "Access"; }

    // IMPORTANT check the setting of the default admin role
    // after the deployment of a GIF instance.
    // this method is called in the deployment of
    // the instance operator proxy/controller 
    /**
     * @dev Sets the default admin role for the Access Control List (ACL).
     * @param defaultAdmin The address of the account to be set as the default admin role.
     *
     * Requirements:
     * - The default admin role must not have been set before.
     *
     * Emits a {RoleGranted} event.
     */
    function setDefaultAdminRole(address defaultAdmin) 
        external 
    {
        require(!_defaultAdminSet, "ERROR:ACL-001:ADMIN_ROLE_ALREADY_SET");
        _defaultAdminSet = true;

        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
    }

    //--- manage role ownership ---------------------------------------------//
    /**
     * @dev Grants a role to a principal.
     * @param role The bytes32 identifier of the role to grant.
     * @param principal The address of the principal to grant the role to.
     *
     * Requirements:
     * - `role` must be a valid role identifier.
     * - The caller must be an instance operator.
     */
    function grantRole(bytes32 role, address principal) 
        public 
        override(IAccessControl, IAccess) 
        onlyInstanceOperator 
    {
        require(validRole[role], "ERROR:ACL-002:ROLE_UNKNOWN_OR_INVALID");
        AccessControl.grantRole(role, principal);
    }

    /**
     * @dev Revokes the specified role from the specified principal.
     * @param role The bytes32 identifier of the role to revoke.
     * @param principal The address of the principal to revoke the role from.
     */
    function revokeRole(bytes32 role, address principal) 
        public 
        override(IAccessControl, IAccess) 
        onlyInstanceOperator 
    {
        AccessControl.revokeRole(role, principal);
    }

    /**
     * @dev Removes the specified `principal` from the `role` in the access control list (ACL) of the contract.
     * @param role The bytes32 identifier of the role to remove the `principal` from.
     * @param principal The address of the principal to remove from the `role`.
     */
    function renounceRole(bytes32 role, address principal) 
        public 
        override(IAccessControl, IAccess) 
    {
        AccessControl.renounceRole(role, principal);
    }
    
    //--- manage roles ------------------------------------------------------//
    /**
     * @dev Adds a new role to the Access Control List.
     * @param role The role to be added.
     */
    function addRole(bytes32 role) 
        public override
        onlyInstanceOperator 
    {
        require(!validRole[role], "ERROR:ACL-003:ROLE_EXISTING_AND_VALID");
        validRole[role] = true;
    }

    /**
     * @dev Invalidates a role.
     * @param role The role to invalidate.
     */
    function invalidateRole(bytes32 role)
        public override
        onlyInstanceOperator 
    {
        require(validRole[role], "ERROR:ACL-004:ROLE_UNKNOWN_OR_INVALID");
        validRole[role] = false;
    }

    /**
     * @dev Checks if a given principal has a specific role.
     * @param role The bytes32 representation of the role to check.
     * @param principal The address of the principal to check.
     * @return Returns true if the principal has the specified role, false otherwise.
     */
    function hasRole(bytes32 role, address principal) 
        public view 
        override(IAccessControl, IAccess) 
        returns(bool)
    {
        return super.hasRole(role, principal);
    }

    /**
     * @dev Returns the default admin role.
     * @return The DEFAULT_ADMIN_ROLE.
     */
    function getDefaultAdminRole() public pure override returns(bytes32) {
        return DEFAULT_ADMIN_ROLE;
    }

    /**
     * @dev Returns the bytes32 value of the PRODUCT_OWNER_ROLE.
     * @return PRODUCT_OWNER_ROLE The bytes32 value of the PRODUCT_OWNER_ROLE.
     */
    function getProductOwnerRole() public pure override returns(bytes32) {
        return PRODUCT_OWNER_ROLE;
    }

    /**
     * @dev Returns the bytes32 identifier of the Oracle Provider role.
     * @return ORACLE_PROVIDER_ROLE The bytes32 identifier of the Oracle Provider role.
     */
    function getOracleProviderRole() public pure override returns(bytes32) {
        return ORACLE_PROVIDER_ROLE;
    }

    /**
     * @dev Returns the bytes32 value of the RISKPOOL_KEEPER_ROLE.
     * @return RISKPOOL_KEEPER_ROLE The bytes32 value of the RISKPOOL_KEEPER_ROLE.
     */
    function getRiskpoolKeeperRole() public pure override returns(bytes32) {
        return RISKPOOL_KEEPER_ROLE;
    }

    /**
     * @dev Populates the validRole mapping with the roles that are considered valid for the contract.
     *
     *
     */
    function _populateValidRoles() private {
        validRole[PRODUCT_OWNER_ROLE] = true;
        validRole[ORACLE_PROVIDER_ROLE] = true;
        validRole[RISKPOOL_KEEPER_ROLE] = true;
    }
}
