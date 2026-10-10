"""Train a QIIME2 naive Bayes classifier inside the pipeline container.

Training happens in the container on purpose. A classifier `.qza` embeds a
pickled scikit-learn model, and QIIME2 refuses to load one built against a
different scikit-learn version. The pipeline image ships QIIME2 2023.2 with
scikit-learn 0.24.1, so a classifier downloaded from any other QIIME2 release --
including the current SILVA and UNITE releases -- fails at `classify-sklearn`
with a version-mismatch error, typically several minutes into a run.

Building it here means the classifier is, by construction, loadable.

The reference is trimmed to the amplicon your primers actually produce before
training. Classifying a 313 bp Leray fragment against full-length 1500 bp COI
references degrades accuracy badly, because the model spends its probability
mass on regions the reads never cover.

    python -m bioradar.train_classifier \\
        --reference data/reference_coi_india \\
        --output bioradar-pipeline/database/qiime2-qza/classifier-coi-india-2026.qza

Expect 10-40 minutes and several GB of RAM for a reference of ~30,000 sequences.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE = "ghcr.io/omtawde09/bioradar-pipeline:v1.0"

# Leray fragment -- the de facto standard for metazoan COI metabarcoding, and
# the pair detected in the Lakshadweep reads. Inosine positions in the published
# jgHCO2198 are written as N, which is what cutadapt and QIIME2 accept.
PRIMERS = {
    "coi-leray": {
        "f": "GGWACWGGWTGAACWGTWTAYCCYCC",
        "r": "TANACYTCNGGRTGNCCRAARAAYCA",
        "min_length": 200,
        "max_length": 450,
        "description": "COI Leray mlCOIintF / jgHCO2198 (~313 bp)",
    },
    "12s-teleo": {
        "f": "ACACCGCCCGTCACTCT",
        "r": "CTTCCGGTACACTTACCATG",
        "min_length": 30,
        "max_length": 200,
        "description": "12S teleo fish (~60 bp)",
    },
    "18s-v9": {
        "f": "GTACACACCGCCCGTC",
        "r": "TGATCCTTCTGCAGGTTCACCTAC",
        "min_length": 80,
        "max_length": 250,
        "description": "18S V9 eukaryote",
    },
}


_COMPLEMENT = {
    "A": "T", "C": "G", "G": "C", "T": "A", "R": "Y", "Y": "R", "S": "S",
    "W": "W", "K": "M", "M": "K", "B": "V", "V": "B", "D": "H", "H": "D",
    "N": "N", "I": "N",
}


def reverse_complement(primer: str) -> str:
    """Reverse-complement an IUPAC primer, preserving ambiguity codes."""
    return "".join(_COMPLEMENT[base] for base in reversed(primer.upper()))


class TrainingError(RuntimeError):
    pass


def build_script(
    marker: str,
    jobs: int,
    work: str = "/work",
    reference: str = "/ref",
    skip_extraction: bool = False,
) -> str:
    """The QIIME2 command sequence, as a shell script run inside the container.

    By default the reference is trimmed to the amplicon with cutadapt before
    training, which is what makes species-level calls trustworthy.

    `skip_extraction` trains on full-length references instead. It is a fallback
    for markers whose primers are unknown, and it costs real precision: on this
    project, a full-length-trained COI classifier resolved 65% of detections no
    deeper than phylum and put 94% of reads on unidentified "<taxon> sp."
    records.
    """
    primer = PRIMERS[marker]
    linked = f"{primer['f']}...{reverse_complement(primer['r'])}"

    # cutadapt rather than `qiime feature-classifier extract-reads`: the QIIME
    # action does mismatch-tolerant pairwise alignment of a heavily degenerate
    # primer against every reference and ran over an hour on 33k sequences
    # without finishing. cutadapt does the same job with a linked adapter in
    # about 3 seconds, and is the same tool the pipeline already uses to trim
    # the reads themselves -- so reference and reads are trimmed consistently.
    extraction = "" if skip_extraction else f"""
echo "== extracting the {marker} amplicon (cutadapt) =="
cutadapt \
  -g '{linked}' \
  --discard-untrimmed \
  -e 0.2 \
  --minimum-length {primer['min_length']} \
  --maximum-length {primer['max_length']} \
  -o {work}/ref-extracted.fasta \
  {reference}/reference.fasta > {work}/cutadapt.log 2>&1
