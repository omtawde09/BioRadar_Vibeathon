"""Turn normalized pipeline output into a readable biodiversity report.

The pipeline's own PDF is a QC report -- read counts, quality profiles, denoising
statistics. Useful for a bioinformatician, useless for anyone deciding what to do
about a site. This produces the other half: what was found, where, how confident
we are, and how much of the sample we could not identify at all.

That last number is deliberately prominent. An eDNA report that lists only the
species it recognised, without saying what fraction of the reads it could not
place, overstates its own completeness. The unassigned fraction is the honest
measure of reference coverage for the region being sampled.

    python -m bioradar.report \\
        --taxonomy runs/<id>/final_results/taxonomy_normalized.csv \\
        --summary  runs/<id>/final_results/sample_summary.csv \\
        --samples  data/india_lakshadweep/samples.csv \\
        -o reports/lakshadweep.md
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bioradar.contract import RANKS, UNASSIGNED


def load_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def shannon(counts: list[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    return round(
        -sum((c / total) * math.log(c / total) for c in counts if c > 0), 4
    )


def simpson(counts: list[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    return round(1 - sum((c / total) ** 2 for c in counts), 4)


def jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return round(len(a & b) / len(union), 3) if union else 0.0


def analyse(
    detections: list[dict[str, str]],
    samples: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Aggregate detections into everything the report needs."""
    sample_meta = {s["sample_id"]: s for s in (samples or [])}

    by_sample: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in detections:
        by_sample[row["sample_id"]].append(row)

    # Site is taken from sample metadata when available; otherwise each sample
    # is treated as its own site so the report still works standalone.
    site_of = {
        sid: sample_meta.get(sid, {}).get("site_id", sid) for sid in by_sample
    }

    species_index: dict[str, dict[str, Any]] = {}
    site_species: dict[str, set[str]] = defaultdict(set)
    phyla = Counter()
    rank_counts = Counter()

    for row in detections:
        rank_counts[row["rank"]] += 1
        reads = int(float(row["read_count"] or 0))
        site = site_of[row["sample_id"]]

        if row["phylum"]:
            phyla[row["phylum"]] += reads

        name = row["species"] or row["genus"]
        if not name or row["rank"] == UNASSIGNED:
            continue
        # NCBI carries unidentified taxa as species records named "<Taxon> sp."
        # (e.g. "Annelida sp.", taxid 2813593). The classifier legitimately
        # assigns to them, but counting them as species overstates resolution --
        # in this dataset they carried 94% of reads. Flagged, not dropped.
        is_placeholder = " sp." in name or name.endswith(" sp.")

        entry = species_index.setdefault(
            name,
            {
                "name": name,
                "rank": "species" if row["species"] else "genus",
                "taxon_id": row["taxon_id"],
                "phylum": row["phylum"],
                "class": row["class"],
                "order": row["order"],
                "family": row["family"],
                "reads": 0,
                "sites": set(),
                "samples": set(),
                "max_confidence": 0.0,
                "asvs": set(),
                "placeholder": is_placeholder,
            },
        )
        entry["reads"] += reads
        entry["sites"].add(site)
        entry["samples"].add(row["sample_id"])
        entry["asvs"].add(row["asv_id"])
        entry["max_confidence"] = max(
            entry["max_confidence"], float(row["confidence"] or 0)
        )
        site_species[site].add(name)

    per_sample: list[dict[str, Any]] = []
    for sample_id, rows in sorted(by_sample.items()):
        reads = [int(float(r["read_count"] or 0)) for r in rows]
        assigned = [r for r in rows if r["rank"] != UNASSIGNED]
        unassigned_reads = sum(
            int(float(r["read_count"] or 0))
            for r in rows
            if r["rank"] == UNASSIGNED
        )
        total = sum(reads)
        meta = sample_meta.get(sample_id, {})
        per_sample.append(
            {
                "sample_id": sample_id,
                "site_id": site_of[sample_id],
                "latitude": meta.get("latitude", ""),
                "longitude": meta.get("longitude", ""),
                "collected_at": meta.get("collected_at", ""),
                "total_reads": total,
                "asv_count": len(rows),
                "species_count": len({r["species"] for r in assigned if r["species"]}),
                "genus_count": len({r["genus"] for r in assigned if r["genus"]}),
                "unassigned_reads": unassigned_reads,
                "unassigned_pct": round(100 * unassigned_reads / total, 1)
                if total
                else 0.0,
                "shannon": shannon(reads),
                "simpson": simpson(reads),
            }
        )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detections": len(detections),
        "samples": per_sample,
        "species": sorted(
            species_index.values(), key=lambda e: -e["reads"]
        ),
        "site_species": {k: sorted(v) for k, v in site_species.items()},
        "phyla": phyla.most_common(),
        "rank_counts": rank_counts.most_common(),
    }
    try:
        from bioradar.ai import nlg_insights
        out["ai_briefing"] = nlg_insights.generate_executive_briefing(out)
    except Exception:
        pass
    return out



