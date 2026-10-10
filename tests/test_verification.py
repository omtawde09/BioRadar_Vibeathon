"""Field verification: evidence, not opinion.

The rules under test are the ones that make the feature trustworthy rather than
decorative -- append-only storage, two independent confirmations before a
verdict, and disagreement surfacing as disagreement instead of being averaged
into a comfortable middle.
"""

from __future__ import annotations

import json

import pytest

from bioradar import verification


@pytest.fixture
def store(tmp_path):
    return tmp_path / "verifications.jsonl"


def add(store, name="Gambusia holbrooki", site="GOA-MANDOVI",
        outcome=verification.CONFIRMED, **kwargs):
    return verification.record(
        scientific_name=name, site_id=site, outcome=outcome, store=store, **kwargs
    )


def test_records_are_appended_never_rewritten(store):
    add(store, observer="A")
    add(store, observer="B", outcome=verification.NOT_FOUND)
    lines = store.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["observer"] == "A"


def test_unknown_outcome_is_rejected(store):
    with pytest.raises(ValueError):
        add(store, outcome="probably")


def test_misidentification_requires_saying_what_was_there(store):
    """The useful half of "that's not it" is what it actually was."""
    with pytest.raises(ValueError):
        add(store, outcome=verification.MISIDENTIFIED)
    entry = add(store, outcome=verification.MISIDENTIFIED, observed_name="Poecilia reticulata")
    assert entry["observed_name"] == "Poecilia reticulata"


def test_one_confirmation_is_not_a_verdict(store):
    """A single observer can be mistaken, and eDNA detections are precisely the
    cases where the observer already expects to find something."""
    add(store, observer="A")
    assert verification.tally(store)["gambusia holbrooki@goa-mandovi"]["status"] == \
        verification.UNVERIFIED


def test_two_independent_confirmations_verify(store):
    add(store, observer="A")
    add(store, observer="B")
    assert verification.tally(store)["gambusia holbrooki@goa-mandovi"]["status"] == \
        verification.VERIFIED


def test_two_negatives_dispute(store):
    add(store, outcome=verification.NOT_FOUND, observer="A")
    add(store, outcome=verification.NOT_FOUND, observer="B")
    assert verification.tally(store)["gambusia holbrooki@goa-mandovi"]["status"] == \
        verification.DISPUTED


def test_disagreement_is_reported_as_disagreement(store):
    add(store, outcome=verification.CONFIRMED, observer="A")
    add(store, outcome=verification.NOT_FOUND, observer="B")
    assert verification.tally(store)["gambusia holbrooki@goa-mandovi"]["status"] == \
        verification.CONTESTED


def test_status_is_per_site_not_per_species(store):
    """The same taxon can be genuinely present at one site and absent 40 km away."""
    add(store, site="GOA-MANDOVI", observer="A")
    add(store, site="GOA-MANDOVI", observer="B")
    add(store, site="GOA-ZUARI", outcome=verification.NOT_FOUND, observer="C")
    add(store, site="GOA-ZUARI", outcome=verification.NOT_FOUND, observer="D")
    counts = verification.tally(store)
    assert counts["gambusia holbrooki@goa-mandovi"]["status"] == verification.VERIFIED
    assert counts["gambusia holbrooki@goa-zuari"]["status"] == verification.DISPUTED


def test_annotate_attaches_status_without_touching_confidence(store):
    """Human evidence changes presentation, never the classifier's number.

    Rewriting confidence retroactively would break the guarantee that the same
    input produces the same output, which is what the chain-of-custody hash
    depends on.
    """
    add(store, observer="A")
    add(store, observer="B")
    species = [{"name": "Gambusia holbrooki", "max_confidence": 0.91, "sites": ["GOA-MANDOVI"]}]
    annotated = verification.annotate(species, {"Gambusia holbrooki": ["GOA-MANDOVI"]}, store)
    assert annotated[0]["verification"]["status"] == verification.VERIFIED
    assert annotated[0]["max_confidence"] == 0.91


def test_unverified_species_still_get_a_status_field(store):
    add(store, observer="A")
    species = [{"name": "Oncorhynchus mykiss", "sites": ["GOA-MANDOVI"]}]
    annotated = verification.annotate(species, None, store)
    assert annotated[0]["verification"]["status"] == verification.UNVERIFIED


def test_a_corrupt_line_does_not_hide_the_rest(store):
    add(store, observer="A")
    with store.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    add(store, observer="B")
    assert len(verification.load(store)) == 2


def test_missing_store_is_empty_not_an_error(tmp_path):
    assert verification.load(tmp_path / "nothing.jsonl") == []
    assert verification.tally(tmp_path / "nothing.jsonl") == {}
