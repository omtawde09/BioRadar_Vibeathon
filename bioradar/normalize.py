"""Turn raw eDNA pipeline output into the frozen BioRadar taxonomy contract.

The pipeline emits a wide table -- one row per ASV, one column per sample, with
the whole taxonomic lineage crammed into a single semicolon-delimited string:

    Feature_ID,sample1,...,sample6,Taxon,Confidence
    a595...,499.0,...,486.0,k__Eukaryota_2759;p__Chordata_7711;...;s__Gambusia holbrooki_37273,0.9959

Every downstream consumer (flagging, analytics, dashboard) wants the opposite:
one row per detection, with ranks split into columns and the NCBI taxid pulled
out as a join key. This module is that translation, and it is deliberately
stdlib-only so the backend can import it without the QIIME2 conda environment.

Usage:
    python -m bioradar.normalize testing_data/final_results.zip -o out/
    python -m bioradar.normalize runs/BR-001/final_results -o out/
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable

from bioradar.contract import (
    RANK_PREFIXES,
    RANKS,
    REDUNDANT_RANK_WORDS,
    SAMPLE_SUMMARY_COLUMNS,
    TAXONOMY_COLUMNS,
    UNASSIGNED,
    UNASSIGNED_PREFIX,
)

# Trailing "_12345" on a lineage segment is the NCBI taxid.
_TAXID_RE = re.compile(r"_(\d+)$")

# Columns in asv_count_tax.csv that are not sample count columns.
_NON_SAMPLE_COLUMNS = {"Feature_ID", "Feature ID", "Taxon", "Confidence", "#OTU ID"}


# --------------------------------------------------------------------------
# Lineage parsing
# --------------------------------------------------------------------------


def parse_lineage(taxon: str) -> dict[str, str]:
    """Split a QIIME2/MIDORI2 lineage string into per-rank names and a taxid.

    Handles the shapes that actually occur in pipeline output:

    * full lineage to species, with spaces in the epithet
      ``s__Gambusia holbrooki_37273`` -> species="Gambusia holbrooki", taxid=37273
    * truncated lineage, stopping at whatever rank the classifier reached
      ``...;g__Carassius_7956`` -> deepest rank is genus, species stays empty
    * a repeated rank word inside the label, which MIDORI2 emits when NCBI has
      no distinct name at that rank
      ``c__class_Testudines_8459`` -> class="Testudines"
    * ``Unassigned`` / ``Unassigned3`` -> every rank empty, rank="unassigned"
    * a missing taxid, e.g. ``g__Carassius`` -> name kept, taxon_id empty

    Returns a dict with one key per rank plus `taxon_id`, `scientific_name` and
    `rank` describing the deepest assigned level. Values are always strings; an
    unassigned rank is the empty string, never None, so the row can be written
    straight to CSV.
    """
    result: dict[str, str] = {rank: "" for rank in RANKS}
    result.update({"taxon_id": "", "scientific_name": "", "rank": UNASSIGNED})

    cleaned = (taxon or "").strip()
    if not cleaned or cleaned.lower().startswith(UNASSIGNED_PREFIX):
        return result

    deepest_rank = ""
    deepest_taxid = ""

    for segment in cleaned.split(";"):
        segment = segment.strip()
        if not segment:
            continue

        rank, _, label = segment.partition("__")
        if not label:
            # Segment carries no rank prefix at all; nothing reliable to do with
            # it, so skip rather than guess at a rank.
            continue

        rank_name = RANK_PREFIXES.get(rank.strip().lower())
        if rank_name is None:
            continue

        name, taxid = _split_taxid(label)
        name = _strip_redundant_rank_word(name)
        if rank_name == "species":
            name = _normalize_species_name(name)
        if not name:
            continue

        result[rank_name] = name
        deepest_rank = rank_name
        deepest_taxid = taxid

    if deepest_rank:
        result["rank"] = deepest_rank
        result["scientific_name"] = result[deepest_rank]
        result["taxon_id"] = deepest_taxid

    return result


def _split_taxid(label: str) -> tuple[str, str]:
    """Peel a trailing ``_<digits>`` NCBI taxid off a lineage label."""
    match = _TAXID_RE.search(label)
    if not match:
        return label.strip(), ""
    return label[: match.start()].strip(), match.group(1)


def _strip_redundant_rank_word(name: str) -> str:
    """Drop a leading rank word, e.g. ``class_Testudines`` -> ``Testudines``."""
    head, sep, tail = name.partition("_")
    if sep and tail and head.lower() in REDUNDANT_RANK_WORDS:
        return tail.strip()
    return name.strip()


def _normalize_species_name(name: str) -> str:
    """Render binomials consistently as ``Genus epithet``.

    MIDORI2 uses a space; some other references use an underscore. Only convert
    when there is no space already, so genuine multi-word names survive.
    """
    if " " not in name:
        return name.replace("_", " ").strip()
    return name


# --------------------------------------------------------------------------
# Reading pipeline output
# --------------------------------------------------------------------------


class ResultsSource:
    """Read pipeline artifacts from a results directory or a results zip.

    The zip case matters: `testing_data/final_results.zip` is the only real
    pipeline output committed to the repo, so tests and mock-data generation run
    against it without anybody needing Docker.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._zip: zipfile.ZipFile | None = None
        if path.is_file() and path.suffix == ".zip":
            self._zip = zipfile.ZipFile(path)

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def __enter__(self) -> "ResultsSource":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def read_text(self, relative: str) -> str | None:
        """Return the contents of `relative`, or None if it is not present."""
        if self._zip is not None:
            for candidate in self._zip.namelist():
                normalized = candidate.replace("\\", "/")
                if normalized == relative or normalized.endswith("/" + relative):
                    return self._zip.read(candidate).decode("utf-8", errors="replace")
            return None

        target = self.path / relative
        if target.is_file():
            return target.read_text(encoding="utf-8", errors="replace")
        return None


