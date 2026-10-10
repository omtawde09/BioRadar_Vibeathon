"""BioRadar dashboard -- one container, one page, every dataset.

The CLI is fine for development but wrong for a demo: seven commands, each with
primers and truncation lengths that differ per dataset, is not something you want
to type in front of judges. This serves a single page that takes an upload,
pre-flights it, runs the pipeline with live progress, and shows the resulting
species report on a map.

It runs *inside* the pipeline image, so `snakemake` is already on PATH and the
pipeline executes as a local subprocess -- no Docker-in-Docker, no socket
mounting, no privileged container.

Deliberately stdlib-only. The pipeline image ships a QIIME 2 conda environment;
adding FastAPI to it would mean rebuilding an 11.7 GB image, and a dashboard is
not worth that.

    docker compose up app        ->  http://localhost:8080
"""

from __future__ import annotations

import json
import mimetypes
import queue
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from bioradar import exports, jobs, notify, obs, verification, watchlist

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "webapp_static"
DATASETS_FILE = REPO_ROOT / "data" / "datasets.json"

obs.configure()
log = obs.logger("webapp")

# One worker: the pipeline is invoked with every available core, so two
# concurrent runs finish no sooner and will be OOM-killed on a 7 GB container.
# Queueing rather than refusing is what the analysis actually asked for.
QUEUE = jobs.JobQueue()

# Runs are killed after an hour. A pipeline that has not finished by then has
# either stalled or been handed a dataset this machine cannot process, and in
# both cases a hung job that never releases the queue is worse than a clear
# failure.
SOFT_TIMEOUT = 55 * 60
HARD_TIMEOUT = 60 * 60

_ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}
_ANALYSIS_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Datasets
# --------------------------------------------------------------------------


def load_datasets() -> List[Dict[str, Any]]:
    if not DATASETS_FILE.is_file():
        return []
    payload = json.loads(DATASETS_FILE.read_text(encoding="utf-8"))
    return payload.get("datasets", [])


# Pre-flight decompresses and scans every FASTQ, which costs tens of seconds on
# a multi-sample dataset. The dataset list is polled every few seconds, so
# without a cache the server spends all its time redoing identical work and
# everything else -- uploads included -- crawls behind it.
_DESCRIBE_CACHE: Dict[str, Any] = {}
_DESCRIBE_LOCK = threading.Lock()


def _fingerprint(fastq_dir: Path) -> tuple:
    """Cheap signature of a directory: changes iff the files change."""
    if not fastq_dir.is_dir():
        return ()
    entries = []
    for path in sorted(fastq_dir.glob("*.fastq.gz")):
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append((path.name, stat.st_size, int(stat.st_mtime)))
    return tuple(entries)


def describe_dataset(entry: Dict[str, Any], *, refresh: bool = False) -> Dict[str, Any]:
    """Add live state: is the data present, does it pass pre-flight."""
    cache_key = entry["id"]
    signature = (_fingerprint(REPO_ROOT / entry["fastq_dir"]), entry.get("denoiser"))
    if not refresh:
        with _DESCRIBE_LOCK:
            cached = _DESCRIBE_CACHE.get(cache_key)
        if cached and cached[0] == signature:
            return cached[1]

    described = _describe_dataset_uncached(entry)
    with _DESCRIBE_LOCK:
        _DESCRIBE_CACHE[cache_key] = (signature, described)
    return described


def _describe_dataset_uncached(entry: Dict[str, Any]) -> Dict[str, Any]:
    described = dict(entry)
    fastq_dir = REPO_ROOT / entry["fastq_dir"]
    described["present"] = fastq_dir.is_dir() and any(fastq_dir.glob("*.fastq.gz"))

    if not described["present"]:
        described["status"] = "missing"
        described["status_detail"] = "Not downloaded yet"
        described["findings"] = []
        return described

    described["sample_count"] = len(list(fastq_dir.glob("*_R1_001.fastq.gz")))

    if entry.get("known_issue"):
        described["status"] = "blocked"
        described["status_detail"] = entry["known_issue"]

    try:
        from bioradar import preflight
        from bioradar.pipeline_runner import discover_pairs

        pairs = discover_pairs(fastq_dir)
        result = preflight.run(
            pairs,
            forward_primer=entry.get("fprimer"),
            reverse_primer=entry.get("rprimer"),
            trunc_len_f=entry.get("trunc_len_f") or None,
            trunc_len_r=entry.get("trunc_len_r") or None,
            amplicon_length=entry.get("amplicon_length"),
        )
        findings = list(result.findings)
        blocking = result.errors

        # A dataset routed to vsearch is *expected* to fail the quality check --
        # that is why it was routed there. Reporting it as blocked would be
        # telling the user about a problem the app has already solved.
        if entry.get("denoiser") == "vsearch":
            blocking = [f for f in blocking if f.check != "quality"]
            findings = [
                f if f.check != "quality"
                else preflight.Finding(
                    "info",
                    "quality",
                    f.message,
                    "Handled: this dataset runs through vsearch OTU clustering, "
                    "which does not use quality scores.",
                )
                for f in findings
            ]

        described["findings"] = [
            {"level": f.level, "check": f.check, "message": f.message, "hint": f.hint}
            for f in findings
        ]
        if blocking:
            described["status"] = "blocked"
            described.setdefault("status_detail", blocking[0].message)
        elif "status" not in described:
            described["status"] = "ready"
            described["status_detail"] = (
                "{n} sample(s), pre-flight clean".format(n=described["sample_count"])
            )
    except Exception as exc:  # noqa: BLE001
        obs.capture("dataset.preflight_failed", exc, dataset=entry.get("id"))
        described["findings"] = []
        described["status"] = "error"
        described["status_detail"] = "{t}: {e}".format(t=type(exc).__name__, e=exc)

    classifier = entry.get("classifier")
    if classifier:
        path = REPO_ROOT / "bioradar-pipeline" / "database" / "qiime2-qza" / classifier
        described["classifier_present"] = path.is_file()
        if not path.is_file() and described.get("status") == "ready":
            described["status"] = "blocked"
            described["status_detail"] = "Classifier {c} not built yet".format(c=classifier)
    else:
        described["classifier_present"] = False
    return described


def _invalidate_describe(dataset_id: str) -> None:
    with _DESCRIBE_LOCK:
        _DESCRIBE_CACHE.pop(dataset_id, None)


# Which bundled datasets this machine has hidden. Gitignored, because it is a
# local preference, not project data.
HIDDEN_FILE = REPO_ROOT / "data" / ".hidden_datasets.json"


def hidden_dataset_ids() -> set:
    if not HIDDEN_FILE.is_file():
        return set()
    try:
        return set(json.loads(HIDDEN_FILE.read_text(encoding="utf-8")))
    except (ValueError, TypeError):
        return set()


