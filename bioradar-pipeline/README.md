# Layer 1 — the analysis pipeline

The bioinformatics half of BioRadar: raw paired-end reads in, taxonomy out.

Run it through the app or `bioradar.pipeline_runner` rather than invoking
Snakemake by hand — those handle per-run isolation, config rendering and
pre-flight checks for you. See [docs/RUNNING.md](../docs/RUNNING.md).

## Layout

| Path | What it is |
|---|---|
| `Snakefile` | The DAG. Fourteen rules from sample sheet to chain-of-custody hash. |
| `rules/bioradar.smk` | BioRadar's additions: `collect_fast`, `normalize_taxonomy`, `emit_hash`. |
| `scripts/` | The shell and Python each rule calls. |
| `scripts/bioradar-denoise.sh` | Dispatches between DADA2 and vsearch OTU clustering. |
| `report/` | Templates for the optional PDF QC report. |
| `env/` | Conda specification for the analysis environment. |
| `database/qiime2-qza/` | Trained classifiers (not in git — see below). |

## Classifiers

Roughly 30 MB, so they are not version-controlled. Extract them from the
pipeline image:

```bash
./scripts/setup.sh
```

## Denoising

`DADA2` by default — it infers exact amplicon sequence variants and is the more
precise choice. Datasets whose quality scores were stripped by the submitter
cannot be denoised that way at all, so those are routed to **vsearch** 97% OTU
clustering, which does not use quality scores. `bioradar.preflight` decides
which applies and the app shows you the choice it made.

## Attribution

This directory is derived from the eDNA-Container App (Wheeler, Brancalion,
Kumar and Lintermans; *Applied Sciences* 2024, 14(6), 2641). See
[NOTICE](../NOTICE) for the full attribution and a complete list of changes.
