"""Download the real public dataset and the reference list, and record both.

Nothing here creates or edits a sequence. Every file comes from a public archive
and is checked against the archive's own md5 before it is trusted.

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


RETRIES = 4


def _retry(call, what: str):
    """Run `call()`; retry on timeouts and 5xx with growing pauses. 4xx is a real error, not retried."""
    import urllib.error
    last = None
    for attempt in range(RETRIES):
        try:
            return call()
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last = exc
        wait = 3 * (attempt + 1)
        print("  {} failed ({}); retry {}/{} in {}s".format(what, last, attempt + 1, RETRIES - 1, wait), flush=True)
        time.sleep(wait)
    raise RuntimeError("{} failed after {} attempts: {}".format(what, RETRIES, last))


def _get(url: str, timeout: int = 120) -> bytes:
    def once() -> bytes:
        with _urlopen(url, timeout=timeout) as response:
            return response.read()
    return _retry(once, url.split("?")[0])


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

    def once() -> None:
        with _urlopen(url, timeout=300) as response, tmp.open("wb") as out:
            for chunk in iter(lambda: response.read(1 << 20), b""):
                out.write(chunk)
        if _md5(tmp) != md5:
            tmp.unlink()
            raise OSError("md5 mismatch for {} -- download corrupted".format(url))

    _retry(once, destination.name)
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
        "used_for": "fish mixtures made on purpose (A to D), and the same four river places sampled in summer (August 2019) and winter (November 2019)",
    },
    {
        "bioproject": "PRJNA1433820",
        "folder": "PRJNA1433820_martapura_12S",
        "title": "eDNA metabarcoding of freshwater fishes, Martapura River & irrigation (12S MiFish-U)",
        "centre": "Universitas Airlangga",
        "publication": "none listed in the archive record",
        "runs": ["SRR37521672", "SRR37521667"],
        "used_for": "a river sample with many short pieces of DNA and real harmful fish (Nile tilapia, sailfin catfish)",
    },
    {
        "bioproject": "PRJNA1269473",
        "folder": "PRJNA1269473_british_columbia_12S",
        "title": "eDNA metabarcoding (12S, MiFish-U), British Columbia",
        "centre": "see ENA record",
        "publication": "none listed in the archive record",
        "runs": ["SRR33845265", "SRR33845234"],
        "used_for": "real water samples with very little DNA (a few hundred pieces): unusable, so collect again",
    },
    {
        "bioproject": "PRJNA985779",
        "folder": "PRJNA985779_uk_12S",
        "title": "12S MiFish water sample metabarcode data, United Kingdom",
        "centre": "see ENA record",
        "publication": "none listed in the archive record",
        "runs": ["SRR25108818"],
        "used_for": "a real blank water sample with very little DNA",
    },
]


def fetch_from_manifest() -> Path:
    """Download exactly the files the committed manifest lists, verifying each md5.

    This is the clean-start path: it never re-queries ENA, so it cannot change the committed
    manifest, and it needs no network service except the file server itself."""
    manifest = DATA_DIR / "manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    total = fresh = 0
    for ds in doc["datasets"]:
        files = [f for run in ds["runs"] for f in run["files"]] + list(ds.get("reference_files", []))
        for f in files:
            status = download_verified(f["source_url"], DATA_DIR / f["file"], f["md5"])
            total += 1
            fresh += status == "downloaded"
            print("  {:<11} {}".format(status, f["file"].rsplit("/", 1)[-1]), flush=True)
    print("  {} files verified against the manifest ({} downloaded)".format(total, fresh), flush=True)
    return manifest


ZENODO_RECORD = "4025362"
FISH_EGG_FOLDER = "ZENODO4025362_fish_egg_mock"


def fetch_fish_egg_mock() -> Path:
    """Register the fish-egg mock-community dataset (Duke & Burton 2020) in the manifest and download it.

    Files come from the Zenodo mirror of the Dryad deposit (CC0); each is checked against the md5 Zenodo publishes.
    Which library is which mock community comes from the paper's Table S1 (ground_truth/), not from file names."""
    import urllib.parse
    folder = DATASETS_DIR / FISH_EGG_FOLDER
    truth = json.loads((folder / "ground_truth" / "fish_egg_ground_truth.json").read_text(encoding="utf-8"))
    rec = json.loads(_get("https://zenodo.org/api/records/" + ZENODO_RECORD))
    by_key = {f["key"]: f for f in rec["files"]}

    def file_entry(key: str) -> Dict[str, Any]:
        f = by_key[key]
        return {"file": "datasets/{}/raw/{}".format(FISH_EGG_FOLDER, key), "mate": 1,
                "md5": f["checksum"].split(":", 1)[1], "bytes": int(f["size"]),
                "source_url": "https://zenodo.org/api/records/{}/files/{}/content".format(
                    ZENODO_RECORD, urllib.parse.quote(key))}

    runs = []
    for lib, info in truth["library_key"].items():
        if info["kind"] != "pooled":
            continue
        key = next(k for k in by_key if k.startswith(lib + "_S") and k.endswith("_merged.fa"))
        mc = truth["mock_communities"][info["mock"]]
        runs.append({
            "run_accession": "ZEN-" + lib, "biosample": "", "sample_alias": lib, "collection_date": "", "location": "",
            "latitude_longitude_as_deposited": ["", ""],
            "design_note_from_submitter": "mock community {} ({} species, {} eggs), {} amplicon, pooled replicate PCRs".format(
                info["mock"], mc["species_count"], mc["total_eggs"], info["primers"]),
            "biosample_attributes": {}, "experiment": "Illumina MiSeq 2x300, merged read pairs (FASTA)",
            "instrument": "Illumina MiSeq", "read_pairs": 0,
            "marker": info["primers"], "mock_community": info["mock"], "library_kind": info["kind"],
            "analyses": [{"profile": "fish_egg_paper", "role": "mixed"},
                         {"profile": "refseq_coi_16s", "role": "unknowns"}],
            "files": [file_entry(key)],
        })
    entry = {
        "bioproject": "ZENODO-4025362", "folder": FISH_EGG_FOLDER,
        "title": "Fish-egg mock communities with known proportions (COI and 16S)",
        "centre": "Scripps Institution of Oceanography (Duke & Burton)",
        "publication": "Duke EM, Burton RS (2020) Ecology and Evolution 10:3463-3476, doi:10.1002/ece3.6144",
        "runs": runs, "ena_url": "https://zenodo.org/records/" + ZENODO_RECORD,
        "used_for": "fish mixtures whose fish AND amounts are published (a known answer), and fish that are missing from the public list (unknown, but the true name is known)",
        "doi": "10.5061/dryad.zw3r22854", "license": "CC0-1.0",
        "reference_files": [file_entry("Burton_Hastings_COI_16S.fasta")],
        "reference_note": "the authors' own COI + 16S reference library for these species",
    }
    manifest = DATA_DIR / "manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["datasets"] = [d for d in doc["datasets"] if d["bioproject"] != entry["bioproject"]] + [entry]
    manifest.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    _write_dataset_folder(entry)
    return manifest


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
        lines.append("| {} | {} | {} | {} | {} | `{}` |".format(
            run["run_accession"], run["sample_alias"], run["collection_date"] or "n/a",
            run["location"] or "n/a", "{:,}".format(run["read_pairs"]) if run["read_pairs"] else "n/a",
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
        "mates_downloaded": "Only the first file of each pair (R1) is used. Files are stored unchanged and checked against the archive's fingerprint (md5). No DNA code or record was made up or edited.",
        "datasets": out_sets,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


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
    meta_file = CACHE_DIR / "refseq_fetch.json"
    if target.is_file() and meta_file.is_file() and (CACHE_DIR / "human_mito.fasta").is_file():
        have = sum(1 for line in target.read_text(encoding="utf-8").splitlines() if line.startswith(">"))
        recorded = json.loads(meta_file.read_text(encoding="utf-8")).get("records_requested")
        if recorded == len(ids) and have == len(ids):
            print("  cached: {} records already match the current NCBI query".format(have), flush=True)
            return target  # keep the recorded retrieval date: the reference version must not drift
    # Rewrite from scratch through a temp file. Never append: re-running used to duplicate every record.
    tmp = target.with_suffix(".fasta.part")
    with tmp.open("w", encoding="utf-8") as out:
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
    tmp.replace(target)
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
OVERPASS_MIRRORS = [OVERPASS, "https://overpass.kumi.systems/api/interpreter"]


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
    last = None
    for endpoint in OVERPASS_MIRRORS:
        req = urllib.request.Request(endpoint, data=body,
                                     headers={"User-Agent": "BioRadar-hackathon/1.0 (eDNA research)"})
        try:
            doc = json.loads(_retry(lambda: _urlopen_request(req).read(), endpoint))
            break
        except Exception as exc:  # try the next mirror
            last = exc
            print("  boundary mirror {} unavailable: {}".format(endpoint, exc), flush=True)
    else:
        raise RuntimeError("no Overpass mirror answered: {}".format(last))
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
    parser.add_argument("what", choices=["samples", "reference", "records", "boundary", "fish_egg", "all"])
    parser.add_argument("--refresh", action="store_true",
                        help="re-query the archives and rewrite the committed manifest/snapshots")
    args = parser.parse_args(argv)
    records_file = DATASETS_DIR / RECORDS_FOLDER / "records" / "PRJEB108476_runs.tsv"
    boundary_file = DATA_DIR / "boundary" / "litoral_norte.geojson"
    manifest = DATA_DIR / "manifest.json"
    steps = []
    if args.what == "fish_egg":
        steps.append(("Fish-egg mock communities (register in the manifest, md5-verified)", fetch_fish_egg_mock))
    if args.what in ("samples", "all"):
        if manifest.is_file() and not args.refresh:
            steps.append(("Samples (from the committed manifest, md5-verified)", fetch_from_manifest))
        else:
            steps.append(("Samples (querying ENA, rewriting the manifest)", fetch_samples))
    committed_reference = DATA_DIR / "reference" / "refseq_fish_12s" / "reference.fasta"
    if args.what == "reference" or (args.what == "all" and (args.refresh or not committed_reference.is_file())):
        steps.append(("Reference (RefSeq fish mitogenomes + human)", fetch_reference))
    elif args.what == "all":
        print("Reference: the built reference is committed ({}); mitogenome download skipped "
              "(`fetch reference` or --refresh rebuilds it)".format(committed_reference.name))
    for name, func, target in (("records", fetch_records, records_file), ("boundary", fetch_boundary, boundary_file)):
        if args.what == name or (args.what == "all" and not target.is_file()) or (args.what == "all" and args.refresh):
            steps.append(("Snapshot: " + name, func))
        elif args.what == "all":
            print("Snapshot: {} present ({}); not re-fetched (use --refresh)".format(name, target.name))
    failed = []
    for title, func in steps:
        print(title + ":", flush=True)
        try:
            print("  ->", func())
        except Exception as exc:  # report the step, keep going so one flaky service does not hide the rest
            print("  FAILED: {}".format(exc), flush=True)
            failed.append(title)
    if failed:
        print("\nFetch incomplete. Failed: {}. Re-run the same command; finished files are kept.".format("; ".join(failed)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
