"""Unit tests for Feature 3: Zero-Shot Species Detection."""

import pytest
from bioradar.ai.zero_shot import classify_unknown, dna_kmer_embedding


def test_dna_kmer_embedding():
    """Tests k-mer frequency vector generation and normalization."""
    seq = "ATGCGTACTAGCTAGCGCATCGATCGATCGATCGATCGATCGATCGATCGATC"
    emb = dna_kmer_embedding(seq, k=4)
    assert len(emb) == 256
    assert abs(float(sum(emb**2)) - 1.0) < 1e-4  # L2 normalized


def test_classify_unknown():
    """Tests taxonomy inferencing on unclassified DNA sequence."""
    seq = "ATGCGTACTAGCTAGCGCATCGATCGATCGATCGATCGATCGATCGATCGATC"
    res = classify_unknown(seq, asv_id="asv-test-123")
    assert res["asv_id"] == "asv-test-123"
    assert "inferred_taxonomy" in res
    assert "scientific_name" in res
    assert "confidence" in res
    assert len(res["nearest_neighbors"]) > 0
    assert "disclaimer" in res
    assert "NOT a definitive identification" in res["disclaimer"]
