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
from bioradar.adjudicate import reference as reference_lists
from bioradar.adjudicate.reference import REF_COI16S_DIR, PAPER_REF, REF_DIR, Reference
from bioradar.adjudicate.thresholds import THRESHOLDS_FILE, load

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "real_challenge"
RESULTS_DIR = DATA_DIR / "results"
MANIFEST = DATA_DIR / "manifest.json"
ENGINE_VERSION = "1"
MAX_DROPPED_SHOWN = 400  # the full list is in the CSV; the JSON keeps the top by reads

# Why each real sample was chosen. Anything not listed here is an ordinary field sample.
ROLES = {
    "SRR27401753": ("mixed", "A mixture made on purpose from 15 fish. Only the number of fish is published, not how much of each"),
    "SRR27401744": ("mixed", "A mixture made on purpose, with very different amounts of each fish"),
    "SRR33845265": ("poor", "Real water sample with only 361 pieces of DNA, much of it human or unusable. It should be collected again"),
    "SRR33845234": ("poor", "Real water sample with very little DNA (814 pieces)"),
    "SRR25108818": ("poor", "A blank: water that should hold no fish DNA (343 pieces)"),
    "SRR37521672": ("unknowns", "River water with many short pieces, fish the list does not know, and real harmful fish"),
    "SRR37521667": ("unknowns", "River water with many short pieces of DNA"),
}


TRUTH_FILE = DATA_DIR / "datasets" / "ZENODO4025362_fish_egg_mock" / "ground_truth" / "fish_egg_ground_truth.json"
PROFILE_FASTA = {"refseq_12s": REF_DIR / "reference.fasta", "refseq_coi_16s": REF_COI16S_DIR / "reference.fasta",
                 "fish_egg_paper": PAPER_REF}
PROFILE_LABEL = {"refseq_12s": "public RefSeq list (12S)", "refseq_coi_16s": "public RefSeq list",
                 "fish_egg_paper": "authors' own reference"}
_TRUTH: Dict[str, Any] = {}


def ground_truth() -> Dict[str, Any]:
    if not _TRUTH and TRUTH_FILE.is_file():
        _TRUTH.update(json.loads(TRUTH_FILE.read_text(encoding="utf-8")))
    return _TRUTH


def _pct_list(species: Dict[str, float]) -> str:
    return " / ".join("{:.0%}".format(v) if v >= 0.095 else "{:.1%}".format(v)
                      for v in sorted(species.values(), reverse=True)[:6])


def sample_table() -> List[Dict[str, Any]]:
    """Flatten the manifest into one metadata row per analysis (a run can be analysed against several references)."""
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for ds in doc["datasets"]:
        for run in ds["runs"]:
            if not run["files"]:
                continue
            if run.get("analyses"):
                rows.extend(_mock_rows(ds, run))
                continue
            lat, lon = (run["latitude_longitude_as_deposited"] + ["", ""])[:2]
            location = run["location"].split(":")[-1].strip() if run["location"] else ""
            role, why = ROLES.get(run["run_accession"], ("field", "Real water sample"))
            note_text = (run.get("design_note_from_submitter") or "").lower()
            if ds["bioproject"] == "PRJNA1059782" and ("gradient" in note_text or "orders of magnitude" in note_text):
                role, why = "mixed", ("A mixture made on purpose from 15 fish ('{}')".format(
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
                "profile": "refseq_12s",
                "marker": "12S",
                "file": str(DATA_DIR / run["files"][0]["file"]),
                "md5": run["files"][0]["md5"],
                "source_url": run["files"][0]["source_url"],
            })
    return rows


def _mock_rows(ds: Dict[str, Any], run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The fish-egg mock libraries: one row per reference they are judged against."""
    truth = ground_truth()
    mc = truth["mock_communities"][run["mock_community"]]
    out = []
    for analysis in run["analyses"]:
        profile = analysis["profile"]
        public = profile == "refseq_coi_16s"
        out.append({
            "sample_id": run["run_accession"] + ("-public" if public else ""),
            "alias": run["sample_alias"],
            "label": "{} - mock {} ({}) - {}".format(run["sample_alias"], run["mock_community"], run["marker"],
                                                   PROFILE_LABEL[profile]),
            "bioproject": ds["bioproject"], "dataset_title": ds["title"], "location": "", "collection_date": "",
            "latitude": None, "longitude": None, "coordinate_note": "",
            "design_note": run["design_note_from_submitter"], "biosample_attributes": {}, "biosample": "",
            "role": "unknown_truth" if public else "mixed_truth",
            "why_chosen": (
                "The same real DNA as the mixture with the authors' own library, now judged against the {}. That list has no "
                "entry for some of these fish. Their DNA must stay unknown and not get a wrong name. The paper says what "
                "they really are."
                if public else
                "A mixture made on purpose from {} fish whose eggs were counted by hand, so the true shares are published: {}. "
                "The result is checked against them.").format(
                    *( [PROFILE_LABEL[profile]] if public else [mc["species_count"], _pct_list(mc["species"])])),
            "profile": profile, "marker": run["marker"], "mock_community": run["mock_community"],
            "library": run["sample_alias"],
            "file": str(DATA_DIR / run["files"][0]["file"]), "md5": run["files"][0]["md5"],
            "source_url": run["files"][0]["source_url"],
        })
    return out


def _expected_spec(row: Dict[str, Any]) -> Dict[str, Any]:
    """Source-supported composition for a mock library (paper Table 1 + Table S1), or {}."""
    truth = ground_truth()
    mc = truth.get("mock_communities", {}).get(row.get("mock_community", ""))
    if not mc:
        return {}
    src = truth["source"]
    fps = truth["false_positives_listed_by_paper"].get(row["library"], [])
    return {"source": "{}. Proportions of eggs per species: Table 1; library and primer: supplementary Table S1.".format(
                src["paper"]),
            "species": [{"name": n, "expected_share": v} for n, v in mc["species"].items()],
            "false_positives": [f for f in fps if f["locus"] == row["marker"]]}


def _cache_key(row: Dict[str, Any]) -> str:
    fasta = PROFILE_FASTA[row.get("profile", "refseq_12s")]
    blob = "|".join([row["md5"], ENGINE_VERSION, row.get("profile", "refseq_12s"),
                     hashlib.md5(THRESHOLDS_FILE.read_bytes()).hexdigest(),
                     hashlib.md5(fasta.read_bytes()).hexdigest(),
                     hashlib.md5(TRUTH_FILE.read_bytes()).hexdigest() if TRUTH_FILE.is_file() else ""])
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
    ref = reference_lists.load_profile(row.get("profile", "refseq_12s"))
    result = adjudicate_file(row["file"], row, ref, t)
    if row.get("profile") == "refseq_coi_16s":
        _answer_key(result, row, ref, t)
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
    wanted = dict(expected.load_expected())
    spec = _expected_spec(row)
    if spec and row.get("profile") == "fish_egg_paper":
        wanted[row["sample_id"]] = spec
    result["expected_check"] = (_unknown_check(result, row, ref) if row.get("profile") == "refseq_coi_16s"
                                else expected.check(result, wanted, t))
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


ANSWER_KEY_CAP = 6000  # unknown sequences looked up in the answer key per sample


def _answer_key(result: Dict[str, Any], row: Dict[str, Any], ref: Reference, t: Any) -> None:
    """Ask the paper's own reference what each unknown sequence really is (the 'reviewable identity').

    The analysis itself never sees this list: the unknown stays unknown and unconfirmed. This is the review step an
    expert would do with a better database, recorded next to the unknown so the result can be judged."""
    key_ref = reference_lists.load_profile("fish_egg_paper")
    cutoff = t.for_marker(row.get("marker", "")).identity_species
    mock = ground_truth()["mock_communities"][row["mock_community"]]["species"]
    groups: Dict[str, Dict[str, Any]] = {}
    for item in result["unknown_queue"][:ANSWER_KEY_CAP]:
        hit = key_ref.search(item["sequence"], cutoff)
        if not hit or hit[0].identity < cutoff:
            continue
        item["answer_key"] = {"species": hit[0].species, "identity": hit[0].identity}
        g = groups.setdefault(hit[0].species, {"true_species": hit[0].species, "reads": 0, "sequences": 0,
                                               "closest_public": {}, "in_mock_design": hit[0].species in mock,
                                               "expected_share": mock.get(hit[0].species)})
        g["reads"] += item["reads"]
        g["sequences"] += 1
        cp = g["closest_public"].setdefault(item["closest_match"], 0)
        g["closest_public"][item["closest_match"]] = cp + item["reads"]
    out = []
    for g in groups.values():
        closest = sorted(g.pop("closest_public").items(), key=lambda kv: -kv[1])
        g["closest_public_match"] = closest[0][0] if closest else ""
        out.append(g)
    out.sort(key=lambda g: -g["reads"])
    result["unknown_groups"] = out


def _unknown_check(result: Dict[str, Any], row: Dict[str, Any], ref: Reference) -> Dict[str, Any]:
    truth = ground_truth()
    mock = truth["mock_communities"][row["mock_community"]]["species"]
    in_list = {e[1] for e in ref.entries}
    absent = [s for s in mock if s not in in_list]
    groups = result.get("unknown_groups", [])
    explained = [g for g in groups if g["in_mock_design"] and g["true_species"] in absent]
    wrong = [r for r in result["species"] if r["kind"] == "species" and r["status"] == "detected"
             and r["species"] not in mock]
    return {"available": True, "mode": "unknown_identity",
            "source": "Paper Table 1 (which fish were mixed) and the authors' own fish DNA library (what each unknown "
                      "piece really is). DOI 10.1002/ece3.6144, Zenodo 4025362.",
            "absent_from_public_list": absent, "expected_count": len(mock),
            "unknown_groups_explained": len(explained), "unknown_groups": groups[:8],
            "wrong_confident_calls": [{"species": r["species"], "reads": r["reads"]} for r in wrong],
            "verdict": ("{} of the {} fish in this mixture are missing from the public list. Their DNA was kept as "
                        "unknown and not given a wrong name. The authors' own library says the {} biggest unknown "
                        "groups are: {}.").format(
                            len(absent), len(mock), min(2, len(explained)),
                            ", ".join(g["true_species"] for g in explained[:2]) or "(none matched)"),
            "limits": "The answer comes from the authors' own library, so it is not an independent check. It shows that the "
                      "unknown DNA belongs to fish that were really in the mixture. It does not make them confirmed "
                      "inside the analysis."}


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

    rows_by_id = {row["sample_id"]: row for row in table}   # the current wording, not what a cached result holds
    index = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seconds": round(time.time() - t0, 1),
        "samples": [{
            "sample_id": r["sample_id"], "label": r["metadata"]["label"],
            "bioproject": r["metadata"]["bioproject"], "role": r["metadata"]["role"],
            "why_chosen": rows_by_id[r["sample_id"]]["why_chosen"], "collection_date": r["metadata"]["collection_date"],
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
    sub.add_parser("verify")
    p_all = sub.add_parser("all")
    p_all.add_argument("--workers", type=int, default=4)
    p_all.add_argument("--force", action="store_true")
    p_one = sub.add_parser("sample")
    p_one.add_argument("sample_id")
    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        from bioradar.adjudicate import fetch
        return fetch.main(["all"])
    if args.cmd == "verify":
        from bioradar.adjudicate import compliance
        return compliance.run()
    if args.cmd == "sample":
        r = run_sample(args.sample_id, force=True)
        print(r["verdict"], r["verdict_reasons"], r["seconds"], "s")
        return 0
    index = run_all(args.workers, args.force)
    print("done: {} samples in {}s".format(len(index["samples"]), index["seconds"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
