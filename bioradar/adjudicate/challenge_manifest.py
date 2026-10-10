"""Flat, judge-readable provenance manifest for the challenge (workpack item C1).

    python -m bioradar.adjudicate.challenge_manifest        # writes data/challenge/manifest.csv

One row per real input file: source URL, accession / run / sample IDs, the original file name,
collection date, site and coordinates exactly as deposited, the assay, reference version, size,
MD5 (the archive's own) and SHA-256 (computed here from the unchanged file).

The assay is reported in two clearly separated parts, so nothing inferred passes as deposited:

* `assay_as_deposited` - the run's experiment title, verbatim from the archive record.
* `marker_inferred` / `marker_basis` - "12S rRNA (MiFish primer family)" only when the dataset
  title or the experiment text names 12S or MiFish; `marker_basis` quotes the text it was read
  from. When neither does, `marker_inferred` is empty and the basis says
  "not stated in archive metadata". No primer citation is asserted that the archive does not carry.

Read-only: raw files are only opened for reading and nothing in the source records is edited.
A manifest `file` path is joined to the data folder with the same guard the downloader uses
(`fetch.safe_join`): absolute paths, drive letters and `..` are never followed.

`verified` is one of:

* `yes` - the file is present and its MD5 and size match the archive.
* `MISSING: ...` - the file has not been downloaded.
* `MISMATCH: ...` - the local MD5 or size disagrees with the archive.
* `REJECTED: unsafe path in manifest` - the manifest names a path outside the data folder;
  it is not opened.

A row that is not `yes` says so instead of being dropped, so a gap is visible, never silent.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bioradar.adjudicate import runner
from bioradar.adjudicate.fetch import safe_join
from bioradar.adjudicate.reference import REF_DIR

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "data" / "challenge" / "manifest.csv"

COLUMNS = [
    "source_id", "bioproject", "run_accession", "sample_accession", "sample_alias",
    "original_filename", "source_url", "collection_date", "site", "latitude_as_deposited",
    "longitude_as_deposited", "coordinate_note", "assay_as_deposited", "marker_inferred",
    "marker_basis", "instrument", "role", "reference_version", "bytes", "md5_archive",
    "md5_local", "sha256_local", "verified",
]

MARKER_INFERRED = "12S rRNA (MiFish primer family)"
MARKER_TEXT = re.compile(r"12S|MiFish", re.IGNORECASE)
REJECTED = "REJECTED: unsafe path in manifest"


def infer_marker(dataset_title: Optional[str], experiment: Optional[str]) -> Tuple[str, str]:
    """(marker_inferred, marker_basis) from the archive's own words, never assumed.

    The experiment text (deposited per run) is checked first, then the dataset title."""
    for text in (experiment, dataset_title):
        if text and MARKER_TEXT.search(text):
            return MARKER_INFERRED, "inferred from dataset title / experiment text: {}".format(
                " ".join(text.split()))
    return "", "not stated in archive metadata"


def _digests(path: Path) -> Dict[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            md5.update(chunk)
            sha.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha.hexdigest()}


def _check(rel: str, md5_archive: str, size_archive: Any) -> Tuple[Dict[str, str], str]:
    """(local digests, verified) for one manifest file entry. Reads only; never follows an unsafe path."""
    local = {"md5": "", "sha256": ""}
    try:
        path = safe_join(runner.DATA_DIR, rel)
    except ValueError:
        return local, REJECTED
    if not path.is_file():
        return local, "MISSING: file not downloaded"
    local = _digests(path)
    if local["md5"] != md5_archive:
        return local, "MISMATCH: local md5 differs from archive md5"
    if path.stat().st_size != size_archive:
        return local, "MISMATCH: size differs from archive size"
    return local, "yes"


def build_rows() -> List[Dict[str, Any]]:
    manifest = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
    ref = json.loads((REF_DIR / "reference.json").read_text(encoding="utf-8"))
    version = ref.get("reference_database_version", "")
    table = {r["sample_id"]: r for r in runner.sample_table()}
    rows: List[Dict[str, Any]] = []
    for ds in manifest["datasets"]:
        for run in ds["runs"]:
            meta = table.get(run["run_accession"], {})
            lat, lon = (list(run.get("latitude_longitude_as_deposited") or []) + ["", ""])[:2]
            experiment = run.get("experiment") or ""
            marker, basis = infer_marker(ds.get("title", ""), experiment)
            for f in run["files"]:
                local, verified = _check(f["file"], f["md5"], f["bytes"])
                rows.append({
                    "source_id": ds["bioproject"], "bioproject": ds["bioproject"],
                    "run_accession": run["run_accession"], "sample_accession": run["biosample"],
                    "sample_alias": run["sample_alias"],
                    "original_filename": Path(f["file"]).name, "source_url": f["source_url"],
                    "collection_date": run["collection_date"], "site": run["location"],
                    "latitude_as_deposited": lat, "longitude_as_deposited": lon,
                    "coordinate_note": meta.get("coordinate_note", ""),
                    "assay_as_deposited": experiment,
                    "marker_inferred": marker, "marker_basis": basis,
                    "instrument": run.get("instrument", ""), "role": meta.get("role", ""),
                    "reference_version": version, "bytes": f["bytes"],
                    "md5_archive": f["md5"], "md5_local": local["md5"],
                    "sha256_local": local["sha256"], "verified": verified,
                })
    return rows


def main() -> int:
    rows = build_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    ok = sum(1 for r in rows if r["verified"] == "yes")
    print("{}: {} rows, {} verified against the archive MD5 + size".format(OUT, len(rows), ok))
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
