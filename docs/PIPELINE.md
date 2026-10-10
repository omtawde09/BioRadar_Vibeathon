# Layer 1 — the analysis pipeline

Raw paired-end reads in, taxonomy out. This document describes
`bioradar-pipeline/` and the image that runs it.

---

## The image

Everything runs inside **`ghcr.io/omtawde09/bioradar-pipeline:v1.0`** — QIIME 2,
DADA2, cutadapt, vsearch and R, version-matched so results are reproducible
across machines.

```bash
docker pull ghcr.io/omtawde09/bioradar-pipeline:v1.0
```

To rebuild and publish it yourself:

```bash
docker build -f docker/Dockerfile.pipeline -t ghcr.io/omtawde09/bioradar-pipeline:v1.0 .
docker push ghcr.io/omtawde09/bioradar-pipeline:v1.0
```

Inside the image:

| Path | Contents |
|---|---|
| `/opt/bioradar/classifiers/` | Trained `.qza` classifiers |
| `/opt/bioradar/pipeline/` | Reference copy of the workflow |
| `/opt/bioradar/NOTICE` | Attribution, travelling with the image |

Point BioRadar at a different image with `BIORADAR_PIPELINE_IMAGE`.

---

## Classifiers

Roughly 30 MB, so they are not in git. `./scripts/setup.sh` extracts them, or by
hand:

```bash
docker create --name tmp ghcr.io/omtawde09/bioradar-pipeline:v1.0
docker cp tmp:/opt/bioradar/classifiers/. bioradar-pipeline/database/qiime2-qza/
docker rm tmp
```

| Classifier | Marker |
|---|---|
| `classifier-coi-india-2026.qza` | COI Leray — the India-curated default |
| `MIDORI2_..._QIIME-classifier.qza` | 12S teleo fish |
| `QIIME-classifier-mccoll-v0.1.qza` | 12S V5 |

Build your own with `python -m bioradar.train_classifier`. It trains **inside the
container** deliberately: a `.qza` embeds a pickled scikit-learn model, and
QIIME 2 refuses to load one built against a different scikit-learn version. The
image ships QIIME 2 2023.2 with scikit-learn 0.24.1, so a classifier downloaded
from any other release fails several minutes into a run. Training in place makes
it loadable by construction.

---

## The workflow

Twelve rules in fast mode, fourteen with the optional QC report:

```
create_metadata     FASTQ filenames        -> metadata.csv
create_manifest     metadata.csv           -> QIIME 2 manifest
import_reads        FASTQ                  -> paired-end-demux.qza
trim_reads          cutadapt, primer trimming
clean_reads         DADA2 or vsearch       -> sequence variants
assign_taxonomy     naive Bayes            -> taxonomy.tsv
export_data         export QIIME 2 artifacts
count_table         counts + taxonomy      -> asv_count_tax.csv
collect_fast        assemble final_results/
normalize_taxonomy  [BioRadar]             -> the frozen contract
emit_hash           [BioRadar]             -> chain-of-custody record
```

With `fast: false` in `config.yaml` you additionally get `write_report_md`,
`rarefaction`, `write_report_pdf` and `finish` — a PDF QC report and alpha
rarefaction curves. They cost about a fifth of the runtime and BioRadar's own
report does not read them, so they are off by default.

### Denoising

**DADA2** infers exact amplicon sequence variants and is the default.

**vsearch** clusters 97% OTUs and ignores quality scores entirely. That matters
because some public datasets are submitted with quality stripped — every base at
the same Phred value — and DADA2 models error rate *as a function of* quality, so
it cannot fit anything at all. Those datasets are not broken, they just need a
different denoiser. `bioradar.preflight` detects the situation and the app shows
which path it chose.

Force one with `--denoiser dada2|vsearch`.

---

## Why every run gets its own directory

Every rule writes to fixed relative paths (`qiime2/loci/...`, `final_results/`)
with no wildcards, so two runs sharing a directory would corrupt each other.

