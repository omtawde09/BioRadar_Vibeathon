"""Test-wide setup.

Structured logging writes one JSON object per line to stderr, which is exactly
what you want in production and pure noise in a test run. Errors still surface;
everything below them is silenced.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _quiet_logs():
    os.environ.setdefault("BIORADAR_LOG_LEVEL", "error")
    from bioradar import obs

    obs.configure()


@pytest.fixture(autouse=True)
def _isolate_error_log(tmp_path_factory, monkeypatch):
    """Keep captured exceptions out of the repository's real logs/errors.jsonl.

    Several tests deliberately raise, and appending those to the file a
    developer greps during a demo would be actively misleading.
    """
    from bioradar import obs

    monkeypatch.setenv(
        "BIORADAR_ERROR_LOG",
        str(tmp_path_factory.mktemp("logs") / "errors.jsonl"),
    )
    obs.configure()
    yield
