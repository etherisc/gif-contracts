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

    function _afterInitialize() internal override {
        // add product owner, oracle provider and riskpool keeper roles
        _populateValidRoles();
    }

    function _getName() internal override pure returns(bytes32) { return "Access"; }

    // IMPORTANT check the setting of the default admin role
    // after the deployment of a GIF instance.
    // this method is called in the deployment of
    // the instance operator proxy/controller 
    function setDefaultAdminRole(address defaultAdmin) 
        external 
    {
        require(!_defaultAdminSet, "ERROR:ACL-001:ADMIN_ROLE_ALREADY_SET");
        _defaultAdminSet = true;

        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
    }

    //--- manage role ownership ---------------------------------------------//
    function grantRole(bytes32 role, address principal) 
        public 
        override(IAccessControl, IAccess) 
        onlyInstanceOperator 
    {
        require(validRole[role], "ERROR:ACL-002:ROLE_UNKNOWN_OR_INVALID");
        AccessControl.grantRole(role, principal);
    }

    function revokeRole(bytes32 role, address principal) 
        public 
        override(IAccessControl, IAccess) 
        onlyInstanceOperator 
    {
        AccessControl.revokeRole(role, principal);
    }

    function renounceRole(bytes32 role, address principal) 
        public 
        override(IAccessControl, IAccess) 
    {
        AccessControl.renounceRole(role, principal);
    }
    
    //--- manage roles ------------------------------------------------------//
    function addRole(bytes32 role) 
        public override
        onlyInstanceOperator 
    {
        require(!validRole[role], "ERROR:ACL-003:ROLE_EXISTING_AND_VALID");
        validRole[role] = true;
    }

    function invalidateRole(bytes32 role)
        public override
        onlyInstanceOperator 
    {
        require(validRole[role], "ERROR:ACL-004:ROLE_UNKNOWN_OR_INVALID");
        validRole[role] = false;
    }

    function hasRole(bytes32 role, address principal) 
        public view 
        override(IAccessControl, IAccess) 
        returns(bool)
    {
        return super.hasRole(role, principal);
    }

    function getDefaultAdminRole() public pure override returns(bytes32) {
        return DEFAULT_ADMIN_ROLE;
    }

    function getProductOwnerRole() public pure override returns(bytes32) {
        return PRODUCT_OWNER_ROLE;
    }

    function getOracleProviderRole() public pure override returns(bytes32) {
        return ORACLE_PROVIDER_ROLE;
    }

    function getRiskpoolKeeperRole() public pure override returns(bytes32) {
        return RISKPOOL_KEEPER_ROLE;
    }

    function _populateValidRoles() private {
        validRole[PRODUCT_OWNER_ROLE] = true;
        validRole[ORACLE_PROVIDER_ROLE] = true;
        validRole[RISKPOOL_KEEPER_ROLE] = true;
    }
}
