"""Time Machine: what changed at this site between two sampling rounds.

Takes two normalized taxonomy CSVs from the same site and answers the question a
forest officer actually asks -- "what is here now that wasn't here last time?"

Comparison is done at a chosen rank (species by default) rather than by ASV,
because ASV hashes are sequence-exact: a one-base difference makes a new ASV for
what is biologically the same organism. Comparing at species level is what makes
"appeared" and "disappeared" mean something.

Read-count changes are reported as fold-change on *relative* abundance, not raw
counts, since sequencing depth varies between runs and raw counts are not
comparable across them. A taxon whose relative abundance moved less than
`noise_threshold` is reported as stable.

    python -m bioradar.time_machine before.csv after.csv --site GOA-MANDOVI -o diff.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

from bioradar.contract import RANKS

# Relative-abundance change below this is treated as run-to-run noise, not signal.
DEFAULT_NOISE_THRESHOLD = 0.25

# Guards log-fold-change when a taxon goes from absent to present.
_PSEUDOCOUNT = 1e-6


def load_taxonomy(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def aggregate(
    rows: Iterable[dict[str, str]],
    *,
    rank: str = "species",
    sample_ids: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Collapse detections to one entry per taxon at `rank`.

    Rows unassigned at that rank are skipped: an ASV identified only to family
    tells us nothing about whether a *species* appeared or vanished.
    """
    if rank not in RANKS:
        raise ValueError(f"rank must be one of {RANKS}, got {rank!r}")

    totals: dict[str, dict[str, Any]] = {}
    grand_total = 0

    for row in rows:
        if sample_ids and row.get("sample_id") not in sample_ids:
            continue
        name = (row.get(rank) or "").strip()
        if not name:
            continue

        reads = int(float(row.get("read_count") or 0))
        if reads <= 0:
            continue
        grand_total += reads

        entry = totals.setdefault(
            name,
            {
                "name": name,
                "rank": rank,
                "taxon_id": row.get("taxon_id", ""),
                "read_count": 0,
                "asvs": set(),
                "confidence_sum": 0.0,
                "confidence_n": 0,
            },
        )
        entry["read_count"] += reads
        entry["asvs"].add(row.get("asv_id", ""))
        entry["confidence_sum"] += float(row.get("confidence") or 0)
        entry["confidence_n"] += 1
        if not entry["taxon_id"]:
            entry["taxon_id"] = row.get("taxon_id", "")

    for entry in totals.values():
        entry["asv_count"] = len(entry["asvs"])
        del entry["asvs"]
        entry["rel_abundance"] = (
            round(entry["read_count"] / grand_total, 6) if grand_total else 0.0
        )
        entry["mean_confidence"] = (
            round(entry["confidence_sum"] / entry["confidence_n"], 4)
            if entry["confidence_n"]
            else 0.0
        )
        del entry["confidence_sum"]
        del entry["confidence_n"]

    return totals


def shannon_index(entries: dict[str, dict[str, Any]]) -> float:
    """Shannon diversity over the aggregated taxa.

    Duplicated deliberately rather than imported from Tanay's analytics module:
    the Time Machine must produce a diversity delta even if analytics is not
    wired up yet. Tanay's CBI remains the authoritative index.
    """
    total = sum(entry["read_count"] for entry in entries.values())
    if total <= 0:
        return 0.0
    accumulator = 0.0
    for entry in entries.values():
        proportion = entry["read_count"] / total
        if proportion > 0:
            accumulator -= proportion * math.log(proportion)
    return round(accumulator, 4)