def _remove_registry_entry(dataset_id: str) -> bool:
    """Hide a bundled dataset on this machine.

    Deliberately does NOT edit data/datasets.json. That file is tracked in git
    and is what gives a fresh clone something to run immediately -- the README
    and README_TEAM both tell a new teammate to click Analyze on the bundled
    demo survey. An earlier version dropped the entry from it, so pressing
    Remove in the UI silently produced a source-code change; it was committed
    twice by accident, and the second time it reached the public repository,
    where every new clone saw an empty dataset list and no reason why.

    The removal is a local preference, so it is stored like one.
    """
    known = {d.get("id") for d in load_datasets()}
    if dataset_id not in known:
        return False

    hidden = hidden_dataset_ids()
    if dataset_id in hidden:
        return False
    hidden.add(dataset_id)
    HIDDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    HIDDEN_FILE.write_text(
        json.dumps(sorted(hidden), indent=2) + "\n", encoding="utf-8"
    )
    return True


def restore_hidden_datasets() -> int:
    """Un-hide everything. `python -m bioradar.webapp --restore-datasets`."""
    count = len(hidden_dataset_ids())
    if HIDDEN_FILE.is_file():
        HIDDEN_FILE.unlink()
    return count


# --------------------------------------------------------------------------
# Live event stream
# --------------------------------------------------------------------------

_streams: List["queue.Queue"] = []
_stream_lock = threading.Lock()


def publish(event_type: str, payload: Dict[str, Any]) -> None:
    """Push an event to every connected dashboard.

    Non-blocking on purpose: a browser tab that has stopped reading must not be
    able to stall the pipeline thread that is emitting progress.
    """
    with _stream_lock:
        listeners = list(_streams)
    for stream in listeners:
        try:
            stream.put_nowait((event_type, payload))
        except queue.Full:
            pass


notify.subscribe(lambda event: publish("alert", event))


# --------------------------------------------------------------------------
# Runs
# --------------------------------------------------------------------------

# Snakemake announces each rule as it starts; the monitor turns them into DAG
# nodes. Keeping the last few log lines lets the UI show what the pipeline is
# actually saying without streaming megabytes of QIIME 2 chatter.
_LOG_TAIL = 40


