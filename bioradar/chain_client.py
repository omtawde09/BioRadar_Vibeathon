"""Chain-of-custody client: hash pipeline artifacts and commit them to the ledger.

This is the genesis of BioRadar's integrity chain. The pipeline hashes what it
produced, records it locally, and POSTs it to the backend. The local write
happens *first* and always -- if the backend is down (very likely during a
hackathon, where services come up in an unpredictable order) nothing is lost and
`flush_queue()` replays the pending records later.

Hashes are computed over canonical JSON (sorted keys, no incidental whitespace)
so the same payload always produces the same hash regardless of who serialises
it. Parth's `/api/v1/chain/record` endpoint must hash the same way or
verification will fail on correct data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bioradar.contract import CHAIN_EVENT_TYPES

DEFAULT_BACKEND_URL = os.environ.get("BIORADAR_BACKEND_URL", "http://localhost:8000")
DEFAULT_QUEUE_DIR = Path(os.environ.get("BIORADAR_CHAIN_QUEUE", "runs/_chain_queue"))

_CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Stream a file through SHA-256 so large BIOM tables do not hit memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: dict[str, Any]) -> str:
    """SHA-256 of a payload serialised canonically.

    Backend must match: `json.dumps(payload, sort_keys=True, separators=(',', ':'))`
    encoded as UTF-8. Any deviation (indentation, key order, trailing newline)
    changes the hash.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def build_event(
    sample_id: str,
    event_type: str,
    artifacts: dict[str, Path],
    *,
    pipeline_run_id: str | None = None,
    actor: str = "bioradar-pipeline",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a chain event describing a set of produced artifacts.

    `artifacts` maps a logical name ('taxonomy', 'biom') to a file path; each is
    hashed individually so a later verifier can tell *which* artifact was
    tampered with, not merely that something changed.
    """
    if event_type not in CHAIN_EVENT_TYPES:
        raise ValueError(
            f"unknown event_type {event_type!r}; expected one of "
            f"{sorted(CHAIN_EVENT_TYPES)}"
        )

    artifact_hashes: dict[str, Any] = {}
    for name, path in artifacts.items():
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"artifact {name!r} not found at {path}")
        artifact_hashes[name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "filename": path.name,
        }

    payload: dict[str, Any] = {"artifacts": artifact_hashes}
    if extra:
        payload.update(extra)

    return {
        "sample_id": sample_id,
        "pipeline_run_id": pipeline_run_id or str(uuid.uuid4()),
        "timestamp": utc_now(),
        "event_type": event_type,
        "actor": actor,
        "payload_hash": canonical_hash(payload),
        "payload": payload,
    }


class ChainClient:
    """Post chain events to the backend, queueing locally when it is unreachable."""

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        queue_dir: Path = DEFAULT_QUEUE_DIR,
        timeout: float = 30.0,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.queue_dir = Path(queue_dir)
        self.timeout = timeout

    @property
    def endpoint(self) -> str:
        return f"{self.backend_url}/api/v1/chain/record"

    def record(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist an event locally, then try to commit it to the backend.

        Never raises on a backend failure -- a pipeline run must not die because
        the ledger is offline. The return value reports what actually happened.
        """
        queued_path = self._write_queue_file(event)

        try:
            import requests
        except ImportError:
            return {
                "committed": False,
                "queued_at": str(queued_path),
                "error": "requests not installed",
            }

        try:
            response = requests.post(self.endpoint, json=event, timeout=self.timeout)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - any failure means "queue it"
            return {
                "committed": False,
                "queued_at": str(queued_path),
                "error": f"{type(exc).__name__}: {exc}",
            }

        queued_path.unlink(missing_ok=True)
        try:
            body = response.json()
        except ValueError:
            body = {}
        return {"committed": True, "queued_at": None, "response": body}

    def flush_queue(self) -> dict[str, int]:
        """Replay queued events once the backend is up.

        Ordering matters: the ledger links each record to the previous hash for
        that sample, so events are replayed oldest-first.
        """
        if not self.queue_dir.is_dir():
            return {"sent": 0, "failed": 0, "remaining": 0}

        sent = failed = 0
        for path in sorted(self.queue_dir.glob("*.json")):
            try:
                event = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                failed += 1
                continue

            result = self.record(event)
            if result["committed"]:
                sent += 1
                path.unlink(missing_ok=True)
            else:
                failed += 1

        remaining = len(list(self.queue_dir.glob("*.json")))
        return {"sent": sent, "failed": failed, "remaining": remaining}

    def _write_queue_file(self, event: dict[str, Any]) -> Path:
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        # Timestamp-prefixed so sorted() replays in chain order.
        stamp = event["timestamp"].replace(":", "").replace("-", "")
        name = f"{stamp}_{event['sample_id']}_{event['event_type']}.json"
        path = self.queue_dir / name
        path.write_text(json.dumps(event, indent=2, sort_keys=True), encoding="utf-8")
        return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.chain_client",
        description="Hash pipeline artifacts and commit them to the custody ledger.",
    )
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--queue-dir", type=Path, default=DEFAULT_QUEUE_DIR)
    parser.add_argument("--event-type", default="pipeline_complete")
    parser.add_argument(
        "--out", type=Path, default=None, help="also write the record here"
    )
    parser.add_argument(
        "--flush", action="store_true", help="replay queued records and exit"
    )
    args = parser.parse_args(argv)

    client = ChainClient(args.backend_url, args.queue_dir)

    if args.flush:
        print(json.dumps(client.flush_queue(), indent=2))
        return 0

    artifacts: dict[str, Path] = {}
    for name, relative in (
        ("taxonomy", "taxonomy_normalized.csv"),
        ("summary", "sample_summary.csv"),
        ("biom", "asvs/asv-table.tsv"),
        ("report", "final-report.pdf"),
    ):
        candidate = args.results_dir / relative
        if candidate.is_file():
            artifacts[name] = candidate

    if not artifacts:
        print(f"no hashable artifacts under {args.results_dir}", file=sys.stderr)
        return 1

    event = build_event(
        args.sample_id,
        args.event_type,
        artifacts,
        pipeline_run_id=args.run_id,
    )
    result = client.record(event)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(event, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({"event": event, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
