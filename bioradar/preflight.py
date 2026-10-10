"""Fail fast, with a useful message, instead of 40 minutes into a run.

Every check here encodes a failure that actually happened while getting real
Indian data through this pipeline. Each one cost between 20 minutes and an hour
before surfacing as a cryptic error deep inside DADA2 or QIIME2:

* **Flat quality scores.** PRJNA1296846 and PRJNA1040471 were both submitted with
  every base at Q30 -- one distinct quality value in the entire file. DADA2 models
  error rate *as a function of* quality, so `learnErrors` fails with "Error rates
  could not be estimated (this is usually because of very few reads)", which
  sends you looking at read counts. The read counts are fine. The data is
  unusable and no parameter fixes it.

* **truncLen longer than the reads.** Primer trimming shortens reads before DADA2
  sees them. Truncating at 240 when the trimmed reads are 226 bp silently filters
  out every read, and DADA2 reports "No reads passed the filter".

* **Wrong primers or wrong mate orientation.** cutadapt runs with
  `--p-discard-untrimmed`, so primers that do not match throw away the entire
  dataset -- quietly, with a zero exit code, until DADA2 has nothing to denoise.

* **Truncation too aggressive to merge.** If trunc_f + trunc_r is less than the
  amplicon plus the minimum overlap, every pair fails to merge and you get zero
  ASVs from a run that reported success at every stage.

Checks are cheap: they read the first few thousand reads of each file.
"""

from __future__ import annotations

import gzip
import re
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# IUPAC ambiguity codes -> regex character classes.
IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T",
    "R": "[AG]", "Y": "[CT]", "S": "[GC]", "W": "[AT]",
    "K": "[GT]", "M": "[AC]", "B": "[CGT]", "D": "[AGT]",
    "H": "[ACT]", "V": "[ACG]", "N": "[ACGT]", "I": "[ACGT]",
}

# DADA2 needs error rates to vary with quality. Two distinct values is already
# marginal; one is fatal.
MIN_QUALITY_LEVELS = 3

# Below this fraction of reads carrying the expected primer, cutadapt's
# --discard-untrimmed will throw away most of the run.
MIN_PRIMER_RATE = 0.05

# DADA2's default minimum overlap for merging pairs.
MIN_MERGE_OVERLAP = 12

# 1,500 reads is ample for every check here -- quality-level diversity, primer
# presence and read length all converge long before that. Larger samples only
# cost gzip decompression time, and this runs on every file.
READS_SAMPLED = 1500


class PreflightError(RuntimeError):
    """A problem serious enough that running the pipeline would waste time."""


@dataclass
class Finding:
    level: str          # "error" or "warning"
    check: str
    message: str
    hint: str = ""

    def render(self) -> str:
        tag = "ERROR" if self.level == "error" else "warn "
        text = f"  [{tag}] {self.check}: {self.message}"
        if self.hint:
            text += f"\n          -> {self.hint}"
        return text


@dataclass
class PreflightResult:
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        if not self.findings:
            return "  all checks passed"
        return "\n".join(f.render() for f in self.findings)


def iupac_regex(primer: str) -> re.Pattern[str]:
    return re.compile("".join(IUPAC.get(c, c) for c in primer.upper()))


def _read_records(path: Path, limit: int = READS_SAMPLED) -> tuple[list[str], list[str]]:
    """Return (sequences, qualities) from the first `limit` reads."""
    sequences: list[str] = []
    qualities: list[str] = []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", errors="replace") as handle:  # type: ignore[operator]
        for index, line in enumerate(handle):
            position = index % 4
            if position == 1:
                sequences.append(line.strip())
            elif position == 3:
                qualities.append(line.strip())
                if len(qualities) >= limit:
                    break
    return sequences, qualities


# A FASTQ under a few hundred bytes cannot hold a usable library; a single file
# over this is either not what the user thinks it is or will not finish on a
# laptop. Both are worth saying before the run rather than after.
MIN_FASTQ_BYTES = 200
MAX_FASTQ_BYTES = 8 * 1024 ** 3

# Enough reads for DADA2 to fit an error model. Below this it will either fail
# outright or produce a model built on noise.
MIN_READS = 100