def compare(
    before_rows: list[dict[str, str]],
    after_rows: list[dict[str, str]],
    *,
    site_id: str,
    rank: str = "species",
    from_sample: str = "",
    to_sample: str = "",
    from_timestamp: str = "",
    to_timestamp: str = "",
    noise_threshold: float = DEFAULT_NOISE_THRESHOLD,
) -> dict[str, Any]:
    """Diff two rounds of sampling at one site."""
    before = aggregate(before_rows, rank=rank)
    after = aggregate(after_rows, rank=rank)

    before_names = set(before)
    after_names = set(after)

    appeared = [
        _detection_entry(after[name], direction="appeared")
        for name in sorted(after_names - before_names)
    ]
    disappeared = [
        _detection_entry(before[name], direction="disappeared")
        for name in sorted(before_names - after_names)
    ]

    changed: list[dict[str, Any]] = []
    stable: list[dict[str, Any]] = []
    for name in sorted(before_names & after_names):
        entry = _change_entry(before[name], after[name])
        if abs(entry["rel_abundance_change"]) >= noise_threshold:
            changed.append(entry)
        else:
            stable.append(entry)

    changed.sort(key=lambda e: abs(e["rel_abundance_change"]), reverse=True)

    before_shannon = shannon_index(before)
    after_shannon = shannon_index(after)

    return {
        "site_id": site_id,
        "rank": rank,
        "from_sample": from_sample,
        "to_sample": to_sample,
        "from_timestamp": from_timestamp,
        "to_timestamp": to_timestamp,
        "appeared": appeared,
        "disappeared": disappeared,
        "changed": changed,
        "stable": stable,
        "summary": {
            "appeared_count": len(appeared),
            "disappeared_count": len(disappeared),
            "changed_count": len(changed),
            "stable_count": len(stable),
            "richness_before": len(before_names),
            "richness_after": len(after_names),
            "richness_delta": len(after_names) - len(before_names),
            "shannon_before": before_shannon,
            "shannon_after": after_shannon,
            "shannon_delta": round(after_shannon - before_shannon, 4),
            "turnover": _turnover(before_names, after_names),
            "noise_threshold": noise_threshold,
        },
    }


def _detection_entry(entry: dict[str, Any], *, direction: str) -> dict[str, Any]:
    return {
        "name": entry["name"],
        "taxon_id": entry["taxon_id"],
        "rank": entry["rank"],
        "direction": direction,
        "read_count": entry["read_count"],
        "rel_abundance": entry["rel_abundance"],
        "mean_confidence": entry["mean_confidence"],
        "asv_count": entry["asv_count"],
    }


def _change_entry(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_abundance = before["rel_abundance"]
    after_abundance = after["rel_abundance"]
    change = (
        (after_abundance - before_abundance) / before_abundance
        if before_abundance > 0
        else 0.0
    )
    return {
        "name": after["name"],
        "taxon_id": after["taxon_id"] or before["taxon_id"],
        "rank": after["rank"],
        "direction": "increased" if change > 0 else "decreased" if change < 0 else "flat",
        "read_count_before": before["read_count"],
        "read_count_after": after["read_count"],
        "rel_abundance_before": before_abundance,
        "rel_abundance_after": after_abundance,
        "rel_abundance_change": round(change, 4),
        "log2_fold_change": round(
            math.log2((after_abundance + _PSEUDOCOUNT) / (before_abundance + _PSEUDOCOUNT)),
            4,
        ),
        "mean_confidence": after["mean_confidence"],
    }


def _turnover(before: set[str], after: set[str]) -> float:
    """Jaccard-based turnover: 0.0 = identical communities, 1.0 = no overlap."""
    union = before | after
    if not union:
        return 0.0
    return round(1 - len(before & after) / len(union), 4)


def compare_files(
    before_path: Path,
    after_path: Path,
    *,
    site_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return compare(
        load_taxonomy(before_path),
        load_taxonomy(after_path),
        site_id=site_id,
        **kwargs,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.time_machine",
        description="Diff two normalized taxonomy CSVs from the same site.",
    )
    parser.add_argument("before", type=Path, help="earlier taxonomy_normalized.csv")
    parser.add_argument("after", type=Path, help="later taxonomy_normalized.csv")
    parser.add_argument("--site", required=True, help="site id, e.g. GOA-MANDOVI")
    parser.add_argument("--rank", default="species", choices=RANKS)
    parser.add_argument("--from-sample", default="")
    parser.add_argument("--to-sample", default="")
    parser.add_argument("--from-timestamp", default="")
    parser.add_argument("--to-timestamp", default="")
    parser.add_argument("--noise-threshold", type=float, default=DEFAULT_NOISE_THRESHOLD)
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args(argv)

    diff = compare_files(
        args.before,
        args.after,
        site_id=args.site,
        rank=args.rank,
        from_sample=args.from_sample,
        to_sample=args.to_sample,
        from_timestamp=args.from_timestamp,
        to_timestamp=args.to_timestamp,
        noise_threshold=args.noise_threshold,
    )

    rendered = json.dumps(diff, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        summary = diff["summary"]
        print(
            f"{args.site}: +{summary['appeared_count']} "
            f"-{summary['disappeared_count']} "
            f"~{summary['changed_count']} "
            f"(turnover {summary['turnover']}) -> {args.output}"
        )
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
