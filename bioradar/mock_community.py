"""Build a labelled synthetic eDNA dataset for demos and testing.

Why this exists: real public Indian eDNA datasets either lack the species that
make a compelling demonstration, or were submitted with quality scores stripped.
Waiting for a perfect dataset is not a plan three days before a deadline.

What this is NOT: invented sequence data. Every read here is simulated **from a
real COI reference sequence** already in `data/reference_coi_india/` -- the same
database the classifier was trained on. So when the pipeline reports
*Gambusia holbrooki*, that is a genuine classification of a genuine
*Gambusia holbrooki* sequence, not a fabricated result. This technique is a
standard *in silico* mock community, routinely used to validate metabarcoding
workflows.

What is simulated: which species are present at which site, in what abundance,
plus sequencing error and quality scores. That is the experimental design, and
it is declared, not hidden -- every output directory carries a DATASET_INFO.md
saying so, and every read header is tagged `SIMULATED`.

Use it to demonstrate the platform. Do not present it as field data.

    python -m bioradar.mock_community -o data/demo_survey

Output is a normal FASTQ directory: upload it to the app like any other dataset.
"""

from __future__ import annotations

import argparse
import gzip
import random
import re
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AMPLICONS = REPO_ROOT / "runs" / "_amplicons" / "amplicons.fasta"
DEFAULT_TAXONOMY = REPO_ROOT / "data" / "reference_coi_india" / "reference.taxon"

# Leray primers -- the reads carry them because cutadapt trims with
# --discard-untrimmed, so a read without its primer is thrown away.
FORWARD_PRIMER = "GGWACWGGWTGAACWGTWTAYCCYCC"
REVERSE_PRIMER = "TANACYTCNGGRTGNCCRAARAAYCA"

_COMPLEMENT = str.maketrans("ACGTNRYSWKMBDHV", "TGCANYRSWMKVHDB")

# IUPAC codes must be resolved to real bases: a sequencer emits ACGT, never W.
_AMBIGUOUS = {
    "R": "AG", "Y": "CT", "S": "GC", "W": "AT", "K": "GT", "M": "AC",
    "B": "CGT", "D": "AGT", "H": "ACT", "V": "ACG", "N": "ACGT",
}


def reverse_complement(sequence: str) -> str:
    return sequence.translate(_COMPLEMENT)[::-1]


def resolve_ambiguity(sequence: str, rng: random.Random) -> str:
    return "".join(
        rng.choice(_AMBIGUOUS[base]) if base in _AMBIGUOUS else base
        for base in sequence.upper()
    )


# --------------------------------------------------------------------------
# The scenario
# --------------------------------------------------------------------------

# Real coordinates. The sites are real places; the biology at them is simulated.
SITES: list[dict[str, Any]] = [
    {
        "id": "GOA-MANDOVI", "name": "Mandovi Estuary, Goa",
        "lat": 15.4989, "lon": 73.8278, "state": "Goa",
        "story": "invaded", "invasive": "Gambusia holbrooki",
    },
    {
        "id": "KER-VEMBANAD", "name": "Vembanad Lake, Kerala",
        "lat": 9.6000, "lon": 76.4000, "state": "Kerala",
        "story": "invaded", "invasive": "Oreochromis mossambicus",
    },
    {
        "id": "AP-KOLLERU", "name": "Kolleru Lake, Andhra Pradesh",
        "lat": 16.6000, "lon": 81.2000, "state": "Andhra Pradesh",
        "story": "invaded", "invasive": "Pterygoplichthys pardalis",
    },
    {
        "id": "LD-KAVARATTI", "name": "Kavaratti Lagoon, Lakshadweep",
        "lat": 10.5667, "lon": 72.6167, "state": "Lakshadweep",
        "story": "protected",
    },
    {
        "id": "TN-MANNAR", "name": "Gulf of Mannar, Tamil Nadu",
        "lat": 9.1000, "lon": 79.1000, "state": "Tamil Nadu",
        "story": "protected",
    },
    {
        "id": "AN-PORTBLAIR", "name": "South Andaman",
        "lat": 11.6234, "lon": 92.7265, "state": "Andaman & Nicobar",
        "story": "reference",
    },
]