def check_integrity(path: Path) -> list[Finding]:
    """Catch a corrupt or mislabelled file now, not 30 minutes into DADA2.

    Truncated downloads are the single most common cause of a pipeline run that
    dies deep inside R with an error nobody can read. gzip carries a CRC32 and a
    length in its trailer precisely so this is detectable, and checking costs one
    decompression of a file we are about to decompress anyway.
    """
    findings: list[Finding] = []
    name = path.name

    if not path.is_file():
        return [Finding("error", "integrity", f"{name}: file is missing")]

    size = path.stat().st_size
    if size < MIN_FASTQ_BYTES:
        return [
            Finding(
                "error",
                "integrity",
                f"{name}: {size} bytes -- too small to contain reads",
                "The upload or download was probably interrupted. Re-transfer it.",
            )
        ]
    if size > MAX_FASTQ_BYTES:
        findings.append(
            Finding(
                "warning",
                "integrity",
                f"{name}: {size / 1e9:.1f} GB",
                "A file this large will take hours on a laptop and may exhaust "
                "memory during denoising. Consider subsampling for the demo.",
            )
        )

    is_gzip = str(path).endswith(".gz")
    if is_gzip:
        with path.open("rb") as handle:
            magic = handle.read(2)
        if magic != b"\x1f\x8b":
            return [
                Finding(
                    "error",
                    "integrity",
                    f"{name}: named .gz but is not gzip data",
                    "The file was probably decompressed and re-named, or renamed "
                    "by a download manager. Check what it actually is.",
                )
            ]

    # Read the whole file so gzip verifies its trailing CRC32 and size. Reading
    # only the first few reads -- which every other check here does -- would sail
    # straight past a file truncated at 90%.
    reads = 0
    first_char = ""
    try:
        opener = gzip.open if is_gzip else open
        with opener(path, "rt", errors="replace") as handle:  # type: ignore[operator]
            for index, line in enumerate(handle):
                if index == 0:
                    first_char = line[:1]
                if index % 4 == 0:
                    reads += 1
    except (OSError, EOFError, zlib.error) as exc:
        return [
            Finding(
                "error",
                "integrity",
                f"{name}: {type(exc).__name__} while reading -- the file is truncated "
                "or corrupt",
                "gzip's checksum did not match. Re-download or re-upload this file; "
                "the pipeline would fail on it several minutes in.",
            )
        ]

    if first_char and first_char != "@":
        findings.append(
            Finding(
                "error",
                "integrity",
                f"{name}: first line does not start with '@'",
                "This is not FASTQ. A FASTA file (starting '>') is the usual "
                "mix-up; the pipeline needs reads with quality scores.",
            )
        )
    if reads < MIN_READS:
        findings.append(
            Finding(
                "error",
                "integrity",
                f"{name}: only {reads} read(s)",
                f"DADA2 needs at least ~{MIN_READS} reads to fit an error model. "
                "This file is effectively empty.",
            )
        )
    return findings


def check_quality_encoding(path: Path) -> tuple[Finding | None, int]:
    """Reject reads whose quality scores carry no information."""
    _, qualities = _read_records(path)
    if not qualities:
        return (
            Finding("error", "quality", f"{path.name} contains no reads"),
            0,
        )

    levels = Counter()
    for quality in qualities:
        levels.update(quality)

    distinct = len(levels)
    if distinct < MIN_QUALITY_LEVELS:
        value = ord(next(iter(levels))) - 33 if distinct == 1 else None
        detail = f"only {distinct} distinct quality value"
        if value is not None:
            detail += f" (Q{value} for every base)"
        return (
            Finding(
                "error",
                "quality",
                f"{path.name}: {detail}",
                "DADA2 models error rate as a function of quality and cannot "
                "learn from flat scores. This dataset was submitted with "
                "quality stripped; it cannot be denoised. Pick another dataset.",
            ),
            distinct,
        )

    if distinct < 8:
        return (
            Finding(
                "warning",
                "quality",
                f"{path.name}: {distinct} distinct quality values (binned)",
                "2-colour instruments bin quality scores. DADA2 usually copes, "
                "but if learnErrors fails this is why.",
            ),
            distinct,
        )
    return None, distinct


