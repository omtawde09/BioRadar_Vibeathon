"""A tampered manifest must not be able to write (or read) outside the data folder, and an aborted
download must not leave a stray `.part` file behind.

The committed manifest's per-file `file` value used to be joined straight onto DATA_DIR and written
to, and its `source_url` was fetched whatever its scheme. These tests pin the guards. Network is
never touched: `_urlopen` / `download_verified` are monkeypatched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bioradar.adjudicate import challenge_manifest as cm
from bioradar.adjudicate import fetch, runner

GOOD_URL = "https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR000/001/SRR0000001/SRR0000001_1.fastq.gz"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network must not be touched")

    monkeypatch.setattr(fetch, "_urlopen", refuse)


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _files_under(root: Path):
    return sorted(p for p in root.rglob("*") if p.is_file())


# --------------------------------------------------------------------------
# _safe_destination / safe_join
# --------------------------------------------------------------------------


@pytest.mark.parametrize("rel", [
    "../x", "/abs", "C:/x", "a/../../x",
    "..", "datasets/../../x", "a\\..\\..\\x", "\\abs", "C:x", "c:\\windows\\x",
    "\\\\server\\share\\x", "//server/share/x", "", "   ", "a/\x00/b",
])
def test_safe_destination_rejects_paths_that_could_escape(rel):
    with pytest.raises(ValueError, match="unsafe path in manifest"):
        fetch._safe_destination(rel)


def test_safe_destination_accepts_a_normal_dataset_file():
    path = fetch._safe_destination("datasets/X/raw/f.fastq.gz")
    root = fetch.DATA_DIR.resolve()
    assert path == root / "datasets" / "X" / "raw" / "f.fastq.gz"
    path.relative_to(root)  # inside DATA_DIR (raises ValueError otherwise)


def test_safe_destination_follows_a_monkeypatched_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch, "DATA_DIR", tmp_path / "data")
    assert fetch._safe_destination("datasets/X/raw/f.fastq.gz") == \
        (tmp_path / "data").resolve() / "datasets" / "X" / "raw" / "f.fastq.gz"


# --------------------------------------------------------------------------
# fetch_from_manifest refuses a tampered manifest before writing anything
# --------------------------------------------------------------------------


def _write_manifest(data_dir: Path, files):
    data_dir.mkdir(parents=True, exist_ok=True)
    doc = {"datasets": [{"bioproject": "PRJTEST", "title": "t", "runs": [
        {"run_accession": "SRR0000001", "files": files}]}]}
    (data_dir / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")


def _file(rel: str, url: str = GOOD_URL):
    return {"file": rel, "md5": _md5(b"x"), "bytes": 1, "source_url": url}


@pytest.fixture
def recorded_downloads(monkeypatch):
    calls = []

    def fake(url, destination, md5, expected_bytes=None):
        calls.append((url, destination, md5, expected_bytes))
        return "cached"

    monkeypatch.setattr(fetch, "download_verified", fake)
    return calls


@pytest.mark.parametrize("bad", ["../../evil.txt", "datasets/../../evil.txt", "C:/evil.txt", "/evil.txt"])
def test_fetch_from_manifest_refuses_a_traversal_path_and_writes_nothing(
        monkeypatch, tmp_path, recorded_downloads, no_network, bad):
    data_dir = tmp_path / "sandbox" / "data"
    monkeypatch.setattr(fetch, "DATA_DIR", data_dir)
    # the good entry comes first: nothing at all may be fetched once a bad one is seen
    _write_manifest(data_dir, [_file("datasets/X/raw/ok.fastq.gz"), _file(bad)])
    before = _files_under(tmp_path)
    with pytest.raises(ValueError, match="unsafe path in manifest"):
        fetch.fetch_from_manifest()
    assert recorded_downloads == []
    assert _files_under(tmp_path) == before
    assert not (tmp_path / "evil.txt").exists() and not (tmp_path / "sandbox" / "evil.txt").exists()


@pytest.mark.parametrize("url", [
    "http://ftp.sra.ebi.ac.uk/x.fastq.gz", "ftp://ftp.sra.ebi.ac.uk/x.fastq.gz",
    "file:///etc/passwd", "file://C:/Windows/win.ini", "https:///no-host", "", "ftp.sra.ebi.ac.uk/x",
])
def test_fetch_from_manifest_refuses_a_non_https_source_url(
        monkeypatch, tmp_path, recorded_downloads, no_network, url):
    monkeypatch.setattr(fetch, "DATA_DIR", tmp_path / "data")
    _write_manifest(tmp_path / "data", [_file("datasets/X/raw/ok.fastq.gz"),
                                        _file("datasets/X/raw/bad.fastq.gz", url)])
    with pytest.raises(ValueError, match="https://"):
        fetch.fetch_from_manifest()
    assert recorded_downloads == []


def test_fetch_from_manifest_passes_safe_destinations_and_sizes(monkeypatch, tmp_path, recorded_downloads):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(fetch, "DATA_DIR", data_dir)
    entry = dict(_file("datasets/X/raw/ok.fastq.gz"), bytes=1234)
    _write_manifest(data_dir, [entry])
    assert fetch.fetch_from_manifest() == data_dir / "manifest.json"
    [(url, destination, md5, expected_bytes)] = recorded_downloads
    assert url == GOOD_URL and md5 == entry["md5"] and expected_bytes == 1234
    assert destination == data_dir.resolve() / "datasets" / "X" / "raw" / "ok.fastq.gz"


def test_download_verified_itself_refuses_non_https(tmp_path, no_network):
    with pytest.raises(ValueError, match="https://"):
        fetch.download_verified("http://example.org/f.gz", tmp_path / "f.gz", _md5(b""))
    assert _files_under(tmp_path) == []


# --------------------------------------------------------------------------
# download_verified never leaves a .part file behind
# --------------------------------------------------------------------------


class _Stream:
    """A fake HTTP response: yields `chunks`, then raises `error` (if any), then EOF."""

    def __init__(self, chunks, error=None):
        self._chunks = list(chunks)
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size=-1):
        if self._chunks:
            return self._chunks.pop(0)
        if self._error is not None:
            raise self._error
        return b""


def _serve(monkeypatch, make):
    calls = {"n": 0}

    def fake_urlopen(url, timeout):
        calls["n"] += 1
        return make()

    monkeypatch.setattr("bioradar.adjudicate.fetch._urlopen", fake_urlopen)
    return calls


def test_part_file_is_removed_when_the_stream_breaks_and_retries_run_out(monkeypatch, tmp_path):
    calls = _serve(monkeypatch, lambda: _Stream([b"A" * 1024], ConnectionResetError("reset by peer")))
    dest = tmp_path / "raw" / "f.fastq.gz"
    with pytest.raises(RuntimeError, match="failed after"):
        fetch.download_verified(GOOD_URL, dest, _md5(b"A" * 2048), expected_bytes=2048)
    assert calls["n"] == fetch.RETRIES
    assert not dest.with_suffix(dest.suffix + ".part").exists() and not dest.exists()
    assert _files_under(tmp_path) == []


def test_part_file_is_removed_on_a_non_network_error_too(monkeypatch, tmp_path):
    calls = _serve(monkeypatch, lambda: _Stream([b"A" * 1024], ValueError("decoder blew up")))
    dest = tmp_path / "f.fastq.gz"
    with pytest.raises(ValueError, match="decoder blew up"):
        fetch.download_verified(GOOD_URL, dest, _md5(b"A"))
    assert calls["n"] == 1  # not a network error: not retried
    assert _files_under(tmp_path) == []


def test_md5_mismatch_leaves_no_part_file_and_no_destination(monkeypatch, tmp_path):
    _serve(monkeypatch, lambda: _Stream([b"corrupted"]))
    dest = tmp_path / "f.fastq.gz"
    with pytest.raises(RuntimeError, match="md5 mismatch"):
        fetch.download_verified(GOOD_URL, dest, _md5(b"original"))
    assert _files_under(tmp_path) == []


def test_size_mismatch_is_caught_before_replacing(monkeypatch, tmp_path):
    data = b"short"
    _serve(monkeypatch, lambda: _Stream([data]))
    dest = tmp_path / "f.fastq.gz"
    with pytest.raises(RuntimeError, match="size mismatch"):
        fetch.download_verified(GOOD_URL, dest, _md5(data), expected_bytes=len(data) + 10)
    assert _files_under(tmp_path) == []


def test_a_good_download_replaces_atomically_and_is_then_cached(monkeypatch, tmp_path):
    data = b"ACGT" * 1000
    calls = _serve(monkeypatch, lambda: _Stream([data[:1500], data[1500:]]))
    dest = tmp_path / "raw" / "f.fastq.gz"
    assert fetch.download_verified(GOOD_URL, dest, _md5(data), expected_bytes=len(data)) == "downloaded"
    assert dest.read_bytes() == data and _files_under(tmp_path) == [dest]
    # positional, 3-argument call (the old signature) still works and hits the cache
    assert fetch.download_verified(GOOD_URL, dest, _md5(data)) == "cached"
    assert calls["n"] == 1


# --------------------------------------------------------------------------
# challenge_manifest: same guard for reading, one row per manifest file
# --------------------------------------------------------------------------


def _run(accession, alias, files, experiment="Illumina MiSeq sequencing: 12S seq of water sample"):
    return {
        "run_accession": accession, "biosample": "SAMN" + accession[3:], "sample_alias": alias,
        "collection_date": "2019-08", "location": "China:Somewhere",
        "latitude_longitude_as_deposited": ["22.0", "113.0"],
        "design_note_from_submitter": "", "biosample_attributes": {},
        "experiment": experiment, "instrument": "Illumina MiSeq", "read_pairs": 10, "files": files,
    }


@pytest.fixture
def challenge_dir(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ref_dir = tmp_path / "ref"
    ref_dir.mkdir()
    (ref_dir / "reference.json").write_text(json.dumps({"reference_database_version": "test-v1"}),
                                            encoding="utf-8")
    monkeypatch.setattr(runner, "DATA_DIR", data_dir)
    monkeypatch.setattr(runner, "MANIFEST", data_dir / "manifest.json")
    monkeypatch.setattr(cm, "REF_DIR", ref_dir)

    def write(datasets):
        (data_dir / "manifest.json").write_text(json.dumps({"datasets": datasets}), encoding="utf-8")

    return data_dir, write


def test_challenge_manifest_one_row_per_file_present_and_missing(challenge_dir):
    data_dir, write = challenge_dir
    present = b"@r1\nACGT\n+\nIIII\n"
    rel_ok = "datasets/D/raw/SRR0000001_1.fastq.gz"
    (data_dir / rel_ok).parent.mkdir(parents=True)
    (data_dir / rel_ok).write_bytes(present)
    files = [
        {"file": rel_ok, "md5": _md5(present), "bytes": len(present), "source_url": GOOD_URL},
        {"file": "datasets/D/raw/SRR0000002_1.fastq.gz", "md5": _md5(b"nope"), "bytes": 4,
         "source_url": GOOD_URL.replace("0000001", "0000002")},
    ]
    write([{"bioproject": "PRJTEST", "title": "Some estuarine fish data",
            "runs": [_run("SRR0000001", "A1", files[:1]), _run("SRR0000002", "A2", files[1:])]}])
    rows = cm.build_rows()
    assert len(rows) == len(files)
    assert all(set(r) == set(cm.COLUMNS) for r in rows)
    ok, missing = rows
    assert ok["verified"] == "yes" and len(ok["sha256_local"]) == 64
    assert ok["sha256_local"] == hashlib.sha256(present).hexdigest() and ok["md5_local"] == ok["md5_archive"]
    assert missing["verified"].startswith("MISSING") and missing["sha256_local"] == ""
    assert ok["reference_version"] == "test-v1"


def test_challenge_manifest_rejects_an_unsafe_path_without_reading_it(challenge_dir, tmp_path):
    data_dir, write = challenge_dir
    secret = b"outside the data folder"
    (tmp_path / "x").write_bytes(secret)  # a real file the tampered path points at
    files = [{"file": "../x", "md5": _md5(secret), "bytes": len(secret), "source_url": GOOD_URL}]
    write([{"bioproject": "PRJTEST", "title": "t", "runs": [_run("SRR0000003", "B1", files)]}])
    [row] = cm.build_rows()
    assert row["verified"] == "REJECTED: unsafe path in manifest"
    assert row["md5_local"] == "" and row["sha256_local"] == ""


def test_marker_is_inferred_only_from_archive_text_and_says_so(challenge_dir):
    data_dir, write = challenge_dir
    f = {"file": "datasets/D/raw/a.fastq.gz", "md5": _md5(b"a"), "bytes": 1, "source_url": GOOD_URL}
    write([
        {"bioproject": "PRJ1", "title": "eDNA survey", "runs": [
            _run("SRR0000004", "C1", [dict(f)], experiment="Illumina iSeq 100 sequencing: August Mifish site 3")]},
        {"bioproject": "PRJ2", "title": "12S water sample data", "runs": [
            _run("SRR0000005", "C2", [dict(f, file="datasets/D/raw/b.fastq.gz")], experiment="Illumina MiSeq run")]},
        {"bioproject": "PRJ3", "title": "eDNA survey", "runs": [
            _run("SRR0000006", "C3", [dict(f, file="datasets/D/raw/c.fastq.gz")], experiment="Illumina MiSeq run")]},
    ])
    by_run = {r["run_accession"]: r for r in cm.build_rows()}
    from_experiment = by_run["SRR0000004"]
    assert from_experiment["assay_as_deposited"] == "Illumina iSeq 100 sequencing: August Mifish site 3"
    assert from_experiment["marker_inferred"] == "12S rRNA (MiFish primer family)"
    assert from_experiment["marker_basis"] == (
        "inferred from dataset title / experiment text: Illumina iSeq 100 sequencing: August Mifish site 3")
    from_title = by_run["SRR0000005"]
    assert from_title["marker_inferred"] == "12S rRNA (MiFish primer family)"
    assert from_title["marker_basis"].endswith(": 12S water sample data")
    unstated = by_run["SRR0000006"]
    assert unstated["assay_as_deposited"] == "Illumina MiSeq run"
    assert unstated["marker_inferred"] == "" and unstated["marker_basis"] == "not stated in archive metadata"
    assert "Miya" not in json.dumps(list(by_run.values()))  # no citation the archive does not carry
