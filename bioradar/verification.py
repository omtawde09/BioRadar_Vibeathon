"""Field verification: closing the loop between a detection and the ground.

An eDNA platform that only emits alerts is making claims nobody ever checks. The
gap analysis calls the fix "the eDNA equivalent of iNaturalist's Research Grade",
and the mechanism is the same: a detection earns a status from independent
observation, not from the confidence number the classifier happened to produce.

A field officer records one of four outcomes for a taxon at a site:

  confirmed      seen, photographed, netted -- the organism is there
  not_found      looked for it properly and did not find it
  misidentified  something was there, but not that species
  uncertain      surveyed, inconclusive

The tally then adjusts how the detection is *presented*. Note the word: it
adjusts presentation, not data. The classifier's confidence is a property of the
sequence and never changes retroactively -- rewriting it would destroy the
chain-of-custody guarantee that the same input yields the same output. What
changes is the field status shown next to it, and that is the honest place to
put human evidence.

Storage is a JSON Lines file. Verifications are append-only on purpose: a record
of what somebody observed on a particular day is evidence, and evidence that can
be silently edited is not evidence. Corrections are added, not applied.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioradar import obs

log = obs.logger("verification")

REPO_ROOT = Path(__file__).resolve().parent.parent
STORE = REPO_ROOT / "data" / "verifications.jsonl"

CONFIRMED = "confirmed"
NOT_FOUND = "not_found"
MISIDENTIFIED = "misidentified"
UNCERTAIN = "uncertain"

OUTCOMES = (CONFIRMED, NOT_FOUND, MISIDENTIFIED, UNCERTAIN)

OUTCOME_LABELS = {
    CONFIRMED: "Confirmed in the field",
    NOT_FOUND: "Searched for, not found",
    MISIDENTIFIED: "Different species present",
    UNCERTAIN: "Surveyed, inconclusive",
}

# Field status, in the order a UI should rank them.
VERIFIED = "verified"
DISPUTED = "disputed"
CONTESTED = "contested"
UNVERIFIED = "unverified"

STATUS_LABELS = {
    VERIFIED: "Field verified",
    DISPUTED: "Not found in the field",
    CONTESTED: "Conflicting field reports",
    UNVERIFIED: "Not yet verified",
}

_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _key(scientific_name: str, site_id: str) -> str:
    """Species and place together. The same taxon can be right at one site and
    wrong at another 40 km away, so a per-species verdict would be nonsense."""
    return "{n}@{s}".format(n=(scientific_name or "").strip().lower(), s=(site_id or "").strip().lower())


def record(
    *,
    scientific_name: str,
    site_id: str,
    outcome: str,
    observer: str = "",
    run_id: str = "",
    sample_id: str = "",
    notes: str = "",
    observed_name: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    observed_at: str = "",
    photo: str = "",
    store: Optional[Path] = None,
) -> Dict[str, Any]:
    """Append one verification. Returns the stored record."""
    if outcome not in OUTCOMES:
        raise ValueError(
            "outcome must be one of {o}, got {got!r}".format(o=", ".join(OUTCOMES), got=outcome)
        )
    if not scientific_name.strip():
        raise ValueError("scientific_name is required")
    if outcome == MISIDENTIFIED and not observed_name.strip():
        raise ValueError(
            "recording a misidentification requires observed_name -- what was "
            "actually there is the useful half of the report"
        )

    entry = {
        "verification_id": uuid.uuid4().hex[:12],
        "recorded_at": _now(),
        "observed_at": observed_at or _now(),
        "scientific_name": scientific_name.strip(),
        "site_id": (site_id or "").strip(),
        "sample_id": sample_id,
        "run_id": run_id,
        "outcome": outcome,
        "observed_name": observed_name.strip(),
        "observer": observer.strip(),
        "notes": notes.strip()[:2000],
        "latitude": latitude,
        "longitude": longitude,
        "photo": photo,
    }

    target = Path(store) if store else STORE
    with _LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    log.info(
        "verification.recorded",
        species=entry["scientific_name"],
        site=entry["site_id"],
        outcome=outcome,
    )
    return entry


def load(store: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = Path(store) if store else STORE
    if not target.is_file():
        return []
    entries: List[Dict[str, Any]] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                # One malformed line must not hide every other verification.
                continue
    except OSError:
        return []
    return entries


def tally(store: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Aggregate verifications per species-and-site."""
    out: Dict[str, Dict[str, Any]] = {}
    for entry in load(store):
        key = _key(entry.get("scientific_name", ""), entry.get("site_id", ""))
        bucket = out.setdefault(
            key,
            {
                "scientific_name": entry.get("scientific_name", ""),
                "site_id": entry.get("site_id", ""),
                "confirmed": 0,
                "not_found": 0,
                "misidentified": 0,
                "uncertain": 0,
                "observers": set(),
                "latest": "",
                "observed_names": [],
            },
        )
        outcome = entry.get("outcome")
        if outcome in OUTCOMES:
            bucket[outcome] += 1
        if entry.get("observer"):
            bucket["observers"].add(entry["observer"])
        if entry.get("observed_name"):
            bucket["observed_names"].append(entry["observed_name"])
        if entry.get("recorded_at", "") > bucket["latest"]:
            bucket["latest"] = entry.get("recorded_at", "")

    for bucket in out.values():
        bucket["observers"] = sorted(bucket["observers"])
        bucket["total"] = (
            bucket["confirmed"] + bucket["not_found"]
            + bucket["misidentified"] + bucket["uncertain"]
        )
        bucket["status"] = _status(bucket)
    return out


