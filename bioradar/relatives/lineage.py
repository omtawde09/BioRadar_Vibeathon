"""Evolutionary history for the reference: the NCBI Taxonomy lineage of every reference entry.

    python -m bioradar.relatives lineage      # fetch once (about 40 small NCBI requests)

The lineage is the "evolutionary history" channel of the relative finder: when the nearest
relatives of an unknown sequence share a family but not a genus, the hypothesis is stated at
family level. It is classification, not a phylogeny built here, and it is only as current as
the NCBI Taxonomy snapshot recorded in `lineage.json`.

Standard library only; Python 3.8 compatible.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from bioradar.adjudicate.reference import REF_DIR

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
LINEAGE_TSV = REF_DIR / "lineage.tsv"
LINEAGE_META = REF_DIR / "lineage.json"
RANKS = ["class", "order", "family", "genus"]  # ranks a hypothesis can be stated at
BATCH = 200


def _get(url: str, timeout: int = 120) -> bytes:
    from bioradar.fetch_data import _urlopen  # TLS context that works behind AV proxies
    for attempt in range(3):
        try:
            with _urlopen(url, timeout=timeout) as response:
                return response.read()
        except Exception:  # network blips: retry twice, then raise
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 3)
    raise RuntimeError("unreachable")


def _reference_accessions() -> List[str]:
    accs = []
    with (REF_DIR / "reference.fasta").open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                accs.append(line[1:].split("|", 1)[0].strip())
    return accs


def _taxids_for(accessions: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for start in range(0, len(accessions), BATCH):
        batch = accessions[start:start + BATCH]
        query = urllib.parse.urlencode({"db": "nuccore", "id": ",".join(batch), "retmode": "json"})
        doc = json.loads(_get(EUTILS + "esummary.fcgi?" + query))
        result = doc.get("result", {})
        for uid in result.get("uids", []):
            rec = result[uid]
            tid = str(rec.get("taxid") or "")
            for key in (rec.get("accessionversion", ""), rec.get("caption", "")):
                if key and tid:
                    out[key] = tid
                    out[key.split(".")[0]] = tid
        time.sleep(0.4)  # NCBI allows 3 requests/s without a key
    return out


def _lineages_for(taxids: List[str]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for start in range(0, len(taxids), BATCH):
        batch = taxids[start:start + BATCH]
        query = urllib.parse.urlencode({"db": "taxonomy", "id": ",".join(batch), "retmode": "xml"})
        root = ET.fromstring(_get(EUTILS + "efetch.fcgi?" + query))
        for taxon in root.findall("Taxon"):
            tid = taxon.findtext("TaxId", "")
            row = {"scientific_name": taxon.findtext("ScientificName", "")}
            path = []
            for node in taxon.findall("LineageEx/Taxon"):
                rank, name = node.findtext("Rank", ""), node.findtext("ScientificName", "")
                if rank in RANKS:
                    row[rank] = name
                if rank not in ("no rank", "clade"):
                    path.append("{}:{}".format(rank, name))
            row["lineage"] = "; ".join(path)
            out[tid] = row
        time.sleep(0.4)
    return out


def fetch() -> Path:
    """Fetch taxid + lineage for every reference accession and write lineage.tsv."""
    accs = _reference_accessions()
    taxids = _taxids_for(accs)
    lineages = _lineages_for(sorted(set(taxids.values())))
    rows = []
    for acc in accs:
        tid = taxids.get(acc) or taxids.get(acc.split(".")[0], "")
        lin = lineages.get(tid, {})
        rows.append({"accession": acc, "taxid": tid,
                     "ncbi_name": lin.get("scientific_name", ""),
                     "class": lin.get("class", ""), "order": lin.get("order", ""),
                     "family": lin.get("family", ""), "genus": lin.get("genus", ""),
                     "lineage": lin.get("lineage", "")})
    with LINEAGE_TSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    LINEAGE_META.write_text(json.dumps({
        "source": "NCBI Taxonomy via E-utilities (esummary nuccore -> taxid; efetch taxonomy -> LineageEx)",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reference_entries": len(rows),
        "entries_without_taxid": sum(1 for r in rows if not r["taxid"]),
        "entries_without_family": sum(1 for r in rows if not r["family"]),
        "ranks": RANKS,
        "note": "Classification from NCBI Taxonomy, not a phylogeny inferred by BioRadar.",
    }, indent=2), encoding="utf-8")
    return LINEAGE_TSV


def load(path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """accession -> {taxid, ncbi_name, class, order, family, genus, lineage}. Empty if absent."""
    path = Path(path) if path else LINEAGE_TSV
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["accession"]: row for row in csv.DictReader(handle, delimiter="\t")}


def meta() -> Dict[str, str]:
    return json.loads(LINEAGE_META.read_text(encoding="utf-8")) if LINEAGE_META.is_file() else {}
