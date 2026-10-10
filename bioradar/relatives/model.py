"""Relative finder: closest reference relatives of an unknown fragment and an identity hypothesis.

For one DNA fragment it answers, in order:

1. DNA sequence     - which reference species are closest (cosine of k-mer embeddings, plus the
                      aligner's identity and coverage for the top hits);
2. Evolutionary     - how far up the NCBI lineage the nearest relatives agree (genus, family,
   history          order, class). The hypothesis is stated at the finest rank whose held-out
                      accuracy at this similarity is high enough (see calibrate.py);
3. Ecology          - optional evidence from what was OBSERVED about the sample or specimen
   and other traits   (habitat and country from sample metadata; karyotype, diet, hormones,
                      genome size only if a user supplies them from a physical specimen).
                      Each candidate's documented traits are compared with the observation.
4. Inferred profile - for traits that were not observed, what the relatives are documented to
                      have: "expected if the hypothesis is right", never a measurement.

The result is always a HYPOTHESIS for expert review, never a confirmed identification.
A fragment of DNA from water does not reveal the animal's diet, karyotype or hormones, so those
factors can only act as evidence when someone measures them on a specimen.

Standard library only; Python 3.8 compatible.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bioradar.adjudicate.reference import REF_DIR, Reference
from bioradar.relatives import lineage as lineage_mod
from bioradar.relatives.kmer import DENSE_DIMS, K, Index, dense

MODEL_VERSION = "1"
CALIBRATION_FILE = REF_DIR / "relatives_calibration.json"
RANKS = ["genus", "family", "order", "class"]  # finest first

CONFIG = {
    "top_relatives": {"value": 10, "why": "Ten distinct species is enough to see whether the "
                      "neighbourhood agrees on a genus or family without being swamped by distant fish."},
    "weight_temperature": {"value": 0.03, "why": "Relative weight = exp((cosine - best cosine) / 0.03): "
                           "a relative 0.03 cosine below the best counts e-times less, so the closest few "
                           "dominate but a near-tie still counts."},
    "min_support": {"value": 0.6, "why": "A rank is only stated when at least 60% of the relatives' "
                    "weight agrees on one taxon at that rank."},
    "min_heldout_accuracy": {"value": 0.8, "why": "A rank is only stated when, in the leave-one-species-out "
                             "test at this similarity, the same rule was right at least 80% of the time."},
    "min_calibration_n": {"value": 20, "why": "A held-out accuracy from fewer than 20 cases is too noisy "
                          "to rely on; the next coarser bin or rank is used instead."},
    "identity_species": {"value": 0.985, "why": "Same species-level identity as the adjudicator; below it "
                         "the closest species is a relative, not an identification."},
}
CONFIDENCE_WORDING = ("Hypothesis for expert review, not an identification. Support is the share of "
                      "relative weight that agrees; held-out accuracy is how often the same rule was right "
                      "when a known species was hidden from the reference.")

UNOBSERVABLE = {
    "karyotype_2n": "chromosomal structure",
    "genome_size_pg": "chromosomal structure (genome size)",
    "diet": "diet",
    "trophic_level": "diet (trophic level)",
    "hormone": "hormones",
}


def _cfg(name: str) -> Any:
    return CONFIG[name]["value"]


def _traits():
    try:
        from bioradar.relatives import traits  # optional channel
        return traits
    except Exception:  # module absent or broken: the channel is reported as unavailable
        return None


def _bin(value: float) -> str:
    edges = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0001]
    for lo, hi in zip(edges, edges[1:]):
        if lo <= value < hi:
            return "{:.2f}-{:.2f}".format(lo, min(hi, 1.0))
    return "0.00-0.50"


class RelativeFinder:
    def __init__(self, ref: Reference, lineage: Dict[str, Dict[str, str]],
                 calibration: Optional[Dict[str, Any]] = None) -> None:
        self.ref = ref
        entries = [e for e in ref.entries if e[1] != "Homo sapiens"]
        self.index = Index.build(entries)
        self.lineage = lineage
        self.calibration = calibration or {}
        self.species_lineage: Dict[str, Dict[str, str]] = {}
        for acc, species, _ in entries:
            row = lineage.get(acc)
            if row and species not in self.species_lineage:
                self.species_lineage[species] = row
        trait_mod = _traits()
        self.trait_table = trait_mod.load_traits() if trait_mod else None

    @classmethod
    def load(cls) -> "RelativeFinder":
        cal = None
        if CALIBRATION_FILE.is_file():
            cal = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        return cls(Reference.load(), lineage_mod.load(), cal)

    # -- 1. DNA sequence --------------------------------------------------------------------

    def relatives(self, seq: str, top: Optional[int] = None, exclude_species: Iterable[str] = (),
                  align_top: int = 3) -> List[Dict[str, Any]]:
        top = top or _cfg("top_relatives")
        hits = self.index.nearest_species(seq, top=top, exclude_species=exclude_species)
        if not hits:
            return []
        best = hits[0][2]
        tau = _cfg("weight_temperature")
        aligned = {}
        if align_top:
            excluded = set(exclude_species)
            for m in self.ref.search(seq, _cfg("identity_species")):
                if m.species not in excluded and m.species not in aligned:
                    aligned[m.species] = m
        out = []
        for rank_no, (species, acc, cos) in enumerate(hits, start=1):
            lin = self.species_lineage.get(species, {})
            m = aligned.get(species) if rank_no <= max(align_top, 0) else None
            out.append({
                "rank": rank_no, "species": species, "accession": acc, "cosine": cos,
                "weight": round(math.exp((cos - best) / tau), 4),
                "identity": m.identity if m else None, "coverage": m.coverage if m else None,
                "genus": lin.get("genus", ""), "family": lin.get("family", ""),
                "order": lin.get("order", ""), "class": lin.get("class", ""),
            })
        return out

    # -- 2. evolutionary history ------------------------------------------------------------

    @staticmethod
    def consensus(rels: List[Dict[str, Any]], weight_key: str = "weight") -> Dict[str, Dict[str, Any]]:
        total = sum(r[weight_key] for r in rels) or 1.0
        out: Dict[str, Dict[str, Any]] = {}
        for rank in RANKS:
            tally: Dict[str, float] = {}
            for r in rels:
                name = r.get(rank) or "(not in NCBI lineage)"
                tally[name] = tally.get(name, 0.0) + r[weight_key]
            name, w = max(tally.items(), key=lambda kv: kv[1])
            out[rank] = {"taxon": name, "support": round(w / total, 3),
                         "alternatives": [{"taxon": n, "support": round(v / total, 3)}
                                          for n, v in sorted(tally.items(), key=lambda kv: -kv[1])[1:4]]}
        return out

    def heldout_accuracy(self, rank: str, top_cosine: float) -> Optional[Dict[str, Any]]:
        table = self.calibration.get("accuracy", {}).get(rank, {})
        cell = table.get(_bin(top_cosine))
        if not cell:
            return None
        return {"value": cell["accuracy"], "n": cell["n"], "cosine_bin": _bin(top_cosine),
                "basis": self.calibration.get("method", "")}

    def state_rank(self, by_rank: Dict[str, Dict[str, Any]], top_cosine: float) -> Dict[str, Any]:
        """Finest rank with enough support AND (when calibrated) enough held-out accuracy."""
        for rank in RANKS:
            cell = by_rank[rank]
            if cell["support"] < _cfg("min_support") or cell["taxon"].startswith("("):
                continue
            acc = self.heldout_accuracy(rank, top_cosine)
            if self.calibration and (acc is None or acc["n"] < _cfg("min_calibration_n")
                                     or acc["value"] < _cfg("min_heldout_accuracy")):
                continue
            return {"rank": rank, "taxon": cell["taxon"], "support": cell["support"],
                    "heldout_accuracy": acc}
        return {"rank": None, "taxon": None, "support": None, "heldout_accuracy": None,
                "note": "relatives do not agree on any rank strongly enough to state one"}

    # -- 3. + 4. ecology / traits -----------------------------------------------------------

    def _trait_channels(self, rels: List[Dict[str, Any]], observations: Dict[str, Any]
                        ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        traits = _traits()
        if not traits or self.trait_table is None:
            for r in rels:
                r["context_weight"] = r["weight"]
            return [], {"status": "trait channel unavailable (bioradar.relatives.traits not loaded)"}
        evidence = []
        for r in rels:
            ev = traits.evidence(r["species"], observations, self.trait_table) if observations else []
            factor = 1.0
            for e in ev:
                factor *= e.get("factor_weight", 1.0)
            r["context_factor"] = round(factor, 4)
            r["context_weight"] = round(r["weight"] * factor, 6)
            if ev:
                evidence.append({"species": r["species"], "checks": ev})
        observed = set(observations)
        if "country" in observed:
            observed.add("country_native")
        profile = traits.inferred_profile([(r["species"], r["weight"]) for r in rels],
                                          self.trait_table, exclude=observed)
        return evidence, profile

    # -- the whole hypothesis ---------------------------------------------------------------

    def speculate(self, seq: str, observations: Optional[Dict[str, Any]] = None,
                  exclude_species: Iterable[str] = ()) -> Dict[str, Any]:
        observations = {k: v for k, v in (observations or {}).items() if v not in (None, "")}
        rels = self.relatives(seq, exclude_species=exclude_species)
        if not rels:
            return {"status": "no relative found: the fragment shares no informative k-mers with "
                              "the reference (not a fish 12S fragment, or too short)",
                    "relatives": [], "hypothesis": None}
        top_cos = rels[0]["cosine"]
        seq_only = self.consensus(rels)
        evidence, profile = self._trait_channels(rels, observations)
        with_ctx = self.consensus(rels, "context_weight") if evidence else seq_only
        closest = rels[0]
        species_level = bool(closest["identity"] is not None
                             and closest["identity"] >= _cfg("identity_species"))
        used = ["dna_sequence"] + (["evolutionary_history"] if self.species_lineage else [])
        used += sorted({c["factor"] for e in evidence for c in e["checks"]
                        if c.get("verdict") != "no_data"})
        not_used = []
        for factor, label in UNOBSERVABLE.items():
            if factor not in observations:
                not_used.append({"factor": factor, "label": label,
                                 "why": "not observable from a DNA fragment in water; supply a "
                                        "measurement from a specimen to use it as evidence. Shown "
                                        "under inferred_profile when relatives have documented values."})
        for factor in ("habitat", "country"):
            if factor not in observations:
                not_used.append({"factor": factor, "label": "ecology",
                                 "why": "not recorded in the sample metadata and not supplied"})
        return {
            "status": "hypothesis - needs expert review; never a confirmed identification",
            "wording": CONFIDENCE_WORDING,
            "query": {"length": len(seq)},
            "closest_species": {"species": closest["species"], "accession": closest["accession"],
                                "cosine": closest["cosine"], "identity": closest["identity"],
                                "coverage": closest["coverage"],
                                "is_species_level_match": species_level},
            "relatives": rels,
            "hypothesis": self.state_rank(with_ctx, top_cos),
            "by_rank": with_ctx,
            "by_rank_sequence_only": seq_only,
            "evidence": evidence,
            "observations": observations,
            "factors_used": used,
            "factors_not_used": not_used,
            "inferred_profile": profile,
            "model": self.describe(),
        }

    def describe(self) -> Dict[str, Any]:
        return {
            "name": "BioRadar relative finder",
            "version": MODEL_VERSION,
            "embedding": "canonical {}-mer TF-IDF, L2-normalised; exact cosine via inverted index; "
                         "{}-d signed-hash dense projection for export".format(K, DENSE_DIMS),
            "features": len(self.index.embedder.idf),
            "reference": self.ref.version,
            "reference_entries": len(self.index.labels),
            "lineage": lineage_mod.meta().get("retrieved_at", "not fetched"),
            "calibration": {k: self.calibration.get(k) for k in ("method", "built_at", "species_tested")}
            if self.calibration else "not calibrated (run: python -m bioradar.relatives calibrate)",
            "config": {k: v["value"] for k, v in CONFIG.items()},
        }

    def embedding(self, seq: str) -> List[float]:
        return dense(self.index.embedder.embed(seq))


_FINDER: Optional[RelativeFinder] = None


def finder() -> RelativeFinder:
    """Process-wide instance (building the index takes about a second)."""
    global _FINDER
    if _FINDER is None:
        _FINDER = RelativeFinder.load()
    return _FINDER
