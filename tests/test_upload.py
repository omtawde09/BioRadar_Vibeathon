"""The 'bring your own file' path: a new file is analysed with the same engine, then forgotten."""

from __future__ import annotations

import glob
import gzip
import json
import tempfile
from pathlib import Path

import pytest

from bioradar.adjudicate import alerts, api, upload

REPO = Path(__file__).resolve().parents[1]
REAL = sorted(glob.glob(str(REPO / "data" / "real_challenge" / "datasets" / "PRJNA1433820_martapura_12S" / "raw" / "*.fastq.gz")))

needs_real = pytest.mark.skipif(not REAL, reason="real data not downloaded")


def _real_slice(limit=600_000) -> bytes:
    """The first records of a real public file, cut at a record boundary (nothing is made up or edited)."""
    raw = gzip.open(REAL[0], "rb").read(limit)
    return raw[:raw.rfind(b"\n@") + 1]


@needs_real
def test_a_new_real_file_is_analysed_like_any_sample():
    result = upload.analyze(_real_slice(), "12S", "my water.fastq")
    assert result["verdict"] in ("Usable", "Usable with caution", "Retake sample")
    assert result["metadata"]["label"] == "my water.fastq"
    assert result["input_format"] == "fastq" and result["quality_scores_available"]
    assert result["uploaded"]["kept_on_server"] is False
    assert result["reads_total"] > 100 and result["species"]
    assert result["expected_check"]["available"] is False       # no published answer for a file we have never seen
    assert result["metadata"]["latitude"] is None               # no location was given, so none is invented


@needs_real
def test_the_file_name_plays_no_part_and_gzip_is_read_by_content():
    raw = _real_slice()
    a = upload.analyze(raw, "12S", "x.txt")
    b = upload.analyze(gzip.compress(raw), "12S", "y.fa")
    assert a["summary"] == b["summary"] and a["reads_total"] == b["reads_total"]


@needs_real
def test_nothing_is_kept_and_no_alert_is_logged():
    before = set(Path(tempfile.gettempdir()).glob("bioradar_upload_*"))
    log_size = alerts.ALERT_LOG.stat().st_size if alerts.ALERT_LOG.is_file() else 0
    upload.analyze(_real_slice(), "12S", "a.fastq")
    assert set(Path(tempfile.gettempdir()).glob("bioradar_upload_*")) == before
    assert (alerts.ALERT_LOG.stat().st_size if alerts.ALERT_LOG.is_file() else 0) == log_size


@pytest.mark.parametrize("raw,message", [
    (b"", "empty"),
    (b"hello, this is a letter and not DNA", "does not look like a sequence file"),
    (b"\x89PNG\r\n\x1a\n\x00\x00", "does not look like a sequence file"),
    (b"\x1f\x8b" + b"not really gzip", "does not look like a sequence file"),
])
def test_files_that_are_not_sequences_get_a_plain_message(raw, message):
    with pytest.raises(upload.UploadError) as err:
        upload.analyze(raw, "12S", "f")
    assert message in str(err.value)


def test_a_file_over_the_limit_is_refused_before_it_is_read():
    with pytest.raises(upload.UploadError) as err:
        upload.analyze(b">x\n" + b"A" * (upload.MAX_BYTES + 1), "12S", "big.fa")
    assert "limit" in str(err.value)


def test_unknown_gene_region_is_refused():
    with pytest.raises(upload.UploadError):
        upload.analyze(b">x\nACGT\n", "XYZ", "f.fa")


def test_the_file_name_cannot_inject_markup_or_paths():
    assert upload._clean_name("..\\..\\evil<script>.fa") == "evilscript.fa"
    assert upload._clean_name("") == "your file" and len(upload._clean_name("a" * 500)) <= 60


def test_api_route_returns_400_with_the_message_and_404_elsewhere():
    status, body, ctype = api.post_raw("/api/adjudicate/analyze", b"not dna", {"marker": ["12S"]})
    assert status == 400 and ctype == "application/json" and "error" in json.loads(body)
    assert api.post_raw("/api/adjudicate/elsewhere", b"", {})[0] == 404


def test_the_web_server_reads_the_body_only_up_to_the_cap():
    source = (REPO / "bioradar" / "webapp.py").read_text(encoding="utf-8")
    assert "adjudicate_upload.MAX_BYTES" in source and "413" in source


def test_a_gzip_bomb_is_refused_without_unpacking_it_all(monkeypatch):
    monkeypatch.setattr(upload, "MAX_UNPACKED", 1024 * 1024)
    bomb = gzip.compress(b">x\n" + b"A" * (5 * 1024 * 1024))   # tiny file, 5 MB once unpacked
    assert len(bomb) < 100_000
    with pytest.raises(upload.UploadError) as err:
        upload.analyze(bomb, "12S", "bomb.fa.gz")
    assert "unpacked" in str(err.value)
