"""Run the relative finder over the review queue of an adjudicated real sample.

Called by the CLI (`python -m bioradar.relatives sample <id>`) and the API
(`GET /api/adjudicate/relatives/<id>`). Results are cached next to the sample result and are
recomputed when the sample result, the model version or the calibration changes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from bioradar.adjudicate import runner
from bioradar.relatives.model import CALIBRATION_FILE, MODEL_VERSION, finder


def _key(result: Dict[str, Any], top: int) -> str:
    cal = CALIBRATION_FILE.read_bytes() if CALIBRATION_FILE.is_file() else b""
    blob = "|".join([result.get("cache_key", ""), MODEL_VERSION, str(top),
                     hashlib.md5(cal).hexdigest()])
    return hashlib.md5(blob.encode()).hexdigest()


def sample_hypotheses(sample_id: str, top: int = 10, force: bool = False) -> Dict[str, Any]:
    """Hypotheses for the `top` unknowns (by reads) of one processed sample."""
    result = runner.run_sample(sample_id)
    out_path = runner.RESULTS_DIR / "{}_relatives.json".format(sample_id)
    key = _key(result, top)
    if out_path.is_file() and not force:
        cached = json.loads(out_path.read_text(encoding="utf-8"))
        if cached.get("cache_key") == key:
            return cached
    context: Dict[str, Any] = {}
    try:  # the trait/ecology channel is optional
        from bioradar.relatives import traits as _t
        context = _t.sample_context(result.get("metadata", {}))
    except Exception:
        context = {}
    observations = {k: context.get(k) for k in ("habitat", "country") if context.get(k)}
    f = finder()
    hyps = []
    for u in result.get("unknown_queue", [])[:top]:
        h = f.speculate(u["sequence"], observations)
        h.update({"seq_id": u["seq_id"], "reads": u["reads"], "adjudicator_kind": u.get("kind"),
                  "adjudicator_closest": u.get("closest_match"),
                  "adjudicator_identity": u.get("identity")})
        hyps.append(h)
    doc = {"sample_id": sample_id, "label": result.get("metadata", {}).get("label", ""),
           "context": context, "observations_used": observations, "top": top,
           "unknowns_in_queue": len(result.get("unknown_queue", [])),
           "hypotheses": hyps, "model": f.describe(), "cache_key": key}
    out_path.write_text(json.dumps(doc), encoding="utf-8")
    return doc
