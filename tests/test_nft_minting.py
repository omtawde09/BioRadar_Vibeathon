"""Unit tests for Feature 5: Biodiversity NFT as Sponsorship Receipt."""

import pytest
from bioradar.blockchain.nft import mint_nft, generate_dna_sequence_art


def test_generate_dna_sequence_art():
    """Tests ATGC DNA sequence generative art PNG rendering."""
    seq = "ATGCGTACTAGCTAGCGCATCGATCGATCGATCGATCGATCGATCGATCGATC"
    data_uri = generate_dna_sequence_art(seq)
    assert data_uri.startswith("data:image/png;base64,")


def test_mint_nft():
    """Tests minting Biodiversity NFT sponsorship receipt on Polygon testnet simulation."""
    res = mint_nft("BR-NFT-TEST-001", to_address="0x1234567890123456789012345678901234567890")
    assert res["status"] in ["MINTED_SUCCESS", "ALREADY_MINTED"]
    assert "nft" in res
    
    nft = res["nft"]
    assert nft["sample_id"] == "BR-NFT-TEST-001"
    assert "token_id" in nft
    assert "tx_hash" in nft
    assert "ipfs_cid" in nft
    assert "metadata" in nft
    assert nft["network"] == "Polygon Amoy Testnet"
    assert len(nft["metadata"]["attributes"]) >= 5
