"""Structured logging, request tracing and health checks.

The gap analysis calls this "the cheapest reliability improvement", and it is
right: when something breaks in front of judges you have seconds, not minutes,
and `print()` statements interleaved from four threads are not a diagnostic tool.

Every request gets an id. Every log line is one JSON object carrying that id.
Tracing a failure is therefore a text search, not an act of archaeology.

The analysis specifies Sentry for error capture. Sentry's SDK is a third-party
package, and adding one to the pipeline image means rebuilding 11.7 GB -- so
unhandled exceptions are captured to a local JSONL file instead. Same purpose,
same fields (exception, traceback, request id, timestamp), no rebuild. Point
BIORADAR_ERROR_LOG somewhere else, or ship the file to a real Sentry later.

    from bioradar import obs
    obs.configure()
    log = obs.logger("webapp")
    log.info("run.started", run_id=..., dataset=...)
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# The request id for the thread currently handling a request. threading.local
# rather than a contextvar because the server is a thread-per-request
# ThreadingHTTPServer -- there is no async context to propagate through.
_local = threading.local()

_LOCK = threading.Lock()
_CONFIGURED = False
_ERROR_LOG: Optional[Path] = None
_LEVEL = "info"

_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}


def new_request_id() -> str:
    """A short, human-quotable id. Long enough not to collide in a session."""
    return uuid.uuid4().hex[:12]


def set_request_id(request_id: Optional[str]) -> None:
    _local.request_id = request_id


def get_request_id() -> Optional[str]:
    return getattr(_local, "request_id", None)


def configure(level: Optional[str] = None, error_log: Optional[Path] = None) -> None:
    """Set up logging once, from the environment by default."""
    global _CONFIGURED, _ERROR_LOG, _LEVEL
    with _LOCK:
        _LEVEL = (level or os.environ.get("BIORADAR_LOG_LEVEL", "info")).lower()
        if _LEVEL not in _LEVELS:
            _LEVEL = "info"
        _ERROR_LOG = Path(
            error_log
            or os.environ.get("BIORADAR_ERROR_LOG", str(REPO_ROOT / "logs" / "errors.jsonl"))
        )
        _CONFIGURED = True


class Logger:
    """Emits one JSON object per line to stderr.

    stderr rather than stdout so that `docker logs` keeps them separate from
    anything the pipeline prints, and so piping the app's stdout somewhere does
    not swallow the diagnostics.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def _emit(self, level: str, event: str, fields: Dict[str, Any]) -> None:
        if _LEVELS[level] < _LEVELS.get(_LEVEL, 20):
            return
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": level,
            "logger": self.name,
            "event": event,
        }
        request_id = get_request_id()
        if request_id:
            record["request_id"] = request_id
        for key, value in fields.items():
            # Anything that is not JSON-serialisable becomes its repr rather than
            # taking down the log call that was meant to diagnose the problem.
            try:
                json.dumps(value)
                record[key] = value
            except (TypeError, ValueError):
                record[key] = repr(value)
        line = json.dumps(record, ensure_ascii=False)
        with _LOCK:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()

    def debug(self, event: str, **fields: Any) -> None:
        self._emit("debug", event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit("info", event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit("warning", event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit("error", event, fields)

    def exception(self, event: str, exc: BaseException, **fields: Any) -> str:
        """Log an exception and persist it. Returns the id to show the user.

        Showing the user an error id rather than a stack trace is the point: it
        is quotable over a phone, and it maps to a full record on disk.
        """
        error_id = new_request_id()
        detail = {
            "error_id": error_id,
            "exception": type(exc).__name__,
            "message": str(exc),
        }
        detail.update(fields)
        self._emit("error", event, detail)
        capture(event, exc, error_id=error_id, **fields)
        return error_id


def logger(name: str) -> Logger:
    if not _CONFIGURED:
        configure()
    return Logger(name)


def capture(event: str, exc: BaseException, **fields: Any) -> None:
    """Append a full exception record to the error log.

    This is the Sentry substitute. One JSON object per line, so `tail -1` during
    a demo shows the last failure in full without opening anything.
    """
    if not _CONFIGURED:
        configure()
    if _ERROR_LOG is None:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
        "exception": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )[-8000:],
        "request_id": get_request_id(),
    }
    for key, value in fields.items():
        try:
            json.dumps(value)
            record[key] = value
        except (TypeError, ValueError):
            record[key] = repr(value)
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _ERROR_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # A failure to record a failure must not itself raise -- that would turn
        # a handled error into an unhandled one.
        pass


def recent_errors(limit: int = 20) -> List[Dict[str, Any]]:
    """The last few captured errors, newest first. Backs the /api/errors view."""
    if not _CONFIGURED:
        configure()
    if _ERROR_LOG is None or not _ERROR_LOG.is_file():
        return []
    try:
        lines = _ERROR_LOG.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: List[Dict[str, Any]] = []
    for line in reversed(lines[-500:]):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------

_STARTED_AT = time.time()


def health() -> Dict[str, Any]:
    """Answer 'is it alive, and what is missing?' without navigating the UI.

    Deliberately reports degraded rather than unhealthy when a classifier is
    absent: the app runs, uploads work, and pre-flight works -- only running the
    pipeline is blocked. Collapsing those into one boolean would make the check
    useless for deciding what to fix.
    """
    checks: Dict[str, Any] = {}

    static_dir = Path(__file__).resolve().parent / "webapp_static"
    checks["static_assets"] = {
        "ok": (static_dir / "index.html").is_file(),
        "detail": str(static_dir),
    }

    classifier_dir = REPO_ROOT / "bioradar-pipeline" / "database" / "qiime2-qza"
    classifiers = sorted(p.name for p in classifier_dir.glob("*.qza")) if classifier_dir.is_dir() else []
    checks["classifiers"] = {
        "ok": bool(classifiers),
        "count": len(classifiers),
        "detail": "run ./scripts/setup.sh to extract them" if not classifiers else "",
    }

    pipeline = REPO_ROOT / "bioradar-pipeline" / "Snakefile"
    checks["pipeline"] = {"ok": pipeline.is_file(), "detail": str(pipeline)}

    import shutil

    snakemake = shutil.which("snakemake")
    checks["snakemake"] = {
        "ok": snakemake is not None,
        "detail": snakemake or "not on PATH -- the app is running outside the pipeline image",
    }

    uploads = REPO_ROOT / "data" / "uploads"
    writable = True
    try:
        uploads.mkdir(parents=True, exist_ok=True)
        probe = uploads / ".write-probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        writable = False
        checks["uploads_writable"] = {"ok": False, "detail": str(exc)}
    if writable:
        checks["uploads_writable"] = {"ok": True, "detail": str(uploads)}

    try:
        free = shutil.disk_usage(str(REPO_ROOT)).free
    except OSError:
        free = -1
    # A pipeline run writes intermediate QIIME 2 artifacts several times the size
    # of the input; running out of disk mid-run fails cryptically deep inside
    # DADA2, so it is worth surfacing before the run starts.
    checks["disk_space"] = {
        "ok": free < 0 or free > 2 * 1024 ** 3,
        "free_bytes": free,
        "detail": "less than 2 GB free" if 0 <= free <= 2 * 1024 ** 3 else "",
    }

    failed = [name for name, check in checks.items() if not check["ok"]]
    critical = {"static_assets", "uploads_writable"}
    if failed and critical & set(failed):
        status = "unhealthy"
    elif failed:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        "checks": checks,
        "failing": failed,
        "version": _version(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _version() -> str:
    try:
        from bioradar import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "unknown"
