// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BiodiversityNFT
 * @dev ERC-721 token representing verified eDNA detection sponsorship receipts on Polygon Amoy testnet.
 */
contract BiodiversityNFT {
    string public name = "BioRadar Verified Biodiversity NFT";
    string public symbol = "BIORADAR";
    address public owner;
    uint256 private _nextTokenId;

    mapping(uint256 => string) private _tokenURIs;
    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event NFTMinted(address indexed to, uint256 indexed tokenId, string tokenURI);

    modifier onlyOwner() {
        require(msg.sender == owner, "Caller is not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        _nextTokenId = 1;
    }

    function mint(address to, string memory uri) public onlyOwner returns (uint256) {
        require(to != address(0), "Invalid target address");
        uint256 tokenId = _nextTokenId++;

        _owners[tokenId] = to;
        _balances[to] += 1;
        _tokenURIs[tokenId] = uri;

        emit Transfer(address(0), to, tokenId);
        emit NFTMinted(to, tokenId, uri);

        return tokenId;
    }

    function tokenURI(uint256 tokenId) public view returns (string memory) {
        require(_owners[tokenId] != address(0), "Token does not exist");
        return _tokenURIs[tokenId];
    }

    function ownerOf(uint256 tokenId) public view returns (address) {
        address tokenOwner = _owners[tokenId];
        require(tokenOwner != address(0), "Token does not exist");
        return tokenOwner;
    }

    function balanceOf(address account) public view returns (uint256) {
        require(account != address(0), "Invalid address");
        return _balances[account];
    }
}
