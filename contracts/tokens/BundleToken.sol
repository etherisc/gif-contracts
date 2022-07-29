// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

import "@etherisc/gif-interface/contracts/tokens/IBundleToken.sol";

contract BundleToken is 
    IBundleToken,
    ERC721,
    Ownable
{
    string public constant NAME = "GIF Bundle Token";
    string public constant SYMBOL = "BTK";

    // event LogBundleTokenMinted(uint256 bundleId, uint256 tokenId, address tokenOwner);
    // event LogBundleTokenBurned(uint256 bundleId, uint256 tokenId);   

    // tokenId => bundleId
    mapping(uint256 => uint256) private _bundleId;
    address private _bundleModule;
    uint256 private _tokens;

    modifier onlyBundleModule() {
        require(_bundleModule != address(0), "ERROR:BTK-001:NOT_INITIALIZED");
        require(_msgSender() == _bundleModule, "ERROR:BTK-002:NOT_BUNDLE_MODULE");
        _;
    }

    constructor() ERC721(NAME, SYMBOL) Ownable() { }

    function setBundleModule(address bundleModule)
        external
        onlyOwner
    {
        require(_bundleModule == address(0), "ERROR:BTK-003:BUNDLE_MODULE_ALREADY_DEFINED");
        require(bundleModule != address(0), "ERROR:BTK-004:INVALID_BUNDLE_MODULE_ADDRESS");
        _bundleModule = bundleModule;
    }


    function mint(uint256 bundleId, address to) 
        external
        onlyBundleModule
        returns(uint256 tokenId)
    {
        _tokens += 1;
        tokenId = _tokens;

        _safeMint(to, tokenId);
        _bundleId[tokenId] = bundleId;
        
        emit LogBundleTokenMinted(bundleId, tokenId, to);   
    }


    function burn(uint256 tokenId) 
        external
        onlyBundleModule
    {
        require(_exists(tokenId), "ERROR:BTK-005:TOKEN_ID_INVALID");        
        _burn(tokenId);
        
        emit LogBundleTokenBurned(_bundleId[tokenId], tokenId);   
    }

    function burned(uint tokenId) 
        external override
        view 
        returns(bool isBurned)
    {
        isBurned = tokenId <= _tokens && !_exists(tokenId);
    }

    function exists(uint256 tokenId) external override view returns(bool) { return tokenId <= _tokens; }
    function getBundleId(uint256 tokenId) external override view returns(uint256) { return _bundleId[tokenId]; }
    function tokens() external override view returns(uint256 tokenCount) { return _tokens; }
}
