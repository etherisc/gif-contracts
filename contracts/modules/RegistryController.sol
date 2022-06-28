// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "../shared/CoreController.sol";
import "@gif-interface/contracts/modules/IRegistry.sol";
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

    // release => contract name => contract address
    mapping(bytes32 => mapping(bytes32 => address)) public contracts;
    // release => contract name []
    mapping(bytes32 => bytes32[]) public contractNames;
    // number of contracts in release
    mapping(bytes32 => uint256) public contractsInRelease;


    function initializeRegistry(bytes32 _initialRelease) public initializer {
        // _setupRegistry(address(this));
        _registry = this;

        // this is a temporary assignment and must only be used
        // during the intial setup of a gif instance
        // at execution time _msgSender is the address of the 
        // registry proxy.
        release = _initialRelease;
        contracts[release]["InstanceOperatorService"] = _msgSender();
        contractNames[release].push("InstanceOperatorService");
        contractsInRelease[release] = 1;


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
        uint256 countContracts = contractsInRelease[release];

        require(countContracts > 0, "ERROR:REC-001:EMPTY_RELEASE");
        require(
            contractsInRelease[_newRelease] == 0,
            "ERROR:REC-004:NEW_RELEASE_NOT_EMPTY"
        );

        // TODO think about how to avoid this loop
        for (uint256 i = 0; i < countContracts; i += 1) {
            bytes32 contractName = contractNames[release][i];
            _registerInRelease(
                _newRelease,
                contractName,
                contracts[release][contractName]
            );
        }

        release = _newRelease;

        emit LogReleasePrepared(release);
    }

    /**
     * @dev Get contract's address in certain release
     */
    function _getContractInRelease(bytes32 _release, bytes32 _contractName)
        internal view
        returns (address _addr)
    {
        _addr = contracts[_release][_contractName];
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
        onlyInstanceOperator 
    {
        bool isNew = false;

        require(
            contractNames[_release].length <= MAX_CONTRACTS,
            "ERROR:REC-001:MAX_CONTRACTS_LIMIT"
        );

        if (contracts[_release][_contractName] == address(0)) {
            contractNames[_release].push(_contractName);
            contractsInRelease[_release] += 1;
            isNew = true;
        }

        contracts[_release][_contractName] = _contractAddress;
        require(
            contractsInRelease[_release] == contractNames[_release].length,
            "ERROR:REC-002:CONTRACT_NUMBER_MISMATCH"
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
        uint256 countContracts = contractNames[_release].length;

        // TODO think about how to avoid this loop
        for (uint256 i = 0; i < countContracts; i += 1) {
            if (contractNames[_release][i] == _contractName) {
                indexToDelete = i;
                break;
            }
        }

        if (indexToDelete < countContracts - 1) {
            contractNames[_release][indexToDelete] = contractNames[_release][
                countContracts - 1
            ];
        }

        contractNames[_release].pop();
        contractsInRelease[_release] -= 1;
        require(
            contractsInRelease[_release] == contractNames[_release].length,
            "ERROR:REC-003:CONTRACT_NUMBER_MISMATCH"
        );

        emit LogContractDeregistered(_release, _contractName);
    }
}
