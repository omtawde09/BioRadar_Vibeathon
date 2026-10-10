"""Leave-one-species-out test: how often is the relative finder's hypothesis right?

For every species in the reference, its own 12S amplicon is used as the query while the species
itself is hidden from the search - exactly the situation of a real fish that is missing from the
reference. The nearest relatives then vote on genus / family / order / class, and the vote is
compared with that species' true NCBI lineage.

The result (`relatives_calibration.json`) gives, per rank and per similarity bin, how often a
stated rank was correct. The relative finder uses it to decide which rank it may state, and
shows the measured accuracy next to every hypothesis. These are measured hit rates on the
reference, not probabilities for any one read: real reads carry sequencing errors and may come
from lineages the reference does not sample at all.

    python -m bioradar.relatives calibrate
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bioradar.relatives.model import CALIBRATION_FILE, RANKS, RelativeFinder, _bin, _cfg


def run(finder: Optional[RelativeFinder] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    finder = finder or RelativeFinder.load()
    if not finder.species_lineage:
        raise RuntimeError("no lineage: run `python -m bioradar.relatives lineage` first")
    started = time.time()
    first_seq: Dict[str, str] = {}
    for _acc, species, seq in finder.ref.entries:
        if species != "Homo sapiens" and species not in first_seq:
            first_seq[species] = seq
    species_list = sorted(first_seq)[:limit] if limit else sorted(first_seq)
    genus_size: Dict[str, int] = {}
    for sp, lin in finder.species_lineage.items():
        if lin.get("genus"):
            genus_size[lin["genus"]] = genus_size.get(lin["genus"], 0) + 1

    cells: Dict[str, Dict[str, Dict[str, int]]] = {r: {} for r in RANKS}
    overall = {r: {"cases": 0, "stated": 0, "correct": 0} for r in RANKS}
    genus_absent = {"cases": 0, "genus_stated": 0, "genus_stated_wrong": 0}
    for sp in species_list:
        truth = finder.species_lineage.get(sp)
        if not truth:
            continue
        rels = finder.relatives(first_seq[sp], exclude_species=[sp], align_top=0)
        if not rels:
            continue
        by_rank = finder.consensus(rels)
        top_bin = _bin(rels[0]["cosine"])
        alone = genus_size.get(truth.get("genus", ""), 0) <= 1
        if alone:
            genus_absent["cases"] += 1
        for rank in RANKS:
            if not truth.get(rank):
                continue
            overall[rank]["cases"] += 1
            cell = by_rank[rank]
            if cell["support"] < _cfg("min_support") or cell["taxon"].startswith("("):
                continue
            ok = cell["taxon"] == truth[rank]
            overall[rank]["stated"] += 1
            overall[rank]["correct"] += int(ok)
            slot = cells[rank].setdefault(top_bin, {"n": 0, "correct": 0})
            slot["n"] += 1
            slot["correct"] += int(ok)
            if rank == "genus" and alone:
                genus_absent["genus_stated"] += 1
                genus_absent["genus_stated_wrong"] += int(not ok)

    accuracy = {r: {b: dict(c, accuracy=round(c["correct"] / c["n"], 3))
                    for b, c in sorted(cells[r].items())} for r in RANKS}
    summary = {r: dict(o, accuracy_when_stated=round(o["correct"] / o["stated"], 3) if o["stated"] else None,
                       stated_fraction=round(o["stated"] / o["cases"], 3) if o["cases"] else None)
               for r, o in overall.items()}
    doc = {
        "method": "leave-one-species-out on the reference: each species' amplicon queried with that "
                  "species hidden; a rank counts as stated when relative-weight support >= {}".format(
                      _cfg("min_support")),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reference": finder.ref.version,
        "species_tested": len(species_list),
        "seconds": round(time.time() - started, 1),
        "accuracy": accuracy,
        "summary": summary,
        "species_whose_genus_has_no_other_reference_species": genus_absent,
        "limits": "Queries are clean reference amplicons, not reads with sequencing errors. Lineages "
                  "absent from the reference are only represented by species whose genus has a single "
                  "reference member. Use as a measured hit rate, not a probability for one read.",
    }
    CALIBRATION_FILE.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc
