// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract BundleToken is
    ERC721
{
    string public constant NAME = "GIF Bundle Token";
    string public constant SYMBOL = "BTK";

    constructor() 
        ERC721(NAME, SYMBOL)
    {

    }

    function mint(address to, uint256 tokenId) external {
        _safeMint(to, tokenId);
    }  
}
