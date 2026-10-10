"""Tests for bioradar.relatives.traits: evidence only from observations, profile from relatives."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from bioradar.relatives import traits
from bioradar.relatives.traits import (
    FACTORS,
    NO_DATA_STATUS,
    OBSERVABLE_FROM_EDNA,
    RULES,
    TraitTable,
    compare,
    evidence,
    inferred_profile,
    load_traits,
    sample_context,
)

SRC = "Test source"


def _write(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["species", "factor", "value", "unit", "source", "source_url", "retrieved"])
        writer.writerows(rows)


def _row(factor, value, unit="", source=SRC):
    return {"species": "X", "factor": factor, "value": value, "unit": unit,
            "source": source, "source_url": "https://example.org/x", "retrieved": "2026-01-01"}


@pytest.fixture
def table(tmp_path):
    _write(tmp_path / "a.csv", [
        ["Labeo rohita", "habitat", "freshwater", "", SRC, "", ""],
        ["Labeo rohita", "diet", "herbivore", "", SRC, "", ""],
        ["Labeo rohita", "trophic_level", "2.0", "", SRC, "", ""],
        ["Labeo rohita", "country_native", "India;Bangladesh", "", SRC, "", ""],
        ["Lates calcarifer", "habitat", "freshwater;brackish;marine", "", SRC, "", ""],
        ["Lates calcarifer", "trophic_level", "4.0", "", SRC, "", ""],
    ])
    _write(tmp_path / "b.csv", [
        ["labeo  rohita", "karyotype_2n", "50", "", "Other source", "", ""],
        ["Catla catla", "diet", "planktivore", "", SRC, "", ""],
        ["Catla catla", "habitat", "freshwater", "", "", "", ""],          # no source -> rejected
        ["Catla catla", "colour", "silver", "", SRC, "", ""],              # unknown factor
        ["Catla catla", "trophic_level", "high", "", SRC, "", ""],         # not numeric
    ])
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    return load_traits(tmp_path)


# --------------------------------------------------------------------------- loading

def test_load_and_coverage(table):
    assert table.files == ["a.csv", "b.csv"]
    cov = table.coverage()
    assert set(cov) == set(FACTORS)
    assert cov["habitat"] == 2
    assert cov["diet"] == 2
    assert cov["trophic_level"] == 2
    assert cov["karyotype_2n"] == 1
    assert cov["hormone"] == 0
    assert table.species_with("diet") == {"Labeo rohita", "Catla catla"}
    # rows from two files merge for one species; name matching ignores case and spacing
    assert [r["value"] for r in table.get("LABEO ROHITA", "karyotype_2n")] == ["50"]
    assert table.get("Labeo rohita", "karyotype_2n")[0]["source"] == "Other source"
    assert table.get("Nobody", "habitat") == []
    reasons = " | ".join(s["reason"] for s in table.skipped)
    assert "no source" in reasons and "unknown factor" in reasons and "not a number" in reasons
    assert len(table.skipped) == 3


def test_missing_folder_gives_empty_table(tmp_path):
    empty = load_traits(tmp_path / "does_not_exist")
    assert isinstance(empty, TraitTable)
    assert len(empty) == 0
    assert all(v == 0 for v in empty.coverage().values())


def test_factor_constants():
    assert FACTORS == ["habitat", "country_native", "diet", "trophic_level", "karyotype_2n",
                       "genome_size_pg", "max_length_cm", "hormone"]
    assert OBSERVABLE_FROM_EDNA == {"habitat", "country"}
    for factor in FACTORS:
        assert RULES[factor]["why"]
    assert RULES["max_length_cm"]["used_as_evidence"] is False


# --------------------------------------------------------------------------- sample context

def test_sample_context_country_from_geo_loc_name():
    meta = {"dataset_title": "eDNA metabarcoding (12S, MiFish-U), British Columbia",
            "design_note": "Keywords: GSC:MIxS MIMARKS:6.0",
            "biosample_attributes": {"geo_loc_name": "China:HongQimen",
                                     "isolation_source": "water"}}
    ctx = sample_context(meta)
    assert ctx["country"] == "China"
    assert "geo_loc_name" in ctx["basis"]["country"]
    assert ctx["habitat"] is None           # 'water' alone says nothing about salinity
    assert ctx["basis"]["habitat"] is None


def test_sample_context_habitat_from_title_words():
    ctx = sample_context({"dataset_title": "eDNA metabarcoding of freshwater fishes, "
                                           "Martapura River & irrigation (12S MiFish-U)"})
    assert ctx["habitat"] == "freshwater"
    assert ctx["country"] is None
    assert "dataset_title" in ctx["basis"]["habitat"]

    assert sample_context({"dataset_title": "Real and mock estuarine fish data"})["habitat"] \
        == "brackish"
    assert sample_context({"design_note": "open ocean transect"})["habitat"] == "marine"
    # estuary wins over river words; 'seasons'/'research' are not 'sea'
    assert sample_context({"dataset_title": "Pearl River estuary survey"})["habitat"] == "brackish"
    assert sample_context({"dataset_title": "Two seasons of research"})["habitat"] is None
    # freshwater and marine words without an estuary: conflict, not a guess
    conflict = sample_context({"dataset_title": "freshwater and marine sites"})
    assert conflict["habitat"] is None and "conflicting" in conflict["basis"]["habitat"]
    assert sample_context({})["country"] is None
    assert sample_context({"biosample_attributes": {"geo_loc_name": "missing"}})["country"] is None


# --------------------------------------------------------------------------- compare

def test_compare_no_rows_is_no_data():
    res = compare("diet", "herbivore", [])
    assert res["verdict"] == "no_data"
    assert res["factor_weight"] == 1.0
    assert set(res) == {"factor", "observed", "documented", "verdict", "factor_weight", "note",
                        "sources"}


def test_compare_habitat():
    rows = [_row("habitat", "freshwater")]
    assert compare("habitat", "freshwater", rows)["verdict"] == "consistent"
    bad = compare("habitat", "marine", rows)
    assert bad["verdict"] == "inconsistent" and bad["factor_weight"] == 0.25
    euryhaline = [_row("habitat", "freshwater;marine")]
    assert compare("habitat", "brackish", euryhaline)["verdict"] == "consistent"
    assert compare("habitat", "brackish", rows)["verdict"] == "inconsistent"
    assert bad["sources"][0]["source"] == SRC


def test_compare_country_native():
    rows = [_row("country_native", "India;Bangladesh")]
    assert compare("country", "india", rows)["verdict"] == "consistent"
    res = compare("country_native", "China", rows)
    assert res["verdict"] == "inconsistent" and res["factor_weight"] == 0.5
    assert "introduced" in res["note"]


def test_compare_numeric_tolerances():
    kar = [_row("karyotype_2n", "50")]
    assert compare("karyotype_2n", 52, kar)["verdict"] == "consistent"
    far = compare("karyotype_2n", 54, kar)
    assert far["verdict"] == "inconsistent" and far["factor_weight"] == 0.2

    gen = [_row("genome_size_pg", "1.0", "pg")]
    assert compare("genome_size_pg", 1.19, gen)["verdict"] == "consistent"
    assert compare("genome_size_pg", 1.25, gen)["verdict"] == "inconsistent"
    assert compare("genome_size_pg", 1.25, gen)["factor_weight"] == 0.5

    tl = [_row("trophic_level", "3.0")]
    assert compare("trophic_level", 3.5, tl)["verdict"] == "consistent"
    assert compare("trophic_level", 3.6, tl)["verdict"] == "inconsistent"
    assert compare("trophic_level", "not a number", tl)["verdict"] == "no_data"


def test_compare_diet_exact_category():
    rows = [_row("diet", "herbivore")]
    assert compare("diet", "Herbivore", rows)["verdict"] == "consistent"
    res = compare("diet", "omnivore", rows)
    assert res["verdict"] == "inconsistent" and res["factor_weight"] == 0.5


def test_max_length_never_evidence_and_hormone_free_text():
    res = compare("max_length_cm", 500, [_row("max_length_cm", "30", "cm")])
    assert res["verdict"] == "no_data" and res["factor_weight"] == 1.0
    assert res["documented"] == [30.0]
    hormones = [_row("hormone", "High plasma 11-ketotestosterone in males")]
    assert compare("hormone", "high plasma 11-ketotestosterone in males",
                   hormones)["verdict"] == "consistent"
    assert compare("hormone", "cortisol", hormones)["verdict"] == "no_data"


# --------------------------------------------------------------------------- evidence

def test_evidence_only_for_observed_factors(table):
    ctx = {"country": "China", "habitat": None, "basis": {"country": "x"}}
    res = evidence("Labeo rohita", ctx, table)
    # diet, trophic level and karyotype are documented but were not observed: not evidence
    assert [r["factor"] for r in res] == ["country_native"]
    assert res[0]["verdict"] == "inconsistent"

    res = evidence("Labeo rohita", {"habitat": "freshwater", "karyotype_2n": 50,
                                    "diet": "", "hormone": None}, table)
    assert [(r["factor"], r["verdict"]) for r in res] == [("habitat", "consistent"),
                                                         ("karyotype_2n", "consistent")]
    assert evidence("Labeo rohita", {}, table) == []
    unknown = evidence("Nobody", {"habitat": "marine"}, table)
    assert unknown[0]["verdict"] == "no_data" and unknown[0]["factor_weight"] == 1.0


# --------------------------------------------------------------------------- inferred profile

def test_inferred_profile_weighted_mean_shares_and_no_data(table):
    weighted = [("Labeo rohita", 3.0), ("Lates calcarifer", 1.0), ("Unlisted sp.", 1.0)]
    prof = inferred_profile(weighted, table)
    assert list(prof) == FACTORS

    tl = prof["trophic_level"]
    assert tl["weighted_mean"] == pytest.approx(2.5)          # (3*2 + 1*4) / 4
    assert tl["min"] == 2.0 and tl["max"] == 4.0
    assert tl["n_species"] == 2
    assert tl["coverage"] == pytest.approx(0.8)               # 4 of 5 weight has data
    assert tl["sources"][0]["source"] == SRC
    assert "not measured" in tl["note"].lower()

    hab = prof["habitat"]["shares"]
    assert hab["freshwater"] == pytest.approx(1.0)            # both relatives documented
    assert hab["brackish"] == pytest.approx(0.25)
    assert hab["marine"] == pytest.approx(0.25)
    assert prof["diet"]["shares"] == {"herbivore": 1.0}
    assert prof["diet"]["coverage"] == pytest.approx(0.6)

    for factor in ("genome_size_pg", "max_length_cm", "hormone"):
        assert prof[factor] == {"status": NO_DATA_STATUS}
    assert NO_DATA_STATUS == "no data in trait tables"


def test_inferred_profile_exclude_and_empty(table):
    prof = inferred_profile([("Labeo rohita", 1.0)], table, exclude=["habitat", "country"])
    assert "habitat" not in prof and "country_native" not in prof
    assert prof["karyotype_2n"]["weighted_mean"] == 50.0
    empty = inferred_profile([], table)
    assert all(v == {"status": NO_DATA_STATUS} for v in empty.values())


# --------------------------------------------------------------------------- seed file

def test_seed_csv_loads_and_every_row_has_source(tmp_path):
    seed = traits.TRAITS_DIR / "bioradar_in_repo.csv"
    assert seed.is_file()
    with seed.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == traits.COLUMNS
        rows = list(reader)
    assert rows
    assert all(r["source"].strip() for r in rows)
    # only the two factors data/species_traits.csv actually holds; nothing guessed
    assert {r["factor"] for r in rows} == {"max_length_cm", "trophic_level"}

    (tmp_path / seed.name).write_bytes(seed.read_bytes())
    alone = load_traits(tmp_path)
    assert alone.skipped == []
    assert len(alone) == len(rows)
    assert alone.coverage()["habitat"] == 0 and alone.coverage()["diet"] == 0
    assert alone.get("Labeo rohita", "max_length_cm")[0]["unit"] == "cm"
    assert alone.get("Labeo rohita", "trophic_level")[0]["value"] == "2.2"

    shipped = load_traits()  # the default folder loads without rejected rows
    assert "bioradar_in_repo.csv" in shipped.files
    assert shipped.skipped == []
