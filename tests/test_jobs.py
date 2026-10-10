"""The job queue stands in for Celery + Redis, so it has to actually behave
like a task queue: queue rather than refuse, deduplicate, retry, and time out.
"""

from __future__ import annotations

import threading
import time

import pytest

from bioradar import jobs


def wait_for(predicate, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_a_job_runs_and_reports_its_result():
    queue = jobs.JobQueue()
    job = queue.submit("test", {"n": 1}, lambda j: {"answer": 42})
    assert wait_for(lambda: job.status == jobs.COMPLETED)
    assert job.summary()["answer"] == 42
    assert job.percent == 100


def test_a_second_submission_is_queued_not_refused():
    """The old behaviour was HTTP 409. Queueing is what the analysis asked for:
    the pipeline saturates every core, so serial execution is correct, but
    telling the user "no" instead of "in a minute" is not."""
    queue = jobs.JobQueue()
    release = threading.Event()
    first = queue.submit("test", {}, lambda j: release.wait(5) and {})
    assert wait_for(lambda: first.status == jobs.RUNNING)

    second = queue.submit("test", {}, lambda j: {})
    assert second.status == jobs.QUEUED
    assert second.job_id != first.job_id

    release.set()
    assert wait_for(lambda: second.status == jobs.COMPLETED)


def test_identical_submissions_collapse_onto_one_job():
    """Double-clicking Analyze must not burn twenty minutes of compute twice."""
    queue = jobs.JobQueue()
    release = threading.Event()
    first = queue.submit("test", {}, lambda j: release.wait(5) and {}, idempotency_key="k")
    assert wait_for(lambda: first.status == jobs.RUNNING)
    second = queue.submit("test", {}, lambda j: {}, idempotency_key="k")
    assert second.job_id == first.job_id
    release.set()
    assert wait_for(lambda: first.status == jobs.COMPLETED)


def test_resubmitting_after_a_failure_is_allowed():
    """Pressing the button again after an error means "try again"; refusing
    would be actively unhelpful."""
    queue = jobs.JobQueue()

    def boom(job):
        raise RuntimeError("nope")

    first = queue.submit("test", {}, boom, idempotency_key="k")
    assert wait_for(lambda: first.status == jobs.FAILED)
    second = queue.submit("test", {}, lambda j: {}, idempotency_key="k")
    assert second.job_id != first.job_id
    assert wait_for(lambda: second.status == jobs.COMPLETED)


def test_transient_failures_retry_with_backoff():
    queue = jobs.JobQueue(retry_base_delay=0.05)
    attempts = []

    def flaky(job):
        attempts.append(job.attempt)
        if job.attempt == 1:
            raise OSError("disk hiccup")
        return {"ok": True}

    job = queue.submit("test", {}, flaky, max_retries=2)
    assert wait_for(lambda: job.status == jobs.COMPLETED)
    assert attempts == [1, 2]


def test_retries_are_bounded():
    queue = jobs.JobQueue(retry_base_delay=0.01)

    def always_fails(job):
        raise RuntimeError("permanent")

    job = queue.submit("test", {}, always_fails, max_retries=2)
    assert wait_for(lambda: job.status == jobs.FAILED)
    assert job.attempt == 3          # the original plus two retries
    assert "permanent" in job.error
    assert job.error_id, "a failure the user can quote needs an id"


def test_a_cancelled_job_stops_at_the_next_checkpoint():
    queue = jobs.JobQueue()
    started = threading.Event()

    def long(job):
        started.set()
        for _ in range(400):
            job.check_cancelled()
            time.sleep(0.01)
        return {}

    job = queue.submit("test", {}, long)
    assert started.wait(5)
    queue.cancel(job.job_id)
    assert wait_for(lambda: job.status == jobs.CANCELLED)


def test_a_queued_job_can_be_cancelled_before_it_starts():
    queue = jobs.JobQueue()
    release = threading.Event()
    first = queue.submit("test", {}, lambda j: release.wait(5) and {})
    assert wait_for(lambda: first.status == jobs.RUNNING)
    second = queue.submit("test", {}, lambda j: {})
    assert queue.cancel(second.job_id)
    assert second.status == jobs.CANCELLED
    release.set()


def test_the_soft_deadline_is_enforced_at_a_checkpoint():
    """A run that has stalled must release the queue rather than hold it forever."""
    queue = jobs.JobQueue()

    def slow(job):
        for _ in range(400):
            job.check_deadline()
            time.sleep(0.01)
        return {}

    job = queue.submit("test", {}, slow, soft_timeout=0.1)
    assert wait_for(lambda: job.status == jobs.TIMED_OUT)
    assert "time limit" in job.error


def test_queue_position_tells_the_user_where_they_are():
    queue = jobs.JobQueue()
    release = threading.Event()
    first = queue.submit("test", {}, lambda j: release.wait(5) and {})
    assert wait_for(lambda: first.status == jobs.RUNNING)
    second = queue.submit("test", {}, lambda j: {})
    third = queue.submit("test", {}, lambda j: {})
    assert queue.queue_position(second) < queue.queue_position(third)
    release.set()


def test_clearing_removes_only_finished_jobs():
    queue = jobs.JobQueue()
    release = threading.Event()
    running = queue.submit("test", {}, lambda j: release.wait(5) and {})
    assert wait_for(lambda: running.status == jobs.RUNNING)
    assert queue.clear_finished() == 0
    release.set()
    assert wait_for(lambda: running.status == jobs.COMPLETED)
    assert queue.clear_finished() == 1
    assert queue.get(running.job_id) is None


def test_progress_events_update_the_summary():
    queue = jobs.JobQueue()

    def work(job):
        job.progress({"label": "Trimming primers", "percent": 40})
        return {}

    job = queue.submit("test", {}, work)
    assert wait_for(lambda: job.status == jobs.COMPLETED)
    assert job.summary(include_events=True)["events"][0]["label"] == "Trimming primers"
