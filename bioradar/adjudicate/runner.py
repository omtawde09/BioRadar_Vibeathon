"""One command from a clean start to every result.

    python -m bioradar.adjudicate.runner all          # all real samples + guard + seasons
    python -m bioradar.adjudicate.runner sample SRR27401753
    python -m bioradar.adjudicate.runner fetch        # download real data first (md5-verified)

Results are cached by (file md5, thresholds, reference build, engine version), so the
demo shows pre-run output instantly and the same command re-runs only what changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioradar.adjudicate import alerts, expected, guard, seasons
from bioradar.adjudicate.adjudicate import adjudicate_file
from bioradar.adjudicate.reference import REF_DIR, Reference
from bioradar.adjudicate.thresholds import THRESHOLDS_FILE, load

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "real_challenge"
RESULTS_DIR = DATA_DIR / "results"
MANIFEST = DATA_DIR / "manifest.json"
ENGINE_VERSION = "1"
MAX_DROPPED_SHOWN = 400  # the full list is in the CSV; the JSON keeps the top by reads

# Why each real sample was chosen. Anything not listed here is an ordinary field sample.
ROLES = {
    "SRR27401753": ("mixed", "Mixed mock community (15 fish tissue DNAs) - tests the species split"),
    "SRR27401744": ("mixed", "Mixed mock community, abundances spanning four orders of magnitude"),
    "SRR33845265": ("poor", "Real field sample with only 361 reads, human DNA and junk - should be a retake"),
    "SRR33845234": ("poor", "Real low-yield field sample (814 reads)"),
    "SRR25108818": ("poor", "Real field water blank (343 reads)"),
    "SRR37521672": ("unknowns", "Freshwater sample: primer-dimer fragments, unknown fish, real invasive species"),
    "SRR37521667": ("unknowns", "Freshwater sample with many short fragments"),
}


def sample_table() -> List[Dict[str, Any]]:
    """Flatten the manifest into one metadata row per run."""
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for ds in doc["datasets"]:
        for run in ds["runs"]:
            if not run["files"]:
                continue
            lat, lon = (run["latitude_longitude_as_deposited"] + ["", ""])[:2]
            location = run["location"].split(":")[-1].strip() if run["location"] else ""
            role, why = ROLES.get(run["run_accession"], ("field", "Real field sample"))
            note_text = (run.get("design_note_from_submitter") or "").lower()
            if ds["bioproject"] == "PRJNA1059782" and ("gradient" in note_text or "orders of magnitude" in note_text):
                role, why = "mixed", ("Mock community of 15 fish tissue DNAs ('{}')".format(
                    run["design_note_from_submitter"]))
            note = ""
            if ds["bioproject"] == "PRJNA1059782" and lat:
                note = "coordinates were deposited at 1-degree precision (22 N 113 E), so every " \
                       "site in this project shares one pin"
            rows.append({
                "sample_id": run["run_accession"],
                "alias": run["sample_alias"],
                "label": "{} - {}".format(run["sample_alias"], location or "no location"),
                "bioproject": ds["bioproject"],
                "dataset_title": ds["title"],
                "location": location,
                "collection_date": run["collection_date"],
                "latitude": float(lat) if lat else None,
                "longitude": float(lon) if lon else None,
                "coordinate_note": note,
                "design_note": run.get("design_note_from_submitter", ""),
                "biosample_attributes": run.get("biosample_attributes", {}),
                "biosample": run["biosample"],
                "role": role,
                "why_chosen": why,
                "file": str(DATA_DIR / run["files"][0]["file"]),
                "md5": run["files"][0]["md5"],
                "source_url": run["files"][0]["source_url"],
            })
    return rows


def _cache_key(row: Dict[str, Any]) -> str:
    blob = "|".join([row["md5"], ENGINE_VERSION,
                     hashlib.md5(THRESHOLDS_FILE.read_bytes()).hexdigest(),
                     (REF_DIR / "reference.json").read_text(encoding="utf-8")])
    return hashlib.md5(blob.encode()).hexdigest()


def run_sample(sample_id: str, force: bool = False, log_alerts: bool = True) -> Dict[str, Any]:
    rows = {r["sample_id"]: r for r in sample_table()}
    if sample_id not in rows:
        raise KeyError("unknown sample {!r}".format(sample_id))
    row = rows[sample_id]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "{}.json".format(sample_id)
    key = _cache_key(row)
    started = time.time()
    if out.is_file() and not force:
        cached = json.loads(out.read_text(encoding="utf-8"))
        if cached.get("cache_key") == key:
            cached["from_cache"] = True
            return cached

    t = load()
    ref = Reference.load()
    result = adjudicate_file(row["file"], row, ref, t)
    full_dropped = result.pop("dropped")
    result.pop("kept")  # the species table already summarises the kept sequences
    csv_path = RESULTS_DIR / "{}_dropped.csv".format(sample_id)
    with csv_path.open("w", encoding="utf-8") as handle:
        handle.write("seq_id,reads,reason_code,reason,sequence\n")
        for d in full_dropped:
            handle.write('{},{},{},"{}",{}\n'.format(d["seq_id"], d["reads"], d["reason_code"],
                                                     d["reason"].replace('"', "'"), d["sequence"]))
    result["dropped"] = full_dropped[:MAX_DROPPED_SHOWN]
    result["dropped_total_listed"] = len(full_dropped)
    result["dropped_csv"] = csv_path.name
    result["expected_check"] = expected.check(result, expected.load_expected(), t)
    result["analysis_seconds"] = round(time.time() - started, 1)
    # Latency = how long after the result existed the alert was written. The analysis
    # time is reported separately and is not hidden inside this number.
    events = alerts.evaluate(result, started=time.time())
    for event in events:
        event["analysis_seconds"] = result["analysis_seconds"]
    result["alerts"] = events
    result["cache_key"] = key
    result["from_cache"] = False
    result["source_file"] = Path(row["file"]).name  # provenance only; never used by the engine
    out.write_text(json.dumps(result), encoding="utf-8")
    if log_alerts and events:
        alerts.log(events)
    return result


def _worker(sample_id: str) -> str:
    result = run_sample(sample_id, log_alerts=False)
    return "{} {} {}s".format(sample_id, result["verdict"], result["seconds"])


def run_all(workers: int = 4, force: bool = False) -> Dict[str, Any]:
    t0 = time.time()
    table = sample_table()
    ids = [r["sample_id"] for r in table]
    if force:
        for i in ids:
            (RESULTS_DIR / "{}.json".format(i)).unlink(missing_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for line in pool.map(_worker, ids):
            print("  ", line, flush=True)

    results = [run_sample(i) for i in ids]
    if alerts.ALERT_LOG.is_file():
        alerts.ALERT_LOG.unlink()
    for r in results:
        if r["alerts"]:
            alerts.log(r["alerts"])

    ref = Reference.load()
    import collections
    seqs, counts = {}, collections.Counter()
    for acc, sp, seq in ref.entries:
        seqs.setdefault(sp, seq)
        counts[sp] += 1
    boundary = guard.load_boundary()
    g = guard.run_guard(guard.load_records(), boundary, species_sequences=seqs,
                        species_counts=counts, spelling_merges=ref.spelling_merges)
    g["records_snapshot_md5"] = guard.file_md5(guard.RECORDS_TSV)
    g.pop("clean")
    (RESULTS_DIR / "guard.json").write_text(json.dumps(g), encoding="utf-8")

    season_doc = seasons.compare(results)
    (RESULTS_DIR / "seasons.json").write_text(json.dumps(season_doc), encoding="utf-8")

    index = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seconds": round(time.time() - t0, 1),
        "samples": [{
            "sample_id": r["sample_id"], "label": r["metadata"]["label"],
            "bioproject": r["metadata"]["bioproject"], "role": r["metadata"]["role"],
            "why_chosen": r["metadata"]["why_chosen"], "collection_date": r["metadata"]["collection_date"],
            "location": r["metadata"]["location"], "verdict": r["verdict"],
            "reads_total": r["reads_total"], "summary": r["summary"],
            "species_detected": sum(1 for s in r["species"] if s["kind"] == "species" and s["status"] == "detected"),
            "unknowns": r["summary"]["unknown"]["distinct"], "alerts": len(r["alerts"]),
        } for r in results],
    }
    (RESULTS_DIR / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return index


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    p_all = sub.add_parser("all")
    p_all.add_argument("--workers", type=int, default=4)
    p_all.add_argument("--force", action="store_true")
    p_one = sub.add_parser("sample")
    p_one.add_argument("sample_id")
    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        from bioradar.adjudicate import fetch
        return fetch.main(["all"])
    if args.cmd == "sample":
        r = run_sample(args.sample_id, force=True)
        print(r["verdict"], r["verdict_reasons"], r["seconds"], "s")
        return 0
    index = run_all(args.workers, args.force)
    print("done: {} samples in {}s".format(len(index["samples"]), index["seconds"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