def _status(bucket: Dict[str, Any]) -> str:
    """Decide a field status from the tally.

    Two independent confirmations rather than one is the iNaturalist rule and it
    is the right one here too: a single observer can be mistaken, and eDNA
    detections are exactly the cases where an observer expects to find something.
    A single confirmation is real evidence but not yet a verdict, so it stays
    'unverified' with the count visible rather than being promoted quietly.
    """
    confirmed = bucket["confirmed"]
    negative = bucket["not_found"] + bucket["misidentified"]
    if confirmed and negative:
        return CONTESTED
    if confirmed >= 2:
        return VERIFIED
    if negative >= 2:
        return DISPUTED
    return UNVERIFIED


def annotate(
    species: List[Dict[str, Any]],
    site_lookup: Optional[Dict[str, List[str]]] = None,
    store: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Attach field status to species entries for display.

    `site_lookup` maps a species name to the sites it was detected at; without it
    every species is looked up against every site it has a verification for.
    """
    counts = tally(store)
    if not counts:
        return species

    by_species: Dict[str, List[Dict[str, Any]]] = {}
    for bucket in counts.values():
        by_species.setdefault(bucket["scientific_name"].lower(), []).append(bucket)

    annotated: List[Dict[str, Any]] = []
    for entry in species:
        row = dict(entry)
        buckets = by_species.get(str(entry.get("name", "")).lower(), [])
        if site_lookup is not None:
            sites = {s.lower() for s in site_lookup.get(entry.get("name", ""), [])}
            if sites:
                buckets = [b for b in buckets if b["site_id"].lower() in sites]
        if buckets:
            row["verification"] = {
                "status": _rollup([b["status"] for b in buckets]),
                "confirmed": sum(b["confirmed"] for b in buckets),
                "not_found": sum(b["not_found"] for b in buckets),
                "misidentified": sum(b["misidentified"] for b in buckets),
                "uncertain": sum(b["uncertain"] for b in buckets),
                "sites": [b["site_id"] for b in buckets],
                "latest": max(b["latest"] for b in buckets),
            }
        else:
            row["verification"] = {"status": UNVERIFIED, "confirmed": 0,
                                   "not_found": 0, "misidentified": 0,
                                   "uncertain": 0, "sites": [], "latest": ""}
        annotated.append(row)
    return annotated


def _rollup(statuses: List[str]) -> str:
    """Across several sites, disagreement is the honest headline."""
    unique = set(statuses)
    if {VERIFIED, DISPUTED} <= unique or CONTESTED in unique:
        return CONTESTED
    if VERIFIED in unique:
        return VERIFIED
    if DISPUTED in unique:
        return DISPUTED
    return UNVERIFIED


def stats(store: Optional[Path] = None) -> Dict[str, Any]:
    entries = load(store)
    counts = tally(store)
    return {
        "reports": len(entries),
        "species_sites": len(counts),
        "verified": sum(1 for b in counts.values() if b["status"] == VERIFIED),
        "disputed": sum(1 for b in counts.values() if b["status"] == DISPUTED),
        "contested": sum(1 for b in counts.values() if b["status"] == CONTESTED),
        "observers": sorted({e["observer"] for e in entries if e.get("observer")}),
        "latest": max((e.get("recorded_at", "") for e in entries), default=""),
    }
