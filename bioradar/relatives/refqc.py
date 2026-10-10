"""Reference quality check: find reference entries whose 12S does not fit their own name.

    python -m bioradar.relatives refqc

An entry is SUSPECT when its nearest other species is near-identical (cosine >= 0.85) but sits in
a different taxonomic ORDER. Two genuinely different orders do not share a near-identical 12S
fragment, so one of the two records is mislabelled or contaminated. Example found on the RefSeq
build of 2026-10-10: NW_028117713.1 "Leuciscus leuciscus" (a carp-like river fish, Cypriniformes)
is 0.915 to Stomias atriventer (a deep-sea dragonfish, Stomiiformes).

Which side is wrong cannot be proven from sequence alone, so the rule is conservative:
* an entry from a genome-scaffold accession (NW_) facing a curated mitogenome (NC_) is
  QUARANTINED: left out of the relative-finder index, with the reason recorded;
* any other conflict is REPORTED only, never silently removed.
The adjudicator's species calls are not changed by this file.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bioradar.adjudicate.reference import REF_DIR

QC_FILE = REF_DIR / "reference_qc.json"
MIN_COSINE = 0.85


def scan(finder=None) -> Dict[str, Any]:
    from bioradar.relatives.model import RelativeFinder
    finder = finder or RelativeFinder.load(apply_qc=False)
    quarantined, reported = [], []
    for acc, species, seq in finder.ref.entries:
        if species == "Homo sapiens":
            continue
        own = finder.species_lineage.get(species, {})
        hits = [h for h in finder.index.nearest_species(seq, top=3) if h[0] != species]
        if not hits or not own.get("order"):
            continue
        other_sp, other_acc, cos = hits[0]
        other = finder.species_lineage.get(other_sp, {})
        if cos < MIN_COSINE or not other.get("order") or other["order"] == own["order"]:
            continue
        item = {"accession": acc, "species": species, "order": own["order"],
                "nearest": other_sp, "nearest_accession": other_acc, "nearest_order": other["order"],
                "cosine": cos,
                "reason": "12S is {:.3f} cosine to {} ({}), a different order from the entry's own "
                          "name ({}): one of the two records is mislabelled or contaminated".format(
                              cos, other_sp, other["order"], own["order"])}
        if acc.startswith("NW_") and other_acc.startswith("NC_"):
            item["action"] = "quarantined: genome-scaffold entry conflicts with a curated mitogenome"
            quarantined.append(item)
        else:
            item["action"] = "reported only"
            reported.append(item)
    doc = {"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "reference": finder.ref.version, "rule": "nearest other species >= {} cosine in a "
           "different order".format(MIN_COSINE),
           "quarantined": quarantined, "reported": reported}
    QC_FILE.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc


def quarantined_accessions(path: Optional[str] = None) -> set:
    p = QC_FILE if path is None else path
    try:
        doc = json.loads(open(p, encoding="utf-8").read())
    except (OSError, ValueError):
        return set()
    return {q["accession"] for q in doc.get("quarantined", [])}
