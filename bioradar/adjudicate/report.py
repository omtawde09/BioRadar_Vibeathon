"""One-page officer report as a real PDF, generated live. Pure standard library.

The page answers what a forest officer needs, in plain words:
animals detected, risk level, source and sample date, what is uncertain or not
covered, and the action to take. The writer below emits a valid single-page PDF
(Helvetica, rectangles for the bars) so it works identically on Windows and inside
the Python 3.8 pipeline image, with no PDF library installed.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

PAGE_W, PAGE_H = 595.0, 842.0
MARGIN = 40.0

LEVEL_COLOR = {"CRITICAL": (0.78, 0.13, 0.13), "HIGH": (0.88, 0.45, 0.05),
               "WATCH": (0.75, 0.62, 0.0), "NONE": (0.18, 0.55, 0.30),
               "RETAKE": (0.40, 0.40, 0.45)}

_NARROW = set("ilI.,;:'|!jtf()[]/ ")
_WIDE = set("mwMW@%")


def _w(text: str, size: float, bold: bool = False) -> float:
    total = 0.0
    for ch in text:
        if ch in _NARROW:
            total += 0.30
        elif ch in _WIDE:
            total += 0.86
        elif ch.isupper():
            total += 0.68
        elif ch.isdigit():
            total += 0.556
        else:
            total += 0.53
    return total * size * (1.06 if bold else 1.0)


def _latin(text: Any) -> str:
    text = str(text)
    for a, b in (("–", "-"), ("—", "-"), ("‘", "'"), ("’", "'"),
                 ("“", '"'), ("”", '"'), ("→", "->"), ("≥", ">="),
                 ("≤", "<="), ("×", "x"), ("•", "-")):
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


FOOTER_TOP = 70.0  # nothing is drawn below this line except the footer


class Page:
    def __init__(self) -> None:
        self.ops: List[str] = []
        self.y = PAGE_H - MARGIN
        self.truncated = False  # True if content had to be cut to stay on one page

    def rect(self, x: float, y: float, w: float, h: float, rgb: Tuple[float, float, float]) -> None:
        self.ops.append("{:.3f} {:.3f} {:.3f} rg {:.1f} {:.1f} {:.1f} {:.1f} re f".format(
            rgb[0], rgb[1], rgb[2], x, y, w, h))

    def text(self, x: float, y: float, s: str, size: float = 10, bold: bool = False,
             rgb: Tuple[float, float, float] = (0.1, 0.1, 0.12)) -> None:
        self.ops.append("BT /{} {:.1f} Tf {:.3f} {:.3f} {:.3f} rg {:.1f} {:.1f} Td ({}) Tj ET".format(
            "F2" if bold else "F1", size, rgb[0], rgb[1], rgb[2], x, y, _esc(_latin(s))))

    def wrap(self, s: str, width: float, size: float, bold: bool = False) -> List[str]:
        words, lines, cur = _latin(s).split(), [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if _w(trial, size, bold) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, s: str, size: float = 10, bold: bool = False, x: float = MARGIN,
             width: Optional[float] = None, lead: float = 1.32,
             rgb: Tuple[float, float, float] = (0.1, 0.1, 0.12)) -> None:
        width = width or (PAGE_W - 2 * MARGIN - (x - MARGIN))
        for line in self.wrap(s, width, size, bold):
            if self.y - size * lead < FOOTER_TOP:
                self.truncated = True
                return
            self.y -= size * lead
            self.text(x, self.y, line, size, bold, rgb)

    def heading(self, s: str) -> None:
        self.y -= 8
        self.rect(MARGIN, self.y - 17, PAGE_W - 2 * MARGIN, 0.8, (0.7, 0.72, 0.75))
        self.y -= 14
        self.text(MARGIN, self.y, s.upper(), 8.5, True, (0.35, 0.38, 0.42))
        self.y -= 3

    def to_pdf(self) -> bytes:
        stream = "\n".join(self.ops).encode("latin-1")
        objs = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {} {}] /Contents 4 0 R "
             "/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>".format(PAGE_W, PAGE_H)).encode(),
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]
        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for i, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += "{} 0 obj\n".format(i).encode() + body + b"\nendobj\n"
        xref = len(out)
        out += "xref\n0 {}\n0000000000 65535 f \n".format(len(objs) + 1).encode()
        for off in offsets:
            out += "{:010d} 00000 n \n".format(off).encode()
        out += "trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{}\n%%EOF\n".format(
            len(objs) + 1, xref).encode()
        return bytes(out)


# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------


def officer_summary(result: Dict[str, Any]) -> Dict[str, str]:
    """Risk level + plain-words action for one adjudicated sample."""
    if result["verdict"] == "Retake sample":
        return {"level": "RETAKE", "label": "RETAKE SAMPLE",
                "action": "Collect a new water sample at this spot. This one was too poor to "
                          "read, so nothing can be said about the fish here from it."}
    events = result.get("alerts", [])
    confirmed = [e for e in events if e["kind"] == "confirmed"]
    if confirmed:
        top = confirmed[0]
        return {"level": top["level"], "label": top["level"] + " - INVASIVE FISH DETECTED",
                "action": top["action"]}
    if events:
        return {"level": "WATCH", "label": "WATCH - POSSIBLE INVASIVE FISH (NOT CONFIRMED)",
                "action": events[0]["action"]}
    return {"level": "NONE", "label": "NO INVASIVE FISH FOUND IN THIS SAMPLE",
            "action": "No action needed now. Keep the normal monitoring schedule. This is not "
                      "proof the water is free of invasive fish: DNA can miss animals that are "
                      "rare or far away."}


def build_pdf(result: Dict[str, Any], season: Optional[Dict[str, Any]] = None,
              reference_note: str = "") -> bytes:
    meta = result["metadata"]
    summary = officer_summary(result)
    colour = LEVEL_COLOR[summary["level"]]
    p = Page()

    # title
    p.rect(0, PAGE_H - 62, PAGE_W, 62, (0.07, 0.30, 0.22))
    p.text(MARGIN, PAGE_H - 30, "BioRadar - Officer Report", 17, True, (1, 1, 1))
    p.text(MARGIN, PAGE_H - 48, "{}  |  generated {}".format(
        meta.get("label", result["sample_id"]), time.strftime("%Y-%m-%d %H:%M")), 9, False,
        (0.85, 0.95, 0.9))
    p.y = PAGE_H - 62 - 10

    # risk + action
    p.rect(MARGIN, p.y - 52, PAGE_W - 2 * MARGIN, 52, colour)
    p.text(MARGIN + 12, p.y - 17, "RISK LEVEL", 8, True, (1, 1, 1))
    p.text(MARGIN + 12, p.y - 34, summary["label"], 14, True, (1, 1, 1))
    p.y -= 58
    p.heading("What to do")
    p.para(summary["action"], 12, True, lead=1.35)

    # animals
    p.heading("Animals detected (share of the fish DNA reads that could be named)")
    species = [s for s in result["species"] if s["kind"] == "species" and s["status"] == "detected"]
    complexes = [s for s in result["species"] if s["kind"] == "complex"]
    flagged = {e["species"] for e in result.get("alerts", [])}
    if result["verdict"] == "Retake sample" or not (species or complexes):
        p.para("No animals can be reported from this sample.", 10)
    else:
        rows = (species + complexes)[:9]
        mx = max(r["share"] for r in rows) or 1.0
        for r in rows:
            p.y -= 14.5
            tag = "  [INVASIVE]" if r["species"] in flagged else (
                "  [cannot be separated]" if r["kind"] == "complex" else "")
            rgb = (0.78, 0.13, 0.13) if r["species"] in flagged else (0.1, 0.1, 0.12)
            p.text(MARGIN, p.y, (r["species"][:34] + tag), 9, r["species"] in flagged, rgb)
            bar = 175 * r["share"] / mx
            p.rect(MARGIN + 232, p.y - 1, max(bar, 1.5), 9,
                   (0.78, 0.13, 0.13) if r["species"] in flagged else (0.20, 0.50, 0.42))
            p.text(MARGIN + 232 + max(bar, 1.5) + 6, p.y, "{:.1%}  ({:,} reads)".format(
                r["share"], r["reads"]), 8.5)
        named = sum(r["reads"] for r in result["species"])
        p.para("Share = reads of the animal / {:,} reads that could be named. A share is a proportion of DNA "
               "reads, not a count of animals or their weight.".format(named), 8, rgb=(0.4, 0.4, 0.45))
        if len(species) + len(complexes) > 9:
            p.para("... and {} more in the full table.".format(
                len(species) + len(complexes) - 9), 8.5)
        maybe = [e for e in result.get("alerts", []) if e["kind"] == "possible"]
        if maybe:
            p.y -= 4
            names = "; ".join("{} (not separable from {})".format(
                e["species"], ", ".join(c for c in e["candidates"] if c != e["species"]) or "other species")
                for e in maybe[:3])
            p.para("Possible invasive fish, NOT confirmed: " + names + ".", 9, True,
                   rgb=(0.55, 0.42, 0.0))

    # source
    p.heading("Source and sample date")
    where = meta.get("location") or "location not recorded"
    if meta.get("latitude") is not None:
        where += "  ({:.4f}, {:.4f})".format(meta["latitude"], meta["longitude"])
    p.para("Sample: {}   |   Collected: {}   |   Place: {}".format(
        meta.get("alias", result["sample_id"]), meta.get("collection_date") or "not recorded", where), 9.5)
    p.para("Public archive: {} ({}), run {}.".format(
        meta.get("bioproject", ""), meta.get("dataset_title", ""), result["sample_id"]), 9)

    # uncertainty
    p.heading("Uncertainty and missing coverage")
    s = result["summary"]
    tot = max(result["reads_total"], 1)
    bullets = [
        "Sample verdict: {}. {}.".format(result["verdict"], "; ".join(result["verdict_reasons"])),
        "{:.0%} of reads were kept as species calls, {:.0%} are unknown or need review, {:.0%} were "
        "dropped by quality checks.".format(s["kept"]["reads"] / tot, s["unknown"]["reads"] / tot,
                                          s["dropped"]["reads"] / tot),
        "{:,} different DNA fragments could not be named. They are NOT identified: each is queued "
        "for an expert to review, with its closest match shown.".format(s["unknown"]["distinct"]),
        "Only fish in the reference list ({:,} species) can be named. A fish that is missing from "
        "it shows up as unknown, never under a wrong name.".format(result["reference"]["species"]),
    ]
    if meta.get("coordinate_note"):
        bullets.append("Map pin: " + meta["coordinate_note"] + ".")
    if season:
        bullets.append("Season: {} species in summer, {} in winter at this place; {} only in summer, "
                       "{} only in winter. 'Not detected' does not mean absent.".format(
                           season["summer"]["species_detected"], season["winter"]["species_detected"],
                           season["counts"]["summer_only"], season["counts"]["winter_only"]))
    else:
        bullets.append("Season: no summer/winter pair is available for this place, so no seasonal "
                       "change can be reported.")
    ec = result.get("expected_check", {})
    if ec and not ec.get("available"):
        bullets.append("No published ground truth was available for this sample's species split.")
    for b in bullets:
        p.para("-  " + b, 9, x=MARGIN + 4, width=PAGE_W - 2 * MARGIN - 8)

    p.y = 58
    p.rect(MARGIN, 52, PAGE_W - 2 * MARGIN, 0.6, (0.7, 0.72, 0.75))
    p.text(MARGIN, 40, _latin("Generated live from real public sequence data. Reference: " +
                              (reference_note or "RefSeq fish mitogenomes (MiFish-U amplicon)")), 7.5, False,
           (0.4, 0.4, 0.45))
    p.text(MARGIN, 30, "Invasive-species listing: IUCN Global Invasive Species Database "
                       "(iucngisd.org). Thresholds: bioradar/adjudicate/thresholds.json.", 7.5, False,
           (0.4, 0.4, 0.45))
    if p.truncated:
        p.text(MARGIN, FOOTER_TOP - 2, "Some detail was cut to keep this report to one page; see the app for the full result.",
               7.5, False, (0.55, 0.42, 0.0))
    return p.to_pdf()


# --------------------------------------------------------------------------
# site report: one place, both seasons
# --------------------------------------------------------------------------

_LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}


def site_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Highest invasive alert across every sample at the site, in plain words."""
    if all(r["verdict"] == "Retake sample" for r in results):
        return {"level": "RETAKE", "label": "RETAKE SAMPLES AT THIS SITE", "top": None,
                "action": "Collect new water samples at this spot. The samples taken here were too poor to read."}
    confirmed: Dict[str, Dict[str, Any]] = {}
    possible: Dict[str, Dict[str, Any]] = {}
    for r in results:
        for e in r.get("alerts", []):
            bucket = confirmed if e["kind"] == "confirmed" else possible
            old = bucket.get(e["species"])
            if old is None or (_LEVEL_ORDER[e["level"]], -e["reads"]) < (_LEVEL_ORDER[old["level"]], -old["reads"]):
                bucket[e["species"]] = e
    if confirmed:
        top = sorted(confirmed.values(), key=lambda e: (_LEVEL_ORDER[e["level"]], -e["reads"]))[0]
        return {"level": top["level"], "label": top["level"] + " - INVASIVE FISH DETECTED AT THIS SITE",
                "action": top["action"], "top": top, "confirmed": confirmed, "possible": possible}
    if possible:
        top = sorted(possible.values(), key=lambda e: -e["reads"])[0]
        return {"level": "WATCH", "label": "WATCH - POSSIBLE INVASIVE FISH (NOT CONFIRMED)",
                "action": top["action"], "top": top, "confirmed": {}, "possible": possible}
    return {"level": "NONE", "label": "NO INVASIVE FISH FOUND AT THIS SITE", "top": None,
            "confirmed": {}, "possible": {},
            "action": "No action needed now. Keep the normal monitoring schedule. This is not proof the "
                      "water is free of invasive fish: DNA can miss animals that are rare or far away."}


