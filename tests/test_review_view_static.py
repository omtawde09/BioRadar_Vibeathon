"""Static regression checks for the Review view (webapp_static/adjudicate.{js,css}).

There is no JS test runner in this repo, so these read the shipped assets directly and enforce
the rules the team guide and the workpack set for the front end: English/Hindi parity, design
tokens only, nothing loaded from a CDN, the view registered through the registry, and the report
endpoints refusing bad input.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "bioradar" / "webapp_static"
JS = (STATIC / "adjudicate.js").read_text(encoding="utf-8")
CSS = (STATIC / "adjudicate.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
I18N = (STATIC / "i18n.js").read_text(encoding="utf-8")


def _table(lang: str) -> dict:
    """The {key: string} object for one language inside the TXT table of adjudicate.js."""
    start = JS.index("  var TXT = {")
    block = JS[start:]
    head = '    {}: {{'.format(lang)
    body = block[block.index(head) + len(head):]
    end = body.index("\n    }")
    entries = re.findall(r'"([a-zA-Z0-9_.\- ]+)":\s*"((?:[^"\\]|\\.)*)"', body[:end])
    return {k: v for k, v in entries}


EN, HI = _table("en"), _table("hi")


def test_the_view_is_registered_through_the_feature_registry():
    assert 'id: "review"' in JS and 'slot: "main-view"' in JS
    assert "Registry.registerFeature" in JS
    assert "adjudicate.js" in HTML and "adjudicate.css" in HTML
    # loaded before app.js, whose boot builds the shell from the registry
    assert HTML.index("adjudicate.js") < HTML.index("/static/app.js")


def test_english_and_hindi_have_exactly_the_same_keys():
    assert EN and HI
    assert set(EN) == set(HI), "keys missing in one language: {}".format(sorted(set(EN) ^ set(HI)))


def test_placeholders_match_between_languages():
    for key in EN:
        assert sorted(re.findall(r"\{(\w+)\}", EN[key])) == sorted(re.findall(r"\{(\w+)\}", HI[key])), key


def test_hindi_strings_are_actually_hindi():
    devanagari = re.compile(r"[ऀ-ॿ]")
    for key, text in HI.items():
        if not re.sub(r"\{\w+\}|[\s·:()\-/]", "", text):
            continue  # a pure template such as "{n} {what}" has no words to translate
        assert devanagari.search(text), "Hindi table has an untranslated string: {} = {!r}".format(key, text)


def test_every_translated_key_used_in_code_exists():
    used = {k for k in re.findall(r'T\("(rv\.[A-Za-z0-9_.\- ]+)"', JS) if not k.endswith(".")}  # "." = dynamic suffix
    assert not (used - set(EN)), "keys used but not defined: {}".format(sorted(used - set(EN)))
    # keys built from a dynamic suffix (verdict, level, reason, role, tab, rule, prec, chk, w)
    prefixes = ["rv.verdict.", "rv.level.", "rv.reason.", "rv.role.", "rv.tab.", "rv.guard.rule.", "rv.prec.", "rv.chk.", "rv.guard.w."]
    for prefix in prefixes:
        assert any(k.startswith(prefix) for k in EN), prefix


def test_every_backend_value_has_a_label():
    from bioradar.adjudicate import quality
    for code in quality.REASON_ORDER:
        assert "rv.reason." + code in EN, code
    for verdict in ("Usable", "Usable with caution", "Retake sample"):
        assert "rv.verdict." + verdict in EN
    for level in ("CRITICAL", "HIGH", "WATCH"):
        assert "rv.level." + level in EN
    for rule in ("duplicate_id", "outside_boundary", "no_coordinates", "future_date", "double_spelling"):
        assert "rv.guard.rule." + rule in EN


def test_i18n_hook_never_overwrites_existing_strings():
    assert "function addStrings" in I18N and "addStrings: addStrings" in I18N
    assert "hasOwnProperty.call(table, key)" in I18N


def test_css_uses_design_tokens_not_hardcoded_colours():
    allowed = {"#fff", "#ffffff", "#241a04"}  # the same constants the app's own CSS allows
    found = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{3,8}\b", CSS)}
    assert found <= allowed, "hard-coded colours in adjudicate.css: {}".format(sorted(found - allowed))
    assert "--neu-" not in CSS or CSS.count("--neu-raised") >= 1  # only the five existing shadow tokens
    new_shadow_tokens = set(re.findall(r"--(neu-[a-z-]+)\s*:", CSS))
    assert not new_shadow_tokens, "adjudicate.css must not define shadow tokens"


def test_js_colours_only_appear_as_fallbacks_of_token_lookups():
    stripped = re.sub(r"tok\([^)]*\)", "", JS)
    leftovers = re.findall(r'"#[0-9a-fA-F]{3,8}"', stripped)
    assert not leftovers, "hard-coded colours outside token lookups: {}".format(leftovers)


def test_nothing_is_loaded_from_a_cdn():
    assert not re.findall(r"https?://", CSS)
    hosts = set(re.findall(r"https?://([^/\"'{}\s]+)", JS))
    assert hosts <= {"tile.openstreetmap.org", "www.ebi.ac.uk", "blast.ncbi.nlm.nih.gov"}, hosts
    # the page tag we added must be local
    for tag in re.findall(r'(?:src|href)="([^"]*adjudicate[^"]*)"', HTML):
        assert tag.startswith("/static/"), tag


def test_results_are_announced_and_forms_are_labelled():
    assert 'aria-live="polite"' in JS
    assert 'role="alert"' in JS and 'role="status"' in JS
    for needle in ('for="adjPick"', 'for="adjSite"', 'aria-label="', "<h1>"):
        assert needle in JS, needle


def test_no_global_selector_collides_with_the_document_root():
    """Same trap the CI guards for: <body> carries data-lang, so never select [data-lang] document-wide."""
    assert "querySelectorAll(\"[data-lang" not in JS and "querySelectorAll('[data-lang" not in JS


def test_non_detection_is_never_called_absence():
    # strings shown to users must say 'not detected'; 'absent' only appears in the 'does not mean absent' caveat
    for text in EN.values():
        stripped = re.sub(r"does not (?:prove|mean) [^.]*absent[^.]*\.?", "", text, flags=re.I)
        assert "absent" not in stripped.lower(), text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_parses():
    for name in ("adjudicate.js", "i18n.js"):
        out = subprocess.run(["node", "--check", str(STATIC / name)], capture_output=True, text=True)
        assert out.returncode == 0, out.stderr


# -- report endpoints: refuse bad input, serve PDFs ---------------------------------------

def _results_built() -> bool:
    from bioradar.adjudicate import runner
    return (runner.RESULTS_DIR / "seasons.json").is_file() and (runner.RESULTS_DIR / "index.json").is_file()


@pytest.mark.skipif(not _results_built(), reason="results not built")
def test_report_endpoints_serve_pdfs_and_reject_bad_input():
    from bioradar.adjudicate import api, runner
    site = json.loads((runner.RESULTS_DIR / "seasons.json").read_text())["sites"][0]["location"]
    status, body, ctype = api.get("/api/adjudicate/site-report/{}.pdf".format(site))
    assert status == 200 and ctype == "application/pdf" and body.startswith(b"%PDF")
    for bad in ("/api/adjudicate/site-report/Nowhere.pdf",
                "/api/adjudicate/site-report/..%2f..%2fetc.pdf",
                "/api/adjudicate/site-report/%00.pdf",
                "/api/adjudicate/report/NOTASAMPLE.pdf",
                "/api/adjudicate/report/..%2f..%2fx.pdf"):
        assert api.get(bad)[0] in (400, 404), bad