def render_markdown(result: dict[str, Any], title: str, notes: dict[str, str]) -> str:
    lines: list[str] = []
    add = lines.append

    species = result["species"]
    species_level = [s for s in species if s["rank"] == "species"]
    genus_level = [s for s in species if s["rank"] == "genus"]
    named = [s for s in species_level if not s.get("placeholder")]
    placeholders = [s for s in species_level if s.get("placeholder")]
    total_reads = sum(s["total_reads"] for s in result["samples"])
    total_unassigned = sum(s["unassigned_reads"] for s in result["samples"])

    add(f"# {title}")
    add("")
    add(f"*Generated {result['generated_at']} by BioRadar Layer 1*")
    add("")
    for key, value in notes.items():
        add(f"- **{key}:** {value}")
    add("")

    add("## Summary")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    add(f"| Samples | {len(result['samples'])} |")
    add(f"| Sites | {len(result['site_species'])} |")
    add(f"| Total reads | {total_reads:,} |")
    add(f"| Detections (ASV x sample) | {result['detections']:,} |")
    add(f"| **Named species (binomials)** | **{len(named)}** |")
    add(f"| Unidentified '<taxon> sp.' records | {len(placeholders)} |")
    add(f"| Additional genus-level taxa | {len(genus_level)} |")
    add(f"| Phyla represented | {len(result['phyla'])} |")
    pct = 100 * total_unassigned / total_reads if total_reads else 0
    add(f"| Reads with no reference match | {total_unassigned:,} ({pct:.1f}%) |")
    add("")

    add("## Per-sample results")
    add("")
    add("| Sample | Site | Lat | Lon | Reads | ASVs | Species | Shannon | Unassigned |")
    add("|---|---|---|---|---|---|---|---|---|")
    for s in result["samples"]:
        add(
            f"| {s['sample_id']} | {s['site_id']} | {s['latitude']} | {s['longitude']} "
            f"| {s['total_reads']:,} | {s['asv_count']} | {s['species_count']} "
            f"| {s['shannon']} | {s['unassigned_pct']}% |"
        )
    add("")

    add("## Composition by phylum")
    add("")
    add("| Phylum | Reads | Share |")
    add("|---|---|---|")
    phylum_total = sum(count for _, count in result["phyla"]) or 1
    for name, count in result["phyla"]:
        add(f"| {name} | {count:,} | {100 * count / phylum_total:.1f}% |")
    add("")

    add("## Species inventory")
    add("")
    if species_level:
        add("| Species | Phylum | Family | Taxid | Reads | Sites | Max conf. |")
        add("|---|---|---|---|---|---|---|")
        for entry in species_level:
            mark = " †" if entry.get("placeholder") else ""
            add(
                f"| *{entry['name']}*{mark} | {entry['phylum']} | {entry['family']} "
                f"| {entry['taxon_id']} | {entry['reads']:,} "
                f"| {len(entry['sites'])} | {entry['max_confidence']:.3f} |"
            )
    else:
        add("_No species-level assignments._")
    add("")
    if placeholders:
        add(
            "† unidentified NCBI `<taxon> sp.` record, not a named species -- "
            "the classifier resolved no further than that group."
        )
        add("")

    if genus_level:
        add("### Genus-level only")
        add("")
        add("Taxa the classifier could place to genus but not species.")
        add("")
        add("| Genus | Phylum | Reads | Sites | Max conf. |")
        add("|---|---|---|---|---|")
        for entry in genus_level[:40]:
            add(
                f"| *{entry['name']}* | {entry['phylum']} | {entry['reads']:,} "
                f"| {len(entry['sites'])} | {entry['max_confidence']:.3f} |"
            )
        add("")

    sites = sorted(result["site_species"])
    if len(sites) > 1:
        add("## Site comparison")
        add("")
        add("Jaccard similarity of taxon lists (1.0 = identical, 0.0 = nothing shared).")
        add("")
        add("| | " + " | ".join(sites) + " |")
        add("|---" * (len(sites) + 1) + "|")
        for a in sites:
            cells = [
                str(jaccard(set(result["site_species"][a]), set(result["site_species"][b])))
                for b in sites
            ]
            add(f"| **{a}** | " + " | ".join(cells) + " |")
        add("")
        add("| Site | Taxa | Unique to site |")
        add("|---|---|---|")
        for site in sites:
            own = set(result["site_species"][site])
            others: set[str] = set()
            for other in sites:
                if other != site:
                    others |= set(result["site_species"][other])
            add(f"| {site} | {len(own)} | {len(own - others)} |")
        add("")

    add("## Reference coverage")
    add("")
    add("| Assignment depth | Detections |")
    add("|---|---|")
    for rank, count in result["rank_counts"]:
        label = "unassigned" if rank == UNASSIGNED else rank
        add(f"| {label} | {count:,} |")
    add("")
    shallow = sum(c for r, c in result["rank_counts"] if r in {"kingdom", "phylum"})
    deep = sum(c for r, c in result["rank_counts"] if r in {"genus", "species"})
    total_detections = shallow + deep + sum(
        c for r, c in result["rank_counts"] if r not in
        {"kingdom", "phylum", "genus", "species"}
    )
    shallow_pct = 100 * shallow / total_detections if total_detections else 0
    placeholder_reads = sum(s["reads"] for s in placeholders)
    all_reads = sum(s["reads"] for s in species) or 1

    add(
        f"**{shallow_pct:.0f}% of detections resolved no deeper than phylum**, and "
        f"{100 * placeholder_reads / all_reads:.0f}% of classified reads landed on "
        "unidentified `<taxon> sp.` records rather than named species."
    )
    add("")
    add(
        "This -- not the literal 'Unassigned' count -- is the honest reference-gap "
        "measurement. A naive Bayes classifier assigns *something* to almost every "
        "sequence, so a 0% unassigned rate says nothing about coverage. What matters "
        "is how deep those assignments go. Closing this gap is what an India-curated "
        "reference is for."
    )
    add("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.report",
        description="Generate a biodiversity report from normalized pipeline output.",
    )
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--samples", type=Path, default=None)
    parser.add_argument("--title", default="BioRadar biodiversity report")
    parser.add_argument("--note", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    detections = load_csv(args.taxonomy)
    if not detections:
        print(f"error: {args.taxonomy} has no rows", file=sys.stderr)
        return 1
    samples = load_csv(args.samples) if args.samples else None

    result = analyse(detections, samples)

    notes = {}
    for item in args.note:
        key, _, value = item.partition("=")
        notes[key] = value

    markdown = render_markdown(result, args.title, notes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    if args.json:
        serialisable = json.loads(
            json.dumps(result, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
        )
        args.json.write_text(json.dumps(serialisable, indent=2), encoding="utf-8")

    species_level = sum(1 for s in result["species"] if s["rank"] == "species")
    print(f"samples : {len(result['samples'])}")
    print(f"species : {species_level}")
    print(f"report  : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
