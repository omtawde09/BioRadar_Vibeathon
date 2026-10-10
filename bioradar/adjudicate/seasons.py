"""Same-site seasonal comparison.

Samples are grouped by location. A collection month maps to a season by the rule in
thresholds.json (`season_months`). For each location with both seasons we report,
per species, whether it was detected in summer, in winter, or both - and the counts.

"Not detected" is NEVER written as "absent": eDNA misses animals at low density, and
a few replicate bottles cannot prove an animal is not there.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from bioradar.adjudicate.guard import parse_date
from bioradar.adjudicate.thresholds import Thresholds, load

NOT_ABSENT = ("'Not detected' means the DNA was not seen in these bottles. It does not prove "
              "the animal is absent.")


def season_of(collection_date: str, t: Thresholds) -> Optional[str]:
    parsed = parse_date(collection_date)
    # A year alone ("2019") says nothing about the season - never guess January.
    if not parsed or parsed[1] == "year":
        return None
    month = parsed[0].month
    for name, months in t.season_months.items():
        if month in months:
            return name
    return None


def compare(results: List[Dict[str, Any]], t: Optional[Thresholds] = None) -> Dict[str, Any]:
    """results: adjudicated samples whose metadata has `location` and `collection_date`."""
    t = t or load()
    sites: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for r in results:
        meta = r.get("metadata", {})
        if meta.get("role") == "mixed":
            continue  # mock communities are controls, not field samples
        season = season_of(meta.get("collection_date", ""), t)
        if not season or not meta.get("location"):
            continue
        sites.setdefault(meta["location"], {}).setdefault(season, []).append(r)

    out_sites = []
    for location, by_season in sorted(sites.items()):
        if "summer" not in by_season or "winter" not in by_season:
            continue
        seasons: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for season, samples in by_season.items():
            table: Dict[str, Dict[str, Any]] = {}
            for s in samples:
                for row in s["species"]:
                    if row["kind"] != "species" or row["status"] != "detected":
                        continue
                    slot = table.setdefault(row["species"], {"reads": 0, "replicates": 0})
                    slot["reads"] += row["reads"]
                    slot["replicates"] += 1
            seasons[season] = table
        summer, winter = seasons["summer"], seasons["winter"]
        species_rows = []
        for name in sorted(set(summer) | set(winter),
                           key=lambda n: -(summer.get(n, {}).get("reads", 0)
                                           + winter.get(n, {}).get("reads", 0))):
            in_s, in_w = name in summer, name in winter
            species_rows.append({
                "species": name,
                "summer_reads": summer.get(name, {}).get("reads", 0),
                "winter_reads": winter.get(name, {}).get("reads", 0),
                "summer_replicates": summer.get(name, {}).get("replicates", 0),
                "winter_replicates": winter.get(name, {}).get("replicates", 0),
                "status": "both" if in_s and in_w else ("summer_only" if in_s else "winter_only"),
            })
        def sample_info(season: str) -> Dict[str, Any]:
            ss = by_season[season]
            return {"samples": len(ss),
                    "dates": sorted({s["metadata"].get("collection_date", "") for s in ss}),
                    "sample_ids": [s["sample_id"] for s in ss],
                    "verdicts": [s["verdict"] for s in ss],
                    "species_detected": len(seasons[season])}
        meta0 = by_season["summer"][0]["metadata"]
        out_sites.append({
            "location": location,
            "latitude": meta0.get("latitude"), "longitude": meta0.get("longitude"),
            "coordinate_note": meta0.get("coordinate_note", ""),
            "summer": sample_info("summer"), "winter": sample_info("winter"),
            "counts": {
                "both": sum(1 for r in species_rows if r["status"] == "both"),
                "summer_only": sum(1 for r in species_rows if r["status"] == "summer_only"),
                "winter_only": sum(1 for r in species_rows if r["status"] == "winter_only"),
            },
            "species": species_rows,
        })
    return {"season_rule": t.rationale()["season_months"], "not_absent_note": NOT_ABSENT,
            "sites": out_sites}
