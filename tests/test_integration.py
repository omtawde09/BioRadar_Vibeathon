"""Integration tests: chain of custody, Time Machine, mock data, run isolation.

These are the tests that catch the failures that actually kill hackathon demos:
a hash that changes when it should not, a ledger that accepts a broken chain, two
pipeline runs overwriting each other, mock data that does not match the contract
everyone coded against.
"""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

import pytest

from bioradar.chain_client import ChainClient, build_event, canonical_hash, sha256_file
from bioradar.contract import (
    SAMPLE_SUMMARY_COLUMNS,
    TAXONOMY_COLUMNS,
    ContractError,
    sample_id_from_fastq,
    validate_taxonomy_rows,
)
from bioradar.mockgen import build_alerts_example, generate, load_csv
from bioradar.time_machine import aggregate, compare, shannon_index
from integration.mock_backend import MockBackend, reset

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    path = tmp_path / "taxonomy_normalized.csv"
    path.write_text("sample_id,asv_id\nBR-001,abc\n", encoding="utf-8")
    return path


class TestHashing:
    def test_canonical_hash_ignores_key_order(self):
        assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})

    def test_canonical_hash_changes_with_content(self):
        assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})

    def test_file_hash_is_stable(self, artifact):
        assert sha256_file(artifact) == sha256_file(artifact)

    def test_file_hash_detects_a_single_byte_change(self, artifact):
        before = sha256_file(artifact)
        artifact.write_text("sample_id,asv_id\nBR-001,abd\n", encoding="utf-8")
        assert sha256_file(artifact) != before

    def test_build_event_hashes_each_artifact_separately(self, artifact):
        event = build_event("BR-001", "pipeline_complete", {"taxonomy": artifact})
        artifacts = event["payload"]["artifacts"]
        assert artifacts["taxonomy"]["sha256"] == sha256_file(artifact)
        assert artifacts["taxonomy"]["bytes"] == artifact.stat().st_size

    def test_unknown_event_type_is_rejected(self, artifact):
        with pytest.raises(ValueError, match="unknown event_type"):
            build_event("BR-001", "not_a_real_event", {"taxonomy": artifact})

    def test_missing_artifact_is_rejected(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            build_event(
                "BR-001", "pipeline_complete", {"taxonomy": tmp_path / "nope.csv"}
            )


class TestChainClient:
    def test_backend_down_queues_instead_of_raising(self, artifact, tmp_path):
        # Port 9 (discard) is reliably closed.
        client = ChainClient("http://127.0.0.1:9", tmp_path / "queue")
        event = build_event("BR-001", "pipeline_complete", {"taxonomy": artifact})
        result = client.record(event)

        assert result["committed"] is False
        assert Path(result["queued_at"]).is_file()

    def test_queue_replays_when_the_backend_returns(self, artifact, tmp_path):
        reset()
        queue = tmp_path / "queue"

        offline = ChainClient("http://127.0.0.1:9", queue)
        offline.record(build_event("BR-002", "pipeline_complete", {"taxonomy": artifact}))
        assert len(list(queue.glob("*.json"))) == 1

        with MockBackend(port=0) as server:
            online = ChainClient(server.url, queue)
            outcome = online.flush_queue()
            assert outcome == {"sent": 1, "failed": 0, "remaining": 0}
            assert not list(queue.glob("*.json"))

            body = urllib.request.urlopen(
                f"{server.url}/api/v1/chain/verify/BR-002"
            ).read()
            verification = json.loads(body)
            assert verification["chain_intact"] is True
            assert verification["event_count"] == 1

    def test_chain_links_successive_records(self, artifact, tmp_path):
        reset()
        with MockBackend(port=0) as server:
            client = ChainClient(server.url, tmp_path / "queue")
            for event_type in ("pipeline_complete", "flagging_complete", "cbi_computed"):
                event = build_event("BR-003", event_type, {"taxonomy": artifact})
                assert client.record(event)["committed"] is True

            body = urllib.request.urlopen(
                f"{server.url}/api/v1/chain/verify/BR-003"
            ).read()
            verification = json.loads(body)

        assert verification["chain_intact"] is True
        assert verification["event_count"] == 3
        assert verification["events"] == [
            "pipeline_complete",
            "flagging_complete",
            "cbi_computed",
        ]

    def test_verify_is_honest_about_an_unknown_sample(self):
        reset()
        with MockBackend(port=0) as server:
            body = urllib.request.urlopen(
                f"{server.url}/api/v1/chain/verify/BR-NEVER-SEEN"
            ).read()
            verification = json.loads(body)
        assert verification["event_count"] == 0


class TestTimeMachine:
    @staticmethod
    def _row(sample: str, species: str, reads: int, genus: str = "G") -> dict[str, str]:
        return {
            "sample_id": sample,
            "asv_id": f"asv-{species}-{reads}",
            "taxon_id": "1",
            "scientific_name": species,
            "rank": "species",
            "kingdom": "Eukaryota",
            "phylum": "Chordata",
            "class": "Actinopteri",
            "order": "O",
            "family": "F",
            "genus": genus,
            "species": species,
            "confidence": "0.95",
            "read_count": str(reads),
            "rel_abundance": "0.5",
            "classification_method": "sklearn",
            "lineage_raw": "",
        }

    def test_detects_appearance_and_disappearance(self):
        before = [self._row("s1", "Species A", 100), self._row("s1", "Species B", 100)]
        after = [self._row("s2", "Species A", 100), self._row("s2", "Species C", 100)]

        diff = compare(before, after, site_id="TEST")

        assert [a["name"] for a in diff["appeared"]] == ["Species C"]
        assert [d["name"] for d in diff["disappeared"]] == ["Species B"]
        assert diff["summary"]["richness_delta"] == 0
        # Jaccard: {A} shared of {A,B,C} union -> 1 - 1/3
        assert diff["summary"]["turnover"] == pytest.approx(0.6667, abs=1e-4)

    def test_abundance_change_is_relative_not_raw(self):
        """Doubling sequencing depth must not look like every species doubled."""
        before = [self._row("s1", "A", 100), self._row("s1", "B", 100)]
        after = [self._row("s2", "A", 200), self._row("s2", "B", 200)]

        diff = compare(before, after, site_id="TEST")

        assert diff["changed"] == []
        assert len(diff["stable"]) == 2

    def test_genuine_expansion_is_flagged(self):
        before = [self._row("s1", "Invasive", 10), self._row("s1", "Native", 990)]
        after = [self._row("s2", "Invasive", 500), self._row("s2", "Native", 500)]

        diff = compare(before, after, site_id="TEST")

        changed = {c["name"]: c for c in diff["changed"]}
        assert changed["Invasive"]["direction"] == "increased"
        assert changed["Invasive"]["log2_fold_change"] > 5
        assert changed["Native"]["direction"] == "decreased"

    def test_genus_only_rows_are_excluded_from_species_comparison(self):
        row = self._row("s1", "", 100)
        row["rank"] = "genus"
        assert aggregate([row], rank="species") == {}
        assert aggregate([row], rank="genus") != {}

    def test_shannon_is_zero_for_a_monoculture(self):
        entries = aggregate([self._row("s1", "Only", 100)], rank="species")
        assert shannon_index(entries) == 0.0

    def test_shannon_rises_with_evenness(self):
        uneven = aggregate(
            [self._row("s1", "A", 990), self._row("s1", "B", 10)], rank="species"
        )
        even = aggregate(
            [self._row("s1", "A", 500), self._row("s1", "B", 500)], rank="species"
        )
        assert shannon_index(even) > shannon_index(uneven)

    def test_invalid_rank_is_rejected(self):
        with pytest.raises(ValueError, match="rank must be one of"):
            aggregate([], rank="subspecies")


class TestMockData:
    @pytest.fixture(scope="class")
    def generated(self):
        sites = load_csv(REPO_ROOT / "data" / "sites.csv")
        species = load_csv(REPO_ROOT / "data" / "species_pool.csv")
        return generate(sites, species, rounds=3, seed=2026)

    def test_mock_detections_satisfy_the_contract(self, generated):
        validate_taxonomy_rows(generated["detections"])

    def test_columns_match_exactly(self, generated):
        assert set(generated["detections"][0]) == set(TAXONOMY_COLUMNS)
        assert set(generated["summaries"][0]) == set(SAMPLE_SUMMARY_COLUMNS)

    def test_generation_is_deterministic(self):
        sites = load_csv(REPO_ROOT / "data" / "sites.csv")
        species = load_csv(REPO_ROOT / "data" / "species_pool.csv")
        first = generate(sites, species, rounds=2, seed=7)
        second = generate(sites, species, rounds=2, seed=7)
        assert first["detections"] == second["detections"]

    def test_every_site_gets_every_round(self, generated):
        sites = load_csv(REPO_ROOT / "data" / "sites.csv")
        assert len(generated["samples"]) == len(sites) * 3

    def test_invaded_site_shows_the_invasive_expanding(self, generated):
        """The Time Machine demo depends on this actually being true."""
        rows = [
            d
            for d in generated["detections"]
            if d["species"] == "Gambusia holbrooki"
            and str(d["sample_id"]).startswith("BR-2026-GOA-MANDOVI")
        ]
        by_round = {str(r["sample_id"])[-3:]: r["rel_abundance"] for r in rows}
        assert by_round["R03"] > by_round["R01"]

    def test_low_confidence_band_is_populated(self, generated):
        """Anshika's AI Second Opinion triggers on 0.70-0.85; mock data must reach it."""
        in_band = [
            d
            for d in generated["detections"]
            if 0.70 <= float(d["confidence"]) <= 0.85
        ]
        assert in_band, "no detections in the second-opinion confidence band"

    def test_unverified_taxids_are_blank_not_invented(self, generated):
        """Fabricated taxids would silently break joins against real references."""
        species = {s["scientific_name"]: s for s in load_csv(
            REPO_ROOT / "data" / "species_pool.csv"
        )}
        for row in generated["detections"]:
            name = row["scientific_name"]
            entry = species.get(name)
            if entry and entry["taxid_verified"] == "no":
                assert row["taxon_id"] == ""

    def test_alerts_example_has_an_invasive(self, generated):
        species = load_csv(REPO_ROOT / "data" / "species_pool.csv")
        alerts = build_alerts_example(generated["detections"], species)
        assert alerts["summary"]["invasive_count"] >= 1


class TestContractValidation:
    def test_missing_column_is_caught(self):
        with pytest.raises(ContractError, match="missing columns"):
            validate_taxonomy_rows([{"sample_id": "a"}])

    def test_out_of_range_confidence_is_caught(self):
        row = {column: "" for column in TAXONOMY_COLUMNS}
        row.update(
            {"sample_id": "s", "asv_id": "a", "rank": "species",
             "confidence": "1.5", "read_count": "10"}
        )
        with pytest.raises(ContractError, match="out of range"):
            validate_taxonomy_rows([row])

    def test_unknown_rank_is_caught(self):
        row = {column: "" for column in TAXONOMY_COLUMNS}
        row.update(
            {"sample_id": "s", "asv_id": "a", "rank": "domain",
             "confidence": "0.9", "read_count": "10"}
        )
        with pytest.raises(ContractError, match="unknown rank"):
            validate_taxonomy_rows([row])


class TestSampleIdentity:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("sample1_S1_L001_R1_001.fastq.gz", "sample1"),
            ("BR-2026-GOA-001_S3_L001_R1_001.fastq.gz", "BR-2026-GOA-001"),
            ("no-underscores.fastq.gz", "no-underscores.fastq.gz"),
        ],
    )
    def test_matches_the_upstream_shell_derivation(self, filename, expected):
        # Mirrors `sample=${R1%%_*}` in scripts/create_metadata_file.sh.
        assert sample_id_from_fastq(filename) == expected


