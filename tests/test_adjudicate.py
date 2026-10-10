"""Tests for the sample-adjudication package (bioradar/adjudicate).

Unit tests use inline strings to exercise rules. Nothing here writes a FASTA/FASTQ
file or edits a sequence. The integration tests run the engine on the REAL public
files fetched by `python -m bioradar.adjudicate.fetch` and skip if they are absent.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from bioradar.adjudicate import alerts, expected, guard, quality, report, seasons
from bioradar.adjudicate.adjudicate import confidence
from bioradar.adjudicate.thresholds import load

T = load()
DATA = Path(__file__).resolve().parents[1] / "data" / "real_challenge"
REAL_POOR = DATA / "raw" / "SRR33845265_1.fastq.gz"
REAL_MIXED = DATA / "raw" / "SRR27401753_1.fastq.gz"
HAVE_REAL = REAL_POOR.is_file() and (DATA / "reference_12s" / "reference.fasta").is_file()
needs_real = pytest.mark.skipif(not HAVE_REAL, reason="real dataset not fetched")


# -- thresholds: one place, each with a reason --------------------------------------------

def test_every_threshold_carries_its_rationale():
    for name, info in T.rationale().items():
        assert info["why"].strip(), name


# -- quality: every rejection has a written reason ----------------------------------------

def test_short_fragment_is_rejected_with_reason():
    code, why = quality.check("ACGT" * 10, 5, None, T)
    assert code == "too_short" and "40 bp" in why and str(T.min_length) in why


def test_n_heavy_sequence_is_rejected():
    seq = "ACGT" * 24 + "NNNNNN"
    code, why = quality.check(seq, 5, None, T)
    assert code == "too_many_n" and "N" in why


def test_singleton_and_low_complexity_and_invalid():
    good = "ACGTTGCAAGCTTCAGGACTTACGGATCAGTACCGATAGCTAGGCTTACGATCGGATCATCGGATCGATTGACCAGTCCATAGGCTAGCTAGCTTACG" * 2
    assert quality.check(good, 1, None, T)[0] == "singleton"
    assert quality.check("A" * 120, 9, None, T)[0] == "low_complexity"
    assert quality.check("ACGT" * 30 + "XYZ", 9, None, T)[0] == "invalid_characters"
    assert quality.check(good, 9, 12.0, T)[0] == "low_quality"
    assert quality.check(good, 9, 30.0, T) is None


# -- confidence: unknowns can never look confirmed ----------------------------------------

def test_unknown_confidence_is_capped_and_known_never_reaches_one():
    assert confidence(1.0, 0.5, called=False, t=T) <= T.unknown_max_confidence
    assert confidence(1.0, 0.5, called=True, t=T) <= T.confidence_max_known < 1.0
    assert confidence(0.90, 0.10, True, T) < confidence(0.99, 0.10, True, T)


# -- data guard ----------------------------------------------------------------------------

BOUNDARY = {"name": "box", "properties": {}, "polygons": [[[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]]}


def _row(run, alias, sample, date_, lat="5", lon="5"):
    return {"run_accession": run, "sample_alias": alias, "sample_accession": sample,
            "collection_date": date_, "lat": lat, "lon": lon, "scientific_name": "x"}


def test_guard_rejects_future_and_outside_and_missing_gps_with_reasons():
    rows = [_row("R1", "a", "S1", "2020-01"), _row("R2", "b", "S2", "2999-01-01"),
            _row("R3", "c", "S3", "2020", lat="50", lon="50"), _row("R4", "d", "S4", "2020", lat="", lon="")]
    g = guard.run_guard(rows, BOUNDARY, today=date(2026, 10, 10))
    by = {d["run_accession"]: d for d in g["decisions"]}
    assert by["R2"]["rule"] == "future_date" and "future" in by["R2"]["reason"] or "after today" in by["R2"]["reason"]
    assert by["R3"]["rule"] == "outside_boundary"
    assert by["R4"]["rule"] == "no_coordinates"
    assert g["clean_count"] == 1 and g["post_check"]["clean"]


def test_guard_merges_rerun_and_rejects_id_collision():
    rows = [_row("R1", "dup", "S1", "2020-01"), _row("R2", "dup", "S1", "2020-01"),
            _row("R3", "clash", "S2", "2020-01"), _row("R4", "clash", "S3", "2020-01")]
    g = guard.run_guard(rows, BOUNDARY, today=date(2026, 10, 10))
    actions = {d["run_accession"]: d["action"] for d in g["decisions"]}
    assert actions["R2"] == "merge" and actions["R4"] == "reject"
    assert g["post_check"]["duplicate_sample_ids"] == 0


def test_partial_dates_are_valid_not_errors():
    assert guard.parse_date("2024-03")[1] == "month"
    assert guard.parse_date("2019")[1] == "year"
    g = guard.run_guard([_row("R1", "a", "S1", "2024-03")], BOUNDARY, today=date(2026, 10, 10))
    assert g["clean_count"] == 1


def test_spelling_needs_sequence_agreement_not_just_similar_names():
    same = "ACGT" * 40
    merged = guard.spelling_variants({"Genus idella": same, "Genus idellus": same})
    assert merged and merged[0]["merge"] in ("Genus idella", "Genus idellus")
    distinct = guard.spelling_variants({"Genus macrolepis": same, "Genus microlepis": "TTTT" * 40})
    assert distinct == []


def test_point_in_polygon():
    assert guard.in_boundary(5, 5, BOUNDARY) and not guard.in_boundary(20, 20, BOUNDARY)


# -- seasons ------------------------------------------------------------------------------

def test_year_only_date_is_never_a_season():
    assert seasons.season_of("2019", T) is None
    assert seasons.season_of("2019-08", T) == "summer"
    assert seasons.season_of("2019-11", T) == "winter"


def _res(sid, date_, species):
    return {"sample_id": sid, "verdict": "Usable",
            "metadata": {"location": "L", "collection_date": date_, "role": "field"},
            "species": [{"species": n, "kind": "species", "status": "detected", "reads": r}
                        for n, r in species]}


def test_season_comparison_reports_new_and_not_detected_never_absent():
    doc = seasons.compare([_res("a", "2019-08", [("X y", 50), ("P q", 20)]),
                           _res("b", "2019-11", [("X y", 40), ("M n", 9)])], T)
    site = doc["sites"][0]
    assert site["counts"] == {"both": 1, "summer_only": 1, "winter_only": 1}
    assert "does not prove" in doc["not_absent_note"]


# -- alerts -------------------------------------------------------------------------------

def test_invasive_alert_carries_pin_species_level_and_source():
    result = {"sample_id": "S", "metadata": {"latitude": 1.0, "longitude": 2.0, "label": "L"},
              "species": [{"species": "Oreochromis niloticus", "kind": "species", "status": "detected",
                           "reads": 500, "share": 0.2, "confidence": 0.8, "best_identity": 0.99,
                           "members": ["Oreochromis niloticus"]}]}
    events = alerts.evaluate(result)
    assert events and events[0]["level"] in ("CRITICAL", "HIGH")
    assert events[0]["pin"]["latitude"] == 1.0 and events[0]["species"] == "Oreochromis niloticus"
    assert events[0]["sources"]


def test_unseparable_candidate_is_watch_never_confirmed():
    result = {"sample_id": "S", "metadata": {"latitude": 1, "longitude": 2},
              "species": [{"species": "Cyprinus a / b", "kind": "complex", "status": "unresolved",
                           "reads": 900, "share": 0.3, "confidence": 0.5, "best_identity": 1.0,
                           "members": ["Cyprinus carpio", "Cyprinus acutidorsalis"]}]}
    events = alerts.evaluate(result)
    assert events and events[0]["level"] == "WATCH" and events[0]["kind"] == "possible"


# -- expected shares: no ground truth => no pass claimed -----------------------------------

def test_no_ground_truth_means_not_checked():
    result = {"sample_id": "S", "metadata": {"alias": "Z", "role": "field"}, "species": []}
    out = expected.check(result, {})
    assert out["available"] is False and "not claimed" in out["note"]


def test_count_only_check_fails_honestly_when_species_are_missing():
    result = {"sample_id": "S", "metadata": {"alias": "Z", "role": "mixed",
                                             "biosample_attributes": {"samp_size": "30 fish"}},
              "species": [{"species": "A b", "kind": "species", "status": "detected"}] * 14}
    out = expected.check(result, {})
    assert out["available"] and not out["all_found"] and out["verdict"].startswith("FAIL")
    assert "NOT verified" in out["limits"]


def test_missing_expected_species_fails_the_composition_check():
    result = {"sample_id": "S", "metadata": {"alias": "Z"}, "species": [
        {"species": "A b", "kind": "species", "status": "detected", "share": 0.5}]}
    spec = {"Z": {"source": "paper", "species": [{"name": "A b", "expected_share": 0.5},
                                                  {"name": "C d", "expected_share": 0.5}]}}
    out = expected.check(result, spec)
    assert not out["all_found"] and out["verdict"].startswith("FAIL")


# -- report -------------------------------------------------------------------------------

def test_report_is_a_valid_one_page_pdf():
    result = {"sample_id": "S", "verdict": "Usable", "verdict_reasons": ["ok"], "reads_total": 100,
              "summary": {"kept": {"reads": 50, "distinct": 3}, "unknown": {"reads": 30, "distinct": 2},
                          "dropped": {"reads": 20, "distinct": 9}},
              "reference": {"species": 100}, "alerts": [],
              "metadata": {"label": "L (with) parens", "alias": "L", "collection_date": "2020-01",
                           "bioproject": "PRJ", "dataset_title": "T", "latitude": 1.0, "longitude": 2.0},
              "species": [{"species": "A b", "kind": "species", "status": "detected",
                           "share": 0.5, "confidence": 0.9}]}
    pdf = report.build_pdf(result)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF") and b"/Count 1" in pdf


# -- real data ----------------------------------------------------------------------------

@needs_real
def test_real_poor_sample_gets_retake_with_human_contamination_reason():
    from bioradar.adjudicate.adjudicate import adjudicate_file
    from bioradar.adjudicate.reference import Reference
    r = adjudicate_file(REAL_POOR, {"sample_id": "t", "role": "poor"}, Reference.load(), T)
    assert r["verdict"] == "Retake sample"
    assert "human_contamination" in r["drop_reasons"]
    assert all(d["reason"] for d in r["dropped"])


@needs_real
@pytest.mark.skipif(not REAL_MIXED.is_file(), reason="mock sample not fetched")
def test_real_mixed_sample_unknowns_are_never_confident():
    from bioradar.adjudicate.adjudicate import adjudicate_file
    from bioradar.adjudicate.reference import Reference
    r = adjudicate_file(REAL_MIXED, {"sample_id": "t", "role": "mixed"}, Reference.load(), T, limit=30000)
    assert r["unknown_queue"], "expected unknowns in a real mock community"
    assert all(u["confidence"] <= T.unknown_max_confidence and u["status"] == "needs review"
               for u in r["unknown_queue"])
    assert all(s["confidence"] < 1.0 for s in r["species"])


@needs_real
def test_file_name_does_not_decide_the_answer(tmp_path):
    """Same bytes under a misleading name give the same result (format read by content)."""
    import shutil
    from bioradar.adjudicate.adjudicate import adjudicate_file
    from bioradar.adjudicate.reference import Reference
    ref = Reference.load()
    disguised = tmp_path / "mock_community_20_species_PASS.txt"
    shutil.copy(REAL_POOR, disguised)
    a = adjudicate_file(REAL_POOR, {"sample_id": "a"}, ref, T)
    b = adjudicate_file(disguised, {"sample_id": "b"}, ref, T)
    assert a["verdict"] == b["verdict"] and a["summary"] == b["summary"]