echo "   references retained: $(grep -c '^>' {work}/ref-extracted.fasta)"

qiime tools import \
  --type 'FeatureData[Sequence]' \
  --input-path {work}/ref-extracted.fasta \
  --output-path {work}/ref-extracts.qza
"""
    training_input = (
        f"{work}/ref-seqs.qza" if skip_extraction else f"{work}/ref-extracts.qza"
    )
    seq_import = f"""echo "== importing reference sequences =="
qiime tools import \
  --type 'FeatureData[Sequence]' \
  --input-path {reference}/reference.fasta \
  --output-path {work}/ref-seqs.qza
""" if skip_extraction else ""

    return f"""set -euo pipefail
cd {work}
echo "== importing reference taxonomy =="
qiime tools import \\
  --type 'FeatureData[Taxonomy]' \\
  --input-path {reference}/reference.taxon \\
  --input-format HeaderlessTSVTaxonomyFormat \\
  --output-path {work}/ref-taxonomy.qza

{seq_import}{extraction}
echo "== training naive Bayes classifier =="
qiime feature-classifier fit-classifier-naive-bayes \\
  --i-reference-reads {training_input} \\
  --i-reference-taxonomy {work}/ref-taxonomy.qza \\
  --o-classifier {work}/classifier.qza

echo "== done =="
ls -la {work}/classifier.qza
"""


def train(
    reference_dir: Path,
    output: Path,
    *,
    marker: str = "coi-leray",
    jobs: int = 2,
    image: str = DEFAULT_IMAGE,
    work_dir: Path | None = None,
    skip_extraction: bool = False,
) -> Path:
    """Run the training pipeline and place the classifier at `output`."""
    reference_dir = reference_dir.resolve()
    for required in ("reference.fasta", "reference.taxon"):
        if not (reference_dir / required).is_file():
            raise TrainingError(
                f"{required} missing from {reference_dir}. "
                "Build it first: python -m bioradar.build_reference"
            )

    if marker not in PRIMERS:
        raise TrainingError(f"unknown marker {marker!r}; expected {sorted(PRIMERS)}")

    if not shutil.which("docker"):
        raise TrainingError("docker not found on PATH")

    work_dir = (work_dir or REPO_ROOT / "runs" / "_classifier").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    script = build_script(marker, jobs, skip_extraction=skip_extraction)
    # newline="\n" is required, not cosmetic: on Windows, write_text() would
    # translate to CRLF and bash inside the container fails on the first line
    # with `set: pipefail: invalid option name` -- the trailing \r is parsed as
    # part of the argument.
    (work_dir / "train.sh").write_text(script, encoding="utf-8", newline="\n")

    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{work_dir}:/work",
        "-v",
        f"{reference_dir}:/ref:ro",
        "--entrypoint",
        "bash",
        image,
        "/work/train.sh",
    ]

    print(f"marker    : {marker} -- {PRIMERS[marker]['description']}")
    print(f"reference : {reference_dir}")
    print(f"work dir  : {work_dir}")
    print(f"jobs      : {jobs}")
    print("training (this takes a while; progress below)\n")

    started = time.time()
    log_path = work_dir / "train.log"
    with log_path.open("w", encoding="utf-8", buffering=1) as log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            if line.startswith("==") or "Saved" in line or "Error" in line:
                print(f"  {line.rstrip()}")
        process.wait()

    if process.returncode != 0:
        raise TrainingError(
            f"training failed (exit {process.returncode}); see {log_path}"
        )

    produced = work_dir / "classifier.qza"
    if not produced.is_file():
        raise TrainingError(f"training reported success but {produced} is missing")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(produced, output)
    elapsed = time.time() - started
    print(f"\nclassifier: {output}  ({output.stat().st_size / 1e6:.1f} MB)")
    print(f"elapsed   : {elapsed / 60:.1f} min")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.train_classifier",
        description="Train a QIIME2 classifier inside the pipeline container.",
    )
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--marker", default="coi-leray", choices=sorted(PRIMERS))
    parser.add_argument(
        "--jobs",
        type=int,
        default=2,
        help="parallel jobs for read extraction; each one costs memory",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="train on full-length references (much faster, slightly less precise)",
    )
    args = parser.parse_args(argv)

    try:
        train(
            args.reference,
            args.output,
            marker=args.marker,
            jobs=args.jobs,
            image=args.image,
            skip_extraction=args.skip_extraction,
        )
    except TrainingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
