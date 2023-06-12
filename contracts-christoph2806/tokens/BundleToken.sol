// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.2;

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

    mapping(uint256 /** tokenId */ => uint256 /** bundleId */) public bundleIdForTokenId;
    address private _bundleModule;
    uint256 private _totalSupply;

    modifier onlyBundleModule() {
        require(_bundleModule != address(0), "ERROR:BTK-001:NOT_INITIALIZED");
        require(_msgSender() == _bundleModule, "ERROR:BTK-002:NOT_BUNDLE_MODULE");
        _;
    }

    /**
     * @dev Constructor function for the ERC721 token contract. It sets the name and symbol of the token and initializes the Ownable contract.
     */
    constructor() ERC721(NAME, SYMBOL) Ownable() { }

    /**
     * @dev Sets the bundle module address.
     * @param bundleModule The address of the bundle module to be set.
     *
     * Emits a {BundleModuleSet} event.
     *
     * Requirements:
     * - The bundle module address must not have already been set.
     * - The bundle module address must not be the zero address.
     */
    function setBundleModule(address bundleModule)
        external
    {
        require(_bundleModule == address(0), "ERROR:BTK-003:BUNDLE_MODULE_ALREADY_DEFINED");
        require(bundleModule != address(0), "ERROR:BTK-004:INVALID_BUNDLE_MODULE_ADDRESS");
        _bundleModule = bundleModule;
    }


    /**
     * @dev Mints a new bundle token and assigns ownership to the specified address.
     * @param bundleId The ID of the bundle to which the token belongs.
     * @param to The address that will receive ownership of the newly minted token.
     * @return tokenId The ID of the newly minted token.
     * @notice This function emits 1 events: 
     * - LogBundleTokenMinted
     */
    function mint(uint256 bundleId, address to) 
        external
        onlyBundleModule
        returns(uint256 tokenId)
    {
        _totalSupply++;
        tokenId = _totalSupply;
        bundleIdForTokenId[tokenId] = bundleId;        
        
        _safeMint(to, tokenId);
        
        emit LogBundleTokenMinted(bundleId, tokenId, to);           
    }


    /**
     * @dev Burns a bundle token.
     * @param tokenId The ID of the token to be burned.
     * @notice This function emits 1 events: 
     * - LogBundleTokenBurned
     */
    function burn(uint256 tokenId) 
        external
        onlyBundleModule
    {
        require(_exists(tokenId), "ERROR:BTK-005:TOKEN_ID_INVALID");        
        _burn(tokenId);
        
        emit LogBundleTokenBurned(bundleIdForTokenId[tokenId], tokenId);   
    }

    /**
     * @dev Checks if a token has been burned.
     * @param tokenId The ID of the token to check.
     * @return isBurned Returns true if the token has been burned, false otherwise.
     */
    function burned(uint tokenId) 
        external override
        view 
        returns(bool isBurned)
    {
        isBurned = tokenId <= _totalSupply && !_exists(tokenId);
    }

    /**
     * @dev Returns the bundle ID associated with a given token ID.
     * @param tokenId The ID of the token to query.
     * @return The bundle ID associated with the given token ID.
     */
    function getBundleId(uint256 tokenId) external override view returns(uint256) { return bundleIdForTokenId[tokenId]; }
    /**
     * @dev Returns the address of the bundle module.
     * @return _bundleModule The address of the bundle module.
     */
    function getBundleModuleAddress() external view returns(address) { return _bundleModule; }

    /**
     * @dev Checks if a given token ID exists.
     * @param tokenId The ID of the token to check.
     * @return A boolean indicating whether the token exists or not.
     */
    function exists(uint256 tokenId) external override view returns(bool) { return tokenId <= _totalSupply; }
    /**
     * @dev Returns the total number of tokens in circulation.
     * @return tokenCount The total number of tokens in circulation.
     */
    function totalSupply() external override view returns(uint256 tokenCount) { return _totalSupply; }
}
