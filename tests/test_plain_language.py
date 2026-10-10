"""Plain-language checks: the objective stand-in for 'could an outsider read this?'.

Every English string the person sees (Review, the shared pages, the Results charts, the plain-words boxes, the
glossary) and every sentence the engine writes is held to a reading level and kept free of jargon. The Hindi
tables must carry the same keys. A real outsider is still the better test; this keeps the wording from drifting.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bioradar.adjudicate import quality, readability

STATIC = Path(__file__).resolve().parents[1] / "bioradar" / "webapp_static"

MAX_MEAN_GRADE = 6.0       # on strings of six or more words
MAX_STRING_GRADE = 10.0
ENTRY = re.compile(r'"([a-zA-Z0-9_.\- ]+)":\s*"((?:[^"\\]|\\.)*)"')

# Technical references that are file or command names, not sentences to read.
EXEMPT = {"rv.notBuiltBody", "rv.season.rule", "app.subtitle"}


def _table(filename: str, lang: str) -> dict:
    text = (STATIC / filename).read_text(encoding="utf-8")
    start = text.index("    {}: {{".format(lang))
    end = text.index("\n    }", start)
    return {k: v.replace('\\"', '"') for k, v in ENTRY.findall(text[start:end])}


FILES = ["adjudicate.js", "plain.js", "i18n.js", "visuals.js"]
EN = {}
HI = {}
for _f in FILES:
    EN.update(_table(_f, "en"))
    HI.update(_table(_f, "hi"))


def test_english_strings_read_at_a_low_grade():
    scored = [(readability.grade(v), k) for k, v in EN.items() if len(v.split()) >= 6 and k not in EXEMPT]
    assert len(scored) > 100
    mean = sum(g for g, _ in scored) / len(scored)
    assert mean <= MAX_MEAN_GRADE, "mean reading grade {:.1f}".format(mean)
    hard = [(round(g, 1), k) for g, k in scored if g > MAX_STRING_GRADE]
    assert not hard, "too hard to read: {}".format(hard)


def test_no_jargon_in_everyday_screen_text():
    bad = {}
    for key, text in EN.items():
        if key.startswith("rv.gl.") or key in EXEMPT:
            continue
        found = readability.jargon_in(text)
        if found:
            bad[key] = found
    assert not bad, bad


def test_review_and_plain_pages_have_the_same_keys_in_hindi():
    for name in ("adjudicate.js", "plain.js"):
        en, hi = _table(name, "en"), _table(name, "hi")
        assert en and set(en) == set(hi), (name, sorted(set(en) ^ set(hi)))


def test_every_page_has_an_in_plain_words_box():
    plain = (STATIC / "plain.js").read_text(encoding="utf-8")
    for page in ("analyze", "monitor", "compare", "alerts", "settings"):
        assert '"plain.{}"'.format(page) in plain, page
        assert "plain.{}".format(page) in EN
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "BioRadarPlain.resultsBox(report)" in app                     # Results gets a computed summary
    review = (STATIC / "adjudicate.js").read_text(encoding="utf-8")
    for tab in ("guard", "seasons", "alerts", "why"):
        assert "rv.plain." + tab in EN, tab                             # one box per Review tab
    assert "plainForSample" in review
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "/static/plain.js" in html and "/static/plain.css" in html
    assert html.index("plain.js") < html.index("/static/app.js")


def test_glossary_explains_the_words_the_screens_use():
    for term in ("edna", "piece", "marker", "list", "match", "score", "unknown", "dropped", "complex", "invasive",
                 "retake", "mock", "share", "boundary"):
        assert "rv.gl.{}.t".format(term) in EN and "rv.gl.{}.d".format(term) in EN, term
        assert len(EN["rv.gl.{}.d".format(term)].split()) <= 30, term   # one short sentence or two


def test_sentences_the_engine_writes_are_plain():
    from bioradar.adjudicate.thresholds import load
    t = load()
    samples = [
        quality.check("ACGT" * 5, 5, None, t),                                   # too short
        quality.check("ACGT" * 40 + "NNNNNNNNNN", 5, None, t),                    # unreadable letters
        quality.check("A" * 150, 5, None, t),                                    # repeats
        quality.check("ACGTTGCAAGCT" * 12, 1, None, t),                          # seen once
        quality.check("ACGTTGCAAGCTXZ" * 12, 5, None, t),                        # not DNA
    ]
    texts = [s[1] for s in samples if s]
    assert len(texts) == 5
    for text in texts:
        assert readability.grade(text) <= MAX_STRING_GRADE + 2, text
        assert not readability.jargon_in(text), text
    for label in quality.REASON_LABELS.values():
        assert not readability.jargon_in(label), label
    for why in (v["why"] for v in t.rationale().values()):
        assert not readability.jargon_in(why), why
        assert readability.grade(why) <= 12, why


def test_the_grade_function_ranks_hard_text_above_easy_text():
    easy = "The sample is good enough to trust."
    hard = ("Taxonomic assignment was heuristically calibrated against a phylogenetically heterogeneous "
            "reference database, notwithstanding amplification stochasticity.")
    assert readability.grade(easy) < 5 < readability.grade(hard)


@pytest.mark.parametrize("text,expected", [("rare", 1), ("species", 2), ("beautiful", 3)])
def test_syllable_counter_is_close_enough(text, expected):
    assert abs(readability.syllables(text) - expected) <= 1
