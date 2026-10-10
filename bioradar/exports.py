"""Get the data back out: CSV, JSON, Darwin Core Archive, printable report.

The gap analysis is blunt about why this matters -- "without export, BioRadar is
a data sink" -- and it is right. A forest officer attaching evidence to a
quarantine order needs a document, not a URL.

Four formats, and the reasoning for each:

  CSV      one row per detection, the frozen contract verbatim. What a
           researcher opens in R or pandas.
  JSON     the full analysis object, for anything programmatic.
  DwC-A    Darwin Core Archive with the GBIF DNA-derived data extension. This
           is the format GBIF and OBIS ingest, and producing it is what turns
           BioRadar from a consumer of the biodiversity commons into a
           contributor.
  HTML     a self-contained, print-optimised document. Ctrl-P gives a PDF.

On the two formats the analysis asked for that are *not* here: a native PDF
writer and .xlsx both need third-party libraries (ReportLab/WeasyPrint,
openpyxl), and this package is stdlib-only so that it can be imported inside the
pipeline image without rebuilding 11.7 GB. The print stylesheet produces a
publication-quality PDF through the browser, and Excel opens the CSV. Neither
substitution costs the user anything real.

What this module deliberately does *not* do is submit to GBIF. Publishing to a
global public registry is irreversible, requires a registered publishing
organisation and credentials, and is the user's decision to make -- so BioRadar
builds the archive and hands it over.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioradar.contract import TAXONOMY_COLUMNS, UNASSIGNED

# GBIF's Darwin Core Archive uses these namespaces. The DNA-derived data
# extension is what makes an eDNA record more than a dot on a map: it carries
# the sequence, the primers and the method, so somebody else can judge the
# detection rather than take it on faith.
DWC_NS = "http://rs.tdwg.org/dwc/terms/"
DNA_EXT = "http://rs.gbif.org/terms/1.0/DNADerivedData"

OCCURRENCE_FIELDS = (
    "occurrenceID",
    "basisOfRecord",
    "eventID",
    "eventDate",
    "decimalLatitude",
    "decimalLongitude",
    "geodeticDatum",
    "coordinateUncertaintyInMeters",
    "country",
    "countryCode",
    "locality",
    "scientificName",
    "taxonRank",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "taxonID",
    "organismQuantity",
    "organismQuantityType",
    "occurrenceStatus",
    "identificationRemarks",
    "identificationVerificationStatus",
    "samplingProtocol",
    "recordedBy",
    "associatedSequences",
)

DNA_FIELDS = (
    "occurrenceID",
    "DNA_sequence",
    "target_gene",
    "target_subfragment",
    "pcr_primer_forward",
    "pcr_primer_reverse",
    "pcr_primer_name_forward",
    "pcr_primer_name_reverse",
    "seq_meth",
    "otu_class_appr",
    "otu_seq_comp_appr",
    "otu_db",
    "sop",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    keep = [c if c.isalnum() or c in "-_" else "-" for c in str(value)]
    return "".join(keep).strip("-") or "bioradar"


# --------------------------------------------------------------------------
# CSV / JSON
# --------------------------------------------------------------------------


def detections_csv(detections: List[Dict[str, str]]) -> bytes:
    """The frozen contract, unchanged. Deliberately not prettified.

    Columns are written in contract order even if the input dict happens to be
    ordered differently, so that a consumer can rely on position as well as name.
    """
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=list(TAXONOMY_COLUMNS), extrasaction="ignore"
    )
    writer.writeheader()
    for row in detections:
        writer.writerow({key: row.get(key, "") for key in TAXONOMY_COLUMNS})
    # utf-8-sig: Excel on Windows reads a plain UTF-8 CSV as the system codepage
    # and mangles every accented species name. The BOM is what makes the
    # difference between "Pseudacris crucifer" and mojibake in the one tool a
    # manager will actually open the file in.
    return buffer.getvalue().encode("utf-8-sig")


def species_csv(analysis: Dict[str, Any]) -> bytes:
    """One row per taxon -- the inventory, not the raw detections."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "scientific_name",
            "rank",
            "taxon_id",
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
            "read_count",
            "sample_count",
            "site_count",
            "asv_count",
            "max_confidence",
            "unidentified_placeholder",
        ]
    )
    for entry in analysis.get("species", []):
        writer.writerow(
            [
                entry["name"],
                entry["rank"],
                entry.get("taxon_id", ""),
                entry.get("kingdom", ""),
                entry.get("phylum", ""),
                entry.get("class", ""),
                entry.get("order", ""),
                entry.get("family", ""),
                entry["reads"],
                len(entry.get("samples", ())),
                len(entry.get("sites", ())),
                len(entry.get("asvs", ())),
                round(float(entry.get("max_confidence", 0)), 4),
                "yes" if entry.get("placeholder") else "no",
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")


def samples_csv(analysis: Dict[str, Any]) -> bytes:
    buffer = io.StringIO(newline="")
    columns = [
        "sample_id",
        "site_id",
        "latitude",
        "longitude",
        "collected_at",
        "total_reads",
        "asv_count",
        "species_count",
        "genus_count",
        "unassigned_reads",
        "unassigned_pct",
        "shannon",
        "simpson",
    ]
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in analysis.get("samples", []):
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8-sig")


def analysis_json(analysis: Dict[str, Any], meta: Dict[str, Any]) -> bytes:
    """The whole analysis, sets flattened to sorted lists so it round-trips."""

    def default(obj: Any) -> Any:
        if isinstance(obj, (set, frozenset)):
            return sorted(obj)
        return str(obj)

    payload = {"bioradar": meta, "analysis": analysis}
    return json.dumps(payload, indent=2, default=default, ensure_ascii=False).encode("utf-8")


# --------------------------------------------------------------------------
# Darwin Core Archive
# --------------------------------------------------------------------------


def _meta_xml() -> str:
    """The descriptor that tells an IPT how to read the two data files."""

    def fields(names: tuple, namespace: str, start: int) -> str:
        return "\n".join(
            '      <field index="{i}" term="{ns}{term}"/>'.format(
                i=index, ns=namespace, term=name
            )
            for index, name in enumerate(names)
            if index >= start
        )

    return """<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/">
  <core encoding="UTF-8" fieldsTerminatedBy="\\t" linesTerminatedBy="\\n"
        fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="{dwc}Occurrence">
    <files><location>occurrence.txt</location></files>
    <id index="0"/>
      <field index="0" term="{dwc}occurrenceID"/>
{core_fields}
  </core>
  <extension encoding="UTF-8" fieldsTerminatedBy="\\t" linesTerminatedBy="\\n"
             fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="{dna}">
    <files><location>dna.txt</location></files>
    <coreid index="0"/>
{dna_fields}
  </extension>
</archive>
""".format(
        dwc=DWC_NS,
        dna=DNA_EXT,
        core_fields=fields(OCCURRENCE_FIELDS, DWC_NS, 1),
        dna_fields=fields(DNA_FIELDS, DNA_EXT + "/", 1),
    )


def _eml_xml(meta: Dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    return """<?xml version="1.0" encoding="UTF-8"?>
<eml:eml xmlns:eml="eml://ecoinformatics.org/eml-2.1.1"
         packageId="{package}" system="BioRadar" scope="system"
         xml:lang="eng">
  <dataset>
    <title>{title}</title>
    <creator>
      <organizationName>{org}</organizationName>
    </creator>
    <pubDate>{date}</pubDate>
    <language>eng</language>
    <abstract>
      <para>{abstract}</para>
    </abstract>
    <intellectualRights>
      <para>Rights not yet asserted. Set a licence before publishing.</para>
    </intellectualRights>
    <methods>
      <methodStep>
        <description>
          <para>{methods}</para>
        </description>
      </methodStep>
    </methods>
  </dataset>
</eml:eml>
""".format(
        package=esc(meta.get("run_id", "bioradar")),
        title=esc(meta.get("title", "BioRadar eDNA survey")),
        org=esc(meta.get("organisation", "BioRadar")),
        date=esc(meta.get("generated_at", _now())[:10]),
        abstract=esc(
            "Environmental DNA metabarcoding detections produced by BioRadar. "
            "Each occurrence is a sequence variant assigned to a taxon by a "
            "naive Bayes classifier; organismQuantity is the read count, which "
            "is a relative and not an absolute measure of abundance."
        ),
        methods=esc(
            "Paired-end reads were primer-trimmed with cutadapt, denoised into "
            "amplicon sequence variants with DADA2 (or clustered at 97% with "
            "vsearch where quality scores were unavailable), and classified "
            "against {db} using a naive Bayes classifier. "
            "Pipeline: {image}.".format(
                db=meta.get("reference", "an India-curated COI reference"),
                image=meta.get("image", "ghcr.io/omtawde09/bioradar-pipeline:v1.0"),
            )
        ),
    )


def _tsv(rows: List[Dict[str, Any]], fields: tuple) -> bytes:
    """Darwin Core text files are tab-delimited with no quoting.

    That means a literal tab or newline inside a value would silently shift every
    subsequent column, so they are stripped rather than escaped -- there is no
    escaping mechanism in the format to use.
    """
    buffer = io.StringIO(newline="")
    buffer.write("\t".join(fields) + "\n")
    for row in rows:
        cells = []
        for field in fields:
            value = row.get(field, "")
            text = "" if value is None else str(value)
            cells.append(text.replace("\t", " ").replace("\n", " ").replace("\r", " "))
        buffer.write("\t".join(cells) + "\n")
    return buffer.getvalue().encode("utf-8")


def darwin_core_archive(
    detections: List[Dict[str, str]],
    analysis: Dict[str, Any],
    sample_meta: Optional[List[Dict[str, str]]] = None,
    *,
    meta: Optional[Dict[str, Any]] = None,
    sequences: Optional[Dict[str, str]] = None,
) -> bytes:
    """Build a GBIF/OBIS-ready Darwin Core Archive as ZIP bytes.

    Unassigned detections are excluded. An occurrence record asserts that a named
    organism was present; "Unassigned" asserts nothing, and publishing thousands
    of them to GBIF would be pollution rather than contribution.
    """
    meta = dict(meta or {})
    meta.setdefault("generated_at", _now())
    by_sample = {s["sample_id"]: s for s in (sample_meta or [])}
    site_of = {s["sample_id"]: s for s in analysis.get("samples", [])}

    occurrences: List[Dict[str, Any]] = []
    dna_rows: List[Dict[str, Any]] = []

    for row in detections:
        if row.get("rank") == UNASSIGNED or not row.get("scientific_name"):
            continue
        reads = int(float(row.get("read_count") or 0))
        if reads <= 0:
            continue

        sample_id = row["sample_id"]
        sheet = by_sample.get(sample_id, {})
        summary = site_of.get(sample_id, {})
        latitude = sheet.get("latitude") or summary.get("latitude") or ""
        longitude = sheet.get("longitude") or summary.get("longitude") or ""

        occurrence_id = "{run}:{sample}:{asv}".format(
            run=meta.get("run_id", "bioradar"),
            sample=sample_id,
            asv=row.get("asv_id", ""),
        )
        confidence = row.get("confidence") or ""

        occurrences.append(
            {
                "occurrenceID": occurrence_id,
                # MaterialSample, not HumanObservation: nobody saw the organism.
                # A DNA fragment in a water sample is what was observed, and
                # Darwin Core has a term for exactly that distinction.
                "basisOfRecord": "MaterialSample",
                "eventID": sample_id,
                "eventDate": sheet.get("collected_at", "") or meta.get("event_date", ""),
                "decimalLatitude": latitude,
                "decimalLongitude": longitude,
                "geodeticDatum": "WGS84" if latitude else "",
                "coordinateUncertaintyInMeters": sheet.get(
                    "coordinate_uncertainty", ""
                ),
                "country": meta.get("country", ""),
                "countryCode": meta.get("country_code", ""),
                "locality": sheet.get("locality", "") or sheet.get("site_id", ""),
                "scientificName": row["scientific_name"],
                "taxonRank": row.get("rank", ""),
                "kingdom": row.get("kingdom", ""),
                "phylum": row.get("phylum", ""),
                "class": row.get("class", ""),
                "order": row.get("order", ""),
                "family": row.get("family", ""),
                "genus": row.get("genus", ""),
                "taxonID": "NCBI:txid" + row["taxon_id"] if row.get("taxon_id") else "",
                "organismQuantity": reads,
                # Read counts are not individuals and must never be read as
                # such; naming the unit is how the record stays honest.
                "organismQuantityType": "DNA sequence reads",
                "occurrenceStatus": "present",
                "identificationRemarks": (
                    "Naive Bayes assignment, confidence {c}".format(c=confidence)
                    if confidence
                    else ""
                ),
                "identificationVerificationStatus": row.get(
                    "verification_status", "unverified"
                ),
                "samplingProtocol": "environmental DNA metabarcoding",
                "recordedBy": meta.get("recorded_by", ""),
                "associatedSequences": meta.get("bioproject", ""),
            }
        )

        dna_rows.append(
            {
                "occurrenceID": occurrence_id,
                "DNA_sequence": (sequences or {}).get(row.get("asv_id", ""), ""),
                "target_gene": meta.get("target_gene", ""),
                "target_subfragment": meta.get("target_subfragment", ""),
                "pcr_primer_forward": meta.get("fprimer", ""),
                "pcr_primer_reverse": meta.get("rprimer", ""),
                "pcr_primer_name_forward": meta.get("fprimer_name", ""),
                "pcr_primer_name_reverse": meta.get("rprimer_name", ""),
                "seq_meth": meta.get("seq_meth", "Illumina paired-end"),
                "otu_class_appr": (
                    "dada2; ASV" if meta.get("denoiser", "dada2") == "dada2"
                    else "vsearch; 97% OTU"
                ),
                "otu_seq_comp_appr": "naive Bayes classifier (scikit-learn), QIIME 2",
                "otu_db": meta.get("reference", ""),
                "sop": meta.get("sop", "https://github.com/omtawde09/BioRadar"),
            }
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("occurrence.txt", _tsv(occurrences, OCCURRENCE_FIELDS))
        archive.writestr("dna.txt", _tsv(dna_rows, DNA_FIELDS))
        archive.writestr("meta.xml", _meta_xml())
        archive.writestr("eml.xml", _eml_xml(meta))
        archive.writestr(
            "README.txt",
            (
                "Darwin Core Archive produced by BioRadar\n"
                "========================================\n\n"
                "Occurrences : {n}\n"
                "Generated   : {when}\n"
                "Run         : {run}\n\n"
                "This archive is ready to upload to a GBIF or OBIS IPT instance.\n"
                "BioRadar does not submit it for you: publishing to a global\n"
                "registry is irreversible and needs a registered publishing\n"
                "organisation, so that step stays with you.\n\n"
                "Before publishing, set a licence in eml.xml (GBIF requires one)\n"
                "and check that decimalLatitude/decimalLongitude are populated --\n"
                "records without coordinates are accepted but far less useful.\n\n"
                "organismQuantity is a READ COUNT, not a number of individuals.\n"
                "eDNA read counts are relative; they depend on primer affinity,\n"
                "biomass and shedding rate, and must not be reported as\n"
                "abundance.\n"
            ).format(n=len(occurrences), when=meta["generated_at"], run=meta.get("run_id", "")).encode("utf-8"),
        )
    return buffer.getvalue()


def archive_stats(detections: List[Dict[str, str]]) -> Dict[str, int]:
    """What the export button should say before you press it."""
    usable = [
        r for r in detections
        if r.get("rank") != UNASSIGNED
        and r.get("scientific_name")
        and int(float(r.get("read_count") or 0)) > 0
    ]
    return {
        "detections": len(detections),
        "occurrences": len(usable),
        "excluded_unassigned": len(detections) - len(usable),
    }


# --------------------------------------------------------------------------
# Printable report
# --------------------------------------------------------------------------

_PRINT_CSS = """
:root { --ink:#1a1f2e; --muted:#5b6472; --rule:#d4dae4; --accent:#4a42c0;
        --invasive:#c0392b; --rare:#b9770e; }
* { box-sizing:border-box; }
body { font:11pt/1.5 "Inter",-apple-system,Segoe UI,Roboto,sans-serif;
       color:var(--ink); margin:0; padding:32px; background:#fff; max-width:900px; }
h1 { font-size:22pt; margin:0 0 4px; letter-spacing:-.01em; }
h2 { font-size:13pt; margin:28px 0 10px; padding-bottom:6px;
     border-bottom:2px solid var(--rule); }
h3 { font-size:11pt; margin:18px 0 8px; }
.sub { color:var(--muted); font-size:10pt; margin-bottom:20px; }
table { width:100%; border-collapse:collapse; margin:10px 0 18px; font-size:9.5pt; }
th { text-align:left; border-bottom:1.5px solid var(--ink); padding:6px 8px;
     font-weight:600; }
td { border-bottom:1px solid var(--rule); padding:5px 8px; }
tr:nth-child(even) td { background:#f7f9fc; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
em { font-style:italic; }
.kpis { display:flex; flex-wrap:wrap; gap:10px; margin:16px 0 8px; }
.kpi { border:1px solid var(--rule); border-radius:6px; padding:10px 14px;
       min-width:118px; }
.kpi .v { font-size:19pt; font-weight:700; line-height:1.1; }
.kpi .k { font-size:8pt; color:var(--muted); text-transform:uppercase;
          letter-spacing:.06em; }
.note { border-left:3px solid var(--accent); background:#f4f3ff; padding:10px 14px;
        margin:14px 0; font-size:9.5pt; }
.chain { font-family:"JetBrains Mono",ui-monospace,monospace; font-size:8pt;
         word-break:break-all; color:var(--muted); }
footer { margin-top:32px; padding-top:12px; border-top:1px solid var(--rule);
         font-size:8.5pt; color:var(--muted); }
@media print {
  body { padding:0; }
  h2 { break-after:avoid; }
  table { break-inside:auto; }
  tr { break-inside:avoid; }
  .no-print { display:none; }
}
"""


def printable_report(
    analysis: Dict[str, Any],
    meta: Dict[str, Any],
) -> bytes:
    """A self-contained HTML document that prints to a clean PDF.

    No external stylesheet, no script, no network reference -- so it survives
    being emailed, opened offline, or attached to a file that outlives the app.
    """

    def esc(value: Any) -> str:
        return (
            str(value if value is not None else "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    species = analysis.get("species", [])
    species_level = [s for s in species if s["rank"] == "species"]
    named = [s for s in species_level if not s.get("placeholder")]
    placeholders = [s for s in species_level if s.get("placeholder")]
    samples = analysis.get("samples", [])
    total_reads = sum(s["total_reads"] for s in samples)
    unassigned = sum(s["unassigned_reads"] for s in samples)

    rows = []
    rows.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    rows.append("<title>{t}</title>".format(t=esc(meta.get("title", "BioRadar report"))))
    rows.append("<style>{css}</style></head><body>".format(css=_PRINT_CSS))

    rows.append("<h1>{t}</h1>".format(t=esc(meta.get("title", "BioRadar biodiversity report"))))
    rows.append(
        "<div class='sub'>{region} &middot; generated {when} &middot; BioRadar Layer 1</div>".format(
            region=esc(meta.get("region", "")),
            when=esc(analysis.get("generated_at", _now())),
        )
    )

    rows.append("<div class='kpis'>")
    for value, label in (
        (len(named), "Named species"),
        (len(analysis.get("phyla", [])), "Phyla"),
        (len(samples), "Samples"),
        (len(analysis.get("site_species", {})), "Sites"),
        ("{:,}".format(total_reads), "Total reads"),
        ("{:.1f}%".format(100 * unassigned / total_reads if total_reads else 0),
         "No reference match"),
    ):
        rows.append(
            "<div class='kpi'><div class='v'>{v}</div><div class='k'>{k}</div></div>".format(
                v=esc(value), k=esc(label)
            )
        )
    rows.append("</div>")

    if not named:
        rows.append(
            "<div class='note'><strong>No named species were identified.</strong> "
            "Every assignment stopped above species level. This usually means the "
            "reference database does not cover the taxa present, not that the "
            "water was sterile.</div>"
        )

    rows.append("<h2>Sites and samples</h2>")
    rows.append(
        "<table><tr><th>Sample</th><th>Site</th><th>Latitude</th><th>Longitude</th>"
        "<th class='num'>Reads</th><th class='num'>ASVs</th>"
        "<th class='num'>Species</th><th class='num'>Shannon</th>"
        "<th class='num'>Unassigned</th></tr>"
    )
    for s in samples:
        rows.append(
            "<tr><td>{sid}</td><td>{site}</td><td>{lat}</td><td>{lon}</td>"
            "<td class='num'>{reads:,}</td><td class='num'>{asv}</td>"
            "<td class='num'>{sp}</td><td class='num'>{sh}</td>"
            "<td class='num'>{un}%</td></tr>".format(
                sid=esc(s["sample_id"]), site=esc(s["site_id"]),
                lat=esc(s.get("latitude", "")), lon=esc(s.get("longitude", "")),
                reads=s["total_reads"], asv=s["asv_count"], sp=s["species_count"],
                sh=s["shannon"], un=s["unassigned_pct"],
            )
        )
    rows.append("</table>")

    if species_level:
        rows.append("<h2>Species inventory</h2>")
        rows.append(
            "<table><tr><th>Species</th><th>Phylum</th><th>Family</th>"
            "<th class='num'>Reads</th><th class='num'>Sites</th>"
            "<th class='num'>Confidence</th></tr>"
        )
        for entry in species_level:
            mark = " &dagger;" if entry.get("placeholder") else ""
            rows.append(
                "<tr><td><em>{n}</em>{m}</td><td>{p}</td><td>{f}</td>"
                "<td class='num'>{r:,}</td><td class='num'>{s}</td>"
                "<td class='num'>{c:.3f}</td></tr>".format(
                    n=esc(entry["name"]), m=mark, p=esc(entry.get("phylum", "")),
                    f=esc(entry.get("family", "")), r=entry["reads"],
                    s=len(entry.get("sites", ())),
                    c=float(entry.get("max_confidence", 0)),
                )
            )
        rows.append("</table>")
        if placeholders:
            rows.append(
                "<div class='note'>&dagger; An unidentified NCBI "
                "<em>&lt;taxon&gt; sp.</em> record, not a named species. The "
                "classifier resolved no further than that group. "
                "{n} of {t} species-level records are of this kind.</div>".format(
                    n=len(placeholders), t=len(species_level)
                )
            )

    if analysis.get("phyla"):
        rows.append("<h2>Composition by phylum</h2>")
        rows.append("<table><tr><th>Phylum</th><th class='num'>Reads</th>"
                    "<th class='num'>Share</th></tr>")
        phylum_total = sum(c for _, c in analysis["phyla"]) or 1
        for name, count in analysis["phyla"]:
            rows.append(
                "<tr><td>{n}</td><td class='num'>{c:,}</td>"
                "<td class='num'>{p:.1f}%</td></tr>".format(
                    n=esc(name), c=count, p=100 * count / phylum_total
                )
            )
        rows.append("</table>")

    rows.append("<h2>Provenance</h2>")
    rows.append("<table>")
    for key, value in (
        ("Pipeline image", meta.get("image", "")),
        ("Classifier", meta.get("classifier", "")),
        ("Denoiser", meta.get("denoiser", "")),
        ("Forward primer", meta.get("fprimer", "")),
        ("Reverse primer", meta.get("rprimer", "")),
        ("Run id", meta.get("run_id", "")),
    ):
        if value:
            rows.append("<tr><td>{k}</td><td>{v}</td></tr>".format(k=esc(key), v=esc(value)))
    rows.append("</table>")
    if meta.get("artifact_hash"):
        rows.append(
            "<p class='chain'>Chain-of-custody SHA-256: {h}</p>".format(
                h=esc(meta["artifact_hash"])
            )
        )

    rows.append(
        "<footer>Read counts are relative measures of DNA abundance and must not "
        "be reported as counts of individuals. Detections are probabilistic "
        "classifier assignments; confirm ecologically significant results in the "
        "field before acting on them.<br>Generated by BioRadar &mdash; "
        "github.com/omtawde09/BioRadar</footer>"
    )
    rows.append("</body></html>")
    return "\n".join(rows).encode("utf-8")


def export_filename(kind: str, run_id: str) -> str:
    stem = _slug(run_id)
    return {
        "detections.csv": "{s}-detections.csv",
        "species.csv": "{s}-species.csv",
        "samples.csv": "{s}-samples.csv",
        "analysis.json": "{s}-analysis.json",
        "dwca.zip": "{s}-dwca.zip",
        "report.html": "{s}-report.html",
    }.get(kind, "{s}-export").format(s=stem)
