"""Compare an estimated species split with what the SOURCE says it should contain.

Two kinds of source support are accepted, and nothing else:

* a full composition table (`data/real_challenge/expected_composition.json`, every
  entry carrying its citation) - checks which species are present and their shares;
* the count the submitter deposited on the BioSample (`samp_size = "15 fish"`) -
  checks only how many species were found, and says it cannot verify which ones.

With neither, this reports "not checked" and claims nothing: a mixed-sample test is
not 'passed' without ground truth.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioradar.adjudicate.thresholds import Thresholds, load

EXPECTED_FILE = Path(__file__).resolve().parents[2] / "data" / "real_challenge" / "expected_composition.json"

NOT_CHECKED = ("No source-supported expected composition is on file for this sample, so the species "
               "split is shown but NOT checked against ground truth. The mixed-sample test is not "
               "claimed as passed.")


def load_expected(path: Path = EXPECTED_FILE) -> Dict[str, Any]:
    if not Path(path).is_file():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8")).get("samples", {})


def check(result: Dict[str, Any], expected: Dict[str, Any],
          t: Optional[Thresholds] = None) -> Dict[str, Any]:
    t = t or load()
    meta = result["metadata"]
    spec = expected.get(meta.get("alias", "")) or expected.get(result.get("sample_id", ""))
    if spec:
        return _composition_check(result, spec, t)
    return _count_check(result, t)


def _design_share_check(meta: Dict[str, Any], n_fish: int, species: List[Dict[str, Any]],
                        t: Thresholds) -> Optional[Dict[str, Any]]:
    """Share check that the SOURCE supports without a species table: when the submitter's
    design note says 'equal concentration', each of the N mixed fish should contribute about
    1/N of the DNA. Reports how many detected species are within the fold tolerance of 1/N.
    It does not say WHICH species they are (the archive does not), and amplification bias
    means a spread around 1/N is expected, so this is a plausibility check, not a pass."""
    note = (meta.get("design_note") or "").lower()
    if not re.search(r"(?<!un)\bequal concentrations?\b", note) or n_fish <= 0:
        return None
    each = 1.0 / n_fish
    lo, hi = each / t.share_tolerance_factor, each * t.share_tolerance_factor
    inside = [r for r in species if lo <= r["share"] <= hi]
    return {
        "design_note": meta.get("design_note", ""),
        "expected_share_each": round(each, 4),
        "tolerance_fold": t.share_tolerance_factor,
        "tolerance_range": [round(lo, 4), round(hi, 4)],
        "detected_species": len(species),
        "within_tolerance": len(inside),
        "outside_tolerance": len(species) - len(inside),
        "assumptions": "one species per mixed fish (samp_size counts fish) and equal DNA per "
                       "fish; the full design note is '{}', and 'gradient' in it is "
                       "ambiguous".format(meta.get("design_note", "")),
        "limits": "Based on the submitter's design note ('{}') and BioSample samp_size = {}. "
                  "Species identities are not given by the source, so this cannot confirm that "
                  "the right species were found; the paper's species table would be needed. "
                  "Read share is not biomass or abundance.".format(meta.get("design_note", ""),
                                                                    n_fish),
    }


def _count_check(result: Dict[str, Any], t: Optional[Thresholds] = None) -> Dict[str, Any]:
    """Source-supported count only: the BioSample says how many fish were mixed."""
    t = t or load()
    meta = result["metadata"]
    attrs = meta.get("biosample_attributes", {}) or {}
    m = re.match(r"^\s*(\d+)\s*fish", attrs.get("samp_size", ""))
    if not m or meta.get("role") != "mixed":
        return {"available": False, "note": NOT_CHECKED}
    want = int(m.group(1))
    species = [r for r in result["species"] if r["kind"] == "species" and r["status"] == "detected"]
    groups = [r for r in result["species"] if r["kind"] == "complex"]
    found = len(species)
    ok = found >= want
    return {
        "design_share_check": _design_share_check(meta, want, species, t),
        "available": True, "mode": "count_only",
        "source": "BioSample {} deposited by the submitter: samp_size = '{}', design = '{}'".format(
            meta.get("biosample", ""), attrs.get("samp_size", ""), meta.get("design_note", "")),
        "expected_count": want, "found_count": found, "unresolved_groups": len(groups),
        "all_found": ok, "rows": [],
        "verdict": ("COUNT CONSISTENT: {} species-level calls for {} fish mixed".format(found, want)
                    if ok else
                    "FAIL: only {} species-level calls for {} fish mixed ({} could not be named: "
                    "absent from the reference list or indistinguishable on 12S)".format(
                        found, want, want - found)),
        "limits": "The source says HOW MANY fish were mixed, not which ones or in what "
                  "proportions. Species identities and shares are therefore NOT verified against "
                  "ground truth; a published species table would be needed for that.",
    }


def _composition_check(result: Dict[str, Any], spec: Dict[str, Any], t: Thresholds) -> Dict[str, Any]:
    observed = {r["species"]: r for r in result["species"] if r["kind"] == "species"}
    complexes = [r for r in result["species"] if r["kind"] == "complex"]
    rows, found = [], 0
    for item in spec["species"]:
        name, want = item["name"], item.get("expected_share")
        obs = observed.get(name)
        in_complex = next((c for c in complexes if name in c["members"]), None)
        row: Dict[str, Any] = {"species": name, "expected_share": want}
        if obs and obs["status"] == "detected":
            found += 1
            row.update(observed_share=obs["share"], status="found")
            if want:
                fold = max(obs["share"], want) / max(min(obs["share"], want), 1e-9)
                row.update(fold_difference=round(fold, 1),
                           share_check="consistent" if fold <= t.share_tolerance_factor
                           else "outside {:g}-fold tolerance".format(t.share_tolerance_factor))
        elif in_complex:
            found += 1
            row.update(observed_share=in_complex["share"], status="found, unresolved",
                       note="present, but 12S cannot separate it from {}".format(
                           ", ".join(m for m in in_complex["members"] if m != name)))
        else:
            row.update(observed_share=0.0, status="MISSING")
        rows.append(row)
    expected_names = {i["name"] for i in spec["species"]}
    extra = [r["species"] for r in result["species"]
             if r["kind"] == "species" and r["status"] == "detected"
             and r["species"] not in expected_names]
    total = len(spec["species"])
    return {"available": True, "mode": "composition", "source": spec.get("source", ""), "rows": rows,
            "expected_count": total, "found_count": found, "all_found": found == total,
            "unexpected_species": extra,
            "verdict": ("PASS: every expected species was found" if found == total
                        else "FAIL: {} of {} expected species missing".format(total - found, total))}
