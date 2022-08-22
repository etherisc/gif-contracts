// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";

import "@etherisc/gif-interface/contracts/modules/IRegistry.sol";

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract RegistryController is
    IRegistry,
    CoreController
{
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
    mapping(bytes32 /* release */ => bytes32[] /* contract names */) public _contractNames;
    mapping(bytes32 /* release */ => uint256 /* number of contracts in release */) public _contractsInRelease;


    function initializeRegistry(bytes32 _initialRelease) public initializer {
        // _setupRegistry(address(this));
        _registry = this;

        // this is a temporary assignment and must only be used
        // during the intial setup of a gif instance
        // at execution time _msgSender is the address of the 
        // registry proxy.
        release = _initialRelease;
        _contracts[release]["InstanceOperatorService"] = _msgSender();
        _contractNames[release].push("InstanceOperatorService");
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
        _registerInRelease(release, _contractName, _contractAddress);
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
        _registerInRelease(_release, _contractName, _contractAddress);
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
            bytes32 contractName = _contractNames[release][i];
            _registerInRelease(
                _newRelease,
                contractName,
                _contracts[release][contractName]
            );
        }

        release = _newRelease;

        emit LogReleasePrepared(release);
    }

    function contracts() external override view returns (uint256 _numberOfContracts) {
        _numberOfContracts = _contractNames[release].length;
    }

    function contractNames() external override view returns (bytes32[] memory _contractNamesOut) {
        _contractNamesOut = _contractNames[release];
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
        bytes32 _contractName,
        address _contractAddress
    ) 
        internal
    {
        bool isNew = false;

        require(
            _contractNames[_release].length < MAX_CONTRACTS,
            "ERROR:REC-005:MAX_CONTRACTS_LIMIT"
        );

        if (_contracts[_release][_contractName] == address(0)) {
            _contractNames[_release].push(_contractName);
            _contractsInRelease[_release]++;
            isNew = true;
        }

        _contracts[_release][_contractName] = _contractAddress;
        require(
            _contractsInRelease[_release] == _contractNames[_release].length,
            "ERROR:REC-006:CONTRACT_NUMBER_MISMATCH"
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
        uint256 indexToDelete;
        uint256 countContracts = _contractNames[_release].length;

        // TODO think about how to avoid this loop
        for (uint256 i = 0; i < countContracts; i += 1) {
            if (_contractNames[_release][i] == _contractName) {
                indexToDelete = i;
                break;
            }
        }

        if (indexToDelete < countContracts - 1) {
            _contractNames[_release][indexToDelete] = _contractNames[_release][
                countContracts - 1
            ];
        }

        _contractNames[_release].pop();
        _contractsInRelease[_release] -= 1;
        require(
            _contractsInRelease[_release] == _contractNames[_release].length,
            "ERROR:REC-010:CONTRACT_NUMBER_MISMATCH"
        );

        emit LogContractDeregistered(_release, _contractName);
    }
}
