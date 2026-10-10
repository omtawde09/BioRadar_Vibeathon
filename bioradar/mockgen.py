"""Generate realistic mock data so the rest of the team can build before a real run.

The pipeline takes tens of minutes and needs Docker and an 11 GB image. Nobody
else on the team should be blocked on that. This module produces data that is
*contract-identical* to real pipeline output -- same columns, same value ranges,
same awkward edge cases (genus-only assignments, human contamination, empty
taxids) -- for as many sites and sampling rounds as you ask for.

Output is deterministic for a given seed, so CI can assert on it and two team
members generating "the same" mock data actually get the same bytes.

    python -m bioradar.mockgen -o mock/ --rounds 3

Produces:
    mock/samples.csv               sites x rounds, with coordinates  (Parth, Ishwar)
    mock/taxonomy_normalized.csv   every detection, frozen contract   (Anshika, Tanay)
    mock/sample_summary.csv        per-sample totals                  (Tanay, Ishwar)
    mock/alerts.example.json       shape of Anshika's output          (Anshika, Ishwar)
    mock/by_sample/<id>.csv        one file per sample                (Time Machine)

Caveat on taxon_id: only the taxids marked `taxid_verified=yes` in
data/species_pool.csv came out of real pipeline output. The rest are blank,
because inventing plausible-looking NCBI taxids would silently break every join
against Jimeet's reference tables. Filling them in is Jimeet's deliverable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from bioradar.contract import (
    RANKS,
    SAMPLE_SUMMARY_COLUMNS,
    TAXONOMY_COLUMNS,
    UNASSIGNED,
)
from bioradar.normalize import write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITES = REPO_ROOT / "data" / "sites.csv"
DEFAULT_SPECIES = REPO_ROOT / "data" / "species_pool.csv"

# Read-count bands, chosen to match the magnitudes in the real test dataset
# (a few hundred to a couple of thousand reads per ASV per sample).
ABUNDANCE_BANDS: dict[str, tuple[int, int]] = {
    "high": (400, 1400),
    "medium": (120, 500),
    "low": (20, 140),
    "trace": (1, 12),
}

# Sites where an invasive is established and expanding. The Time Machine demo
# depends on this: something has to actually change between rounds.
INVADED_SITES: dict[str, str] = {
    "GOA-MANDOVI": "Gambusia holbrooki",
    "KER-VEMBANAD": "Oreochromis mossambicus",
    "AP-KOLLERU": "Pterygoplichthys pardalis",
    "WB-HOOGHLY": "Clarias gariepinus",
    "MH-THANE": "Gambusia holbrooki",
}

# Sites with poor reference coverage produce more unassigned reads -- the honest
# reality of Indian eDNA and a point worth making to judges.
REFERENCE_GAP_SITES = {"AN-PORTBLAIR", "LD-KAVARATTI", "GJ-KUTCH", "TN-MANNAR"}


def load_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _asv_id(*parts: str) -> str:
    """Stable md5 in the same shape DADA2 emits, so ids look real and repeat."""
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


def _confidence(rng: random.Random, rank: str, is_gap_site: bool) -> float:
    """Species calls are confident; genus-only calls sit in the grey zone.

    The 0.70-0.85 band is deliberately populated -- that is exactly the range
    Anshika's AI Second Opinion is specified to trigger on, so the mock data
    exercises her feature instead of leaving it untested.
    """
    if rank == "genus":
        return round(rng.uniform(0.62, 0.86), 6)
    if is_gap_site:
        return round(rng.uniform(0.71, 0.94), 6)
    return round(rng.uniform(0.88, 0.999), 6)


def build_community(
    site: dict[str, str],
    species_pool: list[dict[str, str]],
    round_index: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Pick the taxa present at one site in one round, with read counts.

    Composition is stable across rounds for a site (it is the same water body),
    with one invasive trending upward where INVADED_SITES says so, plus a little
    per-round jitter so nothing looks synthetic.
    """
    site_id = site["site_id"]
    is_gap_site = site_id in REFERENCE_GAP_SITES

    # Deterministic per-site membership: same site always has the same community.
    site_rng = random.Random(f"community:{site_id}")
    natives = [s for s in species_pool if s["india_status"] in {"native", "migratory"}]
    others = [s for s in species_pool if s["india_status"] not in {"native", "migratory"}]

    members = site_rng.sample(natives, k=min(len(natives), site_rng.randint(4, 7)))
    members += site_rng.sample(others, k=min(len(others), site_rng.randint(1, 3)))

    invasive_name = INVADED_SITES.get(site_id)
    if invasive_name:
        planted = next(
            (s for s in species_pool if s["scientific_name"] == invasive_name), None
        )
        if planted and planted not in members:
            members.append(planted)

    # Human contamination shows up in roughly a third of real samples.
    human = next((s for s in species_pool if s["scientific_name"] == "Homo sapiens"), None)
    if human and rng.random() < 0.35 and human not in members:
        members.append(human)

    detections: list[dict[str, Any]] = []
    for entry in members:
        low, high = ABUNDANCE_BANDS.get(entry["typical_abundance"], (50, 200))
        reads = rng.randint(low, high)

        if entry["scientific_name"] == invasive_name:
            # Establishing invasive: roughly 60% more reads each round.
            reads = int(reads * (1.6**round_index))

        rank = "species" if entry.get("species") else "genus"
        detections.append(
            {
                "entry": entry,
                "reads": reads,
                "rank": rank,
                "confidence": _confidence(rng, rank, is_gap_site),
            }
        )

    # Unassigned ASVs: the reference-gap story, worse at under-sequenced sites.
    unassigned_count = rng.randint(3, 6) if is_gap_site else rng.randint(1, 3)
    for index in range(unassigned_count):
        detections.append(
            {
                "entry": None,
                "reads": rng.randint(15, 220 if is_gap_site else 90),
                "rank": UNASSIGNED,
                "confidence": round(rng.uniform(0.10, 0.55), 6),
                "index": index,
            }
        )

    return detections


