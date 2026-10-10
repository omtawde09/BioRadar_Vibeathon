"""A serial job queue with idempotency, timeouts and retries.

The gap analysis prescribes Celery + Redis. That is the right answer for a
service whose tasks are small and numerous, and the wrong one here, for two
reasons worth stating rather than hand-waving:

  * There is no Redis. The app runs *inside* the pipeline image so that
    `snakemake` is on PATH; adding a broker means either a second container the
    app must reach or a rebuild of an 11.7 GB image.
  * Concurrency is not the goal. Snakemake is invoked with every available core,
    so two simultaneous runs do not finish sooner -- they thrash, and on a
    7 GB-RAM container DADA2 will be OOM-killed. Serial execution is the correct
    scheduling policy, not a limitation to engineer around.

What Celery would have bought -- and what this therefore implements -- is the
behaviour, not the broker: work is *queued* rather than refused, duplicate
submissions collapse onto the original (idempotency keys), transient failures
retry with exponential backoff, and runaway jobs are killed on a deadline
instead of hanging forever.

Swapping this for Celery later is a contained change: `submit()` and the job
record are the whole interface.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from bioradar import obs

log = obs.logger("jobs")

# Python 3.8 in the pipeline image: subscripting these at runtime is a
# TypeError, so the alias uses typing's capitalised forms deliberately.
JobFn = Callable[["Job"], Any]

QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
TIMED_OUT = "timed_out"

TERMINAL = {COMPLETED, FAILED, CANCELLED, TIMED_OUT}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Job:
    """One unit of work and everything the UI needs to describe it."""

    def __init__(
        self,
        job_id: str,
        kind: str,
        payload: Dict[str, Any],
        fn: JobFn,
        *,
        idempotency_key: Optional[str] = None,
        max_retries: int = 0,
        soft_timeout: Optional[float] = None,
        hard_timeout: Optional[float] = None,
    ) -> None:
        self.job_id = job_id
        self.kind = kind
        self.payload = payload
        self.fn = fn
        self.idempotency_key = idempotency_key
        self.max_retries = max_retries
        self.soft_timeout = soft_timeout
        self.hard_timeout = hard_timeout

        self.status = QUEUED
        self.attempt = 0
        self.percent = 0
        self.stage = "Queued"
        self.events: List[Dict[str, Any]] = []
        self.result: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.error_id: Optional[str] = None
        self.traceback: Optional[str] = None
        self.queued_at = _now()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.deadline: Optional[float] = None
        self.cancelled = threading.Event()
        self.lock = threading.Lock()

    # -- progress -------------------------------------------------------
    def progress(self, event: Dict[str, Any]) -> None:
        with self.lock:
            self.events.append(event)
            if event.get("percent") is not None:
                self.percent = event["percent"]
            if event.get("label"):
                self.stage = event["label"]

    def note(self, stage: str, percent: Optional[int] = None) -> None:
        self.progress({"type": "note", "label": stage, "percent": percent})

    def check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise JobCancelled(self.job_id)

    def check_deadline(self) -> None:
        """Raise once the soft timeout has passed.

        Called from the progress callback, so a run that is still emitting
        events stops at a rule boundary rather than being killed mid-write.
        """
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise JobTimeout(self.job_id)

    def summary(self, include_events: bool = False) -> Dict[str, Any]:
        with self.lock:
            data: Dict[str, Any] = {
                "job_id": self.job_id,
                "kind": self.kind,
                "status": self.status,
                "percent": self.percent,
                "stage": self.stage,
                "attempt": self.attempt,
                "max_retries": self.max_retries,
                "queued_at": self.queued_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "event_count": len(self.events),
                "idempotency_key": self.idempotency_key,
            }
            data.update(self.payload)
            data.update(self.result)
            if self.error:
                data["error"] = self.error
            if self.error_id:
                data["error_id"] = self.error_id
            if self.traceback:
                data["traceback"] = self.traceback
            if include_events:
                data["events"] = list(self.events)
        return data


class JobCancelled(RuntimeError):
    pass


class JobTimeout(RuntimeError):
    pass


class JobQueue:
    """One worker, FIFO, with idempotent submission.

    A single worker is a decision, not a default: see the module docstring.
    """

    def __init__(self, *, retry_base_delay: float = 5.0) -> None:
        self._jobs: Dict[str, Job] = {}
        self._by_key: Dict[str, str] = {}
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.RLock()
        self._worker: Optional[threading.Thread] = None
        self._current: Optional[Job] = None
        self._retry_base_delay = retry_base_delay
        self._stop = threading.Event()

    # -- submission -----------------------------------------------------
    def submit(
        self,
        kind: str,
        payload: Dict[str, Any],
        fn: JobFn,
        *,
        job_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        max_retries: int = 0,
        soft_timeout: Optional[float] = None,
        hard_timeout: Optional[float] = None,
    ) -> Job:
        """Queue a job, or return the existing one for the same key.

        Idempotency collapses only onto jobs that are queued, running or already
        completed. A previous *failure* does not block a retry -- the user
        pressing the button again after an error means "try again", and refusing
        would be actively unhelpful.
        """
        with self._lock:
            if idempotency_key:
                existing_id = self._by_key.get(idempotency_key)
                existing = self._jobs.get(existing_id or "")
                if existing is not None and existing.status in {QUEUED, RUNNING, COMPLETED}:
                    log.info(
                        "job.deduplicated",
                        job_id=existing.job_id,
                        kind=kind,
                        status=existing.status,
                    )
                    return existing

            job = Job(
                job_id or f"{kind}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}",
                kind,
                payload,
                fn,
                idempotency_key=idempotency_key,
                max_retries=max_retries,
                soft_timeout=soft_timeout,
                hard_timeout=hard_timeout,
            )
            self._jobs[job.job_id] = job
            if idempotency_key:
                self._by_key[idempotency_key] = job.job_id
            position = self._queue.qsize()
            job.stage = "Queued" if position or self._current else "Starting"
            self._queue.put(job.job_id)
            self._ensure_worker()

        log.info("job.submitted", job_id=job.job_id, kind=kind, queue_depth=position)
        return job

    def _ensure_worker(self) -> None:
        if self._worker is None or not self._worker.is_alive():
            self._stop.clear()
            self._worker = threading.Thread(
                target=self._run_forever, name="bioradar-worker", daemon=True
            )
            self._worker.start()

    # -- accessors ------------------------------------------------------
    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> List[Job]:
        with self._lock:
            return list(self._jobs.values())

    def active(self) -> List[Job]:
        return [j for j in self.all() if j.status in {QUEUED, RUNNING}]

    def queue_position(self, job: Job) -> int:
        """0 = running now, 1 = next, and so on."""
        pending = [j for j in self.all() if j.status == QUEUED]
        pending.sort(key=lambda j: j.queued_at)
        running = 1 if self._current is not None else 0
        try:
            return pending.index(job) + running
        except ValueError:
            return 0

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None or job.status in TERMINAL:
            return False
        job.cancelled.set()
        if job.status == QUEUED:
            self._finish(job, CANCELLED, error="Cancelled before it started")
        log.info("job.cancel_requested", job_id=job_id, status=job.status)
        return True

    def clear_finished(self) -> int:
        with self._lock:
            done = [j for j in self._jobs.values() if j.status in TERMINAL]
            for job in done:
                self._jobs.pop(job.job_id, None)
                if job.idempotency_key:
                    self._by_key.pop(job.idempotency_key, None)
            return len(done)

    # -- the worker -----------------------------------------------------
    def _run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                job_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            job = self.get(job_id)
            if job is None or job.status in TERMINAL:
                continue
            self._execute(job)

    def _execute(self, job: Job) -> None:
        while True:
            job.attempt += 1
            with self._lock:
                self._current = job
            with job.lock:
                job.status = RUNNING
                job.started_at = _now()
                job.stage = "Starting"
            job.deadline = (
                time.monotonic() + job.soft_timeout if job.soft_timeout else None
            )
            log.info("job.started", job_id=job.job_id, kind=job.kind, attempt=job.attempt)

            watchdog = self._start_watchdog(job)
            try:
                result = job.fn(job) or {}
                self._finish(job, COMPLETED, result=result)
                log.info("job.completed", job_id=job.job_id, kind=job.kind)
                return
            except JobCancelled:
                self._finish(job, CANCELLED, error="Cancelled")
                log.info("job.cancelled", job_id=job.job_id)
                return
            except JobTimeout:
                self._finish(
                    job,
                    TIMED_OUT,
                    error=(
                        "The pipeline exceeded its time limit and was stopped. "
                        "The dataset may be larger than this machine can process, "
                        "or the run may have stalled."
                    ),
                )
                log.warning("job.timed_out", job_id=job.job_id, attempt=job.attempt)
                return
            except Exception as exc:  # noqa: BLE001
                error_id = log.exception(
                    "job.failed", exc, job_id=job.job_id, kind=job.kind, attempt=job.attempt
                )
                if job.attempt <= job.max_retries and not job.cancelled.is_set():
                    delay = self._retry_base_delay * (2 ** (job.attempt - 1))
                    job.note(
                        f"Attempt {job.attempt} failed; retrying in {int(delay)}s",
                        job.percent,
                    )
                    log.info("job.retrying", job_id=job.job_id, delay=delay)
                    if job.cancelled.wait(delay):
                        self._finish(job, CANCELLED, error="Cancelled")
                        return
                    continue
                self._finish(
                    job,
                    FAILED,
                    error=f"{type(exc).__name__}: {exc}",
                    error_id=error_id,
                    tb=traceback.format_exc()[-4000:],
                )
                return
            finally:
                if watchdog is not None:
                    watchdog.cancel()
                with self._lock:
                    self._current = None

    def _start_watchdog(self, job: Job) -> Optional[threading.Timer]:
        """Set the cancel flag at the hard timeout.

        The soft timeout is checked cooperatively from progress callbacks, which
        is the graceful path. This is the ungraceful one, for a job that has
        stopped emitting events entirely -- it sets the same flag the pipeline
        runner polls, so the subprocess is terminated rather than orphaned.
        """
        if not job.hard_timeout:
            return None
        timer = threading.Timer(job.hard_timeout, job.cancelled.set)
        timer.daemon = True
        timer.start()
        return timer

    def _finish(
        self,
        job: Job,
        status: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        error_id: Optional[str] = None,
        tb: Optional[str] = None,
    ) -> None:
        with job.lock:
            job.status = status
            job.finished_at = _now()
            job.error = error
            job.error_id = error_id
            job.traceback = tb
            if result:
                job.result.update(result)
            if status == COMPLETED:
                job.percent = 100
                job.stage = "Done"
            elif status == TIMED_OUT:
                job.stage = "Timed out"
            elif status == CANCELLED:
                job.stage = "Cancelled"
            else:
                job.stage = "Failed"
