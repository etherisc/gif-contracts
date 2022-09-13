// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";


contract RegistryController is
    IRegistry,
    CoreController
{
    using EnumerableSet for EnumerableSet.Bytes32Set;

    /**
     * @dev  Save number of items to iterate through
     * Currently we have < 20 contracts.
     */
    uint256 public constant MAX_CONTRACTS = 100;

    /**
     * @dev Current release
     * We use semantic versioning.
     */
    bytes32 public release;
    
    uint256 public startBlock;

    mapping(bytes32 /* release */ => mapping(bytes32 /* contract name */ => address /* contract address */)) public _contracts;
    mapping(bytes32 /* release */ => uint256 /* number of contracts in release */) public _contractsInRelease;
    mapping(bytes32 /* release */ => EnumerableSet.Bytes32Set /* contract names */) private _contractNames;

    function initializeRegistry(bytes32 _initialRelease) public initializer {
        // _setupRegistry(address(this));
        _registry = this;

        // this is a temporary assignment and must only be used
        // during the intial setup of a gif instance
        // at execution time _msgSender is the address of the 
        // registry proxy.
        release = _initialRelease;
        _contracts[release]["InstanceOperatorService"] = _msgSender();
        EnumerableSet.add(_contractNames[release], "InstanceOperatorService");
        _contractsInRelease[release] = 1;


        // register the deployment block for reading logs
        startBlock = block.number;
    }

    function ensureSender(address sender, bytes32 _contractName) 
        external view override 
        returns(bool _senderMatches) 
    {
        _senderMatches = (sender == _getContractInRelease(release, _contractName));
    }

    /**
     * @dev get current release
     */
    function getRelease() 
        external override view 
        returns (bytes32 _release) 
    {
        _release = release;
    }

    /**
     * @dev Get contract's address in the current release
     */
    function getContract(bytes32 _contractName)
        public override view
        returns (address _addr)
    {
        _addr = _getContractInRelease(release, _contractName);
    }

    /**
     * @dev Register contract in the current release
     */
    function register(bytes32 _contractName, address _contractAddress)
        external override
        onlyInstanceOperator
    {
        _registerInRelease(release, false, _contractName, _contractAddress);
    }

    /**
     * @dev Deregister contract in the current release
     */
    function deregister(bytes32 _contractName) 
        external override 
        onlyInstanceOperator 
    {
        _deregisterInRelease(release, _contractName);
    }

    /**
     * @dev Get contract's address in certain release
     */
    function getContractInRelease(bytes32 _release, bytes32 _contractName)
        external override view
        returns (address _addr)
    {
        _addr = _getContractInRelease(_release, _contractName);
    }

    /**
     * @dev Register contract in certain release
     */
    function registerInRelease(bytes32 _release, bytes32 _contractName, address _contractAddress)  
        external override 
        onlyInstanceOperator
    {
        _registerInRelease(_release, false, _contractName, _contractAddress);
    }

    function deregisterInRelease(bytes32 _release, bytes32 _contractName)
        external override
        onlyInstanceOperator
    {
        _deregisterInRelease(_release, _contractName);
    }

    /**
     * @dev Create new release, copy contracts from previous release
     */
    function prepareRelease(bytes32 _newRelease) 
        external override 
        onlyInstanceOperator 
    {
        uint256 countContracts = _contractsInRelease[release];

        require(countContracts > 0, "ERROR:REC-001:EMPTY_RELEASE");
        require(
            _contractsInRelease[_newRelease] == 0,
            "ERROR:REC-002:NEW_RELEASE_NOT_EMPTY"
        );

        // TODO think about how to avoid this loop
        for (uint256 i = 0; i < countContracts; i += 1) {
            bytes32 name = EnumerableSet.at(_contractNames[release], i);
            _registerInRelease(
                _newRelease,
                true,
                name,
                _contracts[release][name]
            );
        }

        release = _newRelease;

        emit LogReleasePrepared(release);
    }

    function contracts() external override view returns (uint256 _numberOfContracts) {
        _numberOfContracts = EnumerableSet.length(_contractNames[release]);
    }

    function contractName(uint256 idx) external override view returns (bytes32 _contractName) {
        _contractName = EnumerableSet.at(_contractNames[release], idx);
    }

    /**
     * @dev Get contract's address in certain release
     */
    function _getContractInRelease(bytes32 _release, bytes32 _contractName)
        internal view
        returns (address _addr)
    {
        _addr = _contracts[_release][_contractName];
    }

    /**
     * @dev Register contract in certain release
     */
    function _registerInRelease(
        bytes32 _release,
        bool isNewRelease,
        bytes32 _contractName,
        address _contractAddress
    ) 
        internal
    {
        bool isNew = false;

        require(
            EnumerableSet.length(_contractNames[_release]) < MAX_CONTRACTS,
            "ERROR:REC-010:MAX_CONTRACTS_LIMIT"
        );

        // during `prepareRelease` the _release is not yet known, so check should not fail in this case 
        require(_contractsInRelease[_release] > 0 || isNewRelease, "ERROR:REC-011:RELEASE_UNKNOWN");
        require(_contractName != 0x00, "ERROR:REC-012:CONTRACT_NAME_EMPTY");
        require(
            (! EnumerableSet.contains(_contractNames[_release], _contractName) )
            // the contract 'InstanceOperatorService' is initially registered with the owner address (see method initializeRegistry()); 
            // due to this this special check is required
            || (_contractName == "InstanceOperatorService" && _contracts[_release][_contractName] == _msgSender()), 
            "ERROR:REC-013:CONTRACT_NAME_EXISTS");
        require(_contractAddress != address(0), "ERROR:REC-014:CONTRACT_ADDRESS_ZERO");

        if (_contracts[_release][_contractName] == address(0)) {
            EnumerableSet.add(_contractNames[_release], _contractName);
            _contractsInRelease[_release]++;
            isNew = true;
        }

        _contracts[_release][_contractName] = _contractAddress;
        require(
            _contractsInRelease[_release] == EnumerableSet.length(_contractNames[_release]),
            "ERROR:REC-015:CONTRACT_NUMBER_MISMATCH"
        );

        emit LogContractRegistered(
            _release,
            _contractName,
            _contractAddress,
            isNew
        );
    }


    /**
     * @dev Deregister contract in certain release
     */
    function _deregisterInRelease(bytes32 _release, bytes32 _contractName)
        internal
        onlyInstanceOperator
    {
        require(EnumerableSet.contains(_contractNames[_release], _contractName), "ERROR:REC-020:CONTRACT_UNKNOWN");

        EnumerableSet.remove(_contractNames[_release], _contractName);

        _contractsInRelease[_release] -= 1;
        delete _contracts[_release][_contractName];
        
        require(
            _contractsInRelease[_release] == EnumerableSet.length(_contractNames[_release]),
            "ERROR:REC-021:CONTRACT_NUMBER_MISMATCH");
        emit LogContractDeregistered(_release, _contractName);            
    }
}
