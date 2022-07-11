// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

// import "./IdSet.sol";
import "@gif-interface/contracts/components/IdSet.sol";


contract TestSet is IdSet {

    function add(uint256 id) public {
        _addIdToSet(id);
    }

    function remove(uint256 id) public {
        _removeIdfromSet(id);
    }

    function contains(uint256 id) public view returns(bool) {
        return _containsIdInSet(id);
    }

    function size() public view returns(uint256) {
        return _idSetSize();
    }

    function intAt(uint256 idx) public view returns(uint256 id) {
        return _idInSetAt(idx);
    }
}