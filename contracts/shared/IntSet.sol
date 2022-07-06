// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

contract IntSet {

    mapping(uint256 => uint256) private _intMap;
    uint256 [] _ints;

    function add(uint256 id) public {
        if(_intMap[id] == 0) {
            _ints.push(id);
            _intMap[id] = _ints.length;
        }
    }

    function remove(uint256 id) public {
        uint256 idx = _intMap[id];
        if(idx > 0) {
            idx -= 1;
            _ints[idx] = _ints[_ints.length - 1];
            _ints.pop();
            delete _intMap[id];
        }
    }

    function contains(uint256 id) public view returns(bool) {
        return _intMap[id] > 0;
    }

    function size() public view returns(uint256) {
        return _ints.length;
    }

    function intAt(uint256 idx) public view returns(uint256 id) {
        require(idx < _ints.length, "ERROR:SET-001:INDEX_TOO_LARGE");
        return _ints[idx];
    }
}