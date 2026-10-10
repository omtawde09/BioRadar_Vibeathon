"""Download the real public dataset and the reference list, and record both.

Nothing here creates or edits a sequence. Every file comes from a public archive
and is checked against the archive's own md5 before it is trusted.

    python -m bioradar.adjudicate.fetch reads        # reads listed in the committed manifest (md5-verified)
    python -m bioradar.adjudicate.fetch samples      # PRJNA1059782 R1 reads + manifest
    python -m bioradar.adjudicate.fetch reference    # RefSeq fish mitogenomes + human 12S
    python -m bioradar.adjudicate.fetch all

Python 3.8 compatible (the app runs inside the 3.8 pipeline image).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from bioradar.fetch_data import _urlopen  # TLS context that works behind AV proxies

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "real_challenge"
DATASETS_DIR = DATA_DIR / "datasets"
CACHE_DIR = DATA_DIR / "reference" / "cache"  # downloaded mitogenomes (not committed)
RECORDS_FOLDER = "PRJEB108476_bge_records"

PROJECT = "PRJNA1059782"
ENA_FILEREPORT = "https://www.ebi.ac.uk/ena/portal/api/filereport"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

FIELDS = (
    "run_accession,sample_accession,sample_alias,scientific_name,library_strategy,"
    "instrument_model,read_count,collection_date,country,lat,lon,fastq_ftp,fastq_md5,"
    "fastq_bytes,sample_description,study_title,experiment_title"
)


def _get(url: str, timeout: int = 120) -> bytes:
    with _urlopen(url, timeout=timeout) as response:
        return response.read()


# --------------------------------------------------------------------------
# Samples
# --------------------------------------------------------------------------


def ena_runs(project: str = PROJECT) -> List[Dict[str, str]]:
    query = urllib.parse.urlencode({
        "accession": project, "result": "read_run", "fields": FIELDS, "format": "tsv",
    })
    text = _get("{}?{}".format(ENA_FILEREPORT, query)).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def biosample_attributes(accession: str) -> Dict[str, str]:
    """TAG -> VALUE pairs the submitter deposited on the BioSample (e.g. samp_size)."""
    import re
    xml = _get("https://www.ebi.ac.uk/ena/browser/api/xml/{}".format(accession)).decode("utf-8")
    pairs = re.findall(r"<TAG>([^<]*)</TAG>\s*<VALUE>([^<]*)</VALUE>", xml)
    keep = {"samp_size", "replicate", "lat_lon", "geo_loc_name", "collection_date", "isolation_source"}
    return {k: v for k, v in pairs if k in keep}


def download_verified(url: str, destination: Path, md5: str) -> str:
    """Fetch `url` unless an md5-matching copy is already there. Returns status."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and _md5(destination) == md5:
        return "cached"
    tmp = destination.with_suffix(destination.suffix + ".part")
    with _urlopen(url, timeout=300) as response, tmp.open("wb") as out:
        for chunk in iter(lambda: response.read(1 << 20), b""):
            out.write(chunk)
    if _md5(tmp) != md5:
        tmp.unlink()
        raise RuntimeError("md5 mismatch for {} -- download corrupted".format(url))
    tmp.replace(destination)
    return "downloaded"


# Every public dataset used, why it was chosen, and which runs. `runs: None` = all.
DATASETS = [
    {
        "bioproject": "PRJNA1059782",
        "folder": "PRJNA1059782_pearl_river_12S",
        "title": "Real and mock estuarine fish data (12S MiFish-U)",
        "centre": "South China Agricultural University",
        "publication": "Chen J. et al. 2025, Global Ecology and Conservation 64:e03906, "
                       "doi:10.1016/j.gecco.2025.e03906",
        "runs": None,
        "used_for": "mixed mock communities (A-D) and the same four sites sampled in "
                    "summer (2019-08) and winter (2019-11)",
    },
    {
        "bioproject": "PRJNA1433820",
        "folder": "PRJNA1433820_martapura_12S",
        "title": "eDNA metabarcoding of freshwater fishes, Martapura River & irrigation (12S MiFish-U)",
        "centre": "Universitas Airlangga",
        "publication": "none listed in the archive record",
        "runs": ["SRR37521672", "SRR37521667"],
        "used_for": "real sample with primer-dimer short fragments (ST04, ST07) and real "
                    "invasive fish (Oreochromis niloticus, Pterygoplichthys)",
    },
    {
        "bioproject": "PRJNA1269473",
        "folder": "PRJNA1269473_british_columbia_12S",
        "title": "eDNA metabarcoding (12S, MiFish-U), British Columbia",
        "centre": "see ENA record",
        "publication": "none listed in the archive record",
        "runs": ["SRR33845265", "SRR33845234"],
        "used_for": "real low-yield field samples (a few hundred reads): unusable, retake",
    },
    {
        "bioproject": "PRJNA985779",
        "folder": "PRJNA985779_uk_12S",
        "title": "12S MiFish water sample metabarcode data, United Kingdom",
        "centre": "see ENA record",
        "publication": "none listed in the archive record",
        "runs": ["SRR25108818"],
        "used_for": "real field water blank, low yield",
    },
]


def _write_dataset_folder(entry: Dict[str, Any]) -> None:
    """A manifest and a plain-language README beside each dataset's reads."""
    folder = DATASETS_DIR / entry["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
    lines = [
        "# {}".format(entry["title"]), "",
        "- Public archive: {} ({})".format(entry["bioproject"], entry["ena_url"]),
        "- Submitted by: {}".format(entry["centre"]),
        "- Publication: {}".format(entry["publication"]),
        "- Used for: {}".format(entry["used_for"]),
        "- Runs here: {} (R1 reads only)".format(len(entry["runs"])), "",
        "Files in `raw/` are the archive's original files, byte for byte, verified by md5 against the",
        "archive. Nothing was created, trimmed, converted or edited. `manifest.json` lists every file's",
        "source URL, md5, sample ID and the submitter's metadata.", "",
        "| Run | Sample | Collected | Place | Reads (pairs) | File |", "|---|---|---|---|---|---|",
    ]
    for run in entry["runs"]:
        lines.append("| {} | {} | {} | {} | {:,} | `{}` |".format(
            run["run_accession"], run["sample_alias"], run["collection_date"] or "n/a",
            run["location"] or "n/a", run["read_pairs"],
            run["files"][0]["file"].rsplit("/", 1)[-1] if run["files"] else "-"))
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_samples(datasets: List[Dict[str, Any]] = None, mates: str = "1") -> Path:
    """Download R1 reads for the listed runs and write one manifest for all of them."""
    out_sets = []
    for ds in datasets or DATASETS:
        runs = ena_runs(ds["bioproject"])
        if ds["runs"]:
            runs = [r for r in runs if r["run_accession"] in ds["runs"]]
        records: List[Dict[str, Any]] = []
        for row in sorted(runs, key=lambda r: r["sample_alias"]):
            urls = row["fastq_ftp"].split(";")
            md5s = row["fastq_md5"].split(";")
            sizes = row["fastq_bytes"].split(";")
            files = []
            for index, (url, md5, size) in enumerate(zip(urls, md5s, sizes), start=1):
                if str(index) not in mates:
                    continue
                name = url.rsplit("/", 1)[-1]
                raw_dir = DATASETS_DIR / ds["folder"] / "raw"
                status = download_verified("https://" + url, raw_dir / name, md5)
                print("  {:<11} {:<30} {:>6.1f} MB".format(status, name, int(size) / 1e6),
                      flush=True)
                files.append({"file": "datasets/{}/raw/{}".format(ds["folder"], name), "mate": index, "md5": md5,
                              "bytes": int(size), "source_url": "https://" + url})
            records.append({
                "run_accession": row["run_accession"],
                "biosample": row["sample_accession"],
                "sample_alias": row["sample_alias"],
                "collection_date": row["collection_date"],
                "location": row["country"],
                "latitude_longitude_as_deposited": [row["lat"], row["lon"]],
                "design_note_from_submitter": row["sample_description"],
                "biosample_attributes": biosample_attributes(row["sample_accession"]),
                "experiment": row["experiment_title"],
                "instrument": row["instrument_model"],
                "read_pairs": int(row["read_count"] or 0),
                "files": files,
            })
        entry = dict(ds, ena_url="https://www.ebi.ac.uk/ena/browser/view/" + ds["bioproject"],
                     runs=records)
        out_sets.append(entry)
        _write_dataset_folder(entry)
    manifest = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mates_downloaded": "R1 only. Originals are stored unmodified and verified by md5; "
                            "no sequence or metadata record has been created or edited.",
        "datasets": out_sets,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def fetch_reads_from_manifest(manifest: Path = None) -> int:
    """Download exactly the files the COMMITTED manifest lists, verified against the md5s it
    records. Unlike `fetch_samples` this makes no metadata query and rewrites no manifest, so
    a clean checkout reproduces the same bytes the manifest was written against."""
    manifest = Path(manifest) if manifest else DATA_DIR / "manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    failures = 0
    for ds in doc["datasets"]:
        for run in ds["runs"]:
            for f in run["files"]:
                name = f["file"].split("/", 1)[-1]
                try:
                    status = download_verified(f["source_url"], RAW_DIR / name, f["md5"])
                except Exception as exc:  # report every failure, do not stop at the first
                    failures += 1
                    status = "FAILED ({})".format(exc)
                print("  {:<11} {:<28} {:>6.1f} MB".format(
                    status.split(" ")[0], name, f["bytes"] / 1e6), flush=True)
                if status.startswith("FAILED"):
                    print("      " + status, flush=True)
    return failures


# --------------------------------------------------------------------------
# Reference
# --------------------------------------------------------------------------

REFSEQ_QUERY = ("Actinopteri[Organism] AND srcdb_refseq[PROP] AND biomol_genomic[PROP] "
                "AND mitochondrion[filter]")
HUMAN_MITO = "NC_012920"
BATCH = 100


def _esearch(term: str, retmax: int = 10000) -> List[str]:
    query = urllib.parse.urlencode({"db": "nuccore", "term": term, "retmax": retmax,
                                    "retmode": "json"})
    data = json.loads(_get(EUTILS + "esearch.fcgi?" + query))
    return data["esearchresult"]["idlist"]


def _efetch_fasta(ids: List[str]) -> str:
    query = urllib.parse.urlencode({"db": "nuccore", "id": ",".join(ids), "rettype": "fasta",
                                    "retmode": "text"})
    return _get(EUTILS + "efetch.fcgi?" + query, timeout=180).decode("utf-8")


def fetch_reference() -> Path:
    """Download RefSeq fish mitogenomes + the human mitogenome (the contaminant)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ids = _esearch(REFSEQ_QUERY)
    print("  RefSeq Actinopteri mitogenomes: {}".format(len(ids)), flush=True)
    target = CACHE_DIR / "refseq_fish_mito.fasta"
    done = set()
    if target.is_file():
        done = {line[1:].split()[0] for line in target.read_text().splitlines()
                if line.startswith(">")}
    with target.open("a", encoding="utf-8") as out:
        for start in range(0, len(ids), BATCH):
            batch = ids[start:start + BATCH]
            try:
                text = _efetch_fasta(batch)
            except Exception as exc:  # network blips happen; retry once
                print("  retry after: {}".format(exc), flush=True)
                time.sleep(3)
                text = _efetch_fasta(batch)
            out.write(text if text.endswith("\n") else text + "\n")
            print("  fetched {}/{}".format(min(start + BATCH, len(ids)), len(ids)), flush=True)
            time.sleep(0.4)  # NCBI allows 3 requests/s without a key
    human = _efetch_fasta(_esearch("{}[Accession]".format(HUMAN_MITO)))
    (CACHE_DIR / "human_mito.fasta").write_text(human, encoding="utf-8")
    meta = {
        "source": "NCBI nuccore (RefSeq)",
        "query": REFSEQ_QUERY,
        "human_contaminant_accession": HUMAN_MITO,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records_requested": len(ids),
    }
    (CACHE_DIR / "refseq_fetch.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return target


# --------------------------------------------------------------------------
# Boundary (OpenStreetMap, ODbL)
# --------------------------------------------------------------------------

BOUNDARY_RELATION = 6803599  # "Litoral Norte" protected area, northern Portugal
OVERPASS = "https://overpass-api.de/api/interpreter"


def _stitch(ways: List[List[tuple]]) -> List[List[tuple]]:
    rings = []
    pool = [list(w) for w in ways]
    while pool:
        ring = pool.pop(0)
        moved = True
        while moved and ring[0] != ring[-1]:
            moved = False
            for i, w in enumerate(pool):
                if w[0] == ring[-1]:
                    ring += w[1:]
                elif w[-1] == ring[-1]:
                    ring += w[::-1][1:]
                elif w[-1] == ring[0]:
                    ring = w[:-1] + ring
                elif w[0] == ring[0]:
                    ring = w[::-1][:-1] + ring
                else:
                    continue
                pool.pop(i)
                moved = True
                break
        rings.append(ring)
    return rings


def fetch_boundary(relation: int = BOUNDARY_RELATION) -> Path:
    import urllib.request
    body = urllib.parse.urlencode({"data": "[out:json][timeout:90];relation({});out geom;".format(
        relation)}).encode()
    req = urllib.request.Request(OVERPASS, data=body,
                                 headers={"User-Agent": "BioRadar-hackathon/1.0 (eDNA research)"})
    with _urlopen_request(req) as response:
        doc = json.loads(response.read())
    rel = doc["elements"][0]
    ways = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel["members"]
            if m["type"] == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
    rings = [r for r in _stitch(ways) if r[0] == r[-1]]
    feature = {"type": "Feature", "properties": {
        "name": rel["tags"].get("name", "boundary"),
        "osm_relation": relation,
        "source": "OpenStreetMap contributors, ODbL - https://www.openstreetmap.org/relation/{}".format(
            relation),
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tags": {k: v for k, v in rel["tags"].items() if k in (
            "name", "boundary", "protect_class", "designation", "type")},
    }, "geometry": {"type": "MultiPolygon", "coordinates": [[[list(pt) for pt in r]] for r in rings]}}
    target = DATA_DIR / "boundary" / "litoral_norte.geojson"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}),
                      encoding="utf-8")
    return target


def _urlopen_request(req):
    import ssl
    from bioradar.fetch_data import _ssl_context
    import urllib.request
    return urllib.request.urlopen(req, timeout=120, context=_ssl_context())


def fetch_records() -> Path:
    """Snapshot the archive metadata of the project used for the data-guard checks."""
    query = urllib.parse.urlencode({
        "accession": "PRJEB108476", "result": "read_run", "format": "tsv",
        "fields": "run_accession,sample_accession,sample_alias,scientific_name,collection_date,"
                  "country,location,lat,lon,read_count,fastq_md5,experiment_title,first_public"})
    target = DATASETS_DIR / RECORDS_FOLDER / "records" / "PRJEB108476_runs.tsv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_get("{}?{}".format(ENA_FILEREPORT, query)))
    return target


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=["samples", "reads", "reference", "records", "boundary", "all"])
    args = parser.parse_args(argv)
    if args.what == "reads":
        print("Reads (from the committed manifest, md5-verified):")
        bad = fetch_reads_from_manifest()
        print("done, {} failure(s)".format(bad))
        return 1 if bad else 0
    if args.what in ("samples", "all"):
        print("Samples:")
        print("  manifest ->", fetch_samples())
    if args.what in ("records", "all"):
        print("Records:", fetch_records())
    if args.what in ("boundary", "all"):
        print("Boundary:", fetch_boundary())
    if args.what in ("reference", "all"):
        print("Reference:")
        print("  ->", fetch_reference())
    return 0


if __name__ == "__main__":
    sys.exit(main())
