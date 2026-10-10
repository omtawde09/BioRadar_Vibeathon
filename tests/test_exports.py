"""Exports have to be readable by the tools they claim to target.

A Darwin Core Archive that GBIF rejects is worse than no export at all: it looks
like a working feature right up until somebody tries to publish with it. These
tests check the structure an IPT actually requires.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile

import pytest

from bioradar import exports
from bioradar.contract import TAXONOMY_COLUMNS


def detection(**overrides):
    row = {key: "" for key in TAXONOMY_COLUMNS}
    row.update({
        "sample_id": "BR-2026-GOA-001",
        "asv_id": "a1b2c3",
        "taxon_id": "8022",
        "scientific_name": "Oncorhynchus mykiss",
        "rank": "species",
        "kingdom": "Eukaryota",
        "phylum": "Chordata",
        "class": "Actinopteri",
        "order": "Salmoniformes",
        "family": "Salmonidae",
        "genus": "Oncorhynchus",
        "species": "Oncorhynchus mykiss",
        "confidence": "0.97",
        "read_count": "1420",
        "rel_abundance": "0.184",
        "classification_method": "sklearn",
    })
    row.update(overrides)
    return row


@pytest.fixture
def analysis():
    from bioradar.report import analyse

    rows = [
        detection(),
        detection(asv_id="d4e5", scientific_name="Gambusia holbrooki",
                  species="Gambusia holbrooki", genus="Gambusia",
                  family="Poeciliidae", order="Cyprinodontiformes",
                  taxon_id="37273", read_count="820", confidence="0.91"),
        detection(asv_id="f6g7", scientific_name="Unassigned1", rank="unassigned",
                  kingdom="", phylum="", **{"class": ""}, order="", family="",
                  genus="", species="", taxon_id="", read_count="310",
                  confidence="0.2"),
    ]
    samples = [{
        "sample_id": "BR-2026-GOA-001", "site_id": "GOA-MANDOVI",
        "latitude": "15.4989", "longitude": "73.8278",
        "collected_at": "2026-02-11",
    }]
    return rows, samples, analyse(rows, samples)


def test_detections_csv_keeps_contract_column_order(analysis):
    rows, _, _ = analysis
    body = exports.detections_csv(rows).decode("utf-8-sig")
    header = next(csv.reader(io.StringIO(body)))
    assert header == list(TAXONOMY_COLUMNS)


def test_detections_csv_carries_a_bom_for_excel(analysis):
    """Without the BOM, Excel on Windows mangles every accented species name."""
    rows, _, _ = analysis
    assert exports.detections_csv(rows).startswith(b"\xef\xbb\xbf")


def test_unicode_species_names_survive_the_round_trip(analysis):
    rows, _, _ = analysis
    rows = rows + [detection(asv_id="u1", scientific_name="Pseudacris cruciferé",
                             species="Pseudacris cruciferé")]
    body = exports.detections_csv(rows).decode("utf-8-sig")
    assert "Pseudacris cruciferé" in body


def test_dwca_has_the_files_an_ipt_requires(analysis):
    rows, samples, result = analysis
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(rows, result, samples, meta={"run_id": "test-run"})
    ))
    assert set(archive.namelist()) >= {"occurrence.txt", "dna.txt", "meta.xml", "eml.xml"}


def test_dwca_excludes_unassigned_detections(analysis):
    """An occurrence record asserts a named organism was present.

    "Unassigned" asserts nothing, so publishing it to GBIF would be pollution.
    """
    rows, samples, result = analysis
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(rows, result, samples, meta={"run_id": "test-run"})
    ))
    occurrences = archive.read("occurrence.txt").decode("utf-8").strip().splitlines()
    assert len(occurrences) == 3            # header + 2 assigned detections
    assert "Unassigned" not in "\n".join(occurrences)


def test_dwca_occurrence_columns_match_the_meta_descriptor(analysis):
    rows, samples, result = analysis
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(rows, result, samples, meta={"run_id": "test-run"})
    ))
    header = archive.read("occurrence.txt").decode("utf-8").splitlines()[0].split("\t")
    assert header == list(exports.OCCURRENCE_FIELDS)

    meta = archive.read("meta.xml").decode("utf-8")
    # Every declared column must appear in the descriptor, or the IPT silently
    # drops the ones it was not told about.
    for field in exports.OCCURRENCE_FIELDS:
        assert 'term="{ns}{f}"'.format(ns=exports.DWC_NS, f=field) in meta


def test_dwca_records_read_counts_as_reads_not_individuals(analysis):
    """The single most dangerous misreading of eDNA data, so the unit is explicit."""
    rows, samples, result = analysis
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(rows, result, samples, meta={"run_id": "test-run"})
    ))
    body = archive.read("occurrence.txt").decode("utf-8")
    assert "DNA sequence reads" in body
    assert "read count" in archive.read("README.txt").decode("utf-8").lower()


def test_dwca_carries_coordinates_and_a_datum(analysis):
    rows, samples, result = analysis
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(rows, result, samples, meta={"run_id": "r"})
    ))
    lines = archive.read("occurrence.txt").decode("utf-8").splitlines()
    header = lines[0].split("\t")
    row = dict(zip(header, lines[1].split("\t")))
    assert row["decimalLatitude"] == "15.4989"
    assert row["geodeticDatum"] == "WGS84"
    assert row["basisOfRecord"] == "MaterialSample"


def test_dwca_tab_and_newline_are_stripped_from_values(analysis):
    """The format has no escaping, so an embedded tab would shift every column."""
    rows, samples, result = analysis
    dirty = rows + [detection(asv_id="x1", scientific_name="Bad\tname\nhere",
                              species="Bad\tname\nhere")]
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(dirty, result, samples, meta={"run_id": "r"})
    ))
    # Only the trailing newline is removed. Stripping whitespace would eat the
    # trailing empty fields of the last row and make a correct file look broken
    # -- which is exactly how a naive consumer would mis-parse it too.
    lines = archive.read("occurrence.txt").decode("utf-8").rstrip("\n").split("\n")
    widths = {len(line.split("\t")) for line in lines}
    assert widths == {len(exports.OCCURRENCE_FIELDS)}
    assert "Bad name here" in "\n".join(lines)


def test_dna_extension_links_to_the_core_by_occurrence_id(analysis):
    rows, samples, result = analysis
    archive = zipfile.ZipFile(io.BytesIO(
        exports.darwin_core_archive(rows, result, samples, meta={"run_id": "r"})
    ))
    core = archive.read("occurrence.txt").decode("utf-8").splitlines()
    ext = archive.read("dna.txt").decode("utf-8").splitlines()
    core_ids = {line.split("\t")[0] for line in core[1:]}
    ext_ids = {line.split("\t")[0] for line in ext[1:]}
    assert core_ids == ext_ids


def test_analysis_json_is_serialisable_with_sets_present(analysis):
    _, _, result = analysis
    body = exports.analysis_json(result, {"run_id": "r"})
    parsed = json.loads(body.decode("utf-8"))
    assert parsed["bioradar"]["run_id"] == "r"
    # `sites` is a set in the analysis object and must survive as a list.
    assert isinstance(parsed["analysis"]["species"][0]["sites"], list)


def test_printable_report_is_self_contained(analysis):
    """It gets emailed and opened offline, so it may not reference anything."""
    _, _, result = analysis
    html = exports.printable_report(result, {"title": "Goa survey", "run_id": "r"}).decode("utf-8")
    assert "<style>" in html
    assert "http://" not in html.replace("https://doi.org", "")
    assert "<script" not in html
    assert "Goa survey" in html


def test_printable_report_states_the_no_species_case(analysis):
    from bioradar.report import analyse

    empty = analyse([detection(scientific_name="Unassigned1", rank="unassigned",
                               species="", genus="", read_count="500")],
                    [{"sample_id": "BR-2026-GOA-001", "site_id": "S1"}])
    html = exports.printable_report(empty, {"title": "Empty"}).decode("utf-8")
    assert "No named species were identified" in html


def test_archive_stats_counts_what_will_be_published(analysis):
    rows, _, _ = analysis
    stats = exports.archive_stats(rows)
    assert stats["detections"] == 3
    assert stats["occurrences"] == 2
    assert stats["excluded_unassigned"] == 1
