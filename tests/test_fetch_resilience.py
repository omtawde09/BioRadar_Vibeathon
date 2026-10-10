"""The clean-start path must survive a flaky archive and must never damage committed evidence.

Found by a real clean-start rehearsal: a 504 from one service aborted `fetch`, later steps then ran
on missing files, and a re-run would have duplicated every reference record. These tests pin the fixes.
Network is never touched: calls are monkeypatched.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from bioradar.adjudicate import fetch


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", code, "err", {}, None)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)


def test_5xx_is_retried_then_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _http(504)
        return b"ok"

    assert fetch._retry(flaky, "svc") == b"ok" and calls["n"] == 3


def test_4xx_is_a_real_error_and_not_retried():
    calls = {"n": 0}

    def missing():
        calls["n"] += 1
        raise _http(404)

    with pytest.raises(urllib.error.HTTPError):
        fetch._retry(missing, "svc")
    assert calls["n"] == 1


def test_gives_up_with_a_clear_message_after_the_retry_budget():
    def down():
        raise _http(503)

    with pytest.raises(RuntimeError, match="failed after"):
        fetch._retry(down, "svc")


def test_all_does_not_refetch_committed_snapshots_or_rewrite_the_manifest(monkeypatch, tmp_path):
    for name in ("fetch_records", "fetch_boundary", "fetch_samples"):
        monkeypatch.setattr(fetch, name, lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")))
    monkeypatch.setattr(fetch, "fetch_from_manifest", lambda: "manifest-ok")
    monkeypatch.setattr(fetch, "fetch_reference", lambda: "reference-ok")
    # the repo ships the manifest, the records snapshot and the boundary
    assert fetch.main(["all"]) == 0


def test_a_failing_step_is_reported_and_the_exit_code_is_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(fetch, "fetch_from_manifest", lambda: "ok")

    def boom():
        raise RuntimeError("NCBI unavailable")

    monkeypatch.setattr(fetch, "fetch_reference", boom)
    assert fetch.main(["all"]) == 1
    out = capsys.readouterr().out
    assert "FAILED: NCBI unavailable" in out and "Re-run the same command" in out


def test_reference_fetch_never_appends_duplicates(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path)
    ids = ["1", "2", "3"]
    monkeypatch.setattr(fetch, "_esearch", lambda term, retmax=10000: ids if "Actinopteri" in term else ["9"])
    monkeypatch.setattr(fetch, "BATCH", 2)
    fasta = {"1": ">A1 Genus a\nACGT\n", "2": ">A2 Genus b\nACGT\n", "3": ">A3 Genus c\nACGT\n", "9": ">NC_012920 Homo sapiens\nACGT\n"}
    monkeypatch.setattr(fetch, "_efetch_fasta", lambda batch: "".join(fasta[i] for i in batch))

    target = fetch.fetch_reference()
    first = target.read_text()
    assert first.count(">") == 3
    fetch.fetch_reference()  # second run: cache matches the query, so it is a no-op
    assert target.read_text() == first and first.count(">") == 3
    meta = json.loads((tmp_path / "refseq_fetch.json").read_text())
    assert meta["records_requested"] == 3

    # the query grows (a new RefSeq record): rewrite from scratch, still no duplicates
    ids.append("4")
    fasta["4"] = ">A4 Genus d\nACGT\n"
    fetch.fetch_reference()
    again = target.read_text()
    assert again.count(">") == 4 and len({l for l in again.splitlines() if l.startswith(">")}) == 4