`pipeline_runner.prepare_run()` copies the workflow tree — a few hundred KB; the
classifiers stay put and are referenced by path — into `runs/<run-id>/`, drops
the FASTQs in, renders `config.yaml`, and runs Snakemake there. Runs are
independent and their outputs are retained.

One trap worth knowing: the optional `finish` rule **moves** `qiime2/loci/asvs`
into `final_results/`. Deleting `final_results/` therefore destroys your DADA2
output and forces a full re-denoise. `collect_fast`, used in the default path,
copies instead.

---

## Running it

Through the app, or:

```bash
python -m bioradar.pipeline_runner data/demo_survey/fastq --mode docker \
    --classifier /db/qiime2-qza/classifier-coi-india-2026.qza \
    --fprimer GGWACWGGWTGAACWGTWTAYCCYCC \
    --rprimer TANACYTCNGGRTGNCCRAARAAYCA \
    --trunc-len-f 220 --trunc-len-r 205
```

Or Snakemake directly:

```bash
docker run --rm \
  -v "$PWD/runs/myrun:/work" \
  -v "$PWD/bioradar-pipeline/database:/db:ro" \
  -v "$PWD:/repo:ro" \
  --entrypoint snakemake ghcr.io/omtawde09/bioradar-pipeline:v1.0 \
  --cores 4 --snakefile /work/Snakefile --directory /work all
```

Three mounts, each load-bearing: `/work` is the run directory, `/db` the shared
classifiers, `/repo` makes the `bioradar` package importable from inside the
container — the two BioRadar rules import it.

### Timing

Measured on 12 samples of the demonstration dataset, 16 cores:

| Stage | Time |
|---|---|
| import_reads | 32 s |
| trim_reads | 31 s |
| clean_reads (DADA2) | 56 s |
| assign_taxonomy | 24 s |
| export_data | 18 s |
| **total** | **~3 min** |

Most of the remainder is QIIME 2 process startup — each rule launches a fresh
QIIME 2 that spends 10–15 s loading before doing any work. Real field data at
full sequencing depth will be considerably slower; budget 20–40 minutes and do
not plan a live full run in front of an audience.

---

## Configuration

`config.yaml` is rendered per run from `config-template.yaml`.

| Key | Default | Meaning |
|---|---|---|
| `fprimer` / `rprimer` | detected | Primer sequences for cutadapt |
| `erate`, `overlap` | 0.1, 3 | cutadapt error rate and overlap |
| `trunc-len-f` / `-r` | detected | DADA2 truncation (0 = off) |
| `max-ee-f` / `-r` | 2, 4 | DADA2 maximum expected errors |
| `trunc-q` | 2 | Quality truncation threshold |
| `chimera-method` | consensus | DADA2 chimera removal |
| `classifier` | India-curated COI | Path to the `.qza` |
| `denoiser` | `dada2` | `dada2` or `vsearch` |
| `fast` | `true` | Skip the PDF QC report and rarefaction |

BioRadar also injects `sample_id`, `pipeline_run_id`, `backend_url`,
`bioradar_pkg_path`, `chain_queue_dir` and `classification_method`.

Swapping the classifier is a one-line change — pass `--classifier` — and nothing
else moves.

---

## Determinism

Two independent runs of the same input produce **byte-identical** taxonomy. That
is what makes the chain-of-custody hashes meaningful: a changed hash means
something actually changed — classifier, primers, parameters or image — not that
the pipeline is noisy.

The bundled test data is a regression baseline:

```
taxonomy_normalized.csv
  e4db8fbd641aaeb4069bf9d6635aa2fa9ac008dfff3cb0cb96c95ed9498398e2
```

---

## Attribution

The bioinformatics in `bioradar-pipeline/` is derived from the eDNA-Container App
(Wheeler, Brancalion, Kumar and Lintermans; *Applied Sciences* 2024, 14(6), 2641,
doi:10.3390/app14062641), used under Apache-2.0. See [NOTICE](../NOTICE) for the
full attribution and the complete list of changes.
