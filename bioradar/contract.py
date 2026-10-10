"""The frozen BioRadar integration contract.

Every schema in this module is consumed by more than one team member. Changing a
column name here breaks somebody else's code, so treat this file as an API:
additions are cheap, renames and removals are not.

Derived from the *actual* output of the forked eDNA pipeline (see
`docs/CONTRACTS.md` for how the raw QIIME2 output maps onto these schemas), not
from an idealised design. If the pipeline changes, this file changes with it and
`ci/check_integration.sh` fails loudly.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Taxonomic ranks
# --------------------------------------------------------------------------

# Ordered shallow -> deep. Index position is meaningful: a lineage assigned to
# `family` has every rank up to index 4 populated and the rest empty.
RANKS: tuple[str, ...] = (
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
)

# QIIME2/MIDORI2 emit lineages as "k__Name_taxid;p__Name_taxid;...".
RANK_PREFIXES: dict[str, str] = {
    "k": "kingdom",
    "d": "kingdom",  # some classifiers use d__ (domain) for the top rank
    "p": "phylum",
    "c": "class",
    "o": "order",
    "f": "family",
    "g": "genus",
    "s": "species",
}

# MIDORI2 sometimes repeats the rank word inside the label, producing segments
# like "c__class_Testudines_8459". These words are stripped when they lead a
# label. Kept lowercase; matching is case-insensitive.
REDUNDANT_RANK_WORDS: frozenset[str] = frozenset(
    {
        "domain",
        "superkingdom",
        "kingdom",
        "subkingdom",
        "phylum",
        "subphylum",
        "superclass",
        "class",
        "subclass",
        "infraclass",
        "superorder",
        "order",
        "suborder",
        "infraorder",
        "superfamily",
        "family",
        "subfamily",
        "tribe",
        "genus",
        "subgenus",
        "species",
        "subspecies",
        "no",  # "no_rank"
    }
)

# Value used for the rank field when the classifier returned no assignment.
UNASSIGNED = "unassigned"

# Literal taxon strings the pipeline emits for unclassified ASVs. QIIME2 writes
# "Unassigned"; the upstream create_outputs.py de-duplicates them into
# "Unassigned1", "Unassigned2", ... so we match on the prefix.
UNASSIGNED_PREFIX = "unassigned"


# --------------------------------------------------------------------------
# Schema 1 -- normalized taxonomy (pipeline -> Anshika, Tanay, Parth)
# --------------------------------------------------------------------------

# One row per (sample_id, asv_id) detection. This replaces the wide, one-row-per-
# ASV layout the raw pipeline emits, because every downstream consumer works
# per-sample.
TAXONOMY_COLUMNS: tuple[str, ...] = (
    "sample_id",              # BioRadar sample code, e.g. BR-2026-GOA-001
    "asv_id",                 # md5 feature id from DADA2, stable across runs
    "taxon_id",               # NCBI taxid of the deepest assigned rank ('' if none)
    "scientific_name",        # name at the deepest assigned rank
    "rank",                   # which rank that was: species/genus/.../unassigned
    *RANKS,                   # kingdom..species, '' where unassigned
    "confidence",             # classifier confidence, 0.0-1.0
    "read_count",             # integer reads for this ASV in this sample
    "rel_abundance",          # read_count / total reads in the sample, 6 dp
    "classification_method",  # 'sklearn' (naive Bayes) or 'blast'
    "lineage_raw",            # original semicolon string, kept for provenance
)

# --------------------------------------------------------------------------
# Schema 2 -- per-sample summary (pipeline -> Tanay, Ishwar)
# --------------------------------------------------------------------------

SAMPLE_SUMMARY_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "total_reads",            # sum of all ASV reads, including unassigned
    "asv_count",              # distinct ASVs with >0 reads
    "species_count",          # distinct species-level assignments
    "genus_count",            # distinct genus-level assignments
    "unassigned_reads",       # reads whose lineage was Unassigned
    "unassigned_fraction",    # unassigned_reads / total_reads, 6 dp
)

# --------------------------------------------------------------------------
# Schema 3 -- chain-of-custody record (pipeline -> Parth's backend)
# --------------------------------------------------------------------------

CHAIN_EVENT_FIELDS: tuple[str, ...] = (
    "sample_id",
    "pipeline_run_id",
    "timestamp",              # ISO-8601 UTC with trailing Z
    "event_type",
    "actor",
    "payload_hash",           # sha256 hex of the canonical payload
    "payload",                # dict of per-artifact hashes and run metadata
)

CHAIN_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "pipeline_started",
        "pipeline_complete",
        "pipeline_failed",
        "flagging_complete",
        "cbi_computed",
        "field_verified",
    }
)

# --------------------------------------------------------------------------
# Schema 4 -- Time Machine diff (Om+Jimeet -> Ishwar's Trends view)
# --------------------------------------------------------------------------

TIME_MACHINE_FIELDS: tuple[str, ...] = (
    "site_id",
    "from_sample",
    "to_sample",
    "from_timestamp",
    "to_timestamp",
    "appeared",               # taxa present in `to` but not `from`
    "disappeared",            # taxa present in `from` but not `to`
    "changed",                # taxa in both, with read-count delta
    "stable",                 # taxa in both within the noise threshold
    "summary",                # counts + shannon delta, for the headline number
)

# --------------------------------------------------------------------------
# Sample identity
# --------------------------------------------------------------------------

# The pipeline derives its sample id from the FASTQ filename: everything before
# the first underscore. `sample1_S1_L001_R1_001.fastq.gz` -> `sample1`.
# BioRadar therefore names FASTQ files by BioRadar sample code so the id flows
# through the pipeline untouched. See scripts/create_metadata_file.sh upstream.
FASTQ_R1_SUFFIX = "_R1_001.fastq.gz"
FASTQ_R2_SUFFIX = "_R2_001.fastq.gz"


def sample_id_from_fastq(filename: str) -> str:
    """Reproduce the upstream pipeline's sample-id derivation.

    Matches `sample=${R1%%_*}` in scripts/create_metadata_file.sh. Kept here so
    the backend can predict the sample id before the pipeline runs.
    """
    return filename.split("_", 1)[0]


class ContractError(ValueError):
    """Raised when data does not satisfy a frozen schema."""


def validate_taxonomy_rows(rows: list[dict[str, object]]) -> None:
    """Check normalized taxonomy rows against TAXONOMY_COLUMNS.

    Raises ContractError describing the first problem found. Used by the CI
    integration check and by downstream consumers who want to fail fast.
    """
    expected = set(TAXONOMY_COLUMNS)
    for index, row in enumerate(rows):
        missing = expected - set(row)
        if missing:
            raise ContractError(
                f"row {index}: missing columns {sorted(missing)}"
            )
        extra = set(row) - expected
        if extra:
            raise ContractError(f"row {index}: unexpected columns {sorted(extra)}")

        if not row["sample_id"]:
            raise ContractError(f"row {index}: empty sample_id")
        if not row["asv_id"]:
            raise ContractError(f"row {index}: empty asv_id")

        rank = str(row["rank"])
        if rank != UNASSIGNED and rank not in RANKS:
            raise ContractError(f"row {index}: unknown rank {rank!r}")

        try:
            confidence = float(row["confidence"])
        except (TypeError, ValueError) as exc:
            raise ContractError(
                f"row {index}: confidence {row['confidence']!r} is not numeric"
            ) from exc
        if not 0.0 <= confidence <= 1.0:
            raise ContractError(f"row {index}: confidence {confidence} out of range")

        try:
            read_count = int(row["read_count"])
        except (TypeError, ValueError) as exc:
            raise ContractError(
                f"row {index}: read_count {row['read_count']!r} is not an integer"
            ) from exc
        if read_count < 0:
            raise ContractError(f"row {index}: negative read_count {read_count}")
