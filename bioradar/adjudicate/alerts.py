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
INVASIVE_FILE = DATA_DIR / "invasive_species.json"
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


def evaluate(result: Dict[str, Any], invasive: Optional[Dict[str, Any]] = None,
             started: Optional[float] = None) -> List[Dict[str, Any]]:
    """Alert events for one adjudicated sample. `started` is a time.time() for latency."""
    invasive = invasive or load_list()
    by_name = invasive["by_name"]
    meta = result.get("metadata", {})
    pin = {"latitude": meta.get("latitude"), "longitude": meta.get("longitude"),
           "precision_note": meta.get("coordinate_note", "")}
    events: List[Dict[str, Any]] = []
    for row in result.get("species", []):
        if row["kind"] == "species":
            hit = by_name.get(row["species"].lower())
            if hit and row["status"] == "detected":
                events.append(_event(result, hit, hit["level"], "confirmed", row, pin, started))
        else:
            listed = [by_name[m.lower()] for m in row["members"] if m.lower() in by_name]
            if listed:
                events.append(_event(result, listed[0], "WATCH", "possible", row, pin, started,
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
