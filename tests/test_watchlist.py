"""Watchlist screening -- what the alerting layer actually alerts on."""

from __future__ import annotations

import pytest

from bioradar import watchlist


@pytest.fixture
def listfile(tmp_path):
    path = tmp_path / "species_pool.csv"
    path.write_text(
        "scientific_name,common_name,family,india_status\n"
        "Gambusia holbrooki,Eastern mosquitofish,Poeciliidae,invasive\n"
        "Carassius auratus,Goldfish,Cyprinidae,introduced\n"
        "Homo sapiens,Human,Hominidae,contamination\n"
        "Tenualosa ilisha,Hilsa,Clupeidae,native\n",
        encoding="utf-8",
    )
    return path


def species(name, reads=500, **kwargs):
    entry = {"name": name, "reads": reads, "sites": {"GOA-MANDOVI"},
             "samples": {"S1"}, "max_confidence": 0.93}
    entry.update(kwargs)
    return entry


def test_invasive_detections_raise_a_high_severity_alert(listfile):
    result = watchlist.screen([species("Gambusia holbrooki")], path=listfile)
    assert result["summary"]["high"] == 1
    assert result["alerts"][0]["severity"] == "high"
    assert result["alerts"][0]["common_name"] == "Eastern mosquitofish"


def test_native_species_are_not_alerts(listfile):
    result = watchlist.screen([species("Tenualosa ilisha")], path=listfile)
    assert result["alerts"] == []


def test_unlisted_species_are_not_alerts(listfile):
    result = watchlist.screen([species("Oncorhynchus mykiss")], path=listfile)
    assert result["alerts"] == []


def test_a_lab_contaminant_outranks_an_established_introduction(listfile):
    """A positive for a known contaminant means the run itself may be untrustworthy,
    which is more urgent than a non-native that has been here for a century."""
    result = watchlist.screen(
        [species("Carassius auratus"), species("Homo sapiens")], path=listfile
    )
    assert [a["severity"] for a in result["alerts"]] == ["high", "medium"]
    assert result["alerts"][0]["scientific_name"] == "Homo sapiens"


def test_a_single_read_does_not_raise_an_alarm(listfile):
    """Read counts in the low single digits are routinely index-hopping between
    samples on one flow cell. Alerting on them trains everybody to ignore alerts."""
    result = watchlist.screen(
        [species("Gambusia holbrooki", reads=1)], path=listfile, min_reads=5
    )
    assert result["alerts"] == []


def test_matching_is_case_insensitive(listfile):
    result = watchlist.screen([species("gambusia HOLBROOKI")], path=listfile)
    assert len(result["alerts"]) == 1


def test_alerts_are_ranked_by_severity_then_abundance(listfile):
    result = watchlist.screen([
        species("Carassius auratus", reads=9000),
        species("Gambusia holbrooki", reads=100),
        species("Homo sapiens", reads=50),
    ], path=listfile)
    assert [a["severity"] for a in result["alerts"]] == ["high", "high", "medium"]
    assert result["alerts"][0]["reads"] >= result["alerts"][1]["reads"]


def test_a_missing_watchlist_degrades_to_no_alerts(tmp_path):
    """Not a crash, and not a silent empty result that looks like an all-clear."""
    result = watchlist.screen([species("Gambusia holbrooki")], path=tmp_path / "gone.csv")
    assert result["alerts"] == []
    assert result["watchlist_size"] == 0
    assert "No watchlist file" in result["note"]


def test_the_bundled_watchlist_loads():
    listed = watchlist.load_watchlist()
    assert listed, "data/species_pool.csv should ship with the repo"
    assert any(row.get("india_status") == "invasive" for row in listed.values())