def _lineage_string(entry: dict[str, str]) -> str:
    """Rebuild the semicolon lineage the pipeline would have emitted."""
    prefixes = {
        "kingdom": "k",
        "phylum": "p",
        "class": "c",
        "order": "o",
        "family": "f",
        "genus": "g",
        "species": "s",
    }
    segments = []
    taxid = entry.get("taxon_id", "")
    for rank in RANKS:
        value = entry.get(rank, "")
        if not value:
            continue
        segment = f"{prefixes[rank]}__{value}"
        # Only the deepest rank carries the verified taxid we actually have.
        if taxid and rank == _deepest_rank(entry):
            segment = f"{segment}_{taxid}"
        segments.append(segment)
    return ";".join(segments)


def _deepest_rank(entry: dict[str, str]) -> str:
    deepest = ""
    for rank in RANKS:
        if entry.get(rank):
            deepest = rank
    return deepest


def generate(
    sites: list[dict[str, str]],
    species_pool: list[dict[str, str]],
    *,
    rounds: int = 3,
    start_date: date | None = None,
    interval_days: int = 45,
    seed: int = 2026,
) -> dict[str, list[dict[str, Any]]]:
    """Produce samples, detections and per-sample summaries for every site/round."""
    start_date = start_date or date(2026, 1, 15)

    samples: list[dict[str, Any]] = []
    detections: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for site in sites:
        site_id = site["site_id"]
        for round_index in range(rounds):
            collected = start_date + timedelta(days=interval_days * round_index)
            sample_id = f"BR-{collected.year}-{site_id}-R{round_index + 1:02d}"
            rng = random.Random(f"{seed}:{sample_id}")

            samples.append(
                {
                    "sample_id": sample_id,
                    "site_id": site_id,
                    "site_name": site["site_name"],
                    "state": site["state"],
                    "waterbody": site["waterbody"],
                    "waterbody_type": site["waterbody_type"],
                    "latitude": site["latitude"],
                    "longitude": site["longitude"],
                    "protected_status": site["protected_status"],
                    "round": round_index + 1,
                    "collected_at": collected.isoformat(),
                    "collector": "BioRadar field team",
                    "marker": "12S",
                    "primer_set": "teleo",
                }
            )

            community = build_community(site, species_pool, round_index, rng)
            total_reads = sum(item["reads"] for item in community)

            species_seen: set[str] = set()
            genera_seen: set[str] = set()
            unassigned_reads = 0

            for item in community:
                entry = item["entry"]
                reads = item["reads"]

                if entry is None:
                    unassigned_reads += reads
                    record = {
                        "sample_id": sample_id,
                        "asv_id": _asv_id(sample_id, "unassigned", str(item["index"])),
                        "taxon_id": "",
                        "scientific_name": "",
                        "rank": UNASSIGNED,
                        **{rank: "" for rank in RANKS},
                        "confidence": item["confidence"],
                        "read_count": reads,
                        "rel_abundance": round(reads / total_reads, 6),
                        "classification_method": "sklearn",
                        "lineage_raw": "Unassigned",
                    }
                else:
                    deepest = _deepest_rank(entry)
                    if entry.get("species"):
                        species_seen.add(entry["species"])
                    if entry.get("genus"):
                        genera_seen.add(entry["genus"])
                    record = {
                        "sample_id": sample_id,
                        "asv_id": _asv_id(sample_id, entry["scientific_name"]),
                        "taxon_id": entry.get("taxon_id", ""),
                        "scientific_name": entry.get(deepest, ""),
                        "rank": deepest,
                        **{rank: entry.get(rank, "") for rank in RANKS},
                        "confidence": item["confidence"],
                        "read_count": reads,
                        "rel_abundance": round(reads / total_reads, 6),
                        "classification_method": "sklearn",
                        "lineage_raw": _lineage_string(entry),
                    }
                detections.append(record)

            summaries.append(
                {
                    "sample_id": sample_id,
                    "total_reads": total_reads,
                    "asv_count": len(community),
                    "species_count": len(species_seen),
                    "genus_count": len(genera_seen),
                    "unassigned_reads": unassigned_reads,
                    "unassigned_fraction": round(unassigned_reads / total_reads, 6)
                    if total_reads
                    else 0.0,
                }
            )

    return {"samples": samples, "detections": detections, "summaries": summaries}