# Species drawn from the India-curated reference. `role` drives the narrative;
# `abundance` is the base read share before per-site variation.
COMMUNITY: list[dict[str, Any]] = [
    # Native / fishery background
    {"species": "Rastrelliger kanagurta", "role": "native", "abundance": "high"},
    {"species": "Epinephelus coioides", "role": "native", "abundance": "medium"},
    {"species": "Epinephelus areolatus", "role": "native", "abundance": "low"},
    {"species": "Acanthurus mata", "role": "native", "abundance": "medium"},
    {"species": "Turbinella pyrum", "role": "protected", "abundance": "low"},
    # Threatened -- the conservation headline
    # Olive ridley: India's mass-nesting sea turtle (Odisha), IUCN Vulnerable and
    # Schedule I under the Wildlife Protection Act. Chosen over hawksbill because
    # the reference actually carries a Leray amplicon for it.
    {"species": "Lepidochelys olivacea", "role": "endangered", "abundance": "trace",
     "iucn": "Vulnerable, WPA Schedule I",
     "sites": ["LD-KAVARATTI", "TN-MANNAR", "AP-KOLLERU"]},
    {"species": "Chelonia mydas", "role": "endangered", "abundance": "trace",
     "iucn": "Endangered", "sites": ["TN-MANNAR", "AN-PORTBLAIR"]},
    # Invasive -- the alert headline
    {"species": "Gambusia holbrooki", "role": "invasive", "abundance": "high"},
    {"species": "Oreochromis mossambicus", "role": "invasive", "abundance": "high"},
    {"species": "Pterygoplichthys pardalis", "role": "invasive", "abundance": "medium"},
    {"species": "Clarias gariepinus", "role": "invasive", "abundance": "medium"},
    {"species": "Cyprinus carpio", "role": "invasive", "abundance": "low"},
]

ABUNDANCE_READS = {"high": (2500, 6000), "medium": (700, 2200),
                   "low": (150, 600), "trace": (25, 120)}

# Filled in by main() from audit_reference().
SUSPECT: "set[str]" = set()


# --------------------------------------------------------------------------
# Reference lookup
# --------------------------------------------------------------------------


def audit_reference(
    amplicons: Path, taxonomy: Path
) -> "list[dict[str, Any]]":
    """Find amplicons claimed by species from different taxonomic orders.

    Two species in the same genus sharing a barcode is ordinary -- COI does not
    separate every recent split, and tilapia are a well-known example. Two
    species in *different orders* sharing one is not possible biologically, so
    one of the records is mislabelled in the source database.

    This found a real one: OR430267.1 (*Oreochromis mossambicus*, Cichliformes)
    and PX218311.1 (*Planiliza macrolepis*, Mugiliformes) differ by a single base
    in 313. Reads simulated from the first were classified as the second, which
    is exactly the failure a curated reference is supposed to prevent.
    """
    order_of: dict[str, str] = {}
    species_of: dict[str, str] = {}
    with taxonomy.open(encoding="utf-8") as handle:
        for line in handle:
            accession, _, lineage = line.rstrip().partition("	")
            species = re.search(r"s__(.+?)_\d+(?:;|$)", lineage)
            order = re.search(r"o__(.+?)_\d+(?:;|$)", lineage)
            if species:
                species_of[accession] = species.group(1)
            if order:
                order_of[accession] = order.group(1)

    sequences: dict[str, str] = {}
    accession = None
    chunks: list[str] = []

    def flush() -> None:
        if accession is not None and chunks:
            sequences[accession] = "".join(chunks)

    with amplicons.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                flush()
                accession = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line.strip())
    flush()

    # Near-identical, not just identical: the real mislabel we found differs by
    # a single base. Comparing all pairs would be 350M comparisons, so bucket by
    # the first and last 40 bases -- two sequences a few bases apart must share
    # at least one anchor -- and only compare within buckets.
    buckets: dict[str, list[str]] = {}
    for accession, sequence in sequences.items():
        if len(sequence) < 90:
            continue
        for anchor in (sequence[:40], sequence[-40:]):
            buckets.setdefault(anchor, []).append(accession)

    def distance(a: str, b: str, limit: int) -> int:
        if abs(len(a) - len(b)) > limit:
            return limit + 1
        seen = 0
        for x, y in zip(a, b):
            if x != y:
                seen += 1
                if seen > limit:
                    return seen
        return seen

    MAX_DIFFS = 3
    conflicts: list[dict[str, Any]] = []
    reported: set[tuple[str, str]] = set()

    for members in buckets.values():
        if len(members) < 2:
            continue
        for index, first in enumerate(members):
            for second in members[index + 1:]:
                pair = tuple(sorted((first, second)))
                if pair in reported:
                    continue
                order_a = order_of.get(first, "?")
                order_b = order_of.get(second, "?")
                if order_a == order_b or "?" in (order_a, order_b):
                    continue
                diffs = distance(sequences[first], sequences[second], MAX_DIFFS)
                if diffs > MAX_DIFFS:
                    continue
                reported.add(pair)
                conflicts.append(
                    {
                        "orders": sorted({order_a, order_b}),
                        "differences": diffs,
                        "records": [
                            f"{first} ({species_of.get(first, '?')})",
                            f"{second} ({species_of.get(second, '?')})",
                        ],
                    }
                )
    return conflicts


