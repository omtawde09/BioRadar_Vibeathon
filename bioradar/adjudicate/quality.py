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

VALID = set("ACGTRYKMSWBDHVN")  # IUPAC: R, Y, ... are ambiguous bases (merged reads carry them)
AMBIGUOUS = set("RYKMSWBDHVN")

# Stable order for display.
REASON_ORDER = ["invalid_characters", "too_short", "too_many_n", "low_complexity",
                "low_quality", "singleton", "human_contamination", "unrelated"]

REASON_LABELS = {
    "invalid_characters": "Not DNA",
    "too_short": "Too short",
    "too_many_n": "Too many unreadable letters",
    "low_complexity": "Same letters repeated",
    "low_quality": "Poor quality",
    "singleton": "Seen only once (maybe a mistake)",
    "human_contamination": "Human DNA",
    "unrelated": "Not like any fish on the list",
}


def entropy(seq: str) -> float:
    counts = Counter(seq)
    n = len(seq)
    return -sum((c / n) * math.log2(c / n) for c in counts.values()) if n else 0.0


def check(seq: str, count: int, mean_q: Optional[float], t: Thresholds,
          count_rule: bool = True) -> Optional[Tuple[str, str]]:
    n = len(seq)
    bad = set(seq) - VALID
    if bad:
        return ("invalid_characters",
                "has letters that are not DNA ({}): not a DNA code".format(
                    "".join(sorted(bad))[:10]))
    if n < t.min_length:
        return ("too_short", "too short: {} letters, and at least {} are needed".format(n, t.min_length))
    n_pct = 100.0 * sum(1 for c in seq if c in AMBIGUOUS) / n
    if n_pct > t.max_n_percent:
        return ("too_many_n", "{:.1f}% of the letters could not be read (N or unclear). The most allowed is {}%".format(
            n_pct, t.max_n_percent))
    ent = entropy(seq)
    if ent < t.min_complexity_entropy:
        return ("low_complexity", "the same few letters repeat (variety score {:.2f}, at least {} needed): "
                                  "not a real piece of DNA".format(
                                      ent, t.min_complexity_entropy))
    if mean_q is not None and mean_q < t.min_mean_quality:
        return ("low_quality", "the machine was not sure of its letters (quality Q{:.0f}, at least Q{} needed)".format(
            mean_q, t.min_mean_quality))
    if count_rule and count < t.min_read_count:
        return ("singleton", "seen only {} time(s), and at least {} are needed: probably a "
                             "copying mistake, not real DNA".format(
                                 count, t.min_read_count))
    return None
