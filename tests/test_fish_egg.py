"""The fish-egg mock communities: published ground truth for mixed samples and for unknowns of known identity.

Source: Duke & Burton 2020 (doi:10.1002/ece3.6144); data Zenodo 4025362 (CC0). The truth file is the paper's own Table 1
and supplementary Table S1; nothing is invented. Tests that need the reads skip when the data was not downloaded.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioradar.adjudicate import expected, quality, runner
from bioradar.adjudicate.reference import Reference, extract_region, load_profile
from bioradar.adjudicate.thresholds import load

REPO = Path(__file__).resolve().parents[1]
TRUTH = REPO / "data" / "real_challenge" / "datasets" / "ZENODO4025362_fish_egg_mock" / "ground_truth" / "fish_egg_ground_truth.json"
RESULTS = REPO / "data" / "real_challenge" / "results"
SPECIES_PER_MOCK = {"MC1": 4, "MC2": 9, "MC3": 7, "MC4": 4, "MC5": 10, "MC6": 17}


@pytest.fixture(scope="module")
def truth():
    return json.loads(TRUTH.read_text(encoding="utf-8"))


def test_published_proportions_add_up_and_counts_match_the_paper(truth):
    for name, mock in truth["mock_communities"].items():
        assert abs(sum(mock["species"].values()) - 1.0) < 0.01, name
        assert len(mock["species"]) == mock["species_count"] == SPECIES_PER_MOCK[name], name
    assert len({s for m in truth["mock_communities"].values() for s in m["species"]}) == 23   # the paper's 23 species


def test_every_library_is_mapped_to_a_community_and_a_primer_set(truth):
    pooled = {k: v for k, v in truth["library_key"].items() if v["kind"] == "pooled"}
    assert len(pooled) == 12
    for lib, info in pooled.items():
        assert info["mock"] in truth["mock_communities"] and info["primers"] in ("COI", "16S"), lib


def test_the_sample_table_has_two_analyses_per_library():
    rows = [r for r in runner.sample_table() if r["sample_id"].startswith("ZEN-")]
    assert len(rows) == 24
    by_role = {r["role"] for r in rows}
    assert by_role == {"mixed_truth", "unknown_truth"}
    assert {r["profile"] for r in rows} == {"fish_egg_paper", "refseq_coi_16s"}
    for r in rows:
        assert r["sample_id"].endswith("-public") == (r["role"] == "unknown_truth")


def test_the_expected_spec_is_built_from_the_paper_not_from_results():
    row = next(r for r in runner.sample_table() if r["sample_id"] == "ZEN-G1")
    spec = runner._expected_spec(row)
    assert len(spec["species"]) == 7 and abs(sum(s["expected_share"] for s in spec["species"]) - 1.0) < 0.01
    assert "doi" in json.dumps(spec).lower() or "Duke" in spec["source"]


def test_ambiguous_letters_are_bases_not_errors():
    t = load()
    seq = "ACGTTGCAAGCTAGGC" * 10 + "R" + "ACGTTGCAAGCTAGGC" * 2 + "Y"   # R and Y are standard ambiguity codes
    assert quality.check(seq, 5, None, t) is None                       # two of 194 letters: under the 2% limit
    assert quality.check("ACGTTGCAAGCTAGGC" * 10 + "XZ", 5, None, t)[0] == "invalid_characters"
    reason = quality.check("N" * 20 + "ACGT" * 40, 5, None, t)
    assert reason and reason[0] == "too_many_n"


def test_the_singleton_rule_is_skipped_when_reads_are_trimmed_at_different_places():
    t = load()
    assert quality.check("ACGTTGCAAGCT" * 12, 1, None, t, count_rule=True)[0] == "singleton"
    assert quality.check("ACGTTGCAAGCT" * 12, 1, None, t, count_rule=False) is None


def test_the_species_cutoff_depends_on_the_gene_region():
    t = load()
    assert t.for_marker("12S").identity_species == 0.985
    assert t.for_marker("COI").identity_species == 0.97
    assert t.for_marker("16S").identity_species == 0.97
    assert t.for_marker("").identity_species == t.identity_species


def test_primer_to_primer_region_is_found_on_either_strand():
    from bioradar.adjudicate.reference import MARKER_PRIMERS
    from bioradar.adjudicate.seqio import revcomp
    f, r = MARKER_PRIMERS["16S"]
    body = "ACGT" * 150
    genome = "TTTT" * 20 + f + body + revcomp(r) + "GGGG" * 20
    assert extract_region(genome, f, r) is not None
    assert extract_region(revcomp(genome), f, r) is not None
    assert extract_region("ACGT" * 400, f, r) is None


def _result(name):
    path = RESULTS / "{}.json".format(name)
    if not path.is_file():
        pytest.skip("results not built")
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_mixed_library_is_checked_against_the_published_recipe():
    r = _result("ZEN-G1")
    ec = r["expected_check"]
    assert ec["mode"] == "composition" and ec["expected_count"] == 7
    assert ec["all_found"] and ec["shares_measured"] >= 5
    assert ec["tolerance_fold"] == load().share_tolerance_factor
    assert r["counting"]["singleton_rule_applied"] is False        # reads are trimmed at different places


def test_failures_are_kept_not_hidden():
    """Some libraries do NOT find every fish. They stay in the data and in the compliance line."""
    found = [_result("ZEN-" + lib)["expected_check"]["all_found"] for lib in "E1 F1 G1 H1 A2 B2 C2 D2 E2 F2 G2 H2".split()]
    assert 0 < sum(1 for x in found if not x) < len(found)


def test_unknowns_of_known_identity_are_explained_by_the_answer_key():
    r = _result("ZEN-E1-public")
    ec = r["expected_check"]
    assert ec["mode"] == "unknown_identity"
    assert set(ec["absent_from_public_list"]) == {"Oxyjulis californica", "Paralichthys californicus"}
    assert ec["unknown_groups_explained"] >= 2
    assert all(u["confidence"] <= load().unknown_max_confidence and u["status"] == "needs review" for u in r["unknown_queue"])