def suspect_accessions(conflicts: "list[dict[str, Any]]") -> "set[str]":
    """Accessions involved in a cross-order collision, so we can avoid them."""
    return {
        record.split()[0]
        for conflict in conflicts
        for record in conflict["records"]
    }


def load_reference(
    amplicons: Path, taxonomy: Path
) -> dict[str, list[tuple[str, str]]]:
    """species name -> [(accession, amplicon sequence)] from the real reference."""
    species_of: dict[str, str] = {}
    with taxonomy.open(encoding="utf-8") as handle:
        for line in handle:
            accession, _, lineage = line.rstrip().partition("\t")
            match = re.search(r"s__(.+?)_\d+(?:;|$)", lineage)
            if match:
                species_of[accession] = match.group(1)

    by_species: dict[str, list[tuple[str, str]]] = {}
    accession = None
    chunks: list[str] = []

    def flush() -> None:
        if accession is None:
            return
        species = species_of.get(accession)
        if species:
            by_species.setdefault(species, []).append((accession, "".join(chunks)))

    with amplicons.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                flush()
                accession = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line.strip())
    flush()
    return by_species


# --------------------------------------------------------------------------
# Read simulation
# --------------------------------------------------------------------------


def quality_profile(length: int, position: int, rng: random.Random) -> int:
    """Illumina-like Phred: strong at the start, decaying along the read.

    The decay matters. DADA2 learns its error model from the relationship
    between quality and observed error, so flat or unrealistic quality is
    exactly what made the real Lakshadweep data unusable.
    """
    fraction = position / max(1, length - 1)
    base = 38 - 14 * (fraction**2.2)
    return max(12, min(40, int(rng.gauss(base, 1.8))))


def sequence_read(
    template: str, length: int, rng: random.Random
) -> tuple[str, str]:
    """Emit one read with quality-consistent sequencing error."""
    bases: list[str] = []
    qualities: list[str] = []
    for position in range(length):
        base = template[position] if position < len(template) else rng.choice("ACGT")
        score = quality_profile(length, position, rng)
        # Error probability implied by the Phred score, so the simulated errors
        # and the simulated quality tell the same story.
        if rng.random() < 10 ** (-score / 10):
            base = rng.choice([b for b in "ACGT" if b != base])
        bases.append(base)
        qualities.append(chr(33 + score))
    return "".join(bases), "".join(qualities)


def build_amplicon(insert: str, rng: random.Random) -> str:
    """Reassemble the full PCR product: primers included, as a sequencer sees it."""
    forward = resolve_ambiguity(FORWARD_PRIMER, rng)
    reverse = resolve_ambiguity(REVERSE_PRIMER, rng)
    return forward + insert + reverse_complement(reverse)


