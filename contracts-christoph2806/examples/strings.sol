// SPDX-License-Identifier: Apache2

// source: https://github.com/Arachnid/solidity-stringutils
/*
 * @title String & slice utility library for Solidity contracts.
 * @author Nick Johnson <arachnid@notdot.net>
 *
 * @dev Functionality in this library is largely implemented using an
 *      abstraction called a 'slice'. A slice represents a part of a string -
 *      anything from the entire string to a single character, or even no
 *      characters at all (a 0-length slice). Since a slice only has to specify
 *      an offset and a length, copying and manipulating slices is a lot less
 *      expensive than copying and manipulating the strings they reference.
 *
 *      To further reduce gas costs, most functions on slice that need to return
 *      a slice modify the original one instead of allocating a new one; for
 *      instance, `s.split(".")` will return the text up to the first '.',
 *      modifying s to only contain the remainder of the string after the '.'.
 *      In situations where you do not want to modify the original slice, you
 *      can make a copy first with `.copy()`, for example:
 *      `s.copy().split(".")`. Try and avoid using this idiom in loops; since
 *      Solidity has no memory management, it will result in allocating many
 *      short-lived slices that are later discarded.
 *
 *      Functions that return two slices come in two versions: a non-allocating
 *      version that takes the second slice as an argument, modifying it in
 *      place, and an allocating version that allocates and returns the second
 *      slice; see `nextRune` for example.
 *
 *      Functions that have to copy string data will return strings rather than
 *      slices; these can be cast back to slices for further processing if
 *      required.
 *
 *      For convenience, some functions are provided with non-modifying
 *      variants that create a new slice and return both; for instance,
 *      `s.splitNew('.')` leaves s unmodified, and returns two values
 *      corresponding to the left and right parts of the string.
 */
pragma solidity 0.8.2;

library strings {

    struct slice {
        uint _len;
        uint _ptr;
    }

    /**
     * @dev Copies a specified number of bytes from one memory address to another.
     * @param dest The destination memory address to copy to.
     * @param src The source memory address to copy from.
     * @param len_ The number of bytes to copy.
     */
    function memcpy(uint dest, uint src, uint len_) private pure {
        // Copy word-length chunks while possible
        for(; len_ >= 32; len_ -= 32) {
            assembly {
                mstore(dest, mload(src))
            }
            dest += 32;
            src += 32;
        }

        // Copy remaining bytes
        uint mask = type(uint).max;
        if (len_ > 0) {
            mask = 256 ** (32 - len_) - 1;
        }
        assembly {
            let srcpart := and(mload(src), not(mask))
            let destpart := and(mload(dest), mask)
            mstore(dest, or(destpart, srcpart))
        }
    }

    /*
     * @dev Returns the length of a null-terminated bytes32 string.
     * @param self The value to find the length of.
     * @return The length of the string, from 0 to 32.
     */
    /**
     * @dev Calculates the length of a bytes32 variable.
     * @param self The bytes32 variable to calculate the length of.
     * @return ret The length of the bytes32 variable.
     */
    function len(bytes32 self) internal pure returns (uint) {
        uint ret;
        if (self == 0)
            return 0;
        if (uint(self) & type(uint128).max == 0) {
            ret += 16;
            self = bytes32(uint(self) / 0x100000000000000000000000000000000);
        }
        if (uint(self) & type(uint64).max == 0) {
            ret += 8;
            self = bytes32(uint(self) / 0x10000000000000000);
        }
        if (uint(self) & type(uint32).max == 0) {
            ret += 4;
            self = bytes32(uint(self) / 0x100000000);
        }
        if (uint(self) & type(uint16).max == 0) {
            ret += 2;
            self = bytes32(uint(self) / 0x10000);
        }
        if (uint(self) & type(uint8).max == 0) {
            ret += 1;
        }
        return 32 - ret;
    }

    // merge of toSliceB32 and toString of strings library
    /**
     * @dev Converts a bytes32 value to a string.
     * @param self The bytes32 value to be converted.
     * @return ret The resulting string value.
     *
     * Converts a bytes32 value to a string by creating a slice of the bytes32 value and then copying it to a new string.
     * The resulting string is then returned as the output of the function.
     */
    function toB32String(bytes32 self) internal pure returns (string memory) {
        slice memory slc;
        assembly {
            let ptr := mload(0x40)
            mstore(0x40, add(ptr, 0x20))
            mstore(ptr, self)
            mstore(add(slc, 0x20), ptr)
        }
        slc._len = len(self);

        string memory ret = new string(slc._len);
        uint retptr;
        assembly { retptr := add(ret, 32) }
        memcpy(retptr, slc._ptr, slc._len);
        return ret;
    }
}