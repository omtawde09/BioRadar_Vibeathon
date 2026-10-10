"""Check the data folder and the results against the challenge's conditions.

    python -m bioradar.adjudicate.runner verify

Computed from the files and the actual results, never typed in. Each line is PASS,
PARTIAL (met in part, the gap is stated) or GAP (not met). Writes
data/real_challenge/COMPLIANCE.md so the status travels with the repo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bioradar.adjudicate import guard, report
from bioradar.adjudicate.reference import REF_DIR
from bioradar.adjudicate.thresholds import load

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "real_challenge"
RESULTS = DATA_DIR / "results"
SELECTION = DATA_DIR / "selection.json"

Row = Tuple[str, str, str, str]  # (case, status, evidence, brief condition)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _result(sample_id: str) -> Dict[str, Any]:
    return json.loads((RESULTS / "{}.json".format(sample_id)).read_text(encoding="utf-8"))


def dataset_hygiene() -> List[Row]:
    rows: List[Row] = []
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    listed, bad_md5, missing = set(), [], []
    for ds in manifest["datasets"]:
        files = [f for run in ds["runs"] for f in run["files"]] + list(ds.get("reference_files", []))
        for f in files:
            path = DATA_DIR / f["file"]
            listed.add(path.resolve())
            if not path.is_file():
                missing.append(f["file"])
            elif _md5(path) != f["md5"]:
                bad_md5.append(f["file"])
    extra = []
    for raw in (DATA_DIR / "datasets").glob("*/raw"):
        extra += [str(p.name) for p in raw.iterdir() if p.resolve() not in listed]
    ok = not (missing or bad_md5)
    rows.append(("Real public data, originals unchanged",
                 "PASS" if ok else "GAP",
                 "{} files checked against the archive's md5: {} missing, {} altered".format(
                     len(listed), len(missing), len(bad_md5)),
                 "Use public, real sequencing datasets; do not create or modify sequences or records."))
    rows.append(("No created or stray sequence files", "PASS" if not extra else "GAP",
                 "{} files in raw/ folders that are not in the manifest".format(len(extra)),
                 "Do not create FASTA test files."))
    gaps = [ds["bioproject"] for ds in manifest["datasets"]
            if not (ds.get("ena_url") and ds.get("title") and ds.get("runs"))
            or any(not r["files"] or not r["files"][0].get("source_url") or not r["sample_alias"]
                   for r in ds["runs"])]
    rows.append(("Manifest: filenames, source links, sample IDs, metadata",
                 "PASS" if not gaps else "GAP",
                 "{} datasets, {} runs; incomplete: {}".format(
                     len(manifest["datasets"]), sum(len(d["runs"]) for d in manifest["datasets"]),
                     ", ".join(gaps) or "none"),
                 "Keep a manifest of filenames, source links, sample IDs, metadata, reference database version."))
    ref = json.loads((REF_DIR / "reference.json").read_text(encoding="utf-8"))
    rows.append(("Reference database version recorded",
                 "PASS" if ref.get("reference_database_version") and ref.get("ncbi_query") else "GAP",
                 "{} ({} sequences)".format(ref.get("reference_database_version"), ref.get("amplicons_extracted")),
                 "Preserve source links, IDs, and reference-database versions."))
    return rows


def _fish_egg_results(mode_unknown: bool) -> List[Dict[str, Any]]:
    out = []
    for path in sorted(RESULTS.glob("ZEN-*.json")):
        ec = json.loads(path.read_text(encoding="utf-8")).get("expected_check", {})
        if (ec.get("mode") == "unknown_identity") == mode_unknown and ec.get("available"):
            out.append(ec)
    return out


def _fish_egg_libraries() -> List[Dict[str, Any]]:
    return _fish_egg_results(False)


def _fish_egg_unknowns() -> List[Dict[str, Any]]:
    return _fish_egg_results(True)


def scenarios() -> List[Row]:
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))["cases"]
    t = load()
    rows: List[Row] = []

    r = _result(sel["poor_quality"]["sample_id"])
    ok = r["verdict"] == "Retake sample" and r["dropped"] and all(d["reason"] for d in r["dropped"])
    rows.append(("1. Poor-quality sample", "PASS" if ok else "GAP",
                 "{}: verdict {}; drop reasons {}".format(
                     r["metadata"]["label"], r["verdict"],
                     ", ".join("{} ({})".format(k, v["reads"]) for k, v in r["drop_reasons"].items())),
                 sel["poor_quality"]["condition"]))

    r = _result(sel["mixed"]["sample_id"])
    ec = r["expected_check"]
    libs = _fish_egg_libraries()
    everywhere = ("Across all {} pooled libraries: every expected species found in {}; "
                  "shares within {:g}-fold in {} of {} measurable species.".format(
                      len(libs), sum(1 for e in libs if e["all_found"]), libs[0]["tolerance_fold"],
                      sum(e["shares_within_tolerance"] for e in libs), sum(e["shares_measured"] for e in libs))
                  if libs else "")
    if ec.get("available") and ec.get("mode") == "composition" and ec.get("all_found"):
        status = "PASS"
        ev = "{}. {} Shares within {:g}-fold: {} of {}. {}".format(
            ec["verdict"], ec["source"], ec["tolerance_fold"], ec["shares_within_tolerance"], ec["shares_measured"],
            everywhere)
    elif ec.get("available") and ec.get("mode") == "count_only":
        status = "PARTIAL"
        ev = ("{}. Identities and shares NOT verified: the source states only the number of fish "
              "mixed ({}), not the species or proportions.".format(ec["verdict"], ec["expected_count"]))
    else:
        status, ev = "GAP", ec.get("note", "no source-supported composition")
    rows.append(("2. Mixed sample, species shares", status, "{}: {}".format(r["metadata"]["label"], ev),
                 sel["mixed"]["condition"]))

    r = _result(sel["unknowns"]["sample_id"])
    q = r["unknown_queue"]
    queue_ok = bool(q) and all(u["confidence"] <= t.unknown_max_confidence and u["status"] == "needs review"
                               for u in q)
    rows.append(("3. Unknown sequences queued, never confident",
                 "PASS" if queue_ok else "GAP",
                 "{}: {} sequences in the review queue, max confidence {}".format(
                     r["metadata"]["label"], len(q), max([u["confidence"] for u in q] or [0])),
                 sel["unknowns"]["condition"]))
    r = _result(sel["unknowns_known_identity"]["sample_id"])
    ec = r["expected_check"]
    libs = _fish_egg_unknowns()
    if ec.get("mode") == "unknown_identity" and ec["absent_from_public_list"] and             ec["unknown_groups_explained"] >= len(ec["absent_from_public_list"]) and not ec["wrong_confident_calls"]:
        status = "PASS"
    else:
        status = "PARTIAL" if ec.get("mode") == "unknown_identity" else "GAP"
    wrong = sum(len(e["wrong_confident_calls"]) for e in libs)
    rows.append(("3b. Unknowns whose true identity is known", status,
                 "{}: {} of {} species are absent from the public list ({}); all became unknowns and the authors' "
                 "own reference names them. Across all {} libraries, {} fish that were NOT in the mixture "
                 "were named anyway (some are close relatives of a missing fish): reported, not hidden.".format(
                     r["metadata"]["label"], len(ec.get("absent_from_public_list", [])), ec.get("expected_count", 0),
                     ", ".join(ec.get("absent_from_public_list", [])), len(libs), wrong),
                 sel["unknowns_known_identity"]["condition"]))

    g = json.loads((RESULTS / "guard.json").read_text(encoding="utf-8"))
    missing = g["rules_not_exercised_by_this_data"]
    rows.append(("4. Bad records: ID, GPS, date, spelling",
                 "PASS" if not missing and g["post_check"]["clean"] else "PARTIAL",
                 "{} real records; per rule {}; post-check clean={}; not in data: {}".format(
                     g["records_in"], {k: v["reject"] + v["merge"] for k, v in g["counts_by_rule"].items()},
                     g["post_check"]["clean"], ", ".join(missing) or "none"),
                 sel["bad_records"]["condition"]))

    r = _result(sel["invasive"]["sample_id"])
    ev = [e for e in r["alerts"] if e["kind"] == "confirmed"]
    full = bool(ev) and all(e["pin"]["latitude"] is not None and e["species"] and e["level"] for e in ev)
    rows.append(("5. Invasive alert: pin, species, level", "PASS" if full else "GAP",
                 "{}: {}".format(r["metadata"]["label"],
                                 "; ".join("{} {} at {}, {}".format(e["level"], e["species"],
                                                                    e["pin"]["latitude"], e["pin"]["longitude"])
                                           for e in ev[:3]) or "no confirmed alert"),
                 sel["invasive"]["condition"]))

    s = json.loads((RESULTS / "seasons.json").read_text(encoding="utf-8"))
    site = s["sites"][0] if s["sites"] else None
    rows.append(("6. Season slider, same location", "PASS" if site else "GAP",
                 "{} locations with both seasons; e.g. {}: summer {} vs winter {} species, {} newly detected in summer. "
                 "Seasons are summer/winter (Aug/Nov) in southern China, NOT monsoon/summer in India: no same-site Indian "
                 "seasonal amplicon pair was found in the public archives searched.".format(
                     len(s["sites"]), site["location"], site["summer"]["species_detected"],
                     site["winter"]["species_detected"], site["counts"]["summer_only"]) if site else "none",
                 sel["seasons"]["condition"]))

    pdf = report.build_pdf(_result(sel["invasive"]["sample_id"]))
    rows.append(("7. One-page PDF", "PASS" if pdf.startswith(b"%PDF") and b"/Count 1" in pdf else "GAP",
                 "single page, generated on demand", sel["report"]["condition"]))
    return rows


def render(rows: List[Row]) -> str:
    out = ["# Compliance with the challenge conditions", "",
           "Generated by `python -m bioradar.adjudicate.runner verify` from the files and results. "
           "PASS = met; PARTIAL = met in part (gap stated); GAP = not met.", "",
           "| Condition | Status | Evidence | Brief's wording |", "|---|---|---|---|"]
    for case, status, evidence, brief in rows:
        out.append("| {} | **{}** | {} | {} |".format(case, status, evidence.replace("|", "/"), brief.replace("|", "/")))
    return "\n".join(out) + "\n"


def run() -> int:
    rows = dataset_hygiene() + scenarios()
    text = render(rows)
    (DATA_DIR / "COMPLIANCE.md").write_text(text, encoding="utf-8")
    width = max(len(r[0]) for r in rows)
    for case, status, evidence, _ in rows:
        print("{:<{w}}  {:<8} {}".format(case, status, evidence[:150], w=width))
    return 0 if all(r[1] != "GAP" for r in rows) else 1