def _idempotency_key(entry: Dict[str, Any]) -> str:
    """Same dataset, same files, same parameters -> the same key.

    Double-clicking Analyze should not burn twenty minutes of compute twice.
    The fingerprint is part of the key so that re-uploading changed files is
    correctly treated as different work.
    """
    import hashlib

    material = json.dumps(
        {
            "dataset": entry["id"],
            "files": [list(item) for item in _fingerprint(REPO_ROOT / entry["fastq_dir"])],
            "classifier": entry.get("classifier"),
            "fprimer": entry.get("fprimer"),
            "rprimer": entry.get("rprimer"),
            "trunc_len_f": entry.get("trunc_len_f"),
            "trunc_len_r": entry.get("trunc_len_r"),
            "denoiser": entry.get("denoiser"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _pipeline_job(job: "jobs.Job") -> Dict[str, Any]:
    """Run one pipeline, in the queue's worker thread."""
    from bioradar.pipeline_runner import PipelineRunner, discover_pairs

    entry = job.payload["_entry"]
    stages: List[str] = []
    tail: List[str] = []

    def on_progress(event: Dict[str, Any]) -> None:
        # Cancellation and the soft deadline are both checked here, at a rule
        # boundary, so a stopped run does not die halfway through writing an
        # artifact.
        job.check_cancelled()
        job.check_deadline()

        if event.get("stage") and event["stage"] not in stages:
            stages.append(event["stage"])
        line = event.get("line") or event.get("label")
        if line:
            tail.append(str(line)[:300])
            del tail[:-_LOG_TAIL]
        job.progress(event)
        publish("progress", {
            "run_id": job.job_id,
            "percent": job.percent,
            "stage": job.stage,
            "stages": list(stages),
            "recent_log": list(tail),
        })

    fastq_dir = REPO_ROOT / entry["fastq_dir"]
    runner = PipelineRunner(mode="local", runs_dir=REPO_ROOT / "runs")

    params: Dict[str, Any] = {}
    if entry.get("classifier"):
        params["classifier"] = str(
            REPO_ROOT / "bioradar-pipeline" / "database" / "qiime2-qza" / entry["classifier"]
        )
    for key, field in (
        ("fprimer", "fprimer"), ("rprimer", "rprimer"),
        ("tlf", "trunc_len_f"), ("tlr", "trunc_len_r"),
        ("denoiser", "denoiser"),
    ):
        if entry.get(field) is not None:
            params[key] = entry[field]

    result = runner.run(
        discover_pairs(fastq_dir),
        run_id=job.job_id,
        sample_id=entry["id"].upper(),
        params=params,
        progress=on_progress,
        commit_chain=False,
        # vsearch exists precisely to run data that fails the quality check, so
        # re-blocking on it here would defeat the point.
        skip_preflight=entry.get("denoiser") == "vsearch",
    )

    outcome: Dict[str, Any] = {
        "results_dir": str(result.results_dir),
        "artifact_hash": result.artifact_hash,
        "stages": stages,
        "recent_log": tail,
    }
    outcome.update(_build_report(job.job_id, entry, Path(result.results_dir)))
    return outcome


def _build_report(run_id: str, entry: Dict[str, Any], results_dir: Path) -> Dict[str, Any]:
    """Generate the biodiversity report and cache the analysis for the UI."""
    from bioradar.report import analyse, load_csv, render_markdown

    taxonomy = results_dir / "taxonomy_normalized.csv"
    if not taxonomy.is_file():
        return {"report_error": "the pipeline produced no taxonomy_normalized.csv"}

    detections = load_csv(taxonomy)
    samples = None
    if entry.get("samples_csv"):
        candidate = REPO_ROOT / entry["samples_csv"]
        if candidate.is_file():
            samples = load_csv(candidate)

    result = analyse(detections, samples)

    # Field verification annotates how a detection is *presented*; it never
    # rewrites the classifier's confidence, which is a property of the sequence
    # and must stay reproducible for the chain-of-custody hash to mean anything.
    site_lookup = {s["name"]: sorted(s.get("sites", ())) for s in result["species"]}
    result["species"] = verification.annotate(result["species"], site_lookup)

    markdown = render_markdown(
        result, entry["name"],
        {"Dataset": entry.get("source", ""), "Marker": entry.get("marker", "")},
    )
    report_path = REPO_ROOT / "reports" / "{r}.md".format(r=run_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")

    with _ANALYSIS_LOCK:
        _ANALYSIS_CACHE[run_id] = {
            "analysis": result,
            "detections": detections,
            "samples_meta": samples or [],
            "entry": entry,
            "markdown": markdown,
        }

    species = [s for s in result["species"] if s["rank"] == "species"]
    named = [s for s in species if not s.get("placeholder")]

    return {
        "report": {
            "path": str(report_path),
            "named_species": len(named),
            "placeholders": len(species) - len(named),
            "phyla": len(result["phyla"]),
            "phyla_breakdown": [
                {"name": name, "reads": reads} for name, reads in result["phyla"][:10]
            ],
            "samples": len(result["samples"]),
            "sites": len(result["site_species"]),
            "detections": result["detections"],
            "top_species": [
                {
                    "name": s["name"],
                    "phylum": s["phylum"],
                    "reads": s["reads"],
                    "confidence": round(s["max_confidence"], 3),
                    "placeholder": bool(s.get("placeholder")),
                    "verification": s.get("verification", {}),
                }
                for s in species[:40]
            ],
        },
        "export_stats": exports.archive_stats(detections),
    }


def start_run(dataset_id: str) -> Dict[str, Any]:
    entry = next((d for d in all_datasets() if d["id"] == dataset_id), None)
    if entry is None:
        raise KeyError("unknown dataset {d!r}".format(d=dataset_id))

    run_id = "{d}-{ts:%Y%m%dT%H%M%S}-{u}".format(
        d=dataset_id, ts=datetime.now(timezone.utc), u=uuid.uuid4().hex[:6]
    )

    job = QUEUE.submit(
        "pipeline",
        {"run_id": run_id, "dataset_id": dataset_id, "dataset_name": entry["name"],
         "_entry": entry},
        _pipeline_job,
        job_id=run_id,
        idempotency_key=_idempotency_key(entry),
        # One retry: transient failures here are memory pressure and filesystem
        # contention, which a second attempt on an idle machine often clears.
        # More than one just wastes twenty minutes twice over.
        max_retries=1,
        soft_timeout=SOFT_TIMEOUT,
        hard_timeout=HARD_TIMEOUT,
    )
    _watch_completion(job)
    publish("run", {"run_id": job.job_id, "status": job.status})
    return run_summary(job)


_watched: set = set()
_watch_lock = threading.Lock()


def _watch_completion(job: "jobs.Job") -> None:
    """Fire notifications once a job leaves the queue, without blocking it."""
    with _watch_lock:
        if job.job_id in _watched:
            return
        _watched.add(job.job_id)

    def wait() -> None:
        while job.status not in jobs.TERMINAL:
            time.sleep(1.0)
        summary = run_summary(job)
        publish("run", {"run_id": job.job_id, "status": job.status})
        try:
            if job.status == jobs.COMPLETED:
                notify.run_finished(summary, run_alerts(job.job_id))
            elif job.status in {jobs.FAILED, jobs.TIMED_OUT}:
                notify.run_failed(summary)
        except Exception as exc:  # noqa: BLE001
            obs.capture("notify.dispatch_failed", exc, run_id=job.job_id)

    threading.Thread(target=wait, name="watch-" + job.job_id, daemon=True).start()


def run_summary(job: "jobs.Job", include_events: bool = False) -> Dict[str, Any]:
    """Everything the UI needs, without the internals it must not see."""
    summary = job.summary(include_events=include_events)
    summary.pop("_entry", None)
    summary.pop("traceback", None)
    summary["run_id"] = job.job_id
    summary["started_at"] = job.started_at or job.queued_at
    if job.status == jobs.QUEUED:
        summary["queue_position"] = QUEUE.queue_position(job)
    return summary


def run_alerts(run_id: str) -> Dict[str, Any]:
    """Screen a completed run against the watchlist."""
    with _ANALYSIS_LOCK:
        cached = _ANALYSIS_CACHE.get(run_id)
    if not cached:
        return {"alerts": [], "summary": {"high": 0, "medium": 0, "info": 0, "total": 0},
                "watchlist_size": 0}
    result = watchlist.screen(cached["analysis"]["species"])
    result["verification_stats"] = verification.stats()
    return result


def recover_runs() -> int:
    """Deliberately does nothing: results are session-only.

    An earlier version rebuilt the run list from `runs/` on startup so a
    container restart did not look like data loss. That is the wrong default for
    a demo machine -- the app should open clean, showing only what the person in
    front of it just analysed, not whatever was left over from testing.

    The pipeline still writes its outputs to `runs/<id>/` on disk, because
    Snakemake needs a working directory and the artifacts are what the
    chain-of-custody hashes cover. The app simply does not resurrect them.
    """
    return 0


# --------------------------------------------------------------------------
# Uploads
# --------------------------------------------------------------------------

UPLOAD_ROOT = REPO_ROOT / "data" / "uploads"

# The pipeline derives sample ids from the filename, so uploads must land in the
# Illumina convention. Accept the common shapes and normalise.
_FASTQ_SUFFIXES = (".fastq.gz", ".fq.gz", ".fastq", ".fq")

# A single upload larger than this is either not a FASTQ or will not finish on
# the hardware this is demonstrated on. Refusing early beats filling the disk.
MAX_UPLOAD_BYTES = 8 * 1024 ** 3


def normalise_upload_name(filename: str) -> Optional[tuple]:
    """Map an uploaded filename to (sample_id, mate) or None if unusable.

    Handles the three layouts people actually have: Illumina
    (`X_S1_L001_R1_001.fastq.gz`), archive (`SRR123_1.fastq.gz`) and plain
    (`X_R1.fastq.gz`). Sample ids must not contain underscores -- the pipeline
    splits on the first one -- so everything before the mate marker is joined
    with hyphens.
    """
    name = Path(filename).name
    lowered = name.lower()
    if not lowered.endswith(_FASTQ_SUFFIXES):
        return None
    for suffix in _FASTQ_SUFFIXES:
        if lowered.endswith(suffix):
            stem = name[: -len(suffix)]
            break

    mate = None
    for marker, value in (("_R1", 1), ("_R2", 2), ("_1", 1), ("_2", 2)):
        index = stem.upper().rfind(marker if marker.startswith("_R") else marker)
        if index > 0:
            tail = stem[index + len(marker):]
            # Illumina puts _001 after the mate marker; anything else means this
            # was a coincidental match inside the sample name.
            if tail == "" or tail.startswith("_001") or tail.lstrip("_").isdigit():
                mate = value
                stem = stem[:index]
                break
    if mate is None:
        return None

    # Strip Illumina's lane block (`_S1_L001`) so `X_S1_L001_R1_001.fastq.gz`
    # yields sample `X`, matching what the pipeline itself derives.
    import re as _re

    stem = _re.sub(r"_S\d+(_L\d+)?$", "", stem)

    sample = stem.replace("_", "-").strip("-")
    return (sample or "SAMPLE", mate)


# Column names that mean "this CSV carries coordinates". Several spellings,
# because people export metadata from all sorts of places.
_LAT_COLUMNS = {"latitude", "lat", "decimallatitude", "decimal_latitude"}
_LON_COLUMNS = {"longitude", "lon", "lng", "decimallongitude", "decimal_longitude"}


def find_metadata_csv(directory: Path) -> Optional[Path]:
    """Find an uploaded CSV that has a sample id plus latitude/longitude.

    The coordinates a map needs are never inside a FASTQ -- they live in a sample
    sheet next to it. Uploading the folder should therefore pick that sheet up,
    not discard it because it is not a sequence file.
    """
    import csv as _csv

    for path in sorted(directory.glob("*.csv")) + sorted(directory.glob("*.tsv")):
        delimiter = "\t" if path.suffix == ".tsv" else ","
        try:
            with path.open(newline="", encoding="utf-8", errors="replace") as handle:
                header = next(_csv.reader(handle, delimiter=delimiter), [])
        except OSError:
            continue
        lowered = {h.strip().lower().replace(" ", "_") for h in header}
        has_id = bool(lowered & {"sample_id", "sample-id", "sampleid", "id", "sample"})
        if has_id and (lowered & _LAT_COLUMNS) and (lowered & _LON_COLUMNS):
            return path
    return None


def normalise_metadata(path: Path) -> List[Dict[str, str]]:
    """Read a sample sheet into the column names the rest of the app expects."""
    import csv as _csv

    delimiter = "\t" if path.suffix == ".tsv" else ","
    rows: List[Dict[str, str]] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for raw in _csv.DictReader(handle, delimiter=delimiter):
            mapped: Dict[str, str] = {}
            for key, value in raw.items():
                if key is None:
                    continue
                canonical = key.strip().lower().replace(" ", "_").replace("-", "_")
                if canonical in {"sample_id", "sampleid", "id", "sample"}:
                    mapped["sample_id"] = (value or "").strip()
                elif canonical in _LAT_COLUMNS:
                    mapped["latitude"] = (value or "").strip()
                elif canonical in _LON_COLUMNS:
                    mapped["longitude"] = (value or "").strip()
                else:
                    mapped[canonical] = (value or "").strip()
            if mapped.get("sample_id"):
                rows.append(mapped)
    return rows


def upload_dir(batch: str) -> Path:
    safe = "".join(c for c in batch if c.isalnum() or c in "-_")
    if not safe:
        raise ValueError("invalid batch id")
    return UPLOAD_ROOT / safe


def register_upload(batch: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Turn a finished upload into a dataset entry the rest of the app understands.

    Anything the user did not specify is inferred from the reads themselves --
    the primers are literally at the start of them, the read length is
    measurable, and whether DADA2 can work is decided by the quality encoding.
    Asking a field officer for a truncation length would be absurd.
    """
    from bioradar import preflight
    from bioradar.pipeline_runner import discover_pairs

    directory = upload_dir(batch)
    detected: Dict[str, Any] = {}
    denoiser = config.get("denoiser")

    try:
        pairs = discover_pairs(directory)
        if config.get("autodetect", True):
            detected = preflight.detect_marker(pairs) or {}
            if detected.get("swap_mates"):
                _swap_mates(directory)
                # Re-detect so the stored settings describe the files as they
                # now are, not as they arrived.
                detected = preflight.detect_marker(discover_pairs(directory)) or detected
                detected["swapped_on_import"] = True
        if not denoiser:
            denoiser = preflight.recommend_denoiser(pairs)
    except Exception as exc:  # noqa: BLE001
        obs.capture("upload.detect_failed", exc, batch=batch)
        detected = {"detection_error": "{t}: {e}".format(t=type(exc).__name__, e=exc)}
        denoiser = denoiser or "dada2"

    def pick(key: str, fallback: Any = None) -> Any:
        value = config.get(key)
        if value not in (None, "", 0):
            return value
        return detected.get(key, fallback)

    metadata = find_metadata_csv(directory)
    entry = {
        "id": "upload-{b}".format(b=batch),
        "name": config.get("name") or "Uploaded dataset {b}".format(b=batch),
        "region": config.get("region") or "Uploaded from your computer",
        "fastq_dir": str(directory.relative_to(REPO_ROOT)).replace("\\", "/"),
        "marker": pick("marker", "unknown"),
        "classifier": pick("classifier"),
        "fprimer": pick("fprimer"),
        "rprimer": pick("rprimer"),
        "trunc_len_f": pick("trunc_len_f"),
        "trunc_len_r": pick("trunc_len_r"),
        "amplicon_length": pick("amplicon_length"),
        "denoiser": denoiser,
        "source": "uploaded",
        "uploaded": True,
        "detected": detected,
    }
    if metadata is not None:
        entry["samples_csv"] = str(metadata.relative_to(REPO_ROOT)).replace("\\", "/")
        entry["metadata_file"] = metadata.name
    if entry.get("classifier") is None:
        entry["known_issue"] = (
            "No classifier available for {m}. Build one with "
            "`python -m bioradar.train_classifier`.".format(m=entry["marker"])
        )
    (directory / "_dataset.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
    log.info("upload.registered", dataset=entry["id"], marker=entry["marker"],
             denoiser=denoiser)
    return entry


def _swap_mates(directory: Path) -> None:
    """Exchange R1 and R2 filenames.

    Some libraries are sequenced with the reverse primer on R1. cutadapt runs
    with --discard-untrimmed, so leaving them that way throws away most of the
    data; renaming is the whole fix.
    """
    for r1 in sorted(directory.glob("*_R1_001.fastq.gz")):
        r2 = r1.parent / r1.name.replace("_R1_", "_R2_")
        if not r2.is_file():
            continue
        temporary = r1.with_suffix(".swap")
        r1.rename(temporary)
        r2.rename(r1)
        temporary.rename(r2)


def uploaded_datasets() -> List[Dict[str, Any]]:
    if not UPLOAD_ROOT.is_dir():
        return []
    entries = []
    for meta in sorted(UPLOAD_ROOT.glob("*/_dataset.json")):
        try:
            entries.append(json.loads(meta.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return entries


def all_datasets() -> List[Dict[str, Any]]:
    hidden = hidden_dataset_ids()
    bundled = [d for d in load_datasets() if d.get("id") not in hidden]
    return bundled + uploaded_datasets()


# --------------------------------------------------------------------------
# Map data
# --------------------------------------------------------------------------


_SITE_REGISTRY_CACHE: Optional[Dict[str, tuple]] = None


def _site_registry() -> Dict[str, tuple]:
    """`site_id` (upper-case) -> (lat, lon), read once from data/sites.csv.

    Lets the map resolve coordinates for well-known Indian sites even when an
    upload carries no sample sheet, as long as the sample names encode the site.
    """
    global _SITE_REGISTRY_CACHE
    if _SITE_REGISTRY_CACHE is not None:
        return _SITE_REGISTRY_CACHE
    import csv
    reg: Dict[str, tuple] = {}
    path = REPO_ROOT / "data" / "sites.csv"
    if path.is_file():
        try:
            for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
                sid = (r.get("site_id") or "").strip().upper()
                try:
                    reg[sid] = (float(r["latitude"]), float(r["longitude"]))
                except (KeyError, ValueError, TypeError):
                    continue
        except Exception:
            pass
    _SITE_REGISTRY_CACHE = reg
    return reg


def _site_id_from_sample(sample_id: str) -> str:
    """`BR-GOA-MANDOVI-R01` -> `GOA-MANDOVI` (strip the BR- prefix and -R<round>)."""
    import re
    s = (sample_id or "").strip().upper()
    if s.startswith("BR-"):
        s = s[3:]
    return re.sub(r"-R\d+$", "", s)


def map_points(run_id: str) -> List[Dict[str, Any]]:
    """Per-site coordinates plus what was found there, for the map."""
    with _ANALYSIS_LOCK:
        cached = _ANALYSIS_CACHE.get(run_id)
    if not cached:
        return []

    result = cached["analysis"]
    meta_by_sample = {row["sample_id"]: row for row in (cached.get("samples_meta") or [])}
    registry = _site_registry()

    points = []
    for summary in result["samples"]:
        sample_id = summary["sample_id"]
        row = meta_by_sample.get(sample_id, {})

        # 1) explicit coordinates from an uploaded sample sheet, if any …
        latitude = longitude = None
        try:
            latitude = float(row.get("latitude") or "")
            longitude = float(row.get("longitude") or "")
        except (ValueError, TypeError):
            latitude = longitude = None
        # 2) … otherwise derive them from the known-site registry using the site
        #    code embedded in the sample name. This is what puts the demo (and any
        #    upload named BR-<SITE>-Rnn) on the map without a samples.csv.
        if latitude is None or longitude is None:
            coord = registry.get(_site_id_from_sample(sample_id))
            if coord:
                latitude, longitude = coord

        if latitude is None or longitude is None:
            continue
        # A coordinate outside the globe is a data-entry error, and plotting it
        # sends the map to the middle of the ocean with no explanation.
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            log.warning("map.bad_coordinate", sample=sample_id,
                        latitude=latitude, longitude=longitude)
            continue

        site_species_list = [s for s in result["species"] if sample_id in s["samples"]]
        has_inv = False
        has_thr = False
        try:
            from bioradar.ai import knowledge_base
            for sp in site_species_list:
                prof = knowledge_base.get_species_profile(sp.get("name", ""))
                if prof:
                    st = prof.get("india_status", "")
                    if st == "invasive":
                        has_inv = True
                    elif "endangered" in st or "vulnerable" in st or "threatened" in st:
                        has_thr = True
        except Exception:
            pass

        sev = "invasive" if has_inv else ("threatened" if has_thr else "normal")

        taxa = [
            {"name": s["name"], "reads": s["reads"], "phylum": s["phylum"]}
            for s in result["species"]
            if sample_id in s["samples"]
        ][:6]
        points.append({
            "sample_id": sample_id,
            "site_id": summary["site_id"],
            "latitude": latitude,
            "longitude": longitude,
            "collected_at": row.get("collected_at", ""),
            "total_reads": summary["total_reads"],
            "species_count": summary["species_count"],
            "shannon": summary["shannon"],
            "top_taxa": taxa,
            "has_invasive": has_inv,
            "has_threatened": has_thr,
            "highest_severity": sev,
        })
    return points



def run_analysis_payload(run_id: str) -> Optional[Dict[str, Any]]:
    """The trimmed analysis the comparison radar needs.

    Sets are serialised to sorted lists and the heavy per-detection rows are
    left out: the client needs site metrics, not 60,000 ASV records.
    """
    with _ANALYSIS_LOCK:
        cached = _ANALYSIS_CACHE.get(run_id)
    if not cached:
        return None
    result = cached["analysis"]
    return {
        "samples": result["samples"],
        "species": [
            {
                "name": s["name"],
                "rank": s["rank"],
                "phylum": s["phylum"],
                "reads": s["reads"],
                "sites": sorted(s["sites"]),
                "samples": sorted(s["samples"]),
                "max_confidence": round(s["max_confidence"], 4),
                "placeholder": bool(s.get("placeholder")),
                "verification": s.get("verification", {}),
            }
            for s in result["species"]
        ],
        "phyla": [{"name": n, "reads": r} for n, r in result["phyla"]],
        "site_species": result["site_species"],
        "watchlist": sorted(watchlist.load_watchlist().keys()),
    }


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "BioRadar"

    # -- plumbing -------------------------------------------------------

    def _send(self, status: int, body: bytes, content_type: str,
              extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-ID", obs.get_request_id() or "")
        # The page loads no third-party code and posts nowhere else; saying so
        # explicitly means a compromised dependency could not exfiltrate a
        # dataset even if one appeared.
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def handle_one_request(self) -> None:
        """Give every request an id and make sure no handler can 500 silently."""
        obs.set_request_id(obs.new_request_id())
        try:
            super().handle_one_request()
        finally:
            obs.set_request_id(None)

    def _guard(self, fn) -> None:
        try:
            fn()
        except BrokenPipeError:
            # The browser navigated away mid-response. Not an error.
            pass
        except Exception as exc:  # noqa: BLE001
            error_id = log.exception("request.failed", exc, path=self.path,
                                     method=self.command)
            try:
                self._json(500, {
                    "error": "{t}: {e}".format(t=type(exc).__name__, e=exc),
                    "error_id": error_id,
                })
            except Exception:  # noqa: BLE001
                pass

    # -- GET ------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        self._guard(self._do_get)

    def _do_get(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in {"/", "/index.html"}:
            return self._serve_static("index.html")
        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])

        if path == "/api/health":
            health = obs.health()
            health["runs"] = {
                "active": len(QUEUE.active()),
                "total": len(QUEUE.all()),
            }
            status = 200 if health["status"] != "unhealthy" else 503
            return self._json(status, health)

        if path == "/api/errors":
            return self._json(200, {"errors": obs.recent_errors(
                _int(query.get("limit"), 20, maximum=100))})

        if path == "/api/channels":
            return self._json(200, notify.configured_channels())

        if path == "/api/datasets":
            described = [describe_dataset(d) for d in all_datasets()]
            return self._json(200, _paginate(described, query, "datasets"))

        if path == "/api/verifications":
            entries = verification.load()
            entries.reverse()
            payload = _paginate(entries, query, "verifications")
            payload["stats"] = verification.stats()
            return self._json(200, payload)

        if path == "/api/runs":
            runs = [run_summary(job) for job in QUEUE.all()]
            runs.sort(key=lambda r: r.get("started_at") or "", reverse=True)
            return self._json(200, _paginate(runs, query, "runs"))

        if path == "/api/events":
            return self._stream_events()

        if path.startswith("/api/species/") and path.endswith("/extinction-risk"):
            species_name = path[len("/api/species/"): -len("/extinction-risk")].strip()
            from urllib.parse import unquote
            from bioradar.ai import extinction_risk
            return self._json(200, extinction_risk.predict_extinction_risk(unquote(species_name)))

        if path.startswith("/api/species/") and path.endswith("/establishment-risk"):
            species_name = path[len("/api/species/"): -len("/establishment-risk")].strip()
            from urllib.parse import unquote
            from bioradar.ai import ias_model
            return self._json(200, ias_model.predict_establishment_risk(unquote(species_name)))


        if path.startswith("/api/v1/anomalies/") or path.startswith("/api/anomalies/"):
            sample_id = path.split("/")[-1]
            from bioradar.analytics import anomaly
            return self._json(200, anomaly.detect_anomalies(sample_id))

        if path.startswith("/api/v1/zero-shot/") or path.startswith("/api/zero-shot/"):
            asv_id = path.split("/")[-1]
            from bioradar.ai import zero_shot
            return self._json(200, zero_shot.classify_unknown("", asv_id=asv_id))

        if path.startswith("/api/v1/forecast/") or path.startswith("/api/forecast/"):
            sample_id = path.split("/")[-1]
            from bioradar.analytics import forecast
            return self._json(200, forecast.generate_forecast(sample_id))

        if path in {"/api/v1/satellite-alerts", "/api/satellite-alerts"}:
            from bioradar.satellite import change_detection
            return self._json(200, change_detection.check_site_changes("BR-GOA-001"))

        if path in {"/api/v1/debate", "/api/debate"}:
            from bioradar.ai import debate
            res = debate.run_debate("BR-GOA-001", "Mandovi Estuary Conservation Strategy")
            return self._json(200, res)

        if path.startswith("/api/v1/debate/") or path.startswith("/api/debate/"):
            debate_id = path.split("/")[-1]
            from bioradar.ai import debate
            debates = debate.load_debates()
            if debate_id in debates:
                return self._json(200, debates[debate_id])
            return self._json(404, {"error": "debate not found"})

        if path.startswith("/api/v1/nft/") or path.startswith("/api/nft/"):
            sample_id = path.split("/")[-1]
            from bioradar.blockchain import nft
            mints = nft.load_nft_mints()
            if sample_id in mints:
                return self._json(200, mints[sample_id])
            return self._json(404, {"error": "nft mint not found"})

        if path.startswith("/api/runs/"):
            return self._run_route(path[len("/api/runs/"):])

        self._json(404, {"error": "not found", "path": path})

    def _run_route(self, tail: str) -> None:
        parts = [p for p in tail.split("/") if p]
        if not parts:
            return self._json(404, {"error": "not found"})

        run_id = parts[0]
        job = QUEUE.get(run_id)
        if job is None:
            return self._json(404, {"error": "unknown run"})

        if len(parts) == 1:
            return self._json(200, run_summary(job, include_events=True))

        section = parts[1]
        query = parse_qs(urlparse(self.path).query)

        if section == "report":
            with _ANALYSIS_LOCK:
                cached = _ANALYSIS_CACHE.get(run_id)
            if not cached:
                return self._json(404, {"error": "no report yet"})
            return self._send(200, cached["markdown"].encode("utf-8"),
                              "text/plain; charset=utf-8")

        if section == "map":
            return self._json(200, {"points": map_points(run_id)})

        if section == "log":
            return self._json(200, {"events": job.summary(include_events=True).get("events", [])})

        if section == "analysis":
            payload = run_analysis_payload(run_id)
            if payload is None:
                return self._json(404, {"error": "no analysis yet"})
            return self._json(200, payload)

        if section == "alerts":
            return self._json(200, run_alerts(run_id))

        if section == "nlg-summary":
            payload = run_analysis_payload(run_id)
            if payload and payload.get("report"):
                analysis_dict = payload["report"]
            else:
                with _ANALYSIS_LOCK:
                    cached = _ANALYSIS_CACHE.get(run_id)
                analysis_dict = cached["analysis"] if cached else {}
            dataset_label = job.summary().get("dataset_name") or run_id
            from bioradar.ai import nlg_insights
            return self._json(200, nlg_insights.generate_executive_briefing(analysis_dict, dataset_label))

        if section == "invasive-risk":
            payload = run_analysis_payload(run_id)
            if payload and payload.get("report"):
                analysis_dict = payload["report"]
            else:
                with _ANALYSIS_LOCK:
                    cached = _ANALYSIS_CACHE.get(run_id)
                analysis_dict = cached["analysis"] if cached else {}
            from bioradar.ai import ias_model
            return self._json(200, {"invasive_risks": ias_model.predict_all_invasives_for_run(analysis_dict)})

        if section == "pinn-origin-trace":
            from bioradar.ai import pinn_tracer
            species_param = query.get("species", ["Clarias gariepinus"])[0]
            site_id_param = query.get("site_id", [None])[0]
            points = map_points(run_id)

            if site_id_param and site_id_param != "all":
                target_pt = next((p for p in points if p.get("site_id") == site_id_param), points[0] if points else {})

                try:
                    site_lat = float(target_pt.get("latitude") or 15.4989)
                    site_lon = float(target_pt.get("longitude") or 73.8278)
                    reads = int(target_pt.get("total_reads") or target_pt.get("reads") or 1200)
                except (ValueError, TypeError):
                    site_lat, site_lon, reads = 15.4989, 73.8278, 1200

                trace_res = pinn_tracer.predict_upstream_origin(
                    site_id=site_id_param,
                    site_lat=site_lat,
                    site_lon=site_lon,
                    species_name=species_param,
                    read_count=reads,
                    total_reads=4694,
                    waterbody_type=target_pt.get("waterbody_type", "estuary")
                )
                return self._json(200, trace_res)

            else:
                all_res = pinn_tracer.predict_all_upstream_origins_for_run(points, species_name=species_param)
                return self._json(200, all_res)

        if section == "blockchain-proof":
            import bioradar.blockchain_ledger as ledger
            points = map_points(run_id)
            proof = ledger.generate_blockchain_proof(run_id, points)
            return self._json(200, proof)






        if section == "spread-prediction":
            with _ANALYSIS_LOCK:
                cached = _ANALYSIS_CACHE.get(run_id)
            if not cached:
                return self._json(404, {"error": "no analysis yet"})
            from bioradar.ai import spread_prediction
            species_param = query.get("species", ["Clarias gariepinus"])[0]
            try:
                months_param = int(query.get("months", [6])[0])
            except (ValueError, IndexError):
                months_param = 6
            points = map_points(run_id)
            return self._json(200, spread_prediction.forecast_invasive_spread(species_param, points, months_ahead=months_param))


        if section == "sampling-recommendations":
            with _ANALYSIS_LOCK:
                cached = _ANALYSIS_CACHE.get(run_id)
            if not cached:
                return self._json(404, {"error": "no analysis yet"})
            from bioradar.ai import sampling_optimizer
            species_param = query.get("species", ["Clarias gariepinus"])[0]
            points = map_points(run_id)
            return self._json(200, sampling_optimizer.recommend_sampling_locations(species_param, points))

        if section == "export" and len(parts) > 2:
            return self._export(run_id, parts[2])

        self._json(404, {"error": "not found"})

    def _export(self, run_id: str, kind: str) -> None:
        with _ANALYSIS_LOCK:
            cached = _ANALYSIS_CACHE.get(run_id)
        if not cached:
            return self._json(404, {"error": "no results for this run"})

        job = QUEUE.get(run_id)
        entry = cached["entry"]
        summary = job.summary() if job else {}
        meta = {
            "run_id": run_id,
            "title": entry.get("name", run_id),
            "region": entry.get("region", ""),
            "generated_at": _now(),
            "image": "ghcr.io/omtawde09/bioradar-pipeline:v1.0",
            "classifier": entry.get("classifier", ""),
            "denoiser": entry.get("denoiser", "dada2"),
            "fprimer": entry.get("fprimer", ""),
            "rprimer": entry.get("rprimer", ""),
            "target_gene": entry.get("marker", ""),
            "reference": entry.get("classifier", ""),
            "artifact_hash": summary.get("artifact_hash", ""),
            "country": "India",
            "country_code": "IN",
        }

        try:
            if kind == "detections.csv":
                body, mime = exports.detections_csv(cached["detections"]), "text/csv; charset=utf-8"
            elif kind == "species.csv":
                body, mime = exports.species_csv(cached["analysis"]), "text/csv; charset=utf-8"
            elif kind == "samples.csv":
                body, mime = exports.samples_csv(cached["analysis"]), "text/csv; charset=utf-8"
            elif kind == "analysis.json":
                body, mime = exports.analysis_json(cached["analysis"], meta), "application/json"
            elif kind == "dwca.zip":
                body = exports.darwin_core_archive(
                    cached["detections"], cached["analysis"], cached["samples_meta"], meta=meta
                )
                mime = "application/zip"
            elif kind == "report.html":
                body, mime = exports.printable_report(cached["analysis"], meta), "text/html; charset=utf-8"
            else:
                return self._json(404, {"error": "unknown export format {k!r}".format(k=kind)})
        except Exception as exc:  # noqa: BLE001
            error_id = log.exception("export.failed", exc, run_id=run_id, kind=kind)
            return self._json(500, {"error": str(exc), "error_id": error_id})

        filename = exports.export_filename(kind, run_id)
        # report.html opens in a tab (the reader prints it); everything else is
        # a file they want on disk.
        disposition = "inline" if kind == "report.html" else "attachment"
        log.info("export.served", run_id=run_id, kind=kind, bytes=len(body))
        self._send(200, body, mime, {
            "Content-Disposition": '{d}; filename="{f}"'.format(d=disposition, f=filename)
        })

    def _stream_events(self) -> None:
        """Server-sent events: progress, run transitions, alerts.

        A WebSocket would mean hand-rolling RFC 6455 framing on top of
        BaseHTTPRequestHandler for a stream that only ever flows one way.
        EventSource also reconnects by itself.
        """
        stream: "queue.Queue" = queue.Queue(maxsize=200)
        with _stream_lock:
            _streams.append(stream)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        # Content-Length is unknown and must not be sent, so the connection is
        # explicitly not keep-alive-with-length; HTTP/1.1 chunking is skipped by
        # closing at the end.
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    event_type, payload = stream.get(timeout=15)
                    message = "event: {e}\ndata: {d}\n\n".format(
                        e=event_type, d=json.dumps(payload)
                    )
                except queue.Empty:
                    # A comment frame keeps proxies and load balancers from
                    # closing an idle stream at 30 or 60 seconds.
                    message = ": keepalive\n\n"
                self.wfile.write(message.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _stream_lock:
                if stream in _streams:
                    _streams.remove(stream)

    # -- DELETE ---------------------------------------------------------

    def do_DELETE(self) -> None:  # noqa: N802
        self._guard(self._do_delete)

    def _do_delete(self) -> None:
        import shutil

        path = urlparse(self.path).path

        if path in {"/api/runs", "/api/runs/"}:
            if QUEUE.active():
                return self._json(409, {"error": "a run is in progress; wait for it to finish"})
            cleared = QUEUE.clear_finished()
            with _ANALYSIS_LOCK:
                _ANALYSIS_CACHE.clear()
            publish("run", {"cleared": cleared})
            return self._json(200, {"cleared": cleared})

        if path.startswith("/api/runs/"):
            run_id = path[len("/api/runs/"):]
            if not QUEUE.get(run_id):
                return self._json(404, {"error": "unknown run"})
            cancelled = QUEUE.cancel(run_id)
            publish("run", {"run_id": run_id, "status": "cancelling"})
            return self._json(200, {"cancelled": cancelled, "run_id": run_id})

        if not path.startswith("/api/datasets/"):
            return self._json(404, {"error": "not found"})

        dataset_id = path[len("/api/datasets/"):]
        entry = next((d for d in all_datasets() if d["id"] == dataset_id), None)
        if entry is None:
            return self._json(404, {"error": "unknown dataset"})

        _invalidate_describe(dataset_id)

        if entry.get("uploaded"):
            # An upload lives entirely under data/uploads, so removing the card
            # and removing the data are the same action.
            directory = REPO_ROOT / entry["fastq_dir"]
            # Confined to the upload root so a crafted entry cannot walk out of
            # it and delete the repo.
            if UPLOAD_ROOT.resolve() not in directory.resolve().parents:
                return self._json(
                    400, {"error": "refusing to delete outside the uploads directory"}
                )
            shutil.rmtree(directory, ignore_errors=True)
            log.info("dataset.deleted", dataset=dataset_id, files_deleted=True)
            return self._json(200, {"removed": dataset_id, "files_deleted": True})

        # A registry dataset points at data/ that the user may have generated or
        # downloaded deliberately. Take it off the list by dropping the registry
        # entry, and leave the files alone -- silently deleting someone's data
        # because they wanted a tidier list would be the wrong trade.
        if not _remove_registry_entry(dataset_id):
            return self._json(404, {"error": "dataset is not in the registry"})
        log.info("dataset.hidden", dataset=dataset_id)
        return self._json(200, {
            "removed": dataset_id,
            "files_deleted": False,
            "note": "Hidden on this machine. The FASTQ files are still in {d}, and "
                    "nothing tracked in git changed. Run "
                    "`python -m bioradar.webapp --restore-datasets` to bring it "
                    "back.".format(d=entry["fastq_dir"]),
        })

    # -- POST -----------------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802
        self._guard(self._do_post)

    def _do_post(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/api/v1/debate", "/api/debate"}:
            body = self._read_json() or {}
            from bioradar.ai import debate
            res = debate.run_debate(body.get("sample_id", "BR-GOA-001"), body.get("topic"))
            return self._json(201, res)

        if path in {"/api/v1/nft/mint", "/api/nft/mint"}:
            body = self._read_json() or {}
            from bioradar.blockchain import nft
            res = nft.mint_nft(body.get("sample_id", "BR-GOA-001"), body.get("to_address"))
            return self._json(201, res)

        if path == "/api/upload":
            return self._handle_upload(parsed.query)
        if path == "/api/upload/finalize":
            return self._handle_finalize()
        if path == "/api/verifications":
            return self._handle_verification()
        if path == "/api/verifications/cv":
            return self._handle_cv_verification()
        if path == "/api/runs":
            return self._handle_start_run()

        self._json(404, {"error": "not found"})

    def _handle_cv_verification(self) -> None:
        body = self._read_json()
        if not body:
            return

        photo = body.get("photo", "field_photo.jpg")
        target_species = body.get("scientific_name", "Clarias gariepinus")
        site_id = body.get("site_id", "MANDOVI")
        observer = body.get("observer", "Field Officer")

        from bioradar.ai import cv_verifier
        res = cv_verifier.predict_species_from_photo(photo, target_species)

        # Record in append-only verification ledger if confirmed
        if res["is_confirmed"]:
            verification.record(
                scientific_name=target_species,
                site_id=site_id,
                outcome=verification.CONFIRMED,
                observer=observer,
                notes=f"Auto-verified via Computer Vision (TFLite MobileNetV3) confidence {res['confidence']:.2f}",
                photo=photo,
            )

        return self._json(200, res)


    def _handle_start_run(self) -> None:
        try:
            body = self._read_json()
            state = start_run(body["dataset_id"])
        except KeyError as exc:
            return self._json(400, {"error": str(exc)})
        except ValueError as exc:
            return self._json(400, {"error": "bad request: {e}".format(e=exc)})
        return self._json(201, state)

    def _handle_verification(self) -> None:
        try:
            body = self._read_json()
            entry = verification.record(
                scientific_name=body.get("scientific_name", ""),
                site_id=body.get("site_id", ""),
                outcome=body.get("outcome", ""),
                observer=body.get("observer", ""),
                run_id=body.get("run_id", ""),
                sample_id=body.get("sample_id", ""),
                notes=body.get("notes", ""),
                observed_name=body.get("observed_name", ""),
                latitude=body.get("latitude"),
                longitude=body.get("longitude"),
                observed_at=body.get("observed_at", ""),
            )
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})

        # The status a species carries is derived from the tally, so a new check
        # has to invalidate the cached reports that embed it.
        _refresh_verification_status()
        publish("run", {"verification": entry["verification_id"]})
        return self._json(201, entry)

    def _handle_upload(self, query: str) -> None:
        """Receive one FASTQ as a raw body.

        Raw bytes with the filename in the query string, rather than multipart:
        the stdlib multipart parser (`cgi`) was removed in Python 3.13, and
        hand-rolling one for gigabyte uploads is a bug farm. The browser posts
        each File object directly, which also streams.
        """
        params = parse_qs(query)
        batch = (params.get("batch") or [""])[0]
        filename = (params.get("filename") or [""])[0]
        if not batch or not filename:
            return self._json(400, {"error": "batch and filename are required"})

        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_UPLOAD_BYTES:
            return self._json(413, {
                "error": "{f} is {g:.1f} GB; the limit is {l} GB".format(
                    f=filename, g=length / 1e9, l=MAX_UPLOAD_BYTES // 1024 ** 3)
            })

        try:
            directory = upload_dir(batch)
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})
        directory.mkdir(parents=True, exist_ok=True)

        # A sample sheet is stored under its own name: it is metadata, not a
        # sequence file, and the map needs it.
        if filename.lower().endswith((".csv", ".tsv")):
            target = directory / Path(filename).name
            sample, mate = None, None
        else:
            normalised = normalise_upload_name(filename)
            if normalised is None:
                return self._json(400, {
                    "error": "{f}: not a recognisable paired FASTQ name. "
                             "Expected something like SAMPLE_R1_001.fastq.gz".format(f=filename)
                })
            sample, mate = normalised
            target = directory / "{s}_S1_L001_R{m}_001.fastq.gz".format(s=sample, m=mate)

        remaining = length
        with target.open("wb") as handle:
            while remaining > 0:
                chunk = self.rfile.read(min(1 << 20, remaining))
                if not chunk:
                    break
                handle.write(chunk)
                remaining -= len(chunk)

        if remaining > 0:
            # A short body means the connection dropped mid-upload. Keeping the
            # partial file would send a truncated FASTQ into the pipeline, which
            # fails half an hour later with an error nobody can read.
            target.unlink(missing_ok=True)
            return self._json(400, {
                "error": "{f}: upload was cut short ({r} bytes missing). "
                         "Try again.".format(f=filename, r=remaining)
            })

        return self._json(201, {
            "stored": target.name, "sample_id": sample, "mate": mate,
            "bytes": target.stat().st_size,
        })

    def _handle_finalize(self) -> None:
        try:
            body = self._read_json()
            batch = body.pop("batch")
        except (ValueError, KeyError) as exc:
            return self._json(400, {"error": "bad request: {e}".format(e=exc)})

        try:
            directory = upload_dir(batch)
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})
        if not directory.is_dir():
            return self._json(404, {"error": "no such upload batch"})

        r1 = sorted(directory.glob("*_R1_001.fastq.gz"))
        unpaired = [
            p.name for p in r1
            if not (p.parent / p.name.replace("_R1_", "_R2_")).is_file()
        ]
        if unpaired:
            return self._json(400, {
                "error": "unpaired read files (no R2): {u}".format(u=", ".join(unpaired))
            })
        if not r1:
            return self._json(400, {"error": "no FASTQ files were uploaded"})

        entry = register_upload(batch, body)
        return self._json(201, describe_dataset(entry, refresh=True))

    # -- static ---------------------------------------------------------

    def _serve_static(self, relative: str) -> None:
        # Defend against path traversal before touching the filesystem.
        target = (STATIC_DIR / relative).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            return self._json(404, {"error": "not found"})
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript", "text/javascript"
        }:
            content_type += "; charset=utf-8"
        self._send(200, target.read_bytes(), content_type)

    def log_message(self, fmt: str, *args: Any) -> None:
        if getattr(self.server, "verbose", False):
            log.debug("http", message=fmt % args, client=self.address_string())


def _refresh_verification_status() -> None:
    """Re-annotate cached analyses after a new field check."""
    with _ANALYSIS_LOCK:
        run_ids = list(_ANALYSIS_CACHE.keys())
    for run_id in run_ids:
        with _ANALYSIS_LOCK:
            cached = _ANALYSIS_CACHE.get(run_id)
        if not cached:
            continue
        result = cached["analysis"]
        site_lookup = {s["name"]: sorted(s.get("sites", ())) for s in result["species"]}
        result["species"] = verification.annotate(result["species"], site_lookup)


def _int(values: Optional[List[str]], default: int, maximum: int = 10 ** 6) -> int:
    try:
        return max(0, min(maximum, int((values or [str(default)])[0])))
    except (TypeError, ValueError):
        return default


def _paginate(items: List[Any], query: Dict[str, List[str]], key: str) -> Dict[str, Any]:
    """Bound every list response.

    A survey with 10,000 samples returning one JSON array locks the browser tab.
    The default limit is generous enough that no realistic demo hits it and
    small enough that a pathological dataset cannot take the page down.
    """
    limit = _int(query.get("limit"), 200, maximum=2000)
    offset = _int(query.get("offset"), 0)
    window = items[offset:offset + limit] if limit else items[offset:]
    return {
        key: window,
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(window) < len(items),
    }


def serve(host: str = "0.0.0.0", port: int = 8080, verbose: bool = False) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    server.verbose = verbose  # type: ignore[attr-defined]
    shown = "localhost" if host in {"0.0.0.0", ""} else host
    recover_runs()
    health = obs.health()
    print("BioRadar dashboard")
    print("  http://{h}:{p}".format(h=shown, p=port))
    print("  datasets : {n}".format(n=len(all_datasets())))
    print("  health   : {s}".format(s=health["status"]))
    if health["failing"]:
        print("  degraded : {f}".format(f=", ".join(health["failing"])))
    channels = notify.configured_channels()
    enabled = [name for name in ("email", "webhook") if channels[name]["enabled"]]
    print("  alerts   : {c}".format(c=", ".join(enabled) if enabled else "dashboard only"))
    print("  Ctrl-C to stop")
    log.info("server.started", port=port, health=health["status"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.server_close()


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="bioradar.webapp")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--restore-datasets",
        action="store_true",
        help="un-hide every bundled dataset removed through the UI, then exit",
    )
    args = parser.parse_args(argv)
    if args.restore_datasets:
        print("restored {n} hidden dataset(s)".format(n=restore_hidden_datasets()))
        return 0
    serve(args.host, args.port, args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
