"""Analyse a file the officer brings, the "unseen input" path of the challenge.

    POST /api/adjudicate/analyze?marker=12S&name=<file name>      (raw file as the request body)

The file is checked by its CONTENT (first character '>' or '@'), analysed with exactly the same
engine and thresholds as the pre-run samples, and deleted straight away. Nothing is saved, nothing
is added to the alert log, and the file name plays no part in the result.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
import uuid
import zlib
from typing import Any, Dict, Tuple

from bioradar.adjudicate import alerts, reference as reference_lists
from bioradar.adjudicate.adjudicate import adjudicate_file
from bioradar.adjudicate.seqio import detect_format
from bioradar.adjudicate.thresholds import load

MAX_BYTES = 12 * 1024 * 1024   # the pure-Python engine stays within seconds below this size
MAX_UNPACKED = 80 * 1024 * 1024  # a small .gz can hold a huge file; refuse anything that unpacks past this
READ_LIMIT = 60000             # reads analysed; the answer says so when a file is longer
MAX_DROPPED_SHOWN = 200
MARKERS = {"12S": "refseq_12s", "COI": "refseq_coi_16s", "16S": "refseq_coi_16s"}
_REFS: Dict[str, Any] = {}     # reference lists are slow to index, so keep each one after its first use


class UploadError(ValueError):
    """A problem the person can fix; the message is shown to them as written."""


def _reference(profile: str):
    if profile not in _REFS:
        _REFS[profile] = reference_lists.load_profile(profile)
    return _REFS[profile]


def _clean_name(name: str) -> str:
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[^A-Za-z0-9 _.()-]", "", base).strip()
    return base[:60] or "your file"


def analyze(raw: bytes, marker: str = "12S", name: str = "") -> Dict[str, Any]:
    if not raw:
        raise UploadError("The file is empty. Choose a file that holds DNA sequences (FASTA or FASTQ).")
    if len(raw) > MAX_BYTES:
        raise UploadError("The file is {:.1f} MB. The limit here is {} MB. Use a smaller file, or the first part "
                          "of this one.".format(len(raw) / 1e6, MAX_BYTES // (1024 * 1024)))
    key = (marker or "12S").upper()
    if key not in MARKERS:
        raise UploadError("Choose which gene region the file covers: 12S, COI or 16S.")

    if raw[:2] == bytes([0x1F, 0x8B]):
        try:
            unpacker = zlib.decompressobj(31)       # 31 = gzip wrapper
            body = unpacker.decompress(raw, MAX_UNPACKED)
        except zlib.error:
            raise UploadError("This does not look like a sequence file. It must start with '>' (FASTA) or "
                              "'@' (FASTQ). Text, spreadsheets and pictures cannot be read.")
        if unpacker.unconsumed_tail:
            raise UploadError("This file is far bigger once it is unpacked. The limit is {} MB unpacked. Use a "
                              "smaller file.".format(MAX_UNPACKED // (1024 * 1024)))
        raw = body

    handle, tmp = tempfile.mkstemp(prefix="bioradar_upload_", suffix=".dat")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(raw)
        try:
            fmt = detect_format(tmp)
        except (ValueError, OSError):
            raise UploadError("This does not look like a sequence file. It must start with '>' (FASTA) or "
                              "'@' (FASTQ). Text, spreadsheets and pictures cannot be read.")
        label = _clean_name(name)
        sample = {"sample_id": "UPLOAD-" + uuid.uuid4().hex[:8], "label": label, "marker": key,
                  "role": "upload", "profile": MARKERS[key], "collection_date": "", "location": "",
                  "latitude": None, "longitude": None,
                  "coordinate_note": "No location was given for an uploaded file, so no map pin is shown."}
        t = load()
        started = time.time()
        try:
            result = adjudicate_file(tmp, sample, _reference(MARKERS[key]), t, limit=READ_LIMIT)
        except UnicodeError:
            raise UploadError("The file could not be read as text.")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    full_dropped = result.pop("dropped")
    result.pop("kept")
    result["dropped"] = full_dropped[:MAX_DROPPED_SHOWN]
    result["dropped_total_listed"] = len(full_dropped)
    result["sample_id"] = sample["sample_id"]
    result["analysis_seconds"] = round(time.time() - started, 1)
    result["expected_check"] = {"available": False, "note": "You brought this file, so there is no published answer "
                                                           "to compare it with."}
    result["alerts"] = alerts.evaluate(result, started=time.time())   # shown on screen only, never logged
    result["from_cache"] = False
    result["uploaded"] = {"format": fmt, "bytes": len(raw), "read_limit": READ_LIMIT,
                          "kept_on_server": False,
                          "note": "The file was analysed and then deleted at once. It was not saved."}
    return result


def handle(raw: bytes, query: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    marker = (query.get("marker") or ["12S"])[0]
    name = (query.get("name") or [""])[0]
    try:
        return 200, analyze(raw, marker, name)
    except UploadError as exc:
        return 400, {"error": str(exc)}