def write_sample(
    path_r1: Path,
    path_r2: Path,
    composition: list[tuple[str, str, int]],
    read_length: int,
    rng: random.Random,
) -> int:
    """Write one paired-end sample. `composition` is (species, insert, reads)."""
    path_r1.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with gzip.open(path_r1, "wt") as r1, gzip.open(path_r2, "wt") as r2:
        for species, insert, count in composition:
            amplicon = build_amplicon(resolve_ambiguity(insert, rng), rng)
            reverse_amplicon = reverse_complement(amplicon)
            tag = species.replace(" ", "_")
            for index in range(count):
                total += 1
                name = f"SIMULATED:{tag}:{total:07d}"
                forward_seq, forward_qual = sequence_read(amplicon, read_length, rng)
                reverse_seq, reverse_qual = sequence_read(
                    reverse_amplicon, read_length, rng
                )
                r1.write(f"@{name} 1:N:0:1\n{forward_seq}\n+\n{forward_qual}\n")
                r2.write(f"@{name} 2:N:0:1\n{reverse_seq}\n+\n{reverse_qual}\n")
    return total


# --------------------------------------------------------------------------
# Scenario assembly
# --------------------------------------------------------------------------


def compose_site(
    site: dict[str, Any],
    round_index: int,
    reference: dict[str, list[tuple[str, str]]],
    rng: random.Random,
    missing: set[str],
) -> list[tuple[str, str, int]]:
    """Decide what is present at one site in one sampling round."""
    composition: list[tuple[str, str, int]] = []

    for entry in COMMUNITY:
        species = entry["species"]
        variants = reference.get(species)
        if not variants:
            missing.add(species)
            continue

        role = entry["role"]
        restricted = entry.get("sites")
        if restricted and site["id"] not in restricted:
            continue

        if role == "invasive":
            # Only the site's own invasive establishes; others appear rarely, as
            # the low-level background detections you really do see.
            if site.get("invasive") == species:
                # The base level is drawn from a per-site generator so both
                # rounds start from the same number. Drawing fresh each round
                # let the random range swamp the growth, and a demo whose
                # headline trend depends on the seed is not a demo.
                low, high = ABUNDANCE_READS[entry["abundance"]]
                site_rng = random.Random(f"invasive:{site['id']}:{species}")
                reads = int(site_rng.randint(low, high) * (1.9**round_index))
            elif site["story"] == "reference" or rng.random() > 0.25:
                continue
            else:
                reads = rng.randint(15, 90)
        elif role == "endangered":
            # Rare by definition, and not present every round.
            if rng.random() > 0.7:
                continue
            low, high = ABUNDANCE_READS[entry["abundance"]]
            reads = rng.randint(low, high)
        else:
            low, high = ABUNDANCE_READS[entry["abundance"]]
            reads = rng.randint(low, high)

        # Prefer variants not implicated in a cross-order collision: simulating
        # from a mislabelled reference record guarantees a wrong answer.
        clean = [v for v in variants if v[0] not in SUSPECT] or variants
        accession, insert = rng.choice(clean)
        composition.append((species, insert, max(1, reads)))

    return composition


def generate(
    output: Path,
    reference: dict[str, list[tuple[str, str]]],
    *,
    rounds: int = 2,
    read_length: int = 250,
    seed: int = 2026,
    scale: float = 1.0,
) -> dict[str, Any]:
    rng = random.Random(seed)
    fastq_dir = output / "fastq"
    samples: list[dict[str, Any]] = []
    missing: set[str] = set()
    manifest: list[dict[str, Any]] = []

    for site in SITES:
        for round_index in range(rounds):
            sample_id = f"BR-{site['id']}-R{round_index + 1:02d}"
            composition = compose_site(site, round_index, reference, rng, missing)
            composition = [
                (s, i, max(1, int(c * scale))) for s, i, c in composition
            ]

            reads = write_sample(
                fastq_dir / f"{sample_id}_S1_L001_R1_001.fastq.gz",
                fastq_dir / f"{sample_id}_S1_L001_R2_001.fastq.gz",
                composition,
                read_length,
                rng,
            )
            samples.append(
                {
                    "sample_id": sample_id,
                    "site_id": site["id"],
                    "site_name": site["name"],
                    "state": site["state"],
                    "latitude": site["lat"],
                    "longitude": site["lon"],
                    "round": round_index + 1,
                    "collected_at": f"2026-0{1 + round_index * 3}-15",
                    "read_pairs": reads,
                }
            )
            manifest.append(
                {
                    "sample_id": sample_id,
                    "species": [
                        {"name": s, "reads": c} for s, _, c in sorted(composition)
                    ],
                }
            )

    return {"samples": samples, "manifest": manifest, "missing": sorted(missing)}