def load_detections(source: ResultsSource) -> tuple[list[dict[str, str]], list[str]]:
    """Load the merged ASV count + taxonomy table.

    Prefers `asvs/asv_count_tax.csv`, which the upstream `count_table` rule
    produces. Falls back to merging `asvs/asv-table.tsv` with
    `asvs/taxonomy.tsv` ourselves, so a partially-failed run is still usable.

    Returns (rows, sample_columns).
    """
    merged = source.read_text("asvs/asv_count_tax.csv")
    if merged is not None:
        rows = list(csv.DictReader(io.StringIO(merged)))
        if not rows:
            raise ValueError("asv_count_tax.csv contains no data rows")
        samples = [c for c in rows[0] if c and c not in _NON_SAMPLE_COLUMNS]
        return rows, samples

    return _merge_fallback(source)


def _merge_fallback(source: ResultsSource) -> tuple[list[dict[str, str]], list[str]]:
    """Rebuild the merged table from the BIOM export and the taxonomy TSV."""
    table = source.read_text("asvs/asv-table.tsv")
    taxonomy = source.read_text("asvs/taxonomy.tsv")
    if table is None or taxonomy is None:
        raise FileNotFoundError(
            "no asv_count_tax.csv, and cannot fall back: need both "
            "asvs/asv-table.tsv and asvs/taxonomy.tsv"
        )

    # asv-table.tsv starts with a '# Constructed from biom file' comment line.
    lines = [ln for ln in table.splitlines() if not ln.startswith("# ")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="\t")
    counts = {row["#OTU ID"]: row for row in reader}

    tax_reader = csv.DictReader(io.StringIO(taxonomy), delimiter="\t")
    lookup = {row["Feature ID"]: row for row in tax_reader}

    samples = [c for c in (reader.fieldnames or []) if c not in _NON_SAMPLE_COLUMNS]

    rows: list[dict[str, str]] = []
    for feature_id, count_row in counts.items():
        annotation = lookup.get(feature_id, {})
        row: dict[str, str] = {"Feature_ID": feature_id}
        row.update({s: count_row.get(s, "0") for s in samples})
        row["Taxon"] = annotation.get("Taxon", "Unassigned")
        row["Confidence"] = annotation.get("Confidence", "0")
        rows.append(row)
    return rows, samples


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------


