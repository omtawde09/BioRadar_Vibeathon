"""HTTP endpoints for the review view. Called from webapp.py; returns (status, body, type).

    GET  /api/adjudicate/index                 every real sample with its verdict
    GET  /api/adjudicate/sample/<id>           full result (cached unless missing)
    POST /api/adjudicate/sample/<id>/run       re-run live, log any alert
    GET  /api/adjudicate/dropped/<id>.csv      every dropped sequence with its reason
    GET  /api/adjudicate/guard                 data-guard decisions
    GET  /api/adjudicate/seasons               same-site summer/winter comparison
    GET  /api/adjudicate/alerts                alert log, newest first
    GET  /api/adjudicate/thresholds            every threshold with its rationale
    GET  /api/adjudicate/provenance            dataset manifest + reference version
    GET  /api/adjudicate/report/<id>.pdf       one-page officer report, generated now
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple
from urllib.parse import unquote

from bioradar.adjudicate import alerts, report, runner
from bioradar.adjudicate.reference import REF_DIR
from bioradar.adjudicate.thresholds import load

Response = Tuple[int, bytes, str]

_ID = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")


def _json(status: int, payload: Any) -> Response:
    return status, json.dumps(payload).encode("utf-8"), "application/json"


def _file_json(name: str, hint: str) -> Response:
    path = runner.RESULTS_DIR / name
    if not path.is_file():
        return _json(404, {"error": "not computed yet", "hint": hint})
    return 200, path.read_bytes(), "application/json"


HINT = "run: python -m bioradar.adjudicate.runner all"


def get(path: str) -> Response:
    tail = path[len("/api/adjudicate"):].strip("/")
    parts = tail.split("/")

    if tail == "index":
        return _file_json("index.json", HINT)
    if tail == "guard":
        return _file_json("guard.json", HINT)
    if tail == "seasons":
        return _file_json("seasons.json", HINT)
    if tail == "alerts":
        return _json(200, {"alerts": alerts.read_log(),
                           "latency_budget_seconds": load().alert_latency_seconds})
    if tail == "thresholds":
        return _json(200, load().rationale())
    if tail == "provenance":
        ref = json.loads((REF_DIR / "reference.json").read_text(encoding="utf-8"))
        manifest = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
        return _json(200, {"reference": ref, "manifest": manifest})

    if len(parts) == 2 and parts[0] == "sample" and _ID.match(parts[1]):
        try:
            return _json(200, runner.run_sample(parts[1]))
        except KeyError:
            return _json(404, {"error": "unknown sample"})
    if len(parts) == 2 and parts[0] == "dropped" and parts[1].endswith(".csv"):
        sid = parts[1][:-4]
        path_csv = runner.RESULTS_DIR / "{}_dropped.csv".format(sid)
        if _ID.match(sid) and path_csv.is_file():
            return 200, path_csv.read_bytes(), "text/csv; charset=utf-8"
        return _json(404, {"error": "no such file"})
    if len(parts) == 2 and parts[0] == "report" and parts[1].endswith(".pdf"):
        sid = unquote(parts[1][:-4])
        if not _ID.match(sid):
            return _json(400, {"error": "bad sample id"})
        try:
            result = runner.run_sample(sid)
        except KeyError:
            return _json(404, {"error": "unknown sample"})
        season = None
        seasons_file = runner.RESULTS_DIR / "seasons.json"
        if seasons_file.is_file():
            doc = json.loads(seasons_file.read_text(encoding="utf-8"))
            loc = result["metadata"].get("location")
            season = next((s for s in doc["sites"] if s["location"] == loc), None)
        ref = json.loads((REF_DIR / "reference.json").read_text(encoding="utf-8"))
        pdf = report.build_pdf(result, season, ref.get("reference_database_version", ""))
        return 200, pdf, "application/pdf"
    return _json(404, {"error": "not found"})


def post(path: str, body: Dict[str, Any]) -> Response:
    parts = path[len("/api/adjudicate"):].strip("/").split("/")
    if len(parts) == 3 and parts[0] == "sample" and parts[2] == "run" and _ID.match(parts[1]):
        try:
            return _json(200, runner.run_sample(parts[1], force=True))
        except KeyError:
            return _json(404, {"error": "unknown sample"})
    return _json(404, {"error": "not found"})
