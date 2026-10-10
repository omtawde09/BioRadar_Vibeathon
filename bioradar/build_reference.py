"""Build an India-curated COI reference database for classifier training.

This is the artifact behind BioRadar's central claim. Every eDNA tool runs the
same denoiser; what decides whether an Indian sample yields a name or an
"Unassigned" is the reference database behind the classifier. Global databases
are dominated by North American and European records, so Indian sequences are
systematically under-represented and Indian samples systematically under-called.

The reference is assembled in two passes:

1. **India first.** Every COI record from NCBI for the target phyla that is
   annotated to India. These are the sequences a global database under-weights.
2. **Global top-up.** For phyla where Indian coverage is too thin to classify
   anything at all -- Echinodermata has 55 Indian COI records, Porifera has 48 --
   global records are added so the classifier can at least reach family or genus.

Both passes are recorded in `sources.csv`, so you can state exactly how much of
any assignment rests on Indian reference material. That number is the honest
version of "India-curated", and it is more defensible than a claim.

Output is QIIME2-ready and matches the lineage convention the shipped MIDORI2
classifier uses (`k__Name_taxid;p__Name_taxid;...`), so `bioradar.normalize`
parses the results with no changes.

    python -m bioradar.build_reference -o data/reference_coi_india
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

from bioradar.fetch_data import _urlopen

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI allows 3 requests/second without an API key.
_THROTTLE = 0.35

COI_TERM = (
    "(COI[Gene] OR CO1[Gene] OR cox1[Gene] OR "
    '"cytochrome c oxidase subunit I"[All Fields])'
)
LENGTH_TERM = "300:2000[SLEN]"

# Rank prefixes, matching the MIDORI2 convention the pipeline already emits.
# Iteration order defines the order of segments in the emitted lineage, so the
# top rank must come first. NCBI renamed "superkingdom" to "domain"; both are
# accepted so the builder works against old and current taxonomy dumps.
RANK_PREFIX = {
    "domain": "k",
    "superkingdom": "k",
    "phylum": "p",
    "class": "c",
    "order": "o",
    "family": "f",
    "genus": "g",
    "species": "s",
}

# (phylum, scope, cap). scope="india" restricts to Indian records.
# Caps keep the training set trainable on a 16 GB laptop -- the full global COI
# database needs far more RAM than a hackathon machine has.
DEFAULT_SPEC: tuple[tuple[str, str, int], ...] = (
    # Indian records: take everything for the under-represented marine phyla.
    ("Annelida", "india", 2000),
    ("Mollusca", "india", 4000),
    ("Echinodermata", "india", 2000),
    ("Cnidaria", "india", 2000),
    ("Porifera", "india", 2000),
    ("Platyhelminthes", "india", 1000),
    ("Nematoda", "india", 1000),
    ("Crustacea", "india", 5000),
    ("Chordata", "india", 4000),
    # Global top-up where Indian coverage cannot support classification.
    ("Echinodermata", "global", 5000),
    ("Cnidaria", "global", 4000),
    ("Porifera", "global", 3000),
    ("Annelida", "global", 5000),
    ("Bryozoa", "global", 2500),
)


# NCBI returns 502/503 intermittently under load. A job this size makes a few
# hundred calls, so a transient failure is near-certain; retrying is not
# optional.
_MAX_ATTEMPTS = 5


def _retry(operation, description: str):
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            if attempt == _MAX_ATTEMPTS:
                raise
            backoff = 2**attempt
            print(
                f"\n    {description} failed ({type(exc).__name__}); "
                f"retry {attempt}/{_MAX_ATTEMPTS - 1} in {backoff}s",
                end="",
                flush=True,
            )
            time.sleep(backoff)
    raise RuntimeError("unreachable")


def _get(url: str, timeout: int = 120) -> str:
    def once() -> str:
        time.sleep(_THROTTLE)
        with _urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    return _retry(once, "GET")


def _post(endpoint: str, params: dict[str, str], timeout: int = 180) -> str:
    """POST to E-utilities.

    Batches of accession IDs blow past the ~2 KB practical limit on a GET URL
    and NCBI answers 414. E-utilities accepts the same parameters as a form
    body, which has no such limit.
    """
    import urllib.request

    from bioradar.fetch_data import _ssl_context

    def once() -> str:
        time.sleep(_THROTTLE)
        request = urllib.request.Request(
            f"{EUTILS}/{endpoint}",
            data=urllib.parse.urlencode(params).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(
            request, timeout=timeout, context=_ssl_context()
        ) as response:
            return response.read().decode("utf-8", errors="replace")

    return _retry(once, f"POST {endpoint}")


def esearch(term: str, retmax: int) -> list[str]:
    """Return accession UIDs matching a query."""
    params = urllib.parse.urlencode(
        {"db": "nuccore", "term": term, "retmax": str(retmax), "retmode": "json"}
    )
    payload = json.loads(_get(f"{EUTILS}/esearch.fcgi?{params}"))
    return payload["esearchresult"].get("idlist", [])


def esummary_taxids(uids: list[str]) -> dict[str, str]:
    """Map nucleotide UID -> NCBI taxid."""
    mapping: dict[str, str] = {}
    for batch in _batched(uids, 400):
        try:
            # strict=False: NCBI occasionally emits raw control characters
            # inside record titles, which is invalid JSON by the letter of the
            # spec and aborts the whole batch otherwise.
            result = json.loads(
                _post(
                    "esummary.fcgi",
                    {"db": "nuccore", "id": ",".join(batch), "retmode": "json"},
                ),
                strict=False,
            )["result"]
        except (ValueError, KeyError):
            continue
        for uid in result.get("uids", []):
            record = result[uid]
            taxid = str(record.get("taxid", "")).strip()
            if taxid and taxid != "0":
                mapping[uid] = taxid
    return mapping


def efetch_fasta(uids: list[str]) -> dict[str, str]:
    """Fetch sequences, keyed by UID order within each batch."""
    sequences: dict[str, str] = {}
    for batch in _batched(uids, 300):
        text = _post(
            "efetch.fcgi",
            {
                "db": "nuccore",
                "id": ",".join(batch),
                "rettype": "fasta",
                "retmode": "text",
            },
        )
        for index, block in enumerate(text.split(">")):
            if not block.strip():
                continue
            lines = block.splitlines()
            accession = lines[0].split()[0]
            sequence = "".join(lines[1:]).strip().upper()
            # Reject sequences with heavy ambiguity: they train the classifier
            # toward noise and QIIME2's extract-reads will drop them anyway.
            if not sequence or sequence.count("N") > len(sequence) * 0.02:
                continue
            if index - 1 < len(batch):
                sequences[batch[index - 1]] = f"{accession}\t{sequence}"
    return sequences


def efetch_lineages(taxids: Iterable[str]) -> dict[str, str]:
    """Map taxid -> `k__..;p__..;..;s__..` lineage string."""
    import xml.etree.ElementTree as ElementTree

    lineages: dict[str, str] = {}
    unique = sorted(set(taxids))
    for batch in _batched(unique, 180):
        xml = _post("efetch.fcgi", {"db": "taxonomy", "id": ",".join(batch)})

        # Parsed as a tree rather than by regex: <Taxon> nests inside
        # <LineageEx><Taxon>, so any split on the tag mixes a record with its
        # own ancestors and every rank above species is lost.
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError:
            continue

        for taxon in root.findall("Taxon"):
            taxid = (taxon.findtext("TaxId") or "").strip()
            if not taxid:
                continue

            ranks: dict[str, tuple[str, str]] = {}
            lineage_ex = taxon.find("LineageEx")
            if lineage_ex is not None:
                for ancestor in lineage_ex.findall("Taxon"):
                    rank = (ancestor.findtext("Rank") or "").strip()
                    if rank in RANK_PREFIX:
                        ranks[rank] = (
                            (ancestor.findtext("ScientificName") or "").strip(),
                            (ancestor.findtext("TaxId") or "").strip(),
                        )

            own_rank = (taxon.findtext("Rank") or "").strip()
            if own_rank in RANK_PREFIX:
                ranks[own_rank] = (
                    (taxon.findtext("ScientificName") or "").strip(),
                    taxid,
                )

            segments = [
                f"{RANK_PREFIX[rank]}__{ranks[rank][0]}_{ranks[rank][1]}"
                for rank in RANK_PREFIX
                if rank in ranks and ranks[rank][0]
            ]
            if segments:
                lineages[taxid] = ";".join(segments)
    return lineages


def _batched(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build(
    spec: tuple[tuple[str, str, int], ...] = DEFAULT_SPEC,
    cache_dir: Path | None = None,
) -> tuple[dict[str, str], dict[str, str], list[dict[str, Any]]]:
    """Collect sequences and lineages for every (phylum, scope) in the spec.

    Each group is checkpointed to disk as it completes. The full fetch is several
    hundred throttled NCBI calls over 10+ minutes; losing all of it to a dropped
    connection or a sleeping laptop is not acceptable, so a re-run resumes from
    the last completed group.
    """
    records: dict[str, str] = {}      # uid -> "accession\tsequence"
    record_taxid: dict[str, str] = {}
    provenance: list[dict[str, Any]] = []

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    for phylum, scope, cap in spec:
        cache_file = cache_dir / f"{phylum}.{scope}.{cap}.json" if cache_dir else None
        if cache_file and cache_file.is_file():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                records.update(cached["records"])
                record_taxid.update(cached["taxids"])
                provenance.append(cached["provenance"])
                print(
                    f"  {phylum:<16} {scope:<7} "
                    f"{cached['provenance']['added']:,} sequences (cached)"
                )
                continue
            except (ValueError, KeyError):
                cache_file.unlink(missing_ok=True)

        term = f"{COI_TERM} AND {phylum}[Organism] AND {LENGTH_TERM}"
        if scope == "india":
            term += " AND India[All Fields]"

        print(f"  {phylum:<16} {scope:<7} ", end="", flush=True)
        uids = esearch(term, cap)
        if not uids:
            print("0 records")
            continue

        new_uids = [u for u in uids if u not in records]
        taxids = esummary_taxids(new_uids)
        sequences = efetch_fasta([u for u in new_uids if u in taxids])

        added = 0
        for uid, entry in sequences.items():
            records[uid] = entry
            record_taxid[uid] = taxids[uid]
            added += 1

        entry = {"phylum": phylum, "scope": scope, "requested": cap, "added": added}
        provenance.append(entry)
        print(f"{added:,} sequences")

        if cache_file:
            cache_file.write_text(
                json.dumps(
                    {
                        "records": {u: records[u] for u in sequences},
                        "taxids": {u: taxids[u] for u in sequences},
                        "provenance": entry,
                    }
                ),
                encoding="utf-8",
            )

    print(f"\n  resolving lineages for {len(set(record_taxid.values())):,} taxa...")
    lineages = efetch_lineages(record_taxid.values())

    fasta: dict[str, str] = {}
    taxonomy: dict[str, str] = {}
    for uid, entry in records.items():
        accession, sequence = entry.split("\t", 1)
        lineage = lineages.get(record_taxid[uid])
        if not lineage or "s__" not in lineage:
            # Without at least a species-level name the record cannot teach the
            # classifier anything it does not already get from a genus record.
            continue
        fasta[accession] = sequence
        taxonomy[accession] = lineage

    return fasta, taxonomy, provenance


def write_reference(
    output: Path,
    fasta: dict[str, str],
    taxonomy: dict[str, str],
    provenance: list[dict[str, Any]],
) -> None:
    output.mkdir(parents=True, exist_ok=True)

    with (output / "reference.fasta").open("w", encoding="utf-8") as handle:
        for accession, sequence in fasta.items():
            handle.write(f">{accession}\n{sequence}\n")

    # HeaderlessTSVTaxonomyFormat: id<TAB>lineage, no header row.
    with (output / "reference.taxon").open("w", encoding="utf-8") as handle:
        for accession, lineage in taxonomy.items():
            handle.write(f"{accession}\t{lineage}\n")

    import csv

    with (output / "sources.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["phylum", "scope", "requested", "added"]
        )
        writer.writeheader()
        writer.writerows(provenance)


def summarize(taxonomy: dict[str, str], provenance: list[dict[str, Any]]) -> None:
    import collections

    phyla = collections.Counter()
    species = set()
    for lineage in taxonomy.values():
        match = re.search(r"p__(.+?)_\d+(?:;|$)", lineage)
        if match:
            phyla[match.group(1)] += 1
        match = re.search(r"s__(.+?)_\d+(?:;|$)", lineage)
        if match:
            species.add(match.group(1))

    india = sum(p["added"] for p in provenance if p["scope"] == "india")
    total = sum(p["added"] for p in provenance)

    print()
    print(f"  sequences kept   : {len(taxonomy):,}")
    print(f"  distinct species : {len(species):,}")
    print(f"  Indian records   : {india:,} of {total:,} fetched "
          f"({100 * india / total:.0f}%)" if total else "")
    print(f"  phyla            : {dict(phyla.most_common(10))}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.build_reference",
        description="Build an India-curated COI reference for classifier training.",
    )
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="multiply every per-phylum cap (0.5 = half size, faster)",
    )
    args = parser.parse_args(argv)

    spec = tuple(
        (phylum, scope, max(1, int(cap * args.scale)))
        for phylum, scope, cap in DEFAULT_SPEC
    )

    print("Building India-curated COI reference from NCBI")
    print("=" * 46)
    try:
        fasta, taxonomy, provenance = build(spec, cache_dir=args.output / ".cache")
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not taxonomy:
        print("error: no usable records retrieved", file=sys.stderr)
        return 1

    write_reference(args.output, fasta, taxonomy, provenance)
    summarize(taxonomy, provenance)
    print(f"\n  written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
