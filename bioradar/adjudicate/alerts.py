"""Invasive-species alerts for the forest officer.

A confirmed alert needs a species-level call (kept) on the documented invasive list.
A "WATCH" alert is raised when a sequence cannot be told apart from a listed species:
it is shown, clearly marked not-confirmed, and never as a detection.

The alert is a dashboard banner plus a log line. No SMS, e-mail or webhook is sent.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "real_challenge"
INVASIVE_FILE = DATA_DIR / "lists" / "invasive_species.json"
RESULTS_DIR = DATA_DIR / "results"
ALERT_LOG = RESULTS_DIR / "alert_log.jsonl"

ACTIONS = {
    "CRITICAL": "Send a field team to this pin within days to confirm the fish by net or a second "
                "water sample. Do not release or move any fish from this water until confirmed.",
    "HIGH": "Plan a field check at this pin. Take a second water sample and look for the fish. "
            "Report it to the regional fisheries or forest office.",
    "WATCH": "Do not act yet. The DNA cannot be told apart from an invasive fish. Take a new "
             "water sample here (retake) or send the sequence for expert review.",
}


def load_list(path: Path = INVASIVE_FILE) -> Dict[str, Any]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    doc["by_name"] = {s["name"].lower(): s for s in doc["species"]}
    return doc


def sample_country(meta: Dict[str, Any]) -> str:
    """Country the sample was collected in, from the submitter's `geo_loc_name`
    ('China:HongQimen'). Empty string when the record does not say."""
    attrs = meta.get("biosample_attributes") or {}
    return str(attrs.get("geo_loc_name", "")).split(":")[0].strip()


def native_here(hit: Dict[str, Any], meta: Dict[str, Any]) -> bool:
    """True when the listed species is documented as native in the sample's country.
    Unknown country or no `native_in` data means False: the alert is never hidden by
    missing information."""
    country = sample_country(meta).lower()
    return bool(country) and country in {c.lower() for c in hit.get("native_in", [])}


def native_policy(hit: Dict[str, Any], meta: Dict[str, Any]) -> Optional[str]:
    """What to do when a globally-listed invasive fish is detected where it is NATIVE.

    Return None to suppress the alert, "" to raise it exactly as before, or a short
    sentence to raise it with that sentence shown to the officer as `native_range_note`.

    Policy: suppress. Calling a fish "invasive" in the country it is native to is a false
    alarm that sends a field team to the wrong place. It is not hidden: `native_listed`
    records it in the sample result, and eDNA alone cannot tell a native population from a
    translocated one, so the note says so.
    """
    return None


def native_listed(result: Dict[str, Any], invasive: Optional[Dict[str, Any]] = None
                  ) -> List[Dict[str, Any]]:
    """Listed invasive species seen in this sample that are native at the sample country.
    These raise no alert; they are recorded so the suppression is visible and auditable.
    A species the sample also CONFIRMS elsewhere is reported once, as confirmed."""
    invasive = invasive or load_list()
    meta = result.get("metadata", {})
    country = sample_country(meta)
    out: Dict[str, Dict[str, Any]] = {}
    for row in result.get("species", []):
        if row["kind"] == "species":
            if row["status"] != "detected":
                continue
            names, how = [row["species"]], "detected"
        else:
            names, how = list(row["members"]), "cannot be told apart from"
        for name in names:
            hit = invasive["by_name"].get(name.lower())
            if hit and native_here(hit, meta) and hit["name"] not in out:
                out[hit["name"]] = {
                    "species": hit["name"], "common_name": hit["common"], "country": country,
                    "reads": row["reads"], "share": row["share"],
                    "basis": "confirmed" if row["kind"] == "species" else "possible",
                    "note": "On the global invasive list but native in {}: no alert raised. "
                            "eDNA cannot separate a native population from a translocated "
                            "one.".format(country)}
    return list(out.values())


def evaluate(result: Dict[str, Any], invasive: Optional[Dict[str, Any]] = None,
             started: Optional[float] = None) -> List[Dict[str, Any]]:
    """Alert events for one adjudicated sample. `started` is a time.time() for latency.

    * confirmed: a species-level call (>= min_detection_reads) that is on the list;
    * possible : a sequence group that cannot be told apart from a listed species.
    Rules that keep the officer's queue honest: a species that is native at the sample's
    country raises nothing (see native_policy); a species already confirmed is not repeated
    as 'possible'; one 'possible' event per listed species, from the group with most reads.
    """
    invasive = invasive or load_list()
    by_name = invasive["by_name"]
    meta = result.get("metadata", {})
    pin = {"latitude": meta.get("latitude"), "longitude": meta.get("longitude"),
           "precision_note": meta.get("coordinate_note", "")}
    events: List[Dict[str, Any]] = []
    confirmed: set = set()
    rows = result.get("species", [])

    for row in rows:
        if row["kind"] != "species" or row["status"] != "detected":
            continue
        hit = by_name.get(row["species"].lower())
        if not hit:
            continue
        note = ""
        if native_here(hit, meta):
            note = native_policy(hit, meta)
            if note is None:
                continue
        event = _event(result, hit, hit["level"], "confirmed", row, pin, started)
        if note:
            event["native_range_note"] = note
        events.append(event)
        confirmed.add(hit["name"])

    seen_possible: set = set()
    from bioradar.adjudicate.thresholds import load as _load_thresholds
    min_reads = _load_thresholds().min_detection_reads  # a few stray reads are trace, never an alert
    for row in sorted((r for r in rows if r["kind"] != "species" and r["reads"] >= min_reads),
                      key=lambda r: -r["reads"]):
        for member in row["members"]:
            hit = by_name.get(member.lower())
            if not hit or hit["name"] in confirmed or hit["name"] in seen_possible:
                continue
            if native_here(hit, meta) and native_policy(hit, meta) is None:
                continue
            seen_possible.add(hit["name"])
            events.append(_event(result, hit, "WATCH", "possible", row, pin, started,
                                 members=row["members"]))

    order = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}
    events.sort(key=lambda e: (order[e["level"]], -e["reads"]))
    return events


def _event(result, hit, level, kind, row, pin, started, members=None) -> Dict[str, Any]:
    meta = result.get("metadata", {})
    name = hit["name"]
    text = ("Possible {} ({}) at this site - NOT confirmed".format(hit["common"], name)
            if kind == "possible" else "{} ({}) detected".format(hit["common"], name))
    return {
        "raised_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latency_seconds": round(time.time() - started, 2) if started else None,
        "sample_id": result.get("sample_id"),
        "sample_label": meta.get("label", ""),
        "collected": meta.get("collection_date", ""),
        "level": level,
        "kind": kind,
        "headline": text,
        "species": name,
        "common_name": hit["common"],
        "list_level": hit["level"],
        "reads": row["reads"],
        "share": row["share"],
        "confidence": row["confidence"],
        "score_type": row.get("score_type", "heuristic_identity_x_margin"),
        "best_identity": row["best_identity"],
        "pin": pin,
        "candidates": members or [name],
        "sources": hit["sources"],
        "action": ACTIONS[level],
    }


def log(events: List[Dict[str, Any]], path: Path = ALERT_LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def read_log(path: Path = ALERT_LOG, limit: int = 100) -> List[Dict[str, Any]]:
    if not Path(path).is_file():
        return []
    lines = Path(path).read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(line) for line in lines][::-1]
