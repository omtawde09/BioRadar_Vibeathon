"""The officer report must be exactly one page, readable, and carry every required field.

Runs on the REAL pre-run results (every sample and every two-season site). Skips if the
results have not been built (`python -m bioradar.adjudicate.runner all`) or PyMuPDF is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

fitz = pytest.importorskip("pymupdf")

from bioradar.adjudicate import report, runner  # noqa: E402

RESULTS = runner.RESULTS_DIR
HAVE = (RESULTS / "index.json").is_file() and (RESULTS / "seasons.json").is_file()
pytestmark = pytest.mark.skipif(not HAVE, reason="results not built")

PAGE_W, PAGE_H = 595.0, 842.0
REQUIRED = ["What to do", "RISK LEVEL", "Animals detected", "Source and sample date", "Uncertainty and missing coverage"]


def _all_samples():
    return [s["sample_id"] for s in json.loads((RESULTS / "index.json").read_text())["samples"]]


def _sites():
    return json.loads((RESULTS / "seasons.json").read_text())["sites"]


def _check(pdf: bytes, headings):
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert doc.page_count == 1, "report spilled onto {} pages".format(doc.page_count)
    page = doc[0]
    text = page.get_text()
    for h in headings:
        assert h.lower() in text.lower(), "missing section: " + h
    spans = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip():
                    spans.append(fitz.Rect(span["bbox"]))
    for r in spans:
        assert r.x0 >= 20 and r.x1 <= PAGE_W - 20, "text outside the side margins: {}".format(r)
        assert r.y0 >= 8 and r.y1 <= PAGE_H - 8, "text outside the page: {}".format(r)
    # no two pieces of text printed on top of each other
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            inter = spans[i] & spans[j]
            if not inter.is_empty:
                smaller = min(spans[i].get_area(), spans[j].get_area()) or 1
                assert inter.get_area() / smaller < 0.2, "overlapping text at {} / {}".format(spans[i], spans[j])
    return text


@pytest.mark.parametrize("sample_id", _all_samples() if HAVE else [])
def test_every_sample_report_is_one_clean_page(sample_id):
    result = runner.run_sample(sample_id)
    text = _check(report.build_pdf(result), REQUIRED)
    assert "cut to keep this report to one page" not in text, "report had to truncate content"
    # plain-language rules from the workpack: identity is not called confidence
    assert "conf " not in text and "confidence" not in text.lower()
    assert result["metadata"]["bioproject"] in text           # source
    assert result["verdict"] in text or result["verdict"].split()[0] in text


@pytest.mark.parametrize("index", range(len(_sites())) if HAVE else [])
def test_every_site_report_is_one_clean_page(index):
    site = _sites()[index]
    results = [runner.run_sample(i) for i in site["summer"]["sample_ids"] + site["winter"]["sample_ids"]]
    text = _check(report.build_site_pdf(site, results),
                  REQUIRED + [site["location"], "summer", "winter"])
    assert "cut to keep this report to one page" not in text
    assert "does not mean absent" in text           # non-detection is never "absent"
    assert " absent " not in text.replace("does not mean absent", "")


def test_site_report_risk_is_the_highest_alert_across_both_seasons():
    for site in _sites():
        results = [runner.run_sample(i) for i in site["summer"]["sample_ids"] + site["winter"]["sample_ids"]]
        summ = report.site_summary(results)
        order = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}
        levels = [e["level"] for r in results for e in r["alerts"] if e["kind"] == "confirmed"]
        if levels:
            assert summ["level"] == min(levels, key=lambda lv: order[lv])
        else:
            assert summ["level"] in ("WATCH", "NONE", "RETAKE")