def build_site_pdf(site: Dict[str, Any], results: List[Dict[str, Any]], reference_note: str = "") -> bytes:
    """One-page report for a place sampled in two seasons (data = pre-run results)."""
    summ = site_summary(results)
    p = Page()
    p.rect(0, PAGE_H - 62, PAGE_W, 62, (0.07, 0.30, 0.22))
    p.text(MARGIN, PAGE_H - 30, "BioRadar - Site Officer Report", 17, True, (1, 1, 1))
    p.text(MARGIN, PAGE_H - 48, "{}  |  summer and winter  |  generated {}".format(
        site["location"], time.strftime("%Y-%m-%d %H:%M")), 9, False, (0.85, 0.95, 0.9))
    p.y = PAGE_H - 62 - 10

    p.rect(MARGIN, p.y - 52, PAGE_W - 2 * MARGIN, 52, LEVEL_COLOR[summ["level"]])
    p.text(MARGIN + 12, p.y - 17, "RISK LEVEL", 8, True, (1, 1, 1))
    p.text(MARGIN + 12, p.y - 34, summ["label"], 13, True, (1, 1, 1))
    p.y -= 58
    p.heading("What to do")
    p.para(summ["action"], 12, True, lead=1.35)
    top = summ.get("top")
    if top:
        p.para("Where: {} ({}), seen at pin {}.".format(top["common_name"], top["species"],
               "{:.4f}, {:.4f}".format(top["pin"]["latitude"], top["pin"]["longitude"])
               if top["pin"]["latitude"] is not None else "not recorded"), 9.5)

    # animals, both seasons
    p.heading("Animals detected: summer vs winter (DNA reads)")
    flagged = set(summ.get("confirmed", {}))
    rows = site["species"][:10]
    if rows:
        mx = max(max(r["summer_reads"], r["winter_reads"]) for r in rows) or 1
        p.text(MARGIN + 205, p.y - 11, "summer", 7.5, True, (0.78, 0.45, 0.05))
        p.text(MARGIN + 205 + 60, p.y - 11, "winter", 7.5, True, (0.25, 0.40, 0.70))
        p.y -= 12
        for r in rows:
            p.y -= 15
            bad = r["species"] in flagged
            p.text(MARGIN, p.y, r["species"][:30] + ("  [INVASIVE]" if bad else ""), 9, bad,
                   (0.78, 0.13, 0.13) if bad else (0.1, 0.1, 0.12))
            for k, (key, col) in enumerate((("summer_reads", (0.88, 0.50, 0.08)), ("winter_reads", (0.30, 0.45, 0.75)))):
                w = 150 * r[key] / mx
                p.rect(MARGIN + 205, p.y + 5 - 5 * k, max(w, 1.0) if r[key] else 0, 4, col)
            p.text(MARGIN + 365, p.y, "{:,} / {:,}".format(r["summer_reads"], r["winter_reads"]), 8.5)
    c = site["counts"]
    p.para("{} species detected in summer, {} in winter. {} seen in both; {} only in summer; {} only in winter. "
           "'Only in' means not detected in the other season's bottles. It does not mean absent.".format(
               site["summer"]["species_detected"], site["winter"]["species_detected"],
               c["both"], c["summer_only"], c["winter_only"]), 8.5, rgb=(0.3, 0.3, 0.35))
    possible = summ.get("possible", {})
    if possible and not flagged:
        names = "; ".join("{} (not separable from {})".format(
            e["species"], ", ".join(x for x in e["candidates"] if x != e["species"]) or "other species")
            for e in list(possible.values())[:3])
        p.para("Possible invasive fish, NOT confirmed: " + names + ".", 9, True, rgb=(0.55, 0.42, 0.0))

    # source
    p.heading("Source and sample dates")
    first = results[0]["metadata"]
    where = site["location"]
    if site.get("latitude") is not None:
        where += " ({:.4f}, {:.4f})".format(site["latitude"], site["longitude"])
    p.para("Place: {}.   Summer: {} sample(s) collected {}.   Winter: {} sample(s) collected {}.".format(
        where, site["summer"]["samples"], ", ".join(site["summer"]["dates"]),
        site["winter"]["samples"], ", ".join(site["winter"]["dates"])), 9.5)
    p.para("Public archive: {} ({}). Runs: {}.".format(
        first.get("bioproject", ""), first.get("dataset_title", ""),
        ", ".join(site["summer"]["sample_ids"] + site["winter"]["sample_ids"])), 8.5)

    # uncertainty
    p.heading("Uncertainty and missing coverage")
    def read_share(rs: List[Dict[str, Any]]) -> str:
        tot = sum(max(r["reads_total"], 1) for r in rs)
        named = sum(r["summary"]["kept"]["reads"] for r in rs)
        return "{:.0%}".format(named / tot)
    by = {"summer": [r for r in results if r["sample_id"] in site["summer"]["sample_ids"]],
          "winter": [r for r in results if r["sample_id"] in site["winter"]["sample_ids"]]}
    bullets = [
        "Sample quality - summer: {}. Winter: {}. Reads named to a species: {} (summer), {} (winter); the rest were "
        "dropped by quality checks or could not be named.".format(
            ", ".join(sorted(set(site["summer"]["verdicts"]))), ", ".join(sorted(set(site["winter"]["verdicts"]))),
            read_share(by["summer"]), read_share(by["winter"])),
        "Only fish in the reference list ({:,} species) can be named. A fish missing from it appears as unknown, "
        "never under a wrong name; unknown sequences are queued for expert review.".format(
            results[0]["reference"]["species"]),
        "A season with poorer reads can show fewer species because of the data, not because of the water.",
    ]
    if site.get("coordinate_note"):
        bullets.append("Map pin: " + site["coordinate_note"] + ".")
    for b in bullets:
        p.para("-  " + b, 9, x=MARGIN + 4, width=PAGE_W - 2 * MARGIN - 8)

    p.rect(MARGIN, 52, PAGE_W - 2 * MARGIN, 0.6, (0.7, 0.72, 0.75))
    p.text(MARGIN, 40, _latin("Generated live from real public sequence data. Reference: " +
                              (reference_note or "RefSeq fish mitogenomes (MiFish-U amplicon)")), 7.5, False,
           (0.4, 0.4, 0.45))
    p.text(MARGIN, 30, "Invasive-species listing: IUCN Global Invasive Species Database (iucngisd.org). "
                       "Thresholds: bioradar/adjudicate/thresholds.json.", 7.5, False, (0.4, 0.4, 0.45))
    if p.truncated:
        p.text(MARGIN, FOOTER_TOP - 2, "Some detail was cut to keep this report to one page; see the app for the full result.",
               7.5, False, (0.55, 0.42, 0.0))
    return p.to_pdf()
