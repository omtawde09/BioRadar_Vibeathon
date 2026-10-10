"""A stand-in chain-of-custody backend, for integration testing only.

This is NOT Parth's deliverable and must not be shipped. It exists so the
pipeline's hash emission can be tested end-to-end before the real FastAPI
backend is up, and so `ci/check_integration.sh` can assert that a POST from the
pipeline actually lands somewhere.

It implements exactly the two endpoints the pipeline touches, with the same
hash-chain semantics the real backend must have:

    POST /api/v1/chain/record        append a record, linking previous_hash
    GET  /api/v1/chain/verify/{id}   walk the chain, report whether it is intact
    GET  /health                     liveness

Storage is an in-memory dict. Restarting loses everything, which is fine for a
test double.

    python -m integration.mock_backend --port 8000
"""

from __future__ import annotations

import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

# sample_id -> ordered list of records
_LEDGER: dict[str, list[dict[str, Any]]] = {}
_LOCK = threading.Lock()

_VERIFY_RE = re.compile(r"^/api/v1/chain/verify/(?P<sample_id>[^/]+)/?$")


def append_record(event: dict[str, Any]) -> dict[str, Any]:
    """Append an event, chaining it to the previous record for that sample."""
    sample_id = str(event.get("sample_id", ""))
    if not sample_id:
        raise ValueError("sample_id is required")
    if not event.get("payload_hash"):
        raise ValueError("payload_hash is required")

    with _LOCK:
        chain = _LEDGER.setdefault(sample_id, [])
        previous_hash = chain[-1]["payload_hash"] if chain else None
        record = {
            "record_id": f"{sample_id}-{len(chain) + 1:04d}",
            "sample_id": sample_id,
            "event_type": event.get("event_type", "unknown"),
            "timestamp": event.get("timestamp", ""),
            "actor": event.get("actor", "unknown"),
            "payload_hash": event["payload_hash"],
            "previous_hash": previous_hash,
            "payload": event.get("payload", {}),
        }
        chain.append(record)
        return {
            "record_id": record["record_id"],
            "chain_id": sample_id,
            "chain_intact": True,
            "event_count": len(chain),
        }


def verify_chain(sample_id: str) -> dict[str, Any]:
    """Walk a sample's chain and confirm every link points at its predecessor."""
    with _LOCK:
        chain = list(_LEDGER.get(sample_id, []))

    if not chain:
        return {
            "sample_id": sample_id,
            "chain_intact": True,
            "event_count": 0,
            "message": "No records found",
        }

    previous_hash = None
    for record in chain:
        if record["previous_hash"] != previous_hash:
            return {
                "sample_id": sample_id,
                "chain_intact": False,
                "event_count": len(chain),
                "broken_at": record["record_id"],
                "message": "Chain broken -- tampering detected",
            }
        previous_hash = record["payload_hash"]

    return {
        "sample_id": sample_id,
        "chain_intact": True,
        "event_count": len(chain),
        "latest_hash": previous_hash,
        "events": [r["event_type"] for r in chain],
        "message": "Chain verified -- no tampering detected",
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _respond(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path in {"/health", "/health/"}:
            self._respond(200, {"status": "healthy", "service": "mock_backend"})
            return

        match = _VERIFY_RE.match(self.path)
        if match:
            self._respond(200, verify_chain(match.group("sample_id")))
            return

        if self.path in {"/api/v1/chain", "/api/v1/chain/"}:
            with _LOCK:
                self._respond(
                    200,
                    {sample: len(chain) for sample, chain in _LEDGER.items()},
                )
            return

        self._respond(404, {"error": "not found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        if self.path not in {"/api/v1/chain/record", "/api/v1/chain/record/"}:
            self._respond(404, {"error": "not found", "path": self.path})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            event = json.loads(raw.decode("utf-8"))
            result = append_record(event)
        except (ValueError, UnicodeDecodeError) as exc:
            self._respond(400, {"error": str(exc)})
            return

        self._respond(201, result)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet by default; CI captures stdout and the noise is unhelpful.
        if self.server.verbose:  # type: ignore[attr-defined]
            super().log_message(fmt, *args)


class MockBackend(HTTPServer):
    """HTTPServer with a verbosity flag and a convenient context manager."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, verbose: bool = False):
        super().__init__((host, port), Handler)
        self.verbose = verbose

    @property
    def url(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "MockBackend":
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.shutdown()
        self.server_close()


def reset() -> None:
    """Clear the ledger between tests."""
    with _LOCK:
        _LEDGER.clear()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="integration.mock_backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    server = MockBackend(args.host, args.port, args.verbose)
    print(f"mock chain backend listening on {server.url}")
    print("  POST /api/v1/chain/record")
    print("  GET  /api/v1/chain/verify/{sample_id}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
