"""Decide, for one real sample, what is kept, what is dropped and what is unknown.

    kept     a species-level call that clears every threshold
    dropped  failed quality control, or is human, or is unrelated - each with a reason
    unknown  looks like a real fish fragment but cannot be called to one species;
             goes to the review queue with its closest match and a capped confidence

The sample as a whole gets a verdict. If too little is usable, the verdict is
"Retake sample" - the system says so instead of reporting a species list built
from leftovers.

The file name plays no part. The sample id and metadata come from the manifest.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional

from bioradar.adjudicate import quality
from bioradar.adjudicate.reference import Reference
from bioradar.adjudicate.seqio import dereplicate
from bioradar.adjudicate.thresholds import Thresholds, load

HUMAN = "Homo sapiens"

# `confidence` below is a heuristic ranking score, not a calibrated probability: nobody
# has measured how often a 0.90 is right. The key keeps its name so the stored results
# and the UI stay compatible; every result carries this type + note so no consumer has
# to guess what the number means.
SCORE_TYPE = "heuristic_identity_x_margin"
SCORE_NOTE = ("Match score = identity-to-reference scaled by the margin over the next-best "
              "species (see adjudicate.confidence). It ranks matches; it is NOT a calibrated "
              "probability that the call is correct. Unknowns are capped and are never confirmed.")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def confidence(identity: float, margin: float, called: bool, t: Thresholds) -> float:
    """How much to trust this match, 0-1.

    identity part: 1.0 at a perfect match, falling 4 points per point of identity
    lost (98.5% -> 0.94, 95% -> 0.80, 90% -> 0.60, 80% -> 0.20).
    margin part: a match only slightly better than a different species is half-trusted.
    Unknowns are capped, and no call ever reaches 1.0.
    """
    ident = _clamp(1.0 - 4.0 * (1.0 - identity))
    margin_part = _clamp(0.5 + margin / 0.06, 0.5, 1.0)
    value = ident * margin_part
    cap = t.confidence_max_known if called else t.unknown_max_confidence
    return round(min(value, cap), 3)


def _complex_name(members: List[str]) -> str:
    """'Takifugu fasciatus / obscurus / oblongus' when they share a genus."""
    genera = {m.split()[0] for m in members}
    if len(genera) == 1:
        return "{} {}".format(next(iter(genera)), " / ".join(m.split()[1] for m in members))
    return " / ".join(members)


def _sid(seq: str) -> str:
    return hashlib.md5(seq.encode()).hexdigest()[:10]


def adjudicate_file(path, sample: Dict[str, Any], ref: Reference,
                    t: Optional[Thresholds] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    t = t or load()
    started = time.time()
    distinct, total_reads, fmt = dereplicate(path, limit)

    dropped: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []
    kept: List[Dict[str, Any]] = []

    def drop(d, code: str, why: str, **extra: Any) -> None:
        dropped.append(dict({"seq_id": _sid(d.seq), "sequence": d.seq, "reads": d.count,
                             "reason_code": code, "reason": why}, **extra))

    for d in distinct:
        mean_q = (d.qual_sum / d.count) if d.qual_sum else None
        verdict = quality.check(d.seq, d.count, mean_q, t)
        if verdict:
            drop(d, *verdict)
            continue

        matches = ref.search(d.seq, t.identity_species)
        if not matches or matches[0].identity < t.identity_floor:
            best = matches[0] if matches else None
            drop(d, "unrelated",
                 "no reference entry above {:.0%} identity (closest: {} at {:.1%}) - not "
                 "recognisable as a fish 12S fragment".format(
                     t.identity_floor, best.species if best else "none",
                     best.identity if best else 0.0))
            continue

        best = matches[0]
        if best.species == HUMAN and best.identity >= t.human_identity:
            drop(d, "human_contamination",
                 "matches the human mitochondrial 12S at {:.1%} identity: human contamination, "
                 "not a fish".format(best.identity), closest_match=HUMAN, identity=best.identity)
            continue

        others = [m for m in matches[1:] if m.species != HUMAN]
        runner = others[0] if others else None
        margin = best.identity - (runner.identity if runner else 0.0)
        base = {"seq_id": _sid(d.seq), "sequence": d.seq, "reads": d.count,
                "closest_match": best.species, "closest_accession": best.accession,
                "identity": best.identity, "score_type": SCORE_TYPE,
                "reference_version": ref.version,
                "runner_up": runner.species if runner else "",
                "runner_up_identity": runner.identity if runner else 0.0}

        if best.identity < t.identity_species:
            base.update(
                kind="novel", status="needs review", candidates=[best.species],
                reason="closest match {} is only {:.1%} identical, under the {:.1%} needed for a "
                       "species call: not in the reference list or too divergent".format(
                           best.species, best.identity, t.identity_species),
                confidence=confidence(best.identity, margin, False, t))
            unknown.append(base)
        elif runner and margin < t.min_species_margin and runner.identity >= t.identity_species:
            group = [best.species] + [m.species for m in others
                                      if best.identity - m.identity < t.min_species_margin
                                      and m.identity >= t.identity_species]
            base.update(
                kind="ambiguous", status="needs review", candidates=sorted(set(group)),
                reason="ambiguous: {} ({:.1%}) and {} ({:.1%}) are within {:g} identity points - "
                       "cannot be called to one species".format(
                           best.species, best.identity, runner.species, runner.identity,
                           round(t.min_species_margin * 100, 2)),
                confidence=confidence(best.identity, margin, False, t))
            unknown.append(base)
        else:
            base.update(species=best.species,
                        confidence=confidence(best.identity, margin, True, t))
            kept.append(base)

    def reads(items: List[Dict[str, Any]]) -> int:
        return sum(i["reads"] for i in items)

    by_reason: Dict[str, Dict[str, int]] = {}
    for item in dropped:
        slot = by_reason.setdefault(item["reason_code"], {"distinct": 0, "reads": 0})
        slot["distinct"] += 1
        slot["reads"] += item["reads"]

    kept_reads, unknown_reads, dropped_reads = reads(kept), reads(unknown), reads(dropped)

    # Species table. Indistinguishable species are shown as one honest 'complex' row
    # (e.g. two pufferfish whose 12S differs by less than the margin), never silently
    # assigned to one name.
    groups: Dict[Any, Dict[str, Any]] = {}
    for item in kept:
        groups.setdefault(("species", item["species"]),
                          {"members": [item["species"]], "items": []})["items"].append(item)
    # Overlapping ambiguity sets are one complex: if A~B and B~C then {A,B,C} is one row.
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ambiguous = [i for i in unknown if i["kind"] == "ambiguous"]
    for item in ambiguous:
        for name in item["candidates"][1:]:
            parent[find(name)] = find(item["candidates"][0])
    members_of: Dict[str, set] = {}
    for item in ambiguous:
        for name in item["candidates"]:
            members_of.setdefault(find(name), set()).add(name)
    for item in ambiguous:
        root = find(item["candidates"][0])
        key = ("complex", root)
        groups.setdefault(key, {"members": sorted(members_of[root]), "items": []})[
            "items"].append(item)
    identified = sum(i["reads"] for g in groups.values() for i in g["items"])
    species_rows = []
    for (kind, _), g in groups.items():
        n = sum(i["reads"] for i in g["items"])
        best_item = max(g["items"], key=lambda i: i["identity"])
        species_rows.append({
            "species": g["members"][0] if kind == "species" else _complex_name(g["members"]),
            "kind": kind,
            "members": g["members"],
            "reads": n,
            "distinct_sequences": len(g["items"]),
            "share": round(n / identified, 4) if identified else 0.0,
            "best_identity": best_item["identity"],
            "confidence": round(sum(i["confidence"] * i["reads"] for i in g["items"]) / n, 3),
            "score_type": SCORE_TYPE,
            "reference_accession": best_item["closest_accession"],
            "status": (("detected" if n >= t.min_detection_reads else "trace")
                       if kind == "species" else "unresolved"),
        })
    species_rows.sort(key=lambda r: -r["reads"])

    usable_reads = kept_reads + unknown_reads
    usable_fraction = usable_reads / total_reads if total_reads else 0.0
    dropped_fraction = dropped_reads / total_reads if total_reads else 0.0
    verdict, why = "Usable", []
    if usable_fraction < t.retake_min_kept_fraction:
        verdict = "Retake sample"
        why.append("only {:.0%} of reads were usable after quality control (minimum {:.0%})".format(
            usable_fraction, t.retake_min_kept_fraction))
    if usable_reads < t.retake_min_kept_reads:
        verdict = "Retake sample"
        why.append("only {:,} usable reads (minimum {:,})".format(
            usable_reads, t.retake_min_kept_reads))
    if verdict == "Usable" and dropped_fraction > t.caution_max_dropped_fraction:
        verdict = "Usable with caution"
        why.append("{:.0%} of reads were dropped (caution above {:.0%}): library quality is "
                   "poor, but enough remains to report".format(
                       dropped_fraction, t.caution_max_dropped_fraction))
    if verdict == "Usable":
        why.append("{:.0%} of reads passed quality control".format(usable_fraction))

    unknown.sort(key=lambda u: -u["reads"])
    dropped.sort(key=lambda d: -d["reads"])
    return {
        "sample_id": sample.get("sample_id"),
        "metadata": sample,
        "input_format": fmt,
        "quality_scores_available": fmt == "fastq",
        "score_type": SCORE_TYPE,
        "score_note": SCORE_NOTE,
        "reads_total": total_reads,
        "distinct_sequences": len(distinct),
        "summary": {
            "kept": {"distinct": len(kept), "reads": kept_reads},
            "dropped": {"distinct": len(dropped), "reads": dropped_reads},
            "unknown": {"distinct": len(unknown), "reads": unknown_reads},
        },
        "drop_reasons": {k: by_reason[k] for k in quality.REASON_ORDER if k in by_reason},
        "verdict": verdict,
        "verdict_reasons": why,
        "species": species_rows,
        "unknown_queue": unknown,
        "dropped": dropped,
        "kept": kept,
        "seconds": round(time.time() - started, 1),
        "reference": {"entries": len(ref.entries), "species": ref.species_count},
    }
