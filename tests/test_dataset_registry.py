"""The bundled dataset registry, and the rule that the UI must not edit it.

`data/datasets.json` is tracked in git and is what gives a fresh clone
something to run immediately -- both READMEs tell a new teammate to click
Analyze on the bundled demo survey.

An earlier version of the Remove button dropped the entry from that file, so a
click in the UI silently produced a source-code change. It was committed by
accident twice; the second time it reached the public repository, where every
new clone saw an empty dataset list and no explanation. These tests exist so
that cannot happen a third time.
"""

from __future__ import annotations

import json

import pytest

from bioradar import webapp


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the registry and the hidden-overlay at a scratch directory."""
    registry = tmp_path / "datasets.json"
    registry.write_text(json.dumps({"datasets": [
        {"id": "demo-survey", "name": "Demo", "fastq_dir": "data/demo_survey/fastq"},
        {"id": "other", "name": "Other", "fastq_dir": "data/other/fastq"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(webapp, "DATASETS_FILE", registry)
    monkeypatch.setattr(webapp, "HIDDEN_FILE", tmp_path / ".hidden_datasets.json")
    monkeypatch.setattr(webapp, "UPLOAD_ROOT", tmp_path / "uploads")
    return registry


def test_removing_a_bundled_dataset_does_not_touch_the_tracked_file(isolated):
    before = isolated.read_text(encoding="utf-8")
    assert webapp._remove_registry_entry("demo-survey") is True
    assert isolated.read_text(encoding="utf-8") == before, (
        "the UI edited data/datasets.json -- that is a tracked source file and a "
        "click must never change it"
    )


def test_a_removed_dataset_stops_being_listed(isolated):
    assert [d["id"] for d in webapp.all_datasets()] == ["demo-survey", "other"]
    webapp._remove_registry_entry("demo-survey")
    assert [d["id"] for d in webapp.all_datasets()] == ["other"]


def test_the_removal_is_recorded_outside_git(isolated):
    webapp._remove_registry_entry("demo-survey")
    assert webapp.HIDDEN_FILE.is_file()
    assert json.loads(webapp.HIDDEN_FILE.read_text(encoding="utf-8")) == ["demo-survey"]


def test_removals_accumulate(isolated):
    webapp._remove_registry_entry("demo-survey")
    webapp._remove_registry_entry("other")
    assert webapp.all_datasets() == []
    assert webapp.hidden_dataset_ids() == {"demo-survey", "other"}


def test_removing_twice_reports_nothing_to_do(isolated):
    assert webapp._remove_registry_entry("demo-survey") is True
    assert webapp._remove_registry_entry("demo-survey") is False


def test_removing_an_unknown_dataset_reports_nothing_to_do(isolated):
    assert webapp._remove_registry_entry("no-such-dataset") is False


def test_everything_can_be_brought_back(isolated):
    webapp._remove_registry_entry("demo-survey")
    webapp._remove_registry_entry("other")
    assert webapp.restore_hidden_datasets() == 2
    assert [d["id"] for d in webapp.all_datasets()] == ["demo-survey", "other"]


def test_a_corrupt_overlay_does_not_hide_everything(isolated):
    """Failing open matters: a damaged preference file must not make the app
    look empty, which is indistinguishable from the bug this replaced."""
    webapp.HIDDEN_FILE.write_text("{not json", encoding="utf-8")
    assert webapp.hidden_dataset_ids() == set()
    assert len(webapp.all_datasets()) == 2


# --------------------------------------------------------------------------
# The shipped file itself
# --------------------------------------------------------------------------


def test_the_repository_ships_the_demo_dataset():
    """A fresh clone must have something to run.

    If this fails, data/datasets.json was emptied -- almost certainly by
    pressing Remove in the UI and committing the result. Restore it from git
    history rather than retyping it.
    """
    payload = json.loads(webapp.DATASETS_FILE.read_text(encoding="utf-8"))
    ids = [d["id"] for d in payload.get("datasets", [])]
    assert "demo-survey" in ids, (
        "data/datasets.json no longer lists demo-survey, so a fresh clone opens "
        "with an empty dataset list and the README's first-run instructions fail"
    )


def test_the_shipped_demo_entry_points_at_files_that_exist():
    payload = json.loads(webapp.DATASETS_FILE.read_text(encoding="utf-8"))
    entry = next(d for d in payload["datasets"] if d["id"] == "demo-survey")

    fastq_dir = webapp.REPO_ROOT / entry["fastq_dir"]
    assert fastq_dir.is_dir(), "{d} is missing".format(d=entry["fastq_dir"])

    r1 = sorted(fastq_dir.glob("*_R1_001.fastq.gz"))
    assert len(r1) == 12, "expected 12 samples, found {n}".format(n=len(r1))
    for forward in r1:
        reverse = forward.parent / forward.name.replace("_R1_", "_R2_")
        assert reverse.is_file(), "{f} has no R2 mate".format(f=forward.name)

    samples = webapp.REPO_ROOT / entry["samples_csv"]
    assert samples.is_file(), "the sample sheet is missing, so the map will be empty"