def write_metadata(output: Path, result: dict[str, Any], seed: int) -> None:
    import csv
    import json

    with (output / "samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id", "site_id", "site_name", "state", "latitude",
                "longitude", "round", "collected_at", "read_pairs",
            ],
        )
        writer.writeheader()
        writer.writerows(result["samples"])

    (output / "truth.json").write_text(
        json.dumps(result["manifest"], indent=2), encoding="utf-8"
    )

    invasive = sorted({
        e["species"] for e in COMMUNITY if e["role"] == "invasive"
    })
    endangered = sorted({
        f"{e['species']} ({e.get('iucn', 'threatened')})"
        for e in COMMUNITY if e["role"] == "endangered"
    })

    (output / "DATASET_INFO.md").write_text(
        f"""# Simulated demonstration dataset

**This is synthetic data. Do not present it as field-collected samples.**

## What is real

Every read is simulated from a **real COI reference sequence** in
`data/reference_coi_india/`, the same database the classifier was trained on.
When the pipeline reports a species, it is a genuine classification of a genuine
sequence for that species. The site coordinates are real locations.

## What is simulated

- Which species occur at which site, and in what abundance
- Sequencing error and Phred quality scores
- Sampling dates

In other words: the *experimental design* is invented, the *sequence data* is
derived from real references. This is a standard in-silico mock community, the
usual way to validate a metabarcoding workflow when ground truth is needed.

## Ground truth

`truth.json` lists exactly which species were planted in each sample and at what
read depth. Compare it against the pipeline output to measure recall — that
comparison is a far stronger result to show than a species list alone.

## Scenario

- **{len(SITES)} sites** across the Indian coast, **{max(s['round'] for s in result['samples'])} sampling rounds** each
- Invasive establishment at Mandovi, Vembanad and Kolleru, increasing between
  rounds so temporal comparison has something to find
- Threatened species at Kavaratti, Gulf of Mannar and South Andaman
- South Andaman acts as an uninvaded reference site

Invasive species planted: {', '.join(invasive)}

Threatened species planted: {', '.join(endangered)}

## Reproducing

    python -m bioradar.mock_community -o {output.name} --seed {seed}

Deterministic for a given seed.
""",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.mock_community",
        description="Generate a labelled synthetic eDNA dataset from real references.",
    )
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--amplicons", type=Path, default=DEFAULT_AMPLICONS)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--read-length", type=int, default=250)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--scale", type=float, default=1.0,
        help="multiply every read count (0.2 makes a fast demo dataset)",
    )
    args = parser.parse_args(argv)

    if not args.amplicons.is_file():
        print(
            f"error: {args.amplicons} not found.\n"
            "Extract the amplicons first (see docs/DEMO_DATASET.md).",
            file=sys.stderr,
        )
        return 1

    global SUSPECT
    conflicts = audit_reference(args.amplicons, args.taxonomy)
    SUSPECT = suspect_accessions(conflicts)
    reference = load_reference(args.amplicons, args.taxonomy)
    print(f"reference: {len(reference):,} species with extracted amplicons")
    if conflicts:
        print(
            f"reference QC: {len(conflicts)} amplicon(s) shared across taxonomic "
            f"orders -- {len(SUSPECT)} record(s) avoided as likely mislabelled"
        )
        for conflict in conflicts[:3]:
            print(f"   {' / '.join(conflict['orders'])}: {'; '.join(conflict['records'])}")

    result = generate(
        args.output,
        reference,
        rounds=args.rounds,
        read_length=args.read_length,
        seed=args.seed,
        scale=args.scale,
    )
    write_metadata(args.output, result, args.seed)

    if result["missing"]:
        print(f"WARNING: no reference amplicon for {result['missing']}")
    total = sum(s["read_pairs"] for s in result["samples"])
    print(f"samples  : {len(result['samples'])}")
    print(f"read pairs: {total:,}")
    print(f"written  : {args.output.resolve()}")
    print("\nThis dataset is SIMULATED and labelled as such in DATASET_INFO.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