def normalize(
    rows: Iterable[dict[str, str]],
    sample_columns: list[str],
    *,
    sample_map: dict[str, str] | None = None,
    classification_method: str = "sklearn",
    include_zero: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Convert wide pipeline rows into contract rows plus a per-sample summary.

    `sample_map` renames pipeline sample ids (taken from FASTQ filenames) to
    BioRadar sample codes. Unmapped samples keep their original id.

    Zero-count entries are dropped by default: an ASV with no reads in a sample
    is an absence, not a detection, and emitting it would inflate every
    downstream count. Pass include_zero=True when you need the dense matrix.
    """
    sample_map = sample_map or {}
    materialized = list(rows)

    totals = {s: 0 for s in sample_columns}
    for row in materialized:
        for sample in sample_columns:
            totals[sample] += _to_int(row.get(sample))

    detections: list[dict[str, object]] = []
    stats = {
        s: {"asvs": 0, "species": set(), "genera": set(), "unassigned": 0}
        for s in sample_columns
    }

    for row in materialized:
        asv_id = (row.get("Feature_ID") or row.get("Feature ID") or "").strip()
        if not asv_id:
            continue

        lineage_raw = (row.get("Taxon") or "").strip()
        parsed = parse_lineage(lineage_raw)
        confidence = _to_float(row.get("Confidence"))

        for sample in sample_columns:
            read_count = _to_int(row.get(sample))
            if read_count == 0 and not include_zero:
                continue

            sample_id = sample_map.get(sample, sample)
            total = totals[sample]
            record: dict[str, object] = {
                "sample_id": sample_id,
                "asv_id": asv_id,
                "taxon_id": parsed["taxon_id"],
                "scientific_name": parsed["scientific_name"],
                "rank": parsed["rank"],
                "confidence": round(confidence, 6),
                "read_count": read_count,
                "rel_abundance": round(read_count / total, 6) if total else 0.0,
                "classification_method": classification_method,
                "lineage_raw": lineage_raw,
            }
            record.update({rank: parsed[rank] for rank in RANKS})
            detections.append(record)

            bucket = stats[sample]
            bucket["asvs"] += 1
            if parsed["rank"] == UNASSIGNED:
                bucket["unassigned"] += read_count
            if parsed["species"]:
                bucket["species"].add(parsed["species"])
            if parsed["genus"]:
                bucket["genera"].add(parsed["genus"])

    summary: list[dict[str, object]] = []
    for sample in sample_columns:
        bucket = stats[sample]
        total = totals[sample]
        summary.append(
            {
                "sample_id": sample_map.get(sample, sample),
                "total_reads": total,
                "asv_count": bucket["asvs"],
                "species_count": len(bucket["species"]),
                "genus_count": len(bucket["genera"]),
                "unassigned_reads": bucket["unassigned"],
                "unassigned_fraction": (
                    round(bucket["unassigned"] / total, 6) if total else 0.0
                ),
            }
        )

    detections.sort(key=lambda r: (str(r["sample_id"]), -int(r["read_count"])))
    return detections, summary


def _to_int(value: object) -> int:
    """Counts arrive as floats ('432.0'); coerce without exploding on junk."""
    try:
        return int(round(float(str(value).strip())))
    except (TypeError, ValueError):
        return 0


def _to_float(value: object) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict[str, object]], columns: Iterable[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)
    return path


def normalize_results(
    results_path: Path,
    output_dir: Path,
    *,
    sample_map: dict[str, str] | None = None,
    classification_method: str = "sklearn",
) -> dict[str, Path]:
    """End-to-end: read a results dir/zip, write the two contract CSVs."""
    with ResultsSource(results_path) as source:
        rows, samples = load_detections(source)

    detections, summary = normalize(
        rows,
        samples,
        sample_map=sample_map,
        classification_method=classification_method,
    )

    return {
        "taxonomy": write_csv(
            output_dir / "taxonomy_normalized.csv", detections, TAXONOMY_COLUMNS
        ),
        "summary": write_csv(
            output_dir / "sample_summary.csv", summary, SAMPLE_SUMMARY_COLUMNS
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.normalize",
        description="Normalize eDNA pipeline output into the BioRadar contract.",
    )
    parser.add_argument(
        "results", type=Path, help="final_results directory or final_results.zip"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("out"), help="output directory"
    )
    parser.add_argument(
        "--method",
        default="sklearn",
        choices=("sklearn", "blast"),
        help="value written to classification_method",
    )
    parser.add_argument(
        "--sample-map",
        type=Path,
        help="CSV with pipeline_sample,bioradar_sample_id to rename samples",
    )
    args = parser.parse_args(argv)

    sample_map = _load_sample_map(args.sample_map) if args.sample_map else None

    written = normalize_results(
        args.results,
        args.output,
        sample_map=sample_map,
        classification_method=args.method,
    )
    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


def _load_sample_map(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {
            row["pipeline_sample"]: row["bioradar_sample_id"]
            for row in reader
            if row.get("pipeline_sample")
        }


if __name__ == "__main__":
    sys.exit(main())
