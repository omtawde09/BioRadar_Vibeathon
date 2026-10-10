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
from typing import Any, Dict, Optional

from bioradar.adjudicate.thresholds import Thresholds, load

EXPECTED_FILE = Path(__file__).resolve().parents[2] / "data" / "real_challenge" / "expected_composition.json"

NOT_CHECKED = ("No published recipe is on file for this sample, so the fish list is shown but it is NOT "
               "checked against a known answer. This test is not claimed as passed.")


def load_expected(path: Path = EXPECTED_FILE) -> Dict[str, Any]:
    if not Path(path).is_file():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8")).get("samples", {})


def check(result: Dict[str, Any], expected: Dict[str, Any],
          t: Optional[Thresholds] = None) -> Dict[str, Any]:
    t = t or load()
    meta = result["metadata"]
    # the sample id is unique across datasets; an alias like "A2" is not
    spec = expected.get(result.get("sample_id", "")) or expected.get(meta.get("alias", ""))
    if spec:
        return _composition_check(result, spec, t)
    return _count_check(result)


def _count_check(result: Dict[str, Any]) -> Dict[str, Any]:
    """Source-supported count only: the BioSample says how many fish were mixed."""
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
        "available": True, "mode": "count_only",
        "source": "BioSample {} deposited by the submitter: samp_size = '{}', design = '{}'".format(
            meta.get("biosample", ""), attrs.get("samp_size", ""), meta.get("design_note", "")),
        "expected_count": want, "found_count": found, "unresolved_groups": len(groups),
        "all_found": ok, "rows": [],
        "verdict": ("COUNT MATCHES: {} fish named, and {} were mixed".format(found, want)
                    if ok else
                    "FAIL: only {} fish named, but {} were mixed ({} could not be named: they are "
                    "not on the list, or look the same in this gene region)".format(
                        found, want, want - found)),
        "limits": "The source says HOW MANY fish were mixed, not which ones or how much of each. "
                  "So the fish names and shares are NOT verified against a known answer. A published "
                  "table of the mixture would be needed for that.",
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
                           else "more than {:g} times off".format(t.share_tolerance_factor))
        elif in_complex:
            found += 1
            row.update(observed_share=in_complex["share"], status="found, unresolved",
                       note="found, but it looks the same as {} in this gene region".format(
                           ", ".join(m for m in in_complex["members"] if m != name)))
        else:
            row.update(observed_share=0.0, status="NOT FOUND")
        rows.append(row)
    expected_names = {i["name"] for i in spec["species"]}
    listed = {f["species"]: f["reads"] for f in spec.get("false_positives", [])}
    extra_rows = [r for r in result["species"]
                  if r["kind"] == "species" and r["status"] == "detected" and r["species"] not in expected_names]
    extra = [{"species": r["species"], "reads": r["reads"], "share": r["share"],
              "paper_listed_reads": listed.get(r["species"])} for r in extra_rows]
    measured = [r for r in rows if r.get("share_check")]
    within = sum(1 for r in measured if r["share_check"] == "consistent")
    total = len(spec["species"])
    return {"available": True, "mode": "composition", "source": spec.get("source", ""), "rows": rows,
            "expected_count": total, "found_count": found, "all_found": found == total,
            "shares_within_tolerance": within, "shares_measured": len(measured),
            "tolerance_fold": t.share_tolerance_factor,
            "unexpected_species": extra,
            "unexpected_also_in_paper": sum(1 for e in extra if e["paper_listed_reads"] is not None),
            "verdict": ("PASS: every fish in the mixture was found" if found == total
                        else "FAIL: {} of {} fish in the mixture were not found".format(total - found, total))}