def check_primers(
    r1: Path, r2: Path, forward: str, reverse: str
) -> list[Finding]:
    """Confirm the primers are present, and on the mates we expect."""
    findings: list[Finding] = []
    r1_seqs, _ = _read_records(r1)
    r2_seqs, _ = _read_records(r2)
    if not r1_seqs or not r2_seqs:
        return [Finding("error", "primers", "could not read sequences")]

    f_re, r_re = iupac_regex(forward), iupac_regex(reverse)
    window = max(len(forward), len(reverse)) + 4

    forward_on_r1 = sum(1 for s in r1_seqs if f_re.match(s[:window])) / len(r1_seqs)
    reverse_on_r1 = sum(1 for s in r1_seqs if r_re.match(s[:window])) / len(r1_seqs)
    forward_on_r2 = sum(1 for s in r2_seqs if f_re.match(s[:window])) / len(r2_seqs)
    reverse_on_r2 = sum(1 for s in r2_seqs if r_re.match(s[:window])) / len(r2_seqs)

    if max(forward_on_r1, reverse_on_r1, forward_on_r2, reverse_on_r2) < MIN_PRIMER_RATE:
        findings.append(
            Finding(
                "error",
                "primers",
                f"neither primer found at the start of reads "
                f"(best match {100 * max(forward_on_r1, reverse_on_r1, forward_on_r2, reverse_on_r2):.1f}%)",
                "cutadapt runs with --discard-untrimmed, so this would throw "
                "away the whole dataset. Check the study's primers.",
            )
        )
        return findings

    # Mates the wrong way round: the reverse primer dominating R1 means cutadapt
    # will discard the majority of pairs.
    if reverse_on_r1 > forward_on_r1 * 2 and forward_on_r2 > reverse_on_r2 * 2:
        findings.append(
            Finding(
                "error",
                "primers",
                f"mates appear swapped (forward primer on R1: "
                f"{100 * forward_on_r1:.1f}%, on R2: {100 * forward_on_r2:.1f}%)",
                "Re-download with --swap-mates, or swap the R1/R2 filenames. "
                "Otherwise most pairs are discarded during trimming.",
            )
        )
    elif forward_on_r1 < MIN_PRIMER_RATE:
        findings.append(
            Finding(
                "warning",
                "primers",
                f"forward primer on only {100 * forward_on_r1:.1f}% of R1 reads",
                "Expect low retention through trimming.",
            )
        )
    return findings


