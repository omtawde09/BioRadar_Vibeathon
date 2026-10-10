from bioradar.blockchain_ledger import MerkleTree, generate_blockchain_proof, sha256


def test_sha256_hashing():
    h = sha256("test_payload")
    assert len(h) == 64
    assert isinstance(h, str)


def test_merkle_tree_construction_and_odd_leaves():
    leaves = ["leaf1", "leaf2", "leaf3"]
    tree = MerkleTree(leaves)
    root = tree.root()
    assert len(root) == 64
    proof = tree.get_proof(0)
    assert len(proof) > 0
    assert "hash" in proof[0]

    # Test out-of-bounds proof requests
    assert tree.get_proof(-1) == []
    assert tree.get_proof(999) == []


def test_merkle_tree_empty_leaves():
    tree = MerkleTree([])
    root = tree.root()
    assert len(root) == 64
    assert tree.get_proof(0) == []


def test_generate_blockchain_proof_malformed_sample_points():
    mock_pts = [
        {"site_id": "GOA-MANDOVI", "latitude": None, "longitude": "73.8278", "species_count": "7", "total_reads": None},
        {"site_id": "GOA-ZUARI"}
    ]
    proof = generate_blockchain_proof("demo_run_malformed", mock_pts)
    assert proof["run_id"] == "demo_run_malformed"
    assert proof["chain_of_custody_status"] == "CRYPTOGRAPHICALLY_VERIFIED_UNTAMPERED"
    assert proof["merkle_root"].startswith("0x")
    assert proof["tx_hash"].startswith("0x")
    assert len(proof["leaves"]) == 2
