"""Run the forked eDNA pipeline from Python, one isolated run at a time.

This is the module Parth's FastAPI backend imports. It exists because the
upstream pipeline cannot be called safely as-is: every rule writes to fixed
relative paths (`qiime2/loci/...`, `final_results/`) with no wildcards, and the
upstream Flask app deletes the previous run on every page load. Two concurrent
samples in one directory would silently corrupt each other's results.

The fix is a working directory per run. `prepare_run()` copies the pipeline tree
(a few hundred KB of Snakefile and scripts -- the 22 MB of classifiers stay put
and are referenced by path) into `runs/<run_id>/`, drops the FASTQs in, renders
`config.yaml`, and runs Snakemake there. Runs are then independent and their
outputs are permanently retained.

Two execution modes:
    local   -- `snakemake` on PATH, i.e. inside the conda env or the container
    docker  -- `docker run` against the eDNA image; the default on a laptop

Typical use from the backend:

    runner = PipelineRunner()
    result = runner.run(
        fastq_files=[r1, r2],
        sample_id="BR-2026-GOA-001",
        progress=lambda ev: websocket.send_json(ev),
    )
    result.taxonomy_csv   # -> contract CSV for downstream consumers
    result.artifact_hash  # -> SHA-256 recorded in the custody ledger
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Sequence

from bioradar.chain_client import ChainClient, build_event, sha256_file
from bioradar.contract import (
    FASTQ_R1_SUFFIX,
    FASTQ_R2_SUFFIX,
    sample_id_from_fastq,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PIPELINE_DIR = REPO_ROOT / "bioradar-pipeline"
DEFAULT_RUNS_DIR = REPO_ROOT / "runs"
DEFAULT_IMAGE = os.environ.get("BIORADAR_PIPELINE_IMAGE", "ghcr.io/omtawde09/bioradar-pipeline:v1.0")

# Files and directories copied into each run's working directory. The database
# directory is deliberately excluded -- it is large, read-only, and shared.
_PIPELINE_TREE = ("Snakefile", "rules", "scripts", "report", "config-template.yaml")

# Snakemake announces each rule as it starts; used for progress events.
_RULE_RE = re.compile(r"^\s*(?:localrule|rule)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:")
_PROGRESS_RE = re.compile(r"^\s*(\d+) of (\d+) steps \((\d+)%\) done")

# Ordered as the DAG executes them, for percentage estimates before Snakemake
# starts reporting its own.
PIPELINE_STAGES: tuple[str, ...] = (
    "create_metadata",
    "create_manifest",
    "import_reads",
    "trim_reads",
    "clean_reads",
    "assign_taxonomy",
    "export_data",
    "count_table",
    "write_report_md",
    "rarefaction",
    "write_report_pdf",
    "finish",
    "normalize_taxonomy",
    "emit_hash",
)

STAGE_LABELS: dict[str, str] = {
    "create_metadata": "Reading sample sheet",
    "create_manifest": "Building QIIME2 manifest",
    "import_reads": "Importing paired-end reads",
    "trim_reads": "Trimming primers (cutadapt)",
    "clean_reads": "Denoising into ASVs (DADA2)",
    "assign_taxonomy": "Assigning taxonomy (naive Bayes)",
    "export_data": "Exporting QIIME2 artifacts",
    "count_table": "Building ASV count table",
    "write_report_md": "Writing QC report",
    "rarefaction": "Alpha rarefaction",
    "write_report_pdf": "Rendering PDF report",
    "finish": "Collecting results",
    "normalize_taxonomy": "Normalizing to BioRadar contract",
    "emit_hash": "Recording chain-of-custody hash",
}


class PipelineError(RuntimeError):
    """Raised when the pipeline exits non-zero."""


@dataclass
class PipelineResult:
    """Everything the backend needs to persist after a run."""

    run_id: str
    sample_ids: list[str]
    status: str
    work_dir: Path
    results_dir: Path
    returncode: int
    started_at: str
    finished_at: str
    taxonomy_csv: Path | None = None
    summary_csv: Path | None = None
    report_pdf: Path | None = None
    biom_table: Path | None = None
    hash_record: Path | None = None
    artifact_hash: str | None = None
    chain_committed: bool = False
    log_path: Path | None = None
    stages_completed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, Path):
                payload[key] = str(value)
        return payload


# Dict, not dict: this is a runtime assignment, not an annotation, so
# `from __future__ import annotations` does not defer it. The pipeline image
# ships Python 3.8, where subscripting builtin types raises TypeError -- and the
# web app imports this module *inside* that image.
ProgressCallback = Callable[[Dict[str, Any]], None]


class PipelineRunner:
    def __init__(
        self,
        pipeline_dir: Path = DEFAULT_PIPELINE_DIR,
        runs_dir: Path = DEFAULT_RUNS_DIR,
        *,
        mode: str = "auto",
        image: str = DEFAULT_IMAGE,
        cores: int = 4,
        backend_url: str | None = None,
    ) -> None:
        self.pipeline_dir = Path(pipeline_dir).resolve()
        self.runs_dir = Path(runs_dir).resolve()
        self.image = image
        self.cores = cores
        self.backend_url = backend_url or os.environ.get(
            "BIORADAR_BACKEND_URL", "http://localhost:8000"
        )
        self.mode = self._resolve_mode(mode)

        if not (self.pipeline_dir / "Snakefile").is_file():
            raise FileNotFoundError(
                f"no Snakefile under {self.pipeline_dir}; extract the pipeline first "
                "(see docs/PIPELINE.md)"
            )

    @staticmethod
    def _resolve_mode(mode: str) -> str:
        if mode != "auto":
            if mode not in {"local", "docker"}:
                raise ValueError(f"unknown mode {mode!r}")
            return mode
        if shutil.which("snakemake"):
            return "local"
        if shutil.which("docker"):
            return "docker"
        raise RuntimeError(
            "neither snakemake nor docker found on PATH; cannot run the pipeline"
        )

    # ------------------------------------------------------------------
    # Run preparation
    # ------------------------------------------------------------------

    def prepare_run(
        self,
        fastq_files: Sequence[Path],
        *,
        run_id: str | None = None,
        params: dict[str, Any] | None = None,
        sample_id: str | None = None,
    ) -> tuple[str, Path, list[str]]:
        """Create an isolated working directory for one run.

        Returns (run_id, work_dir, sample_ids). Sample ids are derived exactly as
        the pipeline derives them -- from the FASTQ filename prefix -- so the
        caller can predict them before the run finishes.
        """
        run_id = run_id or f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
        work_dir = self.runs_dir / run_id
        if work_dir.exists():
            raise FileExistsError(f"run directory already exists: {work_dir}")

        work_dir.mkdir(parents=True)
        for item in _PIPELINE_TREE:
            source = self.pipeline_dir / item
            if not source.exists():
                continue
            destination = work_dir / item
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)

        fastq_dir = work_dir / "fastq_data"
        fastq_dir.mkdir(exist_ok=True)
        sample_ids: list[str] = []
        for path in fastq_files:
            path = Path(path)
            if not path.is_file():
                raise FileNotFoundError(f"FASTQ not found: {path}")
            shutil.copy2(path, fastq_dir / path.name)
            if FASTQ_R1_SUFFIX in path.name or "_R1" in path.name:
                sample_ids.append(sample_id_from_fastq(path.name))

        if not sample_ids:
            raise ValueError(
                "no R1 files found; expected filenames like "
                f"<SAMPLE>{FASTQ_R1_SUFFIX} (R2 counterpart {FASTQ_R2_SUFFIX})"
            )

        self._write_config(
            work_dir,
            run_id=run_id,
            sample_id=sample_id or sample_ids[0],
            params=params or {},
        )
        return run_id, work_dir, sorted(set(sample_ids))

    def _write_config(
        self,
        work_dir: Path,
        *,
        run_id: str,
        sample_id: str,
        params: dict[str, Any],
    ) -> Path:
        """Render config.yaml from the upstream Jinja template.

        Only `{{ key }}` substitution is used, so no Jinja2 dependency leaks into
        the backend. Defaults are the upstream teleo 12S fish settings, which is
        what the shipped classifier and test data expect.
        """
        template_path = work_dir / "config-template.yaml"
        defaults: dict[str, Any] = {
            "name": params.get("project", sample_id),
            "fprimer": "ACACCGCCCGTCACTCT",
            "rprimer": "CTTCCGGTACACTTACCATG",
            "tlf": 0,
            "tlr": 0,
            "maxef": 2,
            "maxer": 4,
            "truncq": 2,
            "chimera": "consensus",
            "classifier": self._classifier_path(params.get("classifier")),
        }
        defaults.update({k: v for k, v in params.items() if v is not None})
        # Re-apply after the update: params carries the caller's raw classifier
        # string, which would otherwise clobber the repaired one computed above
        # and put a Git-Bash-mangled path into config.yaml.
        defaults["classifier"] = self._classifier_path(params.get("classifier"))

        rendered = template_path.read_text(encoding="utf-8")
        for key, value in defaults.items():
            rendered = re.sub(r"\{\{\s*%s\s*\}\}" % re.escape(str(key)), str(value), rendered)

        # BioRadar-specific keys consumed by rules/bioradar.smk.
        extra = {
            "sample_id": sample_id,
            "pipeline_run_id": run_id,
            "backend_url": self._backend_url_for_mode(),
            "bioradar_pkg_path": self._package_path_for_mode(),
            "chain_queue_dir": "final_results/_chain_queue",
            "classification_method": "sklearn",
            # dada2 unless the caller asks for vsearch; see
            # bioradar-pipeline/scripts/bioradar-denoise.sh for why that exists.
            "denoiser": params.get("denoiser", "dada2"),
        }
        lines = ["", "# --- BioRadar additions ---"]
        lines += [f'{key}: "{value}"' for key, value in extra.items()]

        config_path = work_dir / "config.yaml"
        config_path.write_text(rendered + "\n".join(lines) + "\n", encoding="utf-8")
        return config_path

    def _classifier_path(self, override: str | None) -> str:
        """Absolute path to the classifier, expressed for the execution mode."""
        if override:
            # Git Bash (MSYS) rewrites a leading POSIX path in argv into a
            # Windows path: `/db/qiime2-qza/x.qza` arrives as
            # `C:/Program Files/Git/db/qiime2-qza/x.qza`. The whole team is on
            # Windows, and the resulting failure surfaces 20 minutes into a run
            # at classification, so repair it here rather than rely on everyone
            # remembering MSYS_NO_PATHCONV=1.
            marker = "/db/qiime2-qza/"
            if self.mode == "docker" and marker in override.replace("\\", "/"):
                normalized = override.replace("\\", "/")
                return normalized[normalized.index(marker) :]
            return override
        name = "MIDORI2_UNIQ_NUC_GB253_srRNA_QIIME-classifier.qza"
        if self.mode == "docker":
            return f"/db/qiime2-qza/{name}"
        return str(self.pipeline_dir / "database" / "qiime2-qza" / name)

    def _backend_url_for_mode(self) -> str:
        """Inside a plain `docker run`, localhost is the container, not the host."""
        if self.mode == "docker" and "localhost" in self.backend_url:
            return self.backend_url.replace("localhost", "host.docker.internal")
        return self.backend_url

    def _package_path_for_mode(self) -> str:
        return "/repo" if self.mode == "docker" else str(REPO_ROOT)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _build_command(self, work_dir: Path, *, dry_run: bool, target: str) -> list[str]:
        snakemake_args = [
            "--cores",
            str(self.cores),
            "--snakefile",
            "/work/Snakefile" if self.mode == "docker" else str(work_dir / "Snakefile"),
            "--directory",
            "/work" if self.mode == "docker" else str(work_dir),
            target,
        ]
        if dry_run:
            snakemake_args.insert(0, "--dry-run")

        if self.mode == "local":
            return ["snakemake", *snakemake_args]

        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{work_dir}:/work",
            "-v",
            f"{self.pipeline_dir / 'database'}:/db:ro",
            "-v",
            f"{REPO_ROOT}:/repo:ro",
            "--add-host",
            "host.docker.internal:host-gateway",
            "--entrypoint",
            "snakemake",
            self.image,
            *snakemake_args,
        ]

    def _execute(
        self,
        command: list[str],
        work_dir: Path,
        progress: ProgressCallback | None,
    ) -> tuple[int, list[str], Path]:
        """Stream the pipeline's output, emitting progress events as rules start."""
        log_path = work_dir / "pipeline.log"
        stages: list[str] = []

        # Line-buffered: a run can take 40 minutes, and a log that only appears
        # after the process exits is useless for debugging one that is stuck.
        with log_path.open("w", encoding="utf-8", buffering=1) as log:
            process = subprocess.Popen(
                command,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            assert process.stdout is not None
            try:
                for line in process.stdout:
                    log.write(line)
                    event = self._parse_progress(line, stages)
                    if event and progress:
                        progress(event)
                process.wait()
            except BaseException:
                # The progress callback is how a caller cancels or enforces a
                # deadline, and it does that by raising. Letting that exception
                # unwind without killing the child would orphan a Snakemake
                # process that holds every core on the machine -- the run would
                # look cancelled while still making the next one impossible.
                log.write("\n[bioradar] terminating pipeline\n")
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    # QIIME 2 spawns R and vsearch children that ignore SIGTERM.
                    process.kill()
                    process.wait(timeout=10)
                raise

        return process.returncode, stages, log_path

    @staticmethod
    def _parse_progress(line: str, stages: list[str]) -> dict[str, Any] | None:
        rule_match = _RULE_RE.match(line)
        if rule_match:
            rule = rule_match.group(1)
            if rule in {"all", "setup", "clean"} or rule in stages:
                return None
            stages.append(rule)
            known = [s for s in PIPELINE_STAGES if s in stages]
            return {
                "type": "stage",
                "stage": rule,
                "label": STAGE_LABELS.get(rule, rule.replace("_", " ").capitalize()),
                "index": len(known),
                "total": len(PIPELINE_STAGES),
                "percent": round(100 * len(known) / len(PIPELINE_STAGES)),
            }

        progress_match = _PROGRESS_RE.match(line)
        if progress_match:
            done, total, percent = progress_match.groups()
            return {
                "type": "progress",
                "steps_done": int(done),
                "steps_total": int(total),
                "percent": int(percent),
            }
        return None

    def run(
        self,
        fastq_files: Sequence[Path],
        *,
        sample_id: str | None = None,
        run_id: str | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
        commit_chain: bool = True,
        dry_run: bool = False,
        skip_preflight: bool = False,
    ) -> PipelineResult:
        """Run the pipeline end-to-end on one batch of paired FASTQ files.

        Raises PipelineError on a non-zero exit. Partial output is left in place
        for debugging -- the working directory is never cleaned up automatically.
        """
        params = params or {}
        if not skip_preflight and not dry_run:
            from bioradar import preflight

            checks = preflight.run(
                [Path(f) for f in fastq_files],
                forward_primer=params.get("fprimer"),
                reverse_primer=params.get("rprimer"),
                trunc_len_f=params.get("tlf"),
                trunc_len_r=params.get("tlr"),
            )
            if checks.findings:
                print("preflight:")
                print(checks.render())
            if not checks.ok:
                raise preflight.PreflightError(
                    "preflight checks failed; refusing to start a run that would "
                    "waste 20-40 minutes. Override with skip_preflight=True."
                )

        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        run_id, work_dir, sample_ids = self.prepare_run(
            fastq_files, run_id=run_id, params=params, sample_id=sample_id
        )

        if progress:
            progress(
                {
                    "type": "started",
                    "run_id": run_id,
                    "samples": sample_ids,
                    "mode": self.mode,
                }
            )

        command = self._build_command(work_dir, dry_run=dry_run, target="all")
        returncode, stages, log_path = self._execute(command, work_dir, progress)
        finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        results_dir = work_dir / "final_results"
        result = PipelineResult(
            run_id=run_id,
            sample_ids=sample_ids,
            status="completed" if returncode == 0 else "failed",
            work_dir=work_dir,
            results_dir=results_dir,
            returncode=returncode,
            started_at=started_at,
            finished_at=finished_at,
            log_path=log_path,
            stages_completed=stages,
        )

        if returncode != 0:
            if progress:
                progress({"type": "failed", "run_id": run_id, "log": str(log_path)})
            raise PipelineError(
                f"pipeline exited {returncode}; see {log_path}"
            )

        if dry_run:
            return result

        self._collect_artifacts(result)
        if commit_chain:
            self._commit_chain(result)

        if progress:
            progress({"type": "completed", "run_id": run_id, "percent": 100})
        return result

    def _collect_artifacts(self, result: PipelineResult) -> None:
        results_dir = result.results_dir
        for attribute, relative in (
            ("taxonomy_csv", "taxonomy_normalized.csv"),
            ("summary_csv", "sample_summary.csv"),
            ("report_pdf", "final-report.pdf"),
            ("biom_table", "asvs/asv-table.tsv"),
            ("hash_record", "hash_record.json"),
        ):
            candidate = results_dir / relative
            if candidate.is_file():
                setattr(result, attribute, candidate)

        if result.taxonomy_csv:
            result.artifact_hash = sha256_file(result.taxonomy_csv)

    def _commit_chain(self, result: PipelineResult) -> None:
        """Record the run in the ledger.

        The Snakemake rule already does this in the normal path; this is the
        fallback for when the rule was skipped (a resumed run whose hash_record
        was already up to date) so the backend still learns about the run.
        """
        if result.hash_record and result.hash_record.is_file():
            try:
                payload = json.loads(result.hash_record.read_text(encoding="utf-8"))
                result.chain_committed = bool(
                    payload.get("delivery", {}).get("committed")
                )
                return
            except (OSError, ValueError):
                pass

        if not result.taxonomy_csv:
            return

        artifacts = {"taxonomy": result.taxonomy_csv}
        if result.summary_csv:
            artifacts["summary"] = result.summary_csv
        if result.biom_table:
            artifacts["biom"] = result.biom_table

        event = build_event(
            sample_id=result.sample_ids[0],
            event_type="pipeline_complete",
            artifacts=artifacts,
            pipeline_run_id=result.run_id,
        )
        delivery = ChainClient(self.backend_url).record(event)
        result.chain_committed = bool(delivery["committed"])


def discover_pairs(fastq_dir: Path) -> list[Path]:
    """Collect R1/R2 pairs from a directory, rejecting unpaired reads early.

    A missing mate is a silent-corruption bug upstream: create_metadata_file.sh
    derives the R2 name by string substitution and never checks it exists.
    """
    fastq_dir = Path(fastq_dir)
    r1_files = sorted(fastq_dir.glob(f"*{FASTQ_R1_SUFFIX}"))
    if not r1_files:
        r1_files = sorted(p for p in fastq_dir.glob("*_R1*.fastq.gz"))
    if not r1_files:
        raise FileNotFoundError(f"no R1 FASTQ files under {fastq_dir}")

    paired: list[Path] = []
    for r1 in r1_files:
        r2 = r1.parent / r1.name.replace("_R1", "_R2")
        if not r2.is_file():
            raise FileNotFoundError(f"{r1.name} has no R2 mate (expected {r2.name})")
        paired.extend([r1, r2])
    return paired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.pipeline_runner",
        description="Run the forked eDNA pipeline on a directory of FASTQ files.",
    )
    parser.add_argument("fastq_dir", type=Path, help="directory of paired FASTQ.gz")
    parser.add_argument("--sample-id", default=None, help="BioRadar sample code")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--mode", default="auto", choices=("auto", "local", "docker"))
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--classifier", default=None, help="path to a .qza classifier")
    parser.add_argument("--fprimer", default=None)
    parser.add_argument("--rprimer", default=None)
    # DADA2 truncation. Needed for 2-colour instruments (NextSeq/NovaSeq), whose
    # binned quality scores make learnErrors fail with "Error rates could not be
    # estimated" when reads are left untruncated. Keep
    # trunc_f + trunc_r >= amplicon length + 12 so mates still overlap.
    parser.add_argument("--trunc-len-f", type=int, default=None)
    parser.add_argument("--trunc-len-r", type=int, default=None)
    parser.add_argument("--max-ee-f", type=int, default=None)
    parser.add_argument("--max-ee-r", type=int, default=None)
    parser.add_argument(
        "--denoiser",
        default=None,
        choices=("dada2", "vsearch"),
        help="vsearch clusters OTUs without using quality scores; use it for "
        "datasets whose quality was stripped, which DADA2 cannot denoise",
    )
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--no-chain", action="store_true", help="skip ledger commit")
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="print the DAG and exit"
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="run even if the input checks fail (not recommended)",
    )
    args = parser.parse_args(argv)

    runner = PipelineRunner(
        mode=args.mode,
        image=args.image,
        cores=args.cores,
        backend_url=args.backend_url,
    )

    params = {
        key: value
        for key, value in (
            ("classifier", args.classifier),
            ("fprimer", args.fprimer),
            ("rprimer", args.rprimer),
            ("tlf", args.trunc_len_f),
            ("tlr", args.trunc_len_r),
            ("maxef", args.max_ee_f),
            ("maxer", args.max_ee_r),
            ("denoiser", args.denoiser),
        )
        if value
    }

    def show(event: dict[str, Any]) -> None:
        if event["type"] == "stage":
            print(f"[{event['percent']:>3}%] {event['label']}")
        elif event["type"] in {"started", "completed", "failed"}:
            print(f"[{event['type']}] {json.dumps(event)}")

    try:
        result = runner.run(
            discover_pairs(args.fastq_dir),
            sample_id=args.sample_id,
            run_id=args.run_id,
            params=params,
            progress=show,
            commit_chain=not args.no_chain,
            dry_run=args.dry_run,
            skip_preflight=args.skip_preflight,
        )
    except (PipelineError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
