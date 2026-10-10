# Running BioRadar — complete guide

## The short version

```bash
docker compose up app
```

Open **http://localhost:8080**. Every dataset is listed with its pre-flight
status; click **Run pipeline** on any that says `ready`, watch the progress bar,
read the species report when it finishes. That is the whole demo.

The container runs the pipeline itself — `snakemake` is already inside the image,
so there is no Docker-in-Docker and nothing to install. Everything below is the
manual path, for when you need to fetch new data or rebuild a classifier.

---

**Contents**
0. [The control panel](#0-the-control-panel)
1. [Prerequisites](#1-prerequisites)
2. [First-time setup](#2-first-time-setup)
3. [Three ways to run](#3-three-ways-to-run)
4. [The full Indian-dataset workflow](#4-the-full-indian-dataset-workflow)
5. [Running the stack](#5-running-the-stack)
6. [Troubleshooting](#6-troubleshooting)
7. [Where everything lives](#7-where-everything-lives)

---

## 0. The control panel

### Docker Desktop, no terminal

The `bioradar/app` image exists so this works entirely by point-and-click. The
stock `ghcr.io/omtawde09/bioradar-pipeline` image cannot: its `ENTRYPOINT` starts the old Flask GUI,
and Docker Desktop's Run dialog has no field to override an entrypoint.

1. **Images** tab → row `bioradar/app` `latest` → click **▶ Run** (Actions column).
2. In *Run a new container*, expand **Optional settings**.
3. **Container name** — `bioradar-app`
4. **Ports** → *Host port* — `8080`
5. **Volumes** → *Host path* — the repo folder, e.g.
   `C:\Users\tawde\OneDrive\Desktop\BioRadar`
   *Container path* — `/bioradar`
6. **Run**. The logs pane should show `BioRadar control panel`.
7. Open **http://localhost:8080** (or click the `8080:8080` link in the
   Containers tab).

The volume is what makes runs and reports land on your host. Skip it and the
container starts but sees no code or data.

Afterwards, use the **Containers** tab: ■ to stop, ▶ to start again. The settings
are remembered, so steps 2–5 are one-time.

If port 8080 is taken, use another host port (e.g. `8081`) and open that instead.
Give Docker at least 6 GB in *Settings → Resources* — DADA2 needs 3–4 GB.

If `bioradar/app` is not in your Images list, it needs building once:
`docker build -f Dockerfile.app -t bioradar/app:latest .`

### Or from a terminal

```bash
docker compose up app          # -> http://localhost:8080
docker compose logs -f app     # if something looks stuck
docker compose down            # stop
```

| The page shows | Meaning |
|---|---|
| `ready` | Data present, pre-flight clean, classifier built — click Run |
| `blocked` | Present but unusable; the reason is shown in full |
| `missing` | Not downloaded — the page shows the exact fetch command |

One run at a time: the pipeline uses every core, so a second request is refused
rather than allowed to thrash.

Runs write to `runs/<run-id>/` and reports to `reports/<run-id>.md`, both on your
host — the repo is bind-mounted, so nothing is lost when the container stops.

Add a dataset by appending to [`data/datasets.json`](../data/datasets.json); it
appears in the UI with no code change.

---

## 1. Prerequisites

| Need | Why | Check |
|---|---|---|
| **Docker Desktop** | The pipeline runs in the eDNA image | `docker info` |
| **Python 3.10+** | The `bioradar` package | `python --version` |
| **16 GB RAM** | DADA2 and classifier training | — |
| **40 GB free disk** | 11.7 GB image + runs + references | — |
| `pip install truststore` | HTTPS downloads behind antivirus | see §6 |

Give Docker Desktop at least **6 GB of memory** (Settings → Resources). DADA2 uses 3–4 GB.

The 11.7 GB image is the single biggest download. Pull it before hackathon day:

```bash
docker pull ghcr.io/omtawde09/bioradar-pipeline:v1.0
```

---

## 2. First-time setup

```bash
./scripts/setup.sh
```

Checks Docker, pulls the image, extracts the bundled classifiers, creates `.env`
with a generated JWT secret, starts PostGIS, generates mock data, and runs the
fast CI. Safe to re-run; skip the image pull with `--no-pull`.

Verify:

```bash
python -m pytest tests/ -q
```

Expect `76 passed`.

---

## 3. Three ways to run

### A. Mock data — 30 seconds, no Docker

For everyone who isn't running the pipeline. Byte-compatible with real output.

```bash
python -m bioradar.mockgen -o mock/ --rounds 3
```

18 Indian sites × 3 rounds: `samples.csv` (with coordinates), `taxonomy_normalized.csv`,
`sample_summary.csv`, `alerts.example.json`, and per-sample files.

### B. Bundled test data — ~7 minutes

Real output from the upstream pipeline, committed to the repo.

```bash
python -m bioradar.pipeline_runner testing_data/fastq_data \
    --mode docker --sample-id BR-TEST-001
```

Results land in `runs/<run-id>/final_results/`. Expected values are in
[TESTING.md](TESTING.md#5-full-pipeline-run-bundled-test-data).

To see real output without running anything at all:

```bash
python -m bioradar.normalize testing_data/final_results.zip -o out/
```

### C. Real Indian data — see §4

---

## 4. The full Indian-dataset workflow

This is the path that produced [reports/goa_reef_india.md](../reports/goa_reef_india.md).

### Step 1 — Fetch the data

```bash
python -m bioradar.fetch_data --project PRJNA985590 \
    -o data/india_goa_reef --prefix BR-GOA-REEF
```

**Grande Island, Goa** — coral reef eDNA, COI marker, 3 samples, ~290 MB.
Downloads, renames into the pipeline's filename convention, and writes
`sites.csv` / `samples.csv` from the archive's own coordinates.

Always look before downloading:

```bash
python -m bioradar.fetch_data --project <ACCESSION> -o <dir> --dry-run
```

Useful flags:

| Flag | When |
|---|---|
| `--match COI` | Multi-marker studies. **Required** — mixing markers trims with the wrong primers and destroys the run |
| `--swap-mates` | Libraries sequenced in reverse orientation (preflight tells you) |
| `--limit N` | Grab a few runs to test before committing to the full download |

### Step 2 — Check the data before spending an hour on it

```bash
python -m bioradar.preflight data/india_goa_reef/fastq \
    --fprimer GGWACWGGWTGAACWGTWTAYCCYCC \
    --rprimer TANACYTCNGGRTGNCCRAARAAYCA \
    --trunc-len-f 210 --trunc-len-r 195 --amplicon-length 313
```

Expect `all checks passed`. This runs automatically inside `pipeline_runner`
too — it exists because three separate datasets failed 20–60 minutes into a run
for reasons visible in the first 5,000 reads. See §6.

### Step 3 — Build the India-curated reference

```bash
python -m bioradar.build_reference -o data/reference_coi_india
```

~15 minutes, resumable — each phylum is checkpointed, so an interrupted run
picks up where it left off. Produces **33,611 sequences / 8,020 species, 43%
from Indian records**, with the India-vs-global split recorded in `sources.csv`.

This is the artifact behind the "India-curated" claim, and `sources.csv` is what
makes it defensible rather than a slogan.

### Step 4 — Train the classifier

```bash
python -m bioradar.train_classifier \
    --reference data/reference_coi_india \
    --output bioradar-pipeline/database/qiime2-qza/classifier-coi-india-2026.qza \
    --marker coi-leray
```

~1 minute. Trains **inside the container** so the scikit-learn version always
matches — a classifier downloaded from any other QIIME2 release fails to load,
several minutes into a run.

Markers available: `coi-leray`, `12s-teleo`, `18s-v9`.

### Step 5 — Run the pipeline

```bash
python -m bioradar.pipeline_runner data/india_goa_reef/fastq \
    --mode docker \
    --classifier /db/qiime2-qza/classifier-coi-india-2026.qza \
    --fprimer GGWACWGGWTGAACWGTWTAYCCYCC \
    --rprimer TANACYTCNGGRTGNCCRAARAAYCA \
    --trunc-len-f 210 --trunc-len-r 195
```

30–60 minutes. The `--classifier` path is **inside the container** (`/db/...`),
which is where the classifier directory is mounted.

### Step 6 — Generate the report

```bash
python -m bioradar.report \
    --taxonomy runs/<run-id>/final_results/taxonomy_normalized.csv \
    --samples data/india_goa_reef/samples.csv \
    --title "Grande Island, Goa - coral reef eDNA" \
    --note "Dataset=PRJNA985590" \
    --note "Marker=COI Leray" \
    -o reports/goa_reef_india.md
```

### Step 7 — Compare two sampling rounds (optional)

```bash
python -m bioradar.time_machine before.csv after.csv \
    --site GOA-REEF -o reports/trends.json
```

---

## 5. Running the stack

```bash
docker compose up -d db                # PostGIS — works today
docker compose --profile full up       # everything, once backend/ and dashboard/ exist
```

Test the chain-of-custody endpoints before Parth's backend exists:

```bash
python -m integration.mock_backend --port 8000
```

Then re-run the pipeline without `--no-chain`, and verify:

```bash
curl -s http://127.0.0.1:8000/api/v1/chain/verify/BR-GOA-REEF
```

If the backend was down during a run, nothing is lost — replay the queue:

```bash
python -m bioradar.chain_client --flush --queue-dir runs/<run-id>/final_results/_chain_queue
```

---

## 6. Troubleshooting

Every entry below is a failure that actually happened on this project.

### `CERTIFICATE_VERIFY_FAILED` on downloads (but curl works)

Antivirus or a corporate proxy is intercepting HTTPS with its own CA, which is in
the OS trust store but not in certifi's bundle.

```bash
pip install truststore
```

Never disable verification — these files get hashed into a chain of custody.

### DADA2: "Error rates could not be estimated"

The dataset has **flat quality scores** — every base at the same Q value. DADA2
models error rate *as a function of* quality, so there is nothing to fit. The
message blames read counts; the read counts are fine.

**This is unfixable.** No parameter changes it. PRJNA1296846 (Lakshadweep) and
PRJNA1040471 (Goa foraminifera) are both affected. Check any new dataset first:

```bash
python -m bioradar.preflight <fastq_dir>
```

### DADA2: "No reads passed the filter"

`truncLen` is longer than the reads. Primer trimming shortens reads *before*
DADA2 sees them — 251 bp reads become ~226 bp after trimming, so `--trunc-len-f 240`
discards everything. Measure the post-trim length:

```bash
ls runs/<run-id>/fastq_data_trimmed/
```

### Everything discarded at the trimming step

Wrong primers, or the mates are the wrong way round. cutadapt runs with
`--discard-untrimmed`, so a primer mismatch silently throws away the run.
Preflight catches both; the fix for orientation is `--swap-mates` at download.

### `Snakefile "C:/Program Files/Git/work/Snakefile" not found`

Git Bash rewrites leading POSIX paths in arguments. `pipeline_runner` repairs
this for `--classifier` automatically; for your own `docker run` commands:

```bash
MSYS_NO_PATHCONV=1 docker run ...
```

### Classifier fails with a scikit-learn version error

The classifier was built against a different QIIME2 release. The container is
QIIME2 2023.2 / scikit-learn 0.24.1. Never download a pre-trained classifier —
build it with `bioradar.train_classifier`.

### Most detections resolve only to phylum

The classifier was trained without amplicon extraction. Retrain **without**
`--skip-extraction` — cutadapt trims the reference to the amplicon in about three
seconds and materially improves species-level resolution.

### `docker compose up` fails on JWT_SECRET

Run `./scripts/setup.sh`, or copy `.env.example` to `.env` and set a secret.

### A run failed and I want to resume it

Snakemake resumes from whatever outputs still exist:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$PWD/runs/<run-id>:/work" \
  -v "$PWD/bioradar-pipeline/database:/db:ro" \
  -v "$PWD:/repo:ro" \
  --entrypoint snakemake ghcr.io/omtawde09/bioradar-pipeline:v1.0 \
  --cores 4 --snakefile /work/Snakefile --directory /work all
```

**Careful:** the `finish` rule *moves* `qiime2/loci/asvs` into `final_results/`.
Deleting `final_results/` therefore deletes your DADA2 output and forces a full
re-denoise.

---

## 7. Where everything lives

```
data/
  india_goa_reef/fastq/        Grande Island, Goa - COI, WORKING
  india_lakshadweep/fastq/     Lakshadweep - COI, UNUSABLE (flat quality)
  india_goa/fastq/             Goa foraminifera - 18S, UNUSABLE (flat quality)
  reference_coi_india/         India-curated COI reference + sources.csv
  sites.csv, species_pool.csv  Reference metadata for mock data

bioradar-pipeline/
  database/qiime2-qza/         Classifiers (gitignored, ~30 MB)
    classifier-coi-india-2026.qza      the India-curated COI classifier
    MIDORI2_..._QIIME-classifier.qza   bundled 12S fish classifier

runs/<run-id>/
  final_results/               taxonomy_normalized.csv, sample_summary.csv,
                               final-report.pdf, hash_record.json, asvs/
  pipeline.log                 full Snakemake output (line-buffered, tail-able)
  logs/dada2.log               DADA2's own log - check this first on failure
  fastq_data_trimmed/          post-cutadapt reads

reports/                       generated biodiversity reports
mock/                          generated mock data (gitignored)
```

**Lakshadweep FASTQ files (downloaded, unusable):**

```
C:\Users\tawde\OneDrive\Desktop\BioRadar\data\india_lakshadweep\fastq\
  BR-LKD-LAKSHADWEEP-ISLANDS-ST01-01_S1_L001_R1_001.fastq.gz   29 MB
  BR-LKD-LAKSHADWEEP-ISLANDS-ST01-01_S1_L001_R2_001.fastq.gz   28 MB
  BR-LKD-LAKSHADWEEP-ISLANDS-ST02-01_S1_L001_R1_001.fastq.gz   23 MB
  BR-LKD-LAKSHADWEEP-ISLANDS-ST02-01_S1_L001_R2_001.fastq.gz   22 MB
  BR-LKD-LAKSHADWEEP-ISLANDS-ST03-01_S1_L001_R1_001.fastq.gz   50 MB
  BR-LKD-LAKSHADWEEP-ISLANDS-ST03-01_S1_L001_R2_001.fastq.gz   50 MB
```

Site coordinates and run mapping are in `data/india_lakshadweep/samples.csv`.
The reads are real Lakshadweep COI data from three atolls, but they cannot be
denoised — keep them only as the worked example of why preflight exists.
