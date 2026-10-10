"""File-integrity pre-flight.

The failure this prevents is the expensive one: a truncated download that dies
half an hour into DADA2 with an error from inside R that nobody can read.
"""

from __future__ import annotations

import gzip

import pytest

from bioradar import preflight


def write_fastq(path, reads=200, length=180):
    """Pseudo-random sequences, not a repeated motif.

    A repeated motif gzips to almost nothing, so a "small" file would trip the
    byte-size check before reaching the check the test is actually about.
    """
    import random

    rng = random.Random(7)
    body = "".join(
        "@read{i}\n{s}\n+\n{q}\n".format(
            i=i,
            s="".join(rng.choice("ACGT") for _ in range(length)),
            q="".join(rng.choice("FGHI") for _ in range(length)),
        )
        for i in range(reads)
    )
    if str(path).endswith(".gz"):
        with gzip.open(path, "wt") as handle:
            handle.write(body)
    else:
        path.write_text(body, encoding="utf-8")
    return path


def levels(findings, level="error"):
    return [f for f in findings if f.level == level]


def test_a_healthy_file_passes(tmp_path):
    path = write_fastq(tmp_path / "ok.fastq.gz")
    assert levels(preflight.check_integrity(path)) == []


def test_a_truncated_gzip_is_caught(tmp_path):
    """gzip carries a CRC32 and a length in its trailer exactly so this is
    detectable. Reading only the first few reads would sail straight past it."""
    path = write_fastq(tmp_path / "cut.fastq.gz")
    data = path.read_bytes()
    path.write_bytes(data[: int(len(data) * 0.6)])
    errors = levels(preflight.check_integrity(path))
    assert errors
    assert "truncated or corrupt" in errors[0].message


def test_a_file_that_is_not_gzip_is_caught(tmp_path):
    path = tmp_path / "fake.fastq.gz"
    path.write_text("@read1\nACGT\n+\nIIII\n" * 100, encoding="utf-8")
    errors = levels(preflight.check_integrity(path))
    assert errors
    assert "not gzip data" in errors[0].message


def test_a_fasta_mistaken_for_fastq_is_caught(tmp_path):
    path = tmp_path / "seqs.fastq"
    path.write_text(">seq1\nACGTACGT\n>seq2\nTTTTGGGG\n" * 60, encoding="utf-8")
    errors = levels(preflight.check_integrity(path))
    assert any("does not start with '@'" in e.message for e in errors)


def test_an_empty_file_is_caught(tmp_path):
    path = tmp_path / "empty.fastq.gz"
    path.write_bytes(b"")
    errors = levels(preflight.check_integrity(path))
    assert errors
    assert "too small" in errors[0].message


def test_too_few_reads_to_fit_an_error_model_is_caught(tmp_path):
    path = write_fastq(tmp_path / "thin.fastq.gz", reads=40)
    errors = levels(preflight.check_integrity(path))
    assert any("read(s)" in e.message for e in errors)


def test_a_missing_file_is_reported_rather_than_raising(tmp_path):
    errors = levels(preflight.check_integrity(tmp_path / "absent.fastq.gz"))
    assert errors
    assert "missing" in errors[0].message


def test_run_stops_at_the_first_real_problem_per_file(tmp_path):
    """A corrupt file must not also generate a confusing complaint about its
    quality scores -- the transfer is the problem, and saying so once is enough."""
    for mate in (1, 2):
        path = write_fastq(tmp_path / "s_S1_L001_R{m}_001.fastq.gz".format(m=mate))
        data = path.read_bytes()
        path.write_bytes(data[: int(len(data) * 0.5)])

    result = preflight.run(sorted(tmp_path.glob("*_R1_001.fastq.gz")) +
                           sorted(tmp_path.glob("*_R2_001.fastq.gz")))
    assert not result.ok
    checks = {f.check for f in result.errors}
    assert checks == {"integrity"}


def test_the_bundled_test_data_still_passes(tmp_path):
    """A regression guard: the integrity checks must not reject good data."""
    from pathlib import Path

    from bioradar.pipeline_runner import discover_pairs

    data = Path("testing_data/fastq_data")
    if not data.is_dir():
        pytest.skip("bundled test data not present")
    assert preflight.run(discover_pairs(data)).ok
