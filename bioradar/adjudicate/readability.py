"""A reading-level check for the words people see in the app.

There is no outside reader here, so this is the objective stand-in: the Flesch-Kincaid grade
(roughly, the school year a reader needs to follow a sentence) plus a list of jargon words that must
not appear in everyday screen text. Used by tests/test_plain_language.py. Stdlib only.
"""

from __future__ import annotations

import re
from typing import List

# Words an outsider cannot be expected to know. They are allowed in the glossary, where they are explained,
# and in file and command names, but not in ordinary sentences on screen.
JARGON = ["amplicon", "asv", "otu", "taxa", "taxon", "taxonomy", "taxonomic", "phylum", "phyla", "denoise", "denoising",
          "heuristic", "calibrated", "metabarcoding", "bioinformatics", "classifier", "provenance", "mitogenome",
          "nucleotide", "entropy", "singleton", "contig", "chimera", "rarefaction"]


def syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def plain_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)          # markup
    return re.sub(r"\{\w+\}", "12", text)          # {placeholders} stand for numbers


def grade(text: str) -> float:
    """Flesch-Kincaid grade level of an English text. Lower is easier."""
    text = plain_text(text)
    sentences = [s for s in re.split(r"(?<=[.!?:;])\s+", text.strip()) if re.search(r"[A-Za-z]", s)]
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)
    if not sentences or not words:
        return 0.0
    syl = sum(syllables(w) for w in words)
    return 0.39 * len(words) / len(sentences) + 11.8 * syl / len(words) - 15.59


def jargon_in(text: str) -> List[str]:
    words = {w.lower() for w in re.findall(r"[A-Za-z]+", plain_text(text))}
    return sorted(w for w in JARGON if w in words)
