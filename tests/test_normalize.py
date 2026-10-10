"""Tests for lineage parsing and normalization.

The edge cases here are not hypothetical -- every one of them was found in the
real pipeline output committed at testing_data/final_results.zip. If a change
makes one of these fail, downstream components will silently receive wrong
taxonomy, which is the worst failure mode in the system.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioradar.contract import TAXONOMY_COLUMNS, UNASSIGNED, validate_taxonomy_rows
from bioradar.normalize import (
    ResultsSource,
    load_detections,
    normalize,
    normalize_results,
    parse_lineage,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_RESULTS = REPO_ROOT / "testing_data" / "final_results.zip"


class TestParseLineage:
    def test_full_species_lineage(self):
        lineage = (
            "k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;"
            "o__Cyprinodontiformes_28738;f__Poeciliidae_8079;g__Gambusia_33527;"
            "s__Gambusia holbrooki_37273"
        )
        parsed = parse_lineage(lineage)
        assert parsed["rank"] == "species"
        assert parsed["scientific_name"] == "Gambusia holbrooki"
        assert parsed["taxon_id"] == "37273"
        assert parsed["genus"] == "Gambusia"
        assert parsed["kingdom"] == "Eukaryota"

    def test_species_name_keeps_its_space(self):
        parsed = parse_lineage("s__Oncorhynchus clarkii_30962")
        assert parsed["species"] == "Oncorhynchus clarkii"
        assert parsed["taxon_id"] == "30962"

    def test_species_name_with_underscore_becomes_a_space(self):
        # Some references separate the binomial with an underscore instead.
        parsed = parse_lineage("s__Lates_calcarifer_12345")
        assert parsed["species"] == "Lates calcarifer"
        assert parsed["taxon_id"] == "12345"

    def test_truncated_lineage_stops_at_genus(self):
        lineage = (
            "k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;"
            "o__Cypriniformes_7952;f__Cyprinidae_7953;g__Carassius_7956"
        )
        parsed = parse_lineage(lineage)
        assert parsed["rank"] == "genus"
        assert parsed["scientific_name"] == "Carassius"
        assert parsed["taxon_id"] == "7956"
        assert parsed["species"] == ""

    def test_redundant_rank_word_is_stripped(self):
        # MIDORI2 emits c__class_Testudines_8459 when NCBI has no distinct
        # class-level name. Without stripping, the class becomes "class_Testudines".
        parsed = parse_lineage(
            "k__Eukaryota_2759;p__Chordata_7711;c__class_Testudines_8459;"
            "o__Testudines_8459;f__Chelidae_8461;g__Myuchelys_904236;"
            "s__Myuchelys bellii_904237"
        )
        assert parsed["class"] == "Testudines"
        assert parsed["order"] == "Testudines"
        assert parsed["species"] == "Myuchelys bellii"

    @pytest.mark.parametrize("value", ["Unassigned", "Unassigned3", "", "   ", None])
    def test_unassigned_variants(self, value):
        parsed = parse_lineage(value)
        assert parsed["rank"] == UNASSIGNED
        assert parsed["scientific_name"] == ""
        assert parsed["taxon_id"] == ""
        assert all(parsed[rank] == "" for rank in ("kingdom", "genus", "species"))

    def test_missing_taxid_keeps_the_name(self):
        parsed = parse_lineage("k__Eukaryota;p__Chordata;g__Carassius")
        assert parsed["genus"] == "Carassius"
        assert parsed["taxon_id"] == ""
        assert parsed["rank"] == "genus"

    def test_domain_prefix_maps_to_kingdom(self):
        parsed = parse_lineage("d__Bacteria_2;p__Proteobacteria_1224")
        assert parsed["kingdom"] == "Bacteria"
        assert parsed["phylum"] == "Proteobacteria"

    def test_unknown_rank_prefix_is_skipped_not_guessed(self):
        parsed = parse_lineage("k__Eukaryota_2759;x__Nonsense_1;g__Carassius_7956")
        assert parsed["rank"] == "genus"
        assert parsed["kingdom"] == "Eukaryota"


class TestNormalize:
    def test_wide_to_long_expansion(self):
        rows = [
            {
                "Feature_ID": "abc123",
                "s1": "100.0",
                "s2": "0.0",
                "Taxon": "k__Eukaryota_2759;g__Carassius_7956",
                "Confidence": "0.91",
            }
        ]
        detections, summary = normalize(rows, ["s1", "s2"])

        # s2 has zero reads, so it is an absence, not a detection.
        assert len(detections) == 1
        assert detections[0]["sample_id"] == "s1"
        assert detections[0]["read_count"] == 100
        assert detections[0]["rel_abundance"] == 1.0
        assert len(summary) == 2
        assert summary[1]["total_reads"] == 0

    def test_include_zero_keeps_absences(self):
        rows = [
            {
                "Feature_ID": "abc123",
                "s1": "100.0",
                "s2": "0.0",
                "Taxon": "g__Carassius_7956",
                "Confidence": "0.91",
            }
        ]
        detections, _ = normalize(rows, ["s1", "s2"], include_zero=True)
        assert len(detections) == 2

    def test_sample_map_renames_samples(self):
        rows = [
            {
                "Feature_ID": "abc",
                "sample1": "10.0",
                "Taxon": "g__Carassius_7956",
                "Confidence": "0.9",
            }
        ]
        detections, summary = normalize(
            rows, ["sample1"], sample_map={"sample1": "BR-2026-GOA-001"}
        )
        assert detections[0]["sample_id"] == "BR-2026-GOA-001"
        assert summary[0]["sample_id"] == "BR-2026-GOA-001"

    def test_malformed_counts_do_not_crash(self):
        rows = [
            {
                "Feature_ID": "abc",
                "s1": "not-a-number",
                "Taxon": "g__Carassius_7956",
                "Confidence": "bad",
            }
        ]
        detections, summary = normalize(rows, ["s1"])
        assert detections == []
        assert summary[0]["total_reads"] == 0


@pytest.mark.skipif(not REAL_RESULTS.is_file(), reason="real results zip not present")
class TestAgainstRealPipelineOutput:
    """The contract must hold against bytes the pipeline actually produced."""

    def test_reads_directly_from_the_zip(self):
        with ResultsSource(REAL_RESULTS) as source:
            rows, samples = load_detections(source)
        assert len(rows) == 9
        assert samples == [f"sample{i}" for i in range(1, 7)]

    def test_normalized_output_satisfies_the_contract(self, tmp_path):
        written = normalize_results(REAL_RESULTS, tmp_path)
        assert written["taxonomy"].is_file()
        assert written["summary"].is_file()

        import csv

        with written["taxonomy"].open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        assert rows, "no detections produced from real output"
        assert list(rows[0]) == list(TAXONOMY_COLUMNS)
        validate_taxonomy_rows(rows)

    def test_known_invasive_is_detected(self, tmp_path):
        """Gambusia holbrooki is the demo's red pin -- it must survive parsing."""
        import csv

        written = normalize_results(REAL_RESULTS, tmp_path)
        with written["taxonomy"].open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        gambusia = [r for r in rows if r["species"] == "Gambusia holbrooki"]
        assert gambusia, "Gambusia holbrooki missing from normalized output"
        assert gambusia[0]["taxon_id"] == "37273"
        assert float(gambusia[0]["confidence"]) > 0.9

    def test_zero_count_rows_are_dropped(self, tmp_path):
        """Homo sapiens appears in exactly one sample in the real data."""
        import csv

        written = normalize_results(REAL_RESULTS, tmp_path)
        with written["taxonomy"].open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        human = [r for r in rows if r["species"] == "Homo sapiens"]
        assert len(human) == 1
        assert human[0]["sample_id"] == "sample4"

    def test_fallback_merge_matches_the_merged_table(self, tmp_path):
        """Rebuilding from asv-table.tsv + taxonomy.tsv must agree with the merged CSV."""
        from bioradar.normalize import _merge_fallback

        with ResultsSource(REAL_RESULTS) as source:
            merged_rows, merged_samples = load_detections(source)
            fallback_rows, fallback_samples = _merge_fallback(source)

        assert merged_samples == fallback_samples
        assert len(merged_rows) == len(fallback_rows)

        merged_by_id = {r["Feature_ID"]: r for r in merged_rows}
        for row in fallback_rows:
            counterpart = merged_by_id[row["Feature_ID"]]
            assert row["Taxon"] == counterpart["Taxon"]
