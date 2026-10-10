"""Per-sequence quality control. Every rejection comes back with a written reason.

A check returns None (sequence is fine) or a (code, sentence) pair. The sentence is
what the officer sees, with the actual measured value and the threshold that was
applied, so nobody has to guess why a sequence was dropped.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Optional, Tuple

from bioradar.adjudicate.thresholds import Thresholds

VALID = set("ACGTN")

# Stable order for display.
REASON_ORDER = ["invalid_characters", "too_short", "too_many_n", "low_complexity",
                "low_quality", "singleton", "human_contamination", "unrelated"]

REASON_LABELS = {
    "invalid_characters": "Not a DNA sequence",
    "too_short": "Short fragment",
    "too_many_n": "Too many N bases",
    "low_complexity": "Low complexity / repeat",
    "low_quality": "Low base quality",
    "singleton": "Seen once (probable error)",
    "human_contamination": "Human contamination",
    "unrelated": "Unrelated to any reference",
}


def entropy(seq: str) -> float:
    counts = Counter(seq)
    n = len(seq)
    return -sum((c / n) * math.log2(c / n) for c in counts.values()) if n else 0.0


def check(seq: str, count: int, mean_q: Optional[float], t: Thresholds) -> Optional[Tuple[str, str]]:
    n = len(seq)
    bad = set(seq) - VALID
    if bad:
        return ("invalid_characters",
                "contains non-DNA characters {} - not a nucleotide sequence".format(
                    "".join(sorted(bad))[:10]))
    if n < t.min_length:
        return ("too_short", "short fragment: {} bp is under the {} bp minimum".format(n, t.min_length))
    n_pct = 100.0 * seq.count("N") / n
    if n_pct > t.max_n_percent:
        return ("too_many_n", "{:.1f}% N (uncalled) bases is over the {}% maximum".format(
            n_pct, t.max_n_percent))
    ent = entropy(seq)
    if ent < t.min_complexity_entropy:
        return ("low_complexity", "low complexity (entropy {:.2f} bits, minimum {}): "
                                  "repeat or single-letter run, not a real fragment".format(
                                      ent, t.min_complexity_entropy))
    if mean_q is not None and mean_q < t.min_mean_quality:
        return ("low_quality", "mean base quality Q{:.0f} is under the Q{} minimum".format(
            mean_q, t.min_mean_quality))
    if count < t.min_read_count:
        return ("singleton", "seen only {} time(s), under the {}-read minimum: probable "
                             "sequencing or PCR error, not a real sequence".format(
                                 count, t.min_read_count))
    return None
