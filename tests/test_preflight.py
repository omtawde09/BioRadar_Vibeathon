"""Tests for the pre-flight checks.

Every scenario here is a failure that actually cost 20-60 minutes of pipeline
time on this project before the checks existed. The point of these tests is that
those failures now surface in under a second.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from bioradar import preflight
from bioradar.train_classifier import reverse_complement

FORWARD = "GGWACWGGWTGAACWGTWTAYCCYCC"
REVERSE = "TANACYTCNGGRTGNCCRAARAAYCA"


def write_fastq(
    path: Path,
    *,
    reads: int = 200,
    length: int = 251,
    quality_levels: int = 20,
    prefix: str = "",
) -> Path:
    """Write a synthetic FASTQ with controllable quality diversity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as handle:
        for index in range(reads):
            body = "ACGT" * length
            sequence = (prefix + body)[:length]
            if quality_levels <= 1:
                quality = "?" * length
            else:
                quality = "".join(
                    chr(33 + 20 + ((index + position) % quality_levels))
                    for position in range(length)
                )
            handle.write(f"@read{index}\n{sequence}\n+\n{quality}\n")
    return path


@pytest.fixture
def good_pair(tmp_path: Path) -> list[Path]:
    r1 = write_fastq(tmp_path / "S1_S1_L001_R1_001.fastq.gz", prefix="GGTACTGGTTGAACTGTTTATCCTCCT")
    r2 = write_fastq(tmp_path / "S1_S1_L001_R2_001.fastq.gz", prefix="TATACTTCTGGATGGCCAAAGAATCA")
    return [r1, r2]


class TestQualityEncoding:
    def test_flat_quality_is_an_error(self, tmp_path):
        """The Lakshadweep failure: one Q value for every base."""
        path = write_fastq(tmp_path / "flat_S1_L001_R1_001.fastq.gz", quality_levels=1)
        finding, distinct = preflight.check_quality_encoding(path)
        assert distinct == 1
        assert finding is not None
        assert finding.level == "error"
        assert "Q30" in finding.message
        assert "cannot be denoised" in finding.hint

    def test_binned_quality_is_a_warning_not_an_error(self, tmp_path):
        path = write_fastq(tmp_path / "binned_S1_L001_R1_001.fastq.gz", quality_levels=4)
        finding, distinct = preflight.check_quality_encoding(path)
        assert distinct == 4
        assert finding is not None
        assert finding.level == "warning"

    def test_normal_quality_passes(self, tmp_path):
        path = write_fastq(tmp_path / "ok_S1_L001_R1_001.fastq.gz", quality_levels=20)
        finding, distinct = preflight.check_quality_encoding(path)
        assert finding is None
        assert distinct >= 8

    def test_empty_file_is_an_error(self, tmp_path):
        path = tmp_path / "empty_S1_L001_R1_001.fastq.gz"
        with gzip.open(path, "wt"):
            pass
        finding, _ = preflight.check_quality_encoding(path)
        assert finding is not None and finding.level == "error"


class TestTruncation:
    def test_trunc_longer_than_reads_is_an_error(self, good_pair):
        """The Goa failure: truncLen 240 against 226 bp post-trim reads."""
        findings = preflight.check_truncation(*good_pair, 300, 200)
        errors = [f for f in findings if f.level == "error"]
        assert errors
        assert "exceeds the median read length" in errors[0].message

    def test_trunc_near_read_length_warns(self, good_pair):
        findings = preflight.check_truncation(*good_pair, 245, 100)
        assert any(f.level == "warning" for f in findings)

    def test_reasonable_truncation_is_silent(self, good_pair):
        assert preflight.check_truncation(*good_pair, 200, 180) == []

    def test_truncation_too_short_to_merge_is_an_error(self, good_pair):
        """Mates that cannot overlap produce zero ASVs from a 'successful' run."""
        findings = preflight.check_truncation(*good_pair, 150, 150, 313)
        errors = [f for f in findings if f.level == "error"]
        assert errors
        assert "cannot span" in errors[0].message

    def test_truncation_sufficient_to_merge_passes(self, good_pair):
        findings = preflight.check_truncation(*good_pair, 200, 180, 313)
        assert not [f for f in findings if f.level == "error"]


