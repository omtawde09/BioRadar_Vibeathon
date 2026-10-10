"""Static checks for the Results-page charts (webapp_static/visuals.{js,css}) and their wiring in app.js."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "bioradar" / "webapp_static"
JS = (STATIC / "visuals.js").read_text(encoding="utf-8")
CSS = (STATIC / "visuals.css").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def _table(lang: str) -> dict:
    block = JS[JS.index("  var TXT = {"):]
    head = "    {}: {{".format(lang)
    body = block[block.index(head) + len(head):]
    body = body[:body.index("\n    }")]
    return dict(re.findall(r'"([a-zA-Z0-9_.\-]+)":\s*"((?:[^"\\]|\\.)*)"', body))


EN, HI = _table("en"), _table("hi")


def test_loaded_before_app_js_and_files_exist():
    assert (STATIC / "visuals.js").is_file() and (STATIC / "visuals.css").is_file()
    assert HTML.index("visuals.js") < HTML.index("/static/app.js")
    assert "visuals.css" in HTML


def test_english_and_hindi_keys_match_and_hindi_is_hindi():
    assert EN and set(EN) == set(HI), sorted(set(EN) ^ set(HI))
    deva = re.compile(r"[ऀ-ॿ]")
    proper_names = {"vz.shannon"}  # a person's name: the app's i18n keeps such terms in Latin script
    for key, text in HI.items():
        if key in proper_names:
            continue
        assert deva.search(text), "untranslated: {} = {!r}".format(key, text)


def test_every_key_used_in_code_exists():
    used = set(re.findall(r'T\("(vz\.[A-Za-z0-9_.\-]+)"', JS)) | set(re.findall(r'text\("(vz\.[A-Za-z0-9_.\-]+)"', APP))
    used |= set(re.findall(r'key: "(vz\.[A-Za-z0-9_.\-]+)"', JS))
    assert not (used - set(EN)), sorted(used - set(EN))


def test_charts_use_design_tokens_only():
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", CSS), "hard-coded colour in visuals.css"
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", JS), "hard-coded colour in visuals.js"
    assert not re.findall(r"--neu-[a-z-]+\s*:", CSS), "must not define shadow tokens"
    assert "box-shadow" not in re.sub(r"details\.vz-fold\s*\{[^}]*\}", "", CSS), "flat data marks: no shadows on chart parts"


def test_nothing_is_fetched_from_outside():
    assert not re.findall(r"https?://", CSS) and not re.findall(r"https?://", JS)
    assert "fetch(" not in JS and "XMLHttpRequest" not in JS  # pure rendering from data already on the page


def test_every_chart_has_a_text_equivalent():
    assert JS.count('role="img"') >= 2 and "aria-label" in JS
    assert 'aria-label="' in JS and "vz-val" in JS  # numbers are printed beside the marks, not colour alone


def test_results_view_uses_the_charts_and_folds_the_text_heavy_blocks():
    assert "V.overview(report, run.run_id)" in APP and "V.samples(" in APP
    assert APP.count('class="vz-fold"') >= 2           # briefing + species table are collapsed
    assert "results.composition" not in APP           # the old phylum bar card is replaced by the donut
    # the late-arriving per-sample data must not re-render (and re-fetch) the whole page
    sig = APP[APP.index("var signature2"):APP.index("if (signature2 === resultsSignature)")]
    assert "analysis" not in sig


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_parses():
    for name in ("visuals.js", "app.js"):
        out = subprocess.run(["node", "--check", str(STATIC / name)], capture_output=True, text=True)
        assert out.returncode == 0, out.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_chart_markup_renders_for_real_shaped_data():
    """Run the real module in node against a stub DOM-free environment: it only builds strings."""
    script = r"""
    global.window = global;
    global.BioRadarUI = { esc: s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
      num: n => Number(n).toLocaleString('en-US'), categorical: k => 'var(--cat)' };
    global.BioRadarI18n = { t: (k, f) => f, addStrings: () => {} };
    require(process.argv[1]);
    const V = global.BioRadarVisuals;
    const report = { phyla: 3, phyla_breakdown: [{name:'Chordata',reads:700},{name:'Mollusca',reads:200},{name:'Annelida',reads:100}],
      top_species: [{name:'Gambusia holbrooki',phylum:'Chordata',reads:500,confidence:0.99},{name:'Unclassified sp.',phylum:'X',reads:5,confidence:0.4,placeholder:true}] };
    const html = V.overview(report, 'run1');
    const samples = V.samples({ samples: [{sample_id:'S1',total_reads:1000,unassigned_reads:100,species_count:12,shannon:2.1}] });
    const out = { donut: html.includes('vz-donut'), bars: html.includes('Gambusia'), hist: html.includes('vz-hist'),
                  placeholderHidden: !html.includes('Unclassified'), slot: html.includes('vz-samples-run1'),
                  stacked: samples.includes('vz-stack'), none: V.samples({samples: []}) === '' };
    console.log(JSON.stringify(out));
    """
    out = subprocess.run(["node", "-e", script, str(STATIC / "visuals.js")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    import json
    assert all(json.loads(out.stdout.strip().splitlines()[-1]).values()), out.stdout