class TestRunIsolation:
    def test_two_runs_get_separate_directories(self, tmp_path):
        """The upstream pipeline has fixed output paths; runs must not share a cwd."""
        from bioradar.pipeline_runner import PipelineRunner

        fastq_dir = REPO_ROOT / "testing_data" / "fastq_data"
        if not fastq_dir.is_dir():
            pytest.skip("test FASTQ data not present")

        runner = PipelineRunner(runs_dir=tmp_path, mode="docker")
        pairs = sorted(fastq_dir.glob("*_R1_001.fastq.gz"))[:1]
        pairs.append(Path(str(pairs[0]).replace("_R1_", "_R2_")))

        first_id, first_dir, _ = runner.prepare_run(pairs)
        second_id, second_dir, _ = runner.prepare_run(pairs)

        assert first_id != second_id
        assert first_dir != second_dir
        assert (first_dir / "Snakefile").is_file()
        assert (second_dir / "config.yaml").is_file()

    def test_reusing_a_run_id_is_refused(self, tmp_path):
        from bioradar.pipeline_runner import PipelineRunner

        fastq_dir = REPO_ROOT / "testing_data" / "fastq_data"
        if not fastq_dir.is_dir():
            pytest.skip("test FASTQ data not present")

        runner = PipelineRunner(runs_dir=tmp_path, mode="docker")
        pairs = sorted(fastq_dir.glob("*_R1_001.fastq.gz"))[:1]
        pairs.append(Path(str(pairs[0]).replace("_R1_", "_R2_")))

        runner.prepare_run(pairs, run_id="fixed")
        with pytest.raises(FileExistsError):
            runner.prepare_run(pairs, run_id="fixed")

    def test_unpaired_reads_are_rejected_early(self, tmp_path):
        from bioradar.pipeline_runner import discover_pairs

        (tmp_path / "orphan_S1_L001_R1_001.fastq.gz").write_bytes(b"")
        with pytest.raises(FileNotFoundError, match="no R2 mate"):
            discover_pairs(tmp_path)