def build_alerts_example(
    detections: list[dict[str, Any]], species_pool: list[dict[str, str]]
) -> dict[str, Any]:
    """A worked example of Anshika's alerts.json, for one invaded sample.

    This is not the flagging engine -- it is the *shape* of its output, so Tanay
    and Ishwar can build against something concrete on day one.
    """
    invasive_names = {
        s["scientific_name"] for s in species_pool if s["india_status"] == "invasive"
    }
    target_sample = next(
        (
            d["sample_id"]
            for d in detections
            if d["scientific_name"] in invasive_names and d["rank"] == "species"
        ),
        detections[0]["sample_id"],
    )
    rows = [d for d in detections if d["sample_id"] == target_sample]

    alerts = []
    for row in rows:
        name = row["scientific_name"]
        confidence = float(row["confidence"])

        if name in invasive_names:
            alerts.append(
                {
                    "taxon": name,
                    "taxon_id": row["taxon_id"],
                    "asv_id": row["asv_id"],
                    "alert_type": "invasive",
                    "severity": "high" if confidence >= 0.9 else "medium",
                    "confidence": confidence,
                    "read_count": row["read_count"],
                    "message": f"Invasive species detected: {name}",
                    "needs_second_opinion": False,
                }
            )
        elif row["rank"] == "genus" and 0.70 <= confidence <= 0.85:
            alerts.append(
                {
                    "taxon": row["genus"],
                    "taxon_id": row["taxon_id"],
                    "asv_id": row["asv_id"],
                    "alert_type": "low_confidence",
                    "severity": "low",
                    "confidence": confidence,
                    "read_count": row["read_count"],
                    "message": (
                        f"Genus-level call only ({row['genus']}); "
                        "confidence in AI second-opinion band"
                    ),
                    "needs_second_opinion": True,
                }
            )
        elif row["rank"] == UNASSIGNED:
            alerts.append(
                {
                    "taxon": None,
                    "taxon_id": "",
                    "asv_id": row["asv_id"],
                    "alert_type": "reference_gap",
                    "severity": "low",
                    "confidence": confidence,
                    "read_count": row["read_count"],
                    "message": "ASV has no reference match; candidate for novel taxon",
                    "needs_second_opinion": True,
                }
            )

    severities = [a["severity"] for a in alerts]
    return {
        "schema_version": "1.0",
        "sample_id": target_sample,
        "generated_at": "2026-01-15T09:30:00Z",
        "generator": "flagging_engine (EXAMPLE OUTPUT -- shape only)",
        "alerts": alerts,
        "summary": {
            "total_alerts": len(alerts),
            "high": severities.count("high"),
            "medium": severities.count("medium"),
            "low": severities.count("low"),
            "invasive_count": sum(1 for a in alerts if a["alert_type"] == "invasive"),
            "needs_second_opinion": sum(1 for a in alerts if a["needs_second_opinion"]),
        },
    }


SAMPLE_COLUMNS = (
    "sample_id",
    "site_id",
    "site_name",
    "state",
    "waterbody",
    "waterbody_type",
    "latitude",
    "longitude",
    "protected_status",
    "round",
    "collected_at",
    "collector",
    "marker",
    "primer_set",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.mockgen",
        description="Generate contract-identical mock data for the BioRadar team.",
    )
    parser.add_argument("-o", "--output", type=Path, default=Path("mock"))
    parser.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    parser.add_argument("--species", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--per-sample",
        action="store_true",
        default=True,
        help="also write one CSV per sample (used by the Time Machine)",
    )
    args = parser.parse_args(argv)

    sites = load_csv(args.sites)
    species_pool = load_csv(args.species)
    if not sites or not species_pool:
        print("sites.csv or species_pool.csv is empty", file=sys.stderr)
        return 1

    data = generate(sites, species_pool, rounds=args.rounds, seed=args.seed)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)

    write_csv(output / "samples.csv", data["samples"], SAMPLE_COLUMNS)
    write_csv(output / "taxonomy_normalized.csv", data["detections"], TAXONOMY_COLUMNS)
    write_csv(output / "sample_summary.csv", data["summaries"], SAMPLE_SUMMARY_COLUMNS)

    alerts = build_alerts_example(data["detections"], species_pool)
    (output / "alerts.example.json").write_text(
        json.dumps(alerts, indent=2), encoding="utf-8"
    )

    if args.per_sample:
        per_sample_dir = output / "by_sample"
        per_sample_dir.mkdir(exist_ok=True)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in data["detections"]:
            grouped.setdefault(str(row["sample_id"]), []).append(row)
        for sample_id, rows in grouped.items():
            write_csv(per_sample_dir / f"{sample_id}.csv", rows, TAXONOMY_COLUMNS)

    print(f"sites:      {len(sites)}")
    print(f"samples:    {len(data['samples'])} ({args.rounds} rounds each)")
    print(f"detections: {len(data['detections'])}")
    print(f"written to: {output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
