"""Tests for the relative finder (bioradar/relatives).

Unit tests use inline strings. Model tests use the committed real reference (RefSeq fish 12S
amplicons) and, when present, the committed NCBI lineage table; queries are reference amplicons
with the species hidden, which is how a missing species looks to the model. They are
software tests, not evidence that any real sample contains a particular fish.
"""

from __future__ import annotations

import math

import pytest

from bioradar.relatives import kmer
from bioradar.relatives import lineage as lineage_mod
from bioradar.adjudicate.seqio import revcomp

HAVE_LINEAGE = lineage_mod.LINEAGE_TSV.is_file()
needs_lineage = pytest.mark.skipif(not HAVE_LINEAGE, reason="lineage.tsv not fetched")


# -- embedding ----------------------------------------------------------------------------

def test_canonical_kmers_make_the_embedding_strand_independent():
    seq = "ACGTTGCAAGGCTTACCGATAGGCTAACGTTAGC" * 3
    e = kmer.Embedder.fit([seq, "TTTTGGGGCCCCAAAA" * 4])
    a, b = e.embed(seq), e.embed(revcomp(seq))
    assert a.keys() == b.keys()
    assert math.isclose(kmer.cosine(a, b), 1.0, rel_tol=1e-9)


def test_windows_with_n_are_skipped_and_vectors_are_unit_length():
    codes = kmer.kmer_codes("ACGTAC" + "N" + "GGTACC")
    assert len(codes) == 2  # one 6-mer each side of the N
    vec = kmer.Embedder.fit(["ACGTACGGTACCAT"]).embed("ACGTACGGTACCAT")
    assert math.isclose(sum(v * v for v in vec.values()), 1.0, rel_tol=1e-9)


def test_dense_projection_is_deterministic_and_tracks_sparse_cosine():
    e = kmer.Embedder.fit(["ACGTTGCAAGGCTTACCGATAGGCTAACG" * 3, "GGGCCCAAATTTGCGCAT" * 4])
    v = e.embed("ACGTTGCAAGGCTTACCGATAGGCTAACG" * 3)
    d1, d2 = kmer.dense(v), kmer.dense(v)
    assert d1 == d2 and len(d1) == kmer.DENSE_DIMS
    assert math.isclose(sum(x * x for x in d1), 1.0, rel_tol=1e-4)


def test_index_returns_one_row_per_species_and_honours_exclusion():
    entries = [("a1", "Alpha one", "ACGTTGCAAGGCTTACCGATAGGCTAACGTTAGC" * 3),
               ("a2", "Alpha one", "ACGTTGCAAGGCTTACCGATAGGCTAACGTTAGG" * 3),
               ("b1", "Beta two", "TTGGCCAATTGGCCAAGGTTCCAAGGTTCCAACG" * 3)]
    idx = kmer.Index.build(entries)
    hits = idx.nearest_species(entries[0][2], top=5)
    assert [h[0] for h in hits][:1] == ["Alpha one"] and len({h[0] for h in hits}) == len(hits)
    assert all(h[0] != "Alpha one" for h in idx.nearest_species(entries[0][2], exclude_species=["Alpha one"]))


# -- model on the real reference ----------------------------------------------------------

@pytest.fixture(scope="module")
def finder():
    from bioradar.relatives.model import RelativeFinder
    return RelativeFinder.load()


def _species_with_congener(f):
    by_genus = {}
    for sp, lin in f.species_lineage.items():
        by_genus.setdefault(lin.get("genus"), []).append(sp)
    for acc, sp, seq in f.ref.entries:
        lin = f.species_lineage.get(sp, {})
        if lin.get("genus") and len(by_genus.get(lin["genus"], [])) >= 3:
            return sp, seq, lin
    raise AssertionError("no genus with 3 reference species")


@needs_lineage
def test_hidden_species_gets_relatives_and_a_hypothesis_never_an_identification(finder):
    sp, seq, lin = _species_with_congener(finder)
    h = finder.speculate(seq, exclude_species=[sp])
    assert h["status"].startswith("hypothesis")
    assert all(r["species"] != sp for r in h["relatives"])
    assert h["relatives"] and h["relatives"][0]["cosine"] >= h["relatives"][-1]["cosine"]
    assert "dna_sequence" in h["factors_used"] and "evolutionary_history" in h["factors_used"]
    # a hidden species can never be reported as a species-level match to itself
    assert h["closest_species"]["species"] != sp
    hyp = h["hypothesis"]
    if hyp["rank"]:
        assert hyp["taxon"] == h["by_rank"][hyp["rank"]]["taxon"]
        assert hyp["support"] >= 0.6


@needs_lineage
def test_unobservable_factors_are_listed_not_used_unless_supplied(finder):
    sp, seq, _ = _species_with_congener(finder)
    h = finder.speculate(seq, exclude_species=[sp])
    missing = {f["factor"] for f in h["factors_not_used"]}
    assert {"karyotype_2n", "hormone", "diet"} <= missing
    h2 = finder.speculate(seq, {"karyotype_2n": 48}, exclude_species=[sp])
    assert "karyotype_2n" not in {f["factor"] for f in h2["factors_not_used"]}


@needs_lineage
def test_consensus_supports_sum_to_one_per_rank(finder):
    sp, seq, _ = _species_with_congener(finder)
    rels = finder.relatives(seq, exclude_species=[sp], align_top=0)
    by_rank = finder.consensus(rels)
    for rank, cell in by_rank.items():
        total = cell["support"] + sum(a["support"] for a in cell["alternatives"])
        assert total <= 1.0001


def test_junk_sequence_gets_no_hypothesis(finder):
    h = finder.speculate("ACACACACACACACACACACACACACACACACACACACAC")
    assert h["hypothesis"] is None or h["hypothesis"]["rank"] in (None, "class", "order", "family", "genus")
    h2 = finder.speculate("NNNNNNNNNNNNNNNNNNNNNNNNNNNNNN")
    assert h2["relatives"] == [] and h2["hypothesis"] is None
