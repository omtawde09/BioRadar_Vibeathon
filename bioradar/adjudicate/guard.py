"""Data guard: reject or merge bad records, with a written reason for each.

Four problems are checked against REAL archive records (never edited, never
fabricated):

    1. duplicate sample ID     same ID on several runs: merge if it is one biological
                               sample re-sequenced, reject if two different samples
                               claim one ID
    2. GPS outside boundary    point-in-polygon against the selected protected area
    3. future collection date  later than today
    4. two spellings           one species recorded under two spellings: merged

Nothing is written back to a source record. Accepted records go to the clean store,
rejected ones to quarantine with the rule and the reason, and `post_check` re-reads
the clean store to prove it contains no duplicate, out-of-bounds, future-dated or
double-spelled record. If a rule found nothing in the real data, the result says so:
it never invents a case.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "real_challenge"
RECORDS_TSV = DATA_DIR / "datasets" / "PRJEB108476_bge_records" / "records" / "PRJEB108476_runs.tsv"
BOUNDARY_FILE = DATA_DIR / "boundary" / "litoral_norte.geojson"

RULES = {
    "duplicate_id": "Duplicate sample ID",
    "outside_boundary": "GPS pin outside the selected boundary",
    "no_coordinates": "No GPS pin to check",
    "future_date": "Collection date in the future",
    "double_spelling": "Species recorded under two spellings",
}


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------


def load_boundary(path: Path = BOUNDARY_FILE) -> Dict[str, Any]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    feature = doc["features"][0] if doc.get("type") == "FeatureCollection" else doc
    geom = feature["geometry"]
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return {"name": feature["properties"].get("name", "boundary"),
            "properties": feature["properties"], "polygons": polygons}


def _ring_contains(lon: float, lat: float, ring: List[List[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_boundary(lon: float, lat: float, boundary: Dict[str, Any]) -> bool:
    for poly in boundary["polygons"]:
        if _ring_contains(lon, lat, poly[0]) and not any(
                _ring_contains(lon, lat, hole) for hole in poly[1:]):
            return True
    return False


# --------------------------------------------------------------------------
# dates
# --------------------------------------------------------------------------


def parse_date(text: str) -> Optional[Tuple[date, str]]:
    """Return (earliest day the text could mean, precision). Accepts 2024 / 2024-03 /
    2024-03-15 / 2024-03-15T10:20Z. Partial dates are valid, not errors."""
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", (text or "").strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    try:
        return date(y, int(mo) if mo else 1, int(d) if d else 1), (
            "day" if d else "month" if mo else "year")
    except ValueError:
        return None


# --------------------------------------------------------------------------
# species spelling
# --------------------------------------------------------------------------

_ENDINGS = re.compile(r"(ii|i|ae|iae|us|a|um|is|e|ensis|ense)$")


def spelling_variants(species_sequences: Dict[str, str],
                      counts: Optional[Dict[str, int]] = None,
                      min_identity: float = 0.99) -> List[Dict[str, Any]]:
    """Names in the same genus whose epithets differ only by spelling AND whose
    sequences are (near) identical. Name similarity alone is not enough: two real
    species can have look-alike names, so the sequence has to agree."""
    counts = counts or {}
    by_genus: Dict[str, List[str]] = defaultdict(list)
    for name in species_sequences:
        by_genus[name.split()[0]].append(name)
    out = []
    for genus, names in by_genus.items():
        names = sorted(names)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i].split()[1], names[j].split()[1]
                similar = (_ENDINGS.sub("", a) == _ENDINGS.sub("", b)
                           or difflib.SequenceMatcher(None, a, b).ratio() >= 0.9)
                if not similar:
                    continue
                sa, sb = species_sequences[names[i]], species_sequences[names[j]]
                ident = sum(x == y for x, y in zip(sa, sb)) / max(len(sa), len(sb))
                if ident >= min_identity:
                    keep, drop = sorted([names[i], names[j]],
                                        key=lambda n: (-counts.get(n, 0), n))
                    out.append({"keep": keep, "merge": drop, "sequence_identity": round(ident, 4),
                                "reason": "same genus, epithets differ only in spelling "
                                          "('{}' vs '{}') and the 12S sequences are {:.1%} "
                                          "identical: one animal, two spellings".format(
                                              a, b, ident)})
    return out


# --------------------------------------------------------------------------
# the guard
# --------------------------------------------------------------------------


def load_records(path: Path = RECORDS_TSV) -> List[Dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def run_guard(records: List[Dict[str, str]], boundary: Dict[str, Any],
              today: Optional[date] = None,
              species_sequences: Optional[Dict[str, str]] = None,
              species_counts: Optional[Dict[str, int]] = None,
              spelling_merges: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    today = today or date.today()
    decisions: List[Dict[str, Any]] = []

    def decide(row: Dict[str, str], rule: str, action: str, why: str) -> None:
        decisions.append({"run_accession": row["run_accession"], "sample_alias": row["sample_alias"],
                          "rule": rule, "rule_label": RULES[rule], "action": action, "reason": why})

    rejected = set()

    # 3. future dates
    for row in records:
        parsed = parse_date(row.get("collection_date", ""))
        if parsed and parsed[0] > today:
            rejected.add(row["run_accession"])
            decide(row, "future_date", "reject",
                   "collection date {} is after today ({}): the sample cannot have been "
                   "collected yet, so the date (or the whole record) is wrong".format(
                       row["collection_date"], today.isoformat()))

    # 2. GPS outside boundary / missing
    for row in records:
        if row["run_accession"] in rejected:
            continue
        if not row.get("lat") or not row.get("lon"):
            rejected.add(row["run_accession"])
            decide(row, "no_coordinates", "reject",
                   "no GPS pin ({}), so it cannot be placed inside the boundary".format(
                       row.get("scientific_name") or "field blank"))
            continue
        lat, lon = float(row["lat"]), float(row["lon"])
        if not in_boundary(lon, lat, boundary):
            rejected.add(row["run_accession"])
            decide(row, "outside_boundary", "reject",
                   "GPS pin ({:.4f}, {:.4f}) is outside the selected boundary '{}'".format(
                       lat, lon, boundary["name"]))

    # 1. duplicate sample IDs (among records that are otherwise acceptable)
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in records:
        if row["run_accession"] not in rejected:
            groups[row["sample_alias"]].append(row)
    merged_runs: Dict[str, List[str]] = {}
    for alias, rows in groups.items():
        if len(rows) < 2:
            continue
        biosamples = {r["sample_accession"] for r in rows}
        if len(biosamples) == 1:
            merged_runs[alias] = [r["run_accession"] for r in rows]
            for r in rows[1:]:
                decide(r, "duplicate_id", "merge",
                       "sample ID '{}' is the same biological sample ({}) sequenced again: "
                       "merged into run {} as a technical re-run".format(
                           alias, rows[0]["sample_accession"], rows[0]["run_accession"]))
        else:
            for r in rows[1:]:
                rejected.add(r["run_accession"])
                decide(r, "duplicate_id", "reject",
                       "sample ID '{}' is claimed by {} different biological samples: ID "
                       "collision, kept only the first".format(alias, len(biosamples)))
    merged_away = {d["run_accession"] for d in decisions if d["action"] == "merge"}

    # 4. double spellings (species vocabulary)
    if spelling_merges is not None:
        spelling = spelling_merges
    else:
        spelling = spelling_variants(species_sequences or {}, species_counts) \
            if species_sequences else []
    for s in spelling:
        decisions.append({"run_accession": "", "sample_alias": "", "rule": "double_spelling",
                          "rule_label": RULES["double_spelling"], "action": "merge",
                          # The source label is never overwritten: both labels are kept in the
                          # audit event, and the basis says what the merge rests on.
                          "original_label": s["merge"], "canonical_label": s["keep"],
                          "basis": "name similarity within the genus + sequence identity "
                                   "{:.1%}; no external synonym authority was consulted".format(
                                       s.get("sequence_identity", 0.0)),
                          "reason": "'{}' merged into '{}': {}".format(
                              s["merge"], s["keep"], s["reason"])})

    clean = [r for r in records if r["run_accession"] not in rejected
             and r["run_accession"] not in merged_away]
    quarantine = [d for d in decisions if d["action"] == "reject"]
    counts: Dict[str, Dict[str, int]] = {}
    for d in decisions:
        slot = counts.setdefault(d["rule"], {"reject": 0, "merge": 0})
        slot[d["action"]] += 1
    not_present = [RULES[r] for r in ("duplicate_id", "outside_boundary", "future_date",
                                      "double_spelling") if r not in counts]
    ids_clean = [r["sample_alias"] for r in clean]
    return {
        "today": today.isoformat(),
        "boundary": {"name": boundary["name"], "source": boundary["properties"].get("source", ""),
                     "osm_relation": boundary["properties"].get("osm_relation", "")},
        "records_in": len(records),
        "clean": clean,
        "clean_count": len(clean),
        "decisions": decisions,
        "counts_by_rule": counts,
        "rules_not_exercised_by_this_data": not_present,
        "merged_runs": merged_runs,
        "spelling_merges": spelling,
        "post_check": post_check(clean, boundary, today, ids_clean, spelling,
                                 vocabulary=species_sequences, counts=species_counts),
    }


def post_check(clean: List[Dict[str, str]], boundary: Dict[str, Any], today: date,
               ids: Optional[List[str]] = None, spelling: Optional[List[Dict[str, Any]]] = None,
               vocabulary: Optional[Dict[str, str]] = None,
               counts: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Re-read the clean store and prove no unintended bad record got through.

    `unmerged_double_spellings` is measured, not assumed: the species vocabulary
    that is left after the merges is scanned again with the same rule. It is None
    ("not checked") when no vocabulary was supplied -- never a silent 0."""
    ids = ids if ids is not None else [r["sample_alias"] for r in clean]
    dup_ids = len(ids) - len(set(ids))
    outside = sum(1 for r in clean if not r.get("lat") or not r.get("lon")
                  or not in_boundary(float(r["lon"]), float(r["lat"]), boundary))
    future = sum(1 for r in clean
                 if (parse_date(r.get("collection_date", "")) or (date.min, ""))[0] > today)
    unmerged: Optional[int] = None
    if vocabulary:
        merged_away = {m["merge"] for m in (spelling or [])}
        left = {n: q for n, q in vocabulary.items() if n not in merged_away}
        unmerged = len(spelling_variants(left, counts))
    return {
        "records_checked": len(clean),
        "duplicate_sample_ids": dup_ids,
        "outside_boundary": outside,
        "future_dated": future,
        "unmerged_double_spellings": unmerged,
        "clean": dup_ids == 0 and outside == 0 and future == 0 and not unmerged,
    }


def file_md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()