def check_truncation(
    r1: Path,
    r2: Path,
    trunc_f: int | None,
    trunc_r: int | None,
    amplicon_length: int | None = None,
) -> list[Finding]:
    """Catch truncation that removes every read, or prevents merging."""
    findings: list[Finding] = []
    r1_seqs, _ = _read_records(r1)
    r2_seqs, _ = _read_records(r2)
    if not r1_seqs or not r2_seqs:
        return findings

    r1_len = sorted(len(s) for s in r1_seqs)[len(r1_seqs) // 2]
    r2_len = sorted(len(s) for s in r2_seqs)[len(r2_seqs) // 2]

    # Raw reads here; primer trimming shortens them further, so leave headroom.
    for label, trunc, median in (("trunc-len-f", trunc_f, r1_len),
                                 ("trunc-len-r", trunc_r, r2_len)):
        if trunc and trunc > median:
            findings.append(
                Finding(
                    "error",
                    "truncation",
                    f"{label}={trunc} exceeds the median read length ({median} bp)",
                    "DADA2 discards every read shorter than truncLen. Primer "
                    "trimming shortens reads further, so set this below the "
                    "post-trim length.",
                )
            )
        elif trunc and trunc > median - 25:
            findings.append(
                Finding(
                    "warning",
                    "truncation",
                    f"{label}={trunc} is close to the read length ({median} bp)",
                    "Primer trimming removes ~25 bp; this may filter most reads.",
                )
            )

    if trunc_f and trunc_r and amplicon_length:
        combined = trunc_f + trunc_r
        needed = amplicon_length + MIN_MERGE_OVERLAP
        if combined < needed:
            findings.append(
                Finding(
                    "error",
                    "truncation",
                    f"trunc_f + trunc_r = {combined} bp cannot span a "
                    f"{amplicon_length} bp amplicon plus {MIN_MERGE_OVERLAP} bp overlap",
                    f"Increase truncation lengths so they sum to at least {needed}.",
                )
            )
    return findings


# Primer pairs we can recognise in uploaded reads. Enough to cover the markers
# BioRadar supports; anything else the user sets by hand.
KNOWN_MARKERS: "list[dict[str, object]]" = [
    {
        "id": "coi-leray",
        "name": "COI Leray",
        "fprimer": "GGWACWGGWTGAACWGTWTAYCCYCC",
        "rprimer": "TANACYTCNGGRTGNCCRAARAAYCA",
        "amplicon_length": 313,
        "classifier": "classifier-coi-india-2026.qza",
    },
    {
        "id": "coi-folmer",
        "name": "COI Folmer",
        "fprimer": "GGTCAACAAATCATAAAGATATTGG",
        "rprimer": "TAAACTTCAGGGTGACCAAAAAATCA",
        "amplicon_length": 658,
        "classifier": "classifier-coi-india-2026.qza",
    },
    {
        "id": "12s-teleo",
        "name": "12S teleo",
        "fprimer": "ACACCGCCCGTCACTCT",
        "rprimer": "CTTCCGGTACACTTACCATG",
        "amplicon_length": 60,
        "classifier": "MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME-classifier.qza",
    },
    {
        "id": "18s-v9",
        "name": "18S V9",
        "fprimer": "GTACACACCGCCCGTC",
        "rprimer": "TGATCCTTCTGCAGGTTCACCTAC",
        "amplicon_length": 130,
        "classifier": None,
    },
]


def detect_marker(fastq_files: Sequence[Path]) -> "dict[str, Any] | None":
    """Work out which primer pair a dataset was amplified with.

    Saves the user from having to know: the primers are literally at the start
    of the reads, so we look rather than ask. Also reports whether the mates are
    the wrong way round, which otherwise silently destroys most of the data at
    the trimming step.
    """
    paths = [Path(p) for p in fastq_files]
    r1_files = [p for p in paths if "_R1" in p.name]
    if not r1_files:
        return None

    r1 = r1_files[0]
    r2 = r1.parent / r1.name.replace("_R1", "_R2")
    if not r2.is_file():
        return None

    forward_reads, _ = _read_records(r1, 3000)
    reverse_reads, _ = _read_records(r2, 3000)
    if not forward_reads or not reverse_reads:
        return None

    best = None
    for marker in KNOWN_MARKERS:
        f_re = iupac_regex(str(marker["fprimer"]))
        r_re = iupac_regex(str(marker["rprimer"]))
        window = max(len(str(marker["fprimer"])), len(str(marker["rprimer"]))) + 4

        standard = sum(1 for s in forward_reads if f_re.match(s[:window])) / len(forward_reads)
        swapped = sum(1 for s in forward_reads if r_re.match(s[:window])) / len(forward_reads)
        score = max(standard, swapped)
        if best is None or score > best["score"]:
            best = {
                "score": round(score, 4),
                "marker": marker,
                "swap_mates": swapped > standard,
            }

    if best is None or best["score"] < MIN_PRIMER_RATE:
        return None

    marker = best["marker"]
    read_length = sorted(len(s) for s in forward_reads)[len(forward_reads) // 2]
    return {
        "marker_id": marker["id"],
        "marker": marker["name"],
        "fprimer": marker["fprimer"],
        "rprimer": marker["rprimer"],
        "amplicon_length": marker["amplicon_length"],
        "classifier": marker["classifier"],
        "match_rate": best["score"],
        "swap_mates": best["swap_mates"],
        "read_length": read_length,
        **_truncation_for(read_length, marker["amplicon_length"]),
    }


def _truncation_for(read_length: int, amplicon: "int | None") -> "dict[str, int]":
    """Pick DADA2 truncation lengths, or none at all.

    Truncation exists to cut low-quality tails off long reads. On short reads it
    only throws away signal, and on a short amplicon it can stop the mates
    overlapping altogether -- which yields zero merged pairs from a run that
    reported success at every stage. So: leave short reads alone, and never
    truncate below what the amplicon needs to merge.
    """
    if read_length < 150:
        return {"trunc_len_f": 0, "trunc_len_r": 0}

    forward = read_length - 30
    reverse = read_length - 45
    if amplicon:
        needed = amplicon + MIN_MERGE_OVERLAP
        if forward + reverse < needed:
            return {"trunc_len_f": 0, "trunc_len_r": 0}
    return {"trunc_len_f": forward, "trunc_len_r": reverse}


def quality_levels(fastq_files: Sequence[Path]) -> int:
    """Smallest number of distinct quality values across the inputs."""
    counts = []
    for path in [Path(p) for p in fastq_files][:4]:
        _, distinct = check_quality_encoding(path)
        counts.append(distinct)
    return min(counts) if counts else 0


def recommend_denoiser(fastq_files: Sequence[Path]) -> str:
    """dada2 where it can work, vsearch where the quality scores cannot support it."""
    return "dada2" if quality_levels(fastq_files) >= MIN_QUALITY_LEVELS else "vsearch"


def run(
    fastq_files: Sequence[Path],
    *,
    forward_primer: str | None = None,
    reverse_primer: str | None = None,
    trunc_len_f: int | None = None,
    trunc_len_r: int | None = None,
    amplicon_length: int | None = None,
) -> PreflightResult:
    """Check a batch of FASTQ files before handing them to the pipeline."""
    result = PreflightResult()
    paths = [Path(p) for p in fastq_files]
    r1_files = [p for p in paths if "_R1" in p.name]
    if not r1_files:
        result.findings.append(
            Finding("error", "layout", "no R1 files found among the inputs")
        )
        return result

    quality_levels: dict[str, int] = {}
    for r1 in r1_files:
        r2 = r1.parent / r1.name.replace("_R1", "_R2")
        if not r2.is_file():
            result.findings.append(
                Finding("error", "layout", f"{r1.name} has no R2 mate")
            )
            continue

        corrupt = False
        for path in (r1, r2):
            integrity = check_integrity(path)
            result.findings.extend(integrity)
            if any(f.level == "error" for f in integrity):
                corrupt = True
        # Every check below decodes the same bytes. Running them on a file we
        # have just proved is truncated produces a second, more confusing error
        # about quality scores when the real problem is the transfer.
        if corrupt:
            continue

        for path in (r1, r2):
            finding, distinct = check_quality_encoding(path)
            quality_levels[path.name] = distinct
            if finding:
                result.findings.append(finding)

        if forward_primer and reverse_primer:
            result.findings.extend(
                check_primers(r1, r2, forward_primer, reverse_primer)
            )
        result.findings.extend(
            check_truncation(r1, r2, trunc_len_f, trunc_len_r, amplicon_length)
        )

    result.stats["samples"] = len(r1_files)
    result.stats["quality_levels"] = quality_levels

    # A whole study normally shares the same problem, so collapse identical
    # findings rather than repeating them once per sample. Per-file quality
    # findings keep their filename and so stay distinct.
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Finding] = []
    for finding in result.findings:
        key = (finding.level, finding.check, finding.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    result.findings = deduped
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from bioradar.pipeline_runner import discover_pairs

    parser = argparse.ArgumentParser(
        prog="bioradar.preflight",
        description="Check FASTQ files before running the pipeline.",
    )
    parser.add_argument("fastq_dir", type=Path)
    parser.add_argument("--fprimer", default=None)
    parser.add_argument("--rprimer", default=None)
    parser.add_argument("--trunc-len-f", type=int, default=None)
    parser.add_argument("--trunc-len-r", type=int, default=None)
    parser.add_argument("--amplicon-length", type=int, default=None)
    args = parser.parse_args(argv)

    try:
        pairs = discover_pairs(args.fastq_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = run(
        pairs,
        forward_primer=args.fprimer,
        reverse_primer=args.rprimer,
        trunc_len_f=args.trunc_len_f,
        trunc_len_r=args.trunc_len_r,
        amplicon_length=args.amplicon_length,
    )
    print(f"preflight: {result.stats['samples']} sample(s)")
    print(result.render())
    if not result.ok:
        print("\nrefusing to run: fix the errors above")
        return 1
    print("\nok to run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