class TestPrimers:
    def test_primers_present_in_expected_orientation(self, good_pair):
        findings = preflight.check_primers(*good_pair, FORWARD, REVERSE)
        assert not [f for f in findings if f.level == "error"]

    def test_absent_primers_are_an_error(self, tmp_path):
        r1 = write_fastq(tmp_path / "x_S1_L001_R1_001.fastq.gz", prefix="TTTTTTTTTT")
        r2 = write_fastq(tmp_path / "x_S1_L001_R2_001.fastq.gz", prefix="TTTTTTTTTT")
        findings = preflight.check_primers(r1, r2, FORWARD, REVERSE)
        errors = [f for f in findings if f.level == "error"]
        assert errors
        assert "discard-untrimmed" in errors[0].hint

    def test_swapped_mates_are_detected(self, tmp_path):
        """The Lakshadweep orientation problem: reverse primer dominating R1."""
        r1 = write_fastq(
            tmp_path / "s_S1_L001_R1_001.fastq.gz", prefix="TATACTTCTGGATGGCCAAAGAATCA"
        )
        r2 = write_fastq(
            tmp_path / "s_S1_L001_R2_001.fastq.gz", prefix="GGTACTGGTTGAACTGTTTATCCTCCT"
        )
        findings = preflight.check_primers(r1, r2, FORWARD, REVERSE)
        errors = [f for f in findings if f.level == "error"]
        assert errors
        assert "swapped" in errors[0].message
        assert "--swap-mates" in errors[0].hint


class TestRun:
    def test_clean_input_passes(self, good_pair):
        result = preflight.run(
            good_pair,
            forward_primer=FORWARD,
            reverse_primer=REVERSE,
            trunc_len_f=200,
            trunc_len_r=180,
        )
        assert result.ok
        assert result.stats["samples"] == 1

    def test_missing_mate_is_an_error(self, tmp_path):
        r1 = write_fastq(tmp_path / "lonely_S1_L001_R1_001.fastq.gz")
        result = preflight.run([r1])
        assert not result.ok
        assert any("no R2 mate" in f.message for f in result.errors)

    def test_no_r1_files_is_an_error(self, tmp_path):
        stray = write_fastq(tmp_path / "weird.fastq.gz")
        result = preflight.run([stray])
        assert not result.ok

    def test_identical_findings_are_deduplicated(self, tmp_path):
        """A whole study shares one problem; report it once, not per sample."""
        paths = []
        for sample in range(3):
            paths.append(
                write_fastq(
                    tmp_path / f"s{sample}_S1_L001_R1_001.fastq.gz", quality_levels=1
                )
            )
            paths.append(
                write_fastq(
                    tmp_path / f"s{sample}_S1_L001_R2_001.fastq.gz", quality_levels=1
                )
            )
        result = preflight.run(paths)
        assert not result.ok
        # Six files, six distinct filenames -> six findings, but each appears once.
        messages = [f.message for f in result.errors]
        assert len(messages) == len(set(messages))

    def test_render_is_human_readable(self, tmp_path):
        path = write_fastq(tmp_path / "f_S1_L001_R1_001.fastq.gz", quality_levels=1)
        write_fastq(tmp_path / "f_S1_L001_R2_001.fastq.gz", quality_levels=1)
        result = preflight.run([path])
        text = result.render()
        assert "ERROR" in text and "->" in text


class TestReverseComplement:
    def test_iupac_codes_are_preserved(self):
        assert reverse_complement("TANACYTCNGGRTGNCCRAARAAYCA") == (
            "TGRTTYTTYGGNCAYCCNGARGTNTA"
        )

    def test_round_trip(self):
        primer = "GGWACWGGWTGAACWGTWTAYCCYCC"
        assert reverse_complement(reverse_complement(primer)) == primer
