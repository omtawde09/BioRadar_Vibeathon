# BioRadar

**Biodiversity intelligence for Indian waters, from environmental DNA.**

> From a single litre of estuarine or coastal water, BioRadar reconstructs complete
> biological communities, detects invasive threats, forecasts how they will spread,
> and cryptographically proves every finding — without catching, seeing, or
> disturbing a single organism.

Smart India Hackathon 2026 · Problem Statement **SIH25042** (Ministry of Earth Sciences)
K.C. College of Engineering, Thane

Maintainer: **Om Tawde** ([@omtawde09](https://github.com/omtawde09))
Licence: **Apache-2.0**

---

## Table of contents

1. [What this is](#1-what-this-is)
2. [Feature overview](#2-feature-overview)
3. [The web application](#3-the-web-application)
4. [The landing site](#4-the-landing-site)
5. [The six advanced intelligence features](#5-the-six-advanced-intelligence-features)
6. [AI & analytics modules](#6-ai--analytics-modules)
7. [Provenance, exports & standards](#7-provenance-exports--standards)
8. [How it works](#8-how-it-works)
9. [Technology stack](#9-technology-stack)
10. [Quick start (Docker)](#10-quick-start-docker)
11. [Testing with the sample data](#11-testing-with-the-sample-data)
12. [Analysing your own data](#12-analysing-your-own-data)
13. [Running the web UI in development](#13-running-the-web-ui-in-development)
14. [Troubleshooting](#14-troubleshooting)
15. [Project layout](#15-project-layout)
16. [For developers](#16-for-developers)
17. [Documentation index](#17-documentation-index)
18. [Licence & attribution](#18-licence--attribution)

---

## 1. What this is

Scoop a litre of water out of an estuary and it carries DNA from everything living
in it — shed skin, scales, mucus, waste. Sequence that DNA and you can list the
species present without catching, seeing, or disturbing a single one. That is
**environmental DNA (eDNA)**, and it is the cheapest biodiversity survey method that
exists.

The problem is what comes back from the sequencer: millions of short text strings.
Turning those into *"an invasive tilapia is establishing in Vembanad Lake, and here
is the evidence"* takes a bioinformatics pipeline, a curated reference database, and
somewhere to put the answer that a forest officer can actually read.

**BioRadar is that path, end to end.** You give it sequencing files. It gives you a
species list, an interactive map, a spread forecast, an invasion-risk score, an
auto-written executive brief, and a tamper-evident record of exactly how it got
there — in English or Hindi.

### Validation

Measured against an *in silico* mock community with known ground truth:

> **100 % recall, zero false positives** — 80 of 80 planted species-in-sample
> detections recovered, at exact read counts.

That validation also caught a **mislabelled record in the public NCBI reference
data** — two sequences one base apart, assigned to species in different taxonomic
*orders*. Details in [docs/DEMO_DATASET.md](docs/DEMO_DATASET.md).

---

## 2. Feature overview

BioRadar is three layers: a **self-configuring bioinformatics pipeline**, a stack of
**AI/analytics intelligence engines** on top of its output, and a **bilingual web
control panel** with a matching marketing landing page.

### Core pipeline

| Capability | What it does |
|---|---|
| **Reads your data and configures itself** | Detects the genetic marker, primers, read length and quality encoding from the reads. You never type truncation lengths. |
| **Refuses to waste your time** | Pre-flight catches unusable data in about a second, instead of failing 40 minutes into a run. |
| **Recovers awkward datasets** | Data DADA2 cannot denoise is routed to vsearch OTU clustering rather than rejected; reversed R1/R2 mates are detected and swapped. |
| **Names species against an India-curated reference** | 33,611 COI sequences covering 8,020 species, 43 % from Indian records. |
| **Maps what it finds** | Sites on an interactive Leaflet map, sized and popped up with species counts and diversity indices. |
| **Proves the result was not altered** | SHA-256 of every artifact, chained per sample into a Merkle ledger. The pipeline is deterministic: two independent runs produce byte-identical output. |

### Intelligence engines (built on the species table)

| Engine | Answers the question |
|---|---|
| 🌦️ **Biodiversity Weather Forecast** | *Where is diversity heading over the next rounds?* |
| 🗣️ **Multi-Agent Stakeholder Debate** | *What would an ecologist, an economist and a fisher each conclude?* |
| 🧬 **Zero-Shot Taxonomy Classifier** | *Can we flag a sequence with no reference match?* |
| 🚨 **Real-Time Anomaly Alerts** | *Is this reading a statistically significant departure from baseline?* |
| 🪸 **Biodiversity NFT Receipt** | *Can a sponsor get a tamper-proof, generative-art record of a survey?* |
| 🛰️ **Sentinel-2 Change Detection** | *Did the habitat around this site physically change?* |
| ⚠️ **Invasive-species establishment risk** | *How likely is this alien species to establish here?* |
| 📉 **Extinction-risk / population viability** | *What is the trajectory for a threatened species under scenarios?* |
| 🌊 **Hydro-corridor spread prediction** | *Which downstream sites are next, and when?* |
| 🎯 **Sampling-site optimiser** | *Where should the next survey go to maximise information?* |
| 📍 **PINN source-origin finder** | *Where upstream did this eDNA signal actually come from?* |
| 🧠 **Smart contextual alerts** | *Which detections matter, and why, in plain language?* |
| 📖 **Species knowledge base & legal mapping** | *What is this species, and what Indian law applies?* |
| 📝 **NLG executive report** | *Write the brief a decision-maker will actually read.* |
| 🔍 **Explainable AI (XAI)** | *Why did the model decide that?* |
| 📷 **Computer-vision field verification** | *Does a field photo corroborate the eDNA call?* |

Each is detailed in [§5](#5-the-six-advanced-intelligence-features) and
[§6](#6-ai--analytics-modules).

---

## 3. The web application

A single-page control panel served on `http://localhost:8080`, fully bilingual
(**English / हिन्दी**) with a modern eco-green light theme and an optional dark
theme.

| View | What you do there |
|---|---|
| **Home** | A full landing experience inside the app — the story, the science, and quick jumps into the tools. |
| **Analyze** | Drag a folder of paired-end FASTQ (or click *Select folder / files*). BioRadar auto-detects marker, primers, read length, truncation and denoiser, shows you what it found, and runs. Your uploaded datasets are listed with a live readiness check. |
| **Monitor** | Watch a run move through every pipeline stage in real time, with live logs and progress. |
| **Results** | The species table with read counts and confidence, an interactive site map, phylum-composition charts, and the intelligence engines' output. |
| **Compare** | Multi-site comparative radar and biodiversity indices — Shannon, Simpson, richness — across sites and sampling rounds (the *Time Machine*). |
| **Alerts** | Invasive-species anomaly alerts and biosecurity flags, with contextual reasoning and severity. |
| **Settings** | Pipeline configuration, theme (light/dark), and interface language. |

Navigation lives in the top bar on desktop and a bottom tab bar on mobile; the
interface is responsive and keyboard-accessible.

---

## 4. The landing site

A dedicated marketing landing page (also the app's Home view) built as a modern
React + Tailwind experience, sharing BioRadar's brand and design language with the
app so the two read as one product.

Sections: a **video hero**, a **metrics banner** (curated sequences, taxa verified,
benchmark recall, coastal baselines), **Restoring Ecology** (the eDNA biological
principles), an interactive **pipeline flowchart**, a **capabilities/zones**
showcase, a **mathematical & AI theory** deep-dive, and the **validated Indian
ecosystem baselines** (Goa, Vembanad, Kolleru, Gulf of Mannar, Lakshadweep, South
Andaman). Fully bilingual, animated, and responsive.

---

## 5. The six advanced intelligence features

Full mathematics and implementation notes are in
[docs/ADVANCED_FEATURES.md](docs/ADVANCED_FEATURES.md).

1. **AI Biodiversity Weather Forecast** — projects diversity indices forward across
   sampling rounds, giving a "forecast" of where an ecosystem is heading.
   *(`bioradar/analytics/forecast.py`)*

2. **Multi-Agent Stakeholder Debate** — an LLM debate engine with distinct personas
   (ecologist, economist, community/fisher, regulator) that argue a finding from
   their interests and converge on a recommendation.
   *(`bioradar/ai/debate.py`)*

3. **Zero-Shot eDNA Taxonomy Classifier** — flags and tentatively places sequences
   that have *no* match in the reference database, using distance-based
   classification rules, so novel or under-sequenced taxa aren't silently dropped.
   *(`bioradar/ai/zero_shot.py`)*

4. **Real-Time Streaming Anomaly Alerts** — detects statistically significant
   departures from a site's baseline as data streams in, the moment they occur.
   *(`bioradar/analytics/anomaly.py`)*

5. **Biodiversity NFT Sponsorship Receipt** — mints a tamper-proof, on-chain receipt
   for a sponsored survey, with **generative DNA-spiral art** derived from the actual
   community composition. *(`bioradar/blockchain/nft.py`,
   `bioradar/blockchain/BiodiversityNFT.sol`)*

6. **Sentinel-2 Change Detection Alerts** — correlates eDNA findings with satellite
   change detection to catch physical habitat change around a site.
   *(`bioradar/satellite/change_detection.py`)*

---

## 6. AI & analytics modules

Beyond the six headline features, BioRadar ships a broad AI/intelligence layer:

| Module | Purpose |
|---|---|
| `ai/ias_model.py` · `train_ias_model.py` | **Invasive Alien Species establishment-risk** inference model (with a trained `ias_classifier.joblib`). |
| `ai/extinction_risk.py` | Scenario-based **Population Viability Analysis** and extinction-risk trajectories. |
| `ai/spread_prediction.py` | **Hydro-corridor** fluid dispersal & site-anchored water-flow spread modelling. |
| `ai/pinn_tracer.py` | **Physics-Informed Neural Network** that traces an eDNA signal to its upstream source. |
| `ai/sampling_optimizer.py` | Biodiversity-maximising **optimal sampling-site selection**. |
| `ai/smart_alerts.py` | **Smart alerts** with contextual reasoning — ranks and explains what matters. |
| `ai/knowledge_base.py` | Species **ecological knowledge base & Indian legal mapping** (protection status, applicable law). |
| `ai/nlg_insights.py` | **Natural-language executive report** generator (data-to-text). |
| `ai/xai_explainer.py` | **Explainable-AI** feature attribution for model decisions. |
| `ai/cv_verifier.py` | On-device (**TFLite**) computer-vision field verification against photos. |
| `analytics/forecast.py` · `analytics/anomaly.py` | Diversity forecasting and streaming anomaly detection. |
| `satellite/change_detection.py` | Sentinel-2 remote-sensing change detection. |

---

## 7. Provenance, exports & standards

| Capability | Module |
|---|---|
| **Chain-of-custody** — SHA-256 per artifact, chained per sample into a cryptographic **Merkle ledger** | `bioradar/blockchain_ledger.py`, `chain_client.py`, `contract.py` |
| **Time Machine** — what changed at a site between two sampling rounds | `bioradar/time_machine.py` |
| **Watchlist** — match detections against India-priority species | `bioradar/watchlist.py` |
| **Field verification** — close the loop between a detection and the ground | `bioradar/verification.py` |
| **Exports** — CSV, JSON, **Darwin Core Archive (DwC-A)**, printable report | `bioradar/exports.py` |
| **Multi-channel alerting** — get an alert off the screen and into a pocket | `bioradar/notify.py` |

**Standards compliance:** Darwin Core (DwC) and MIxS metadata, QIIME 2 workflow
standards, deterministic reproducible runs.

---

## 8. How it works

```
FASTQ reads
    ↓  pre-flight — quality, primers, orientation, truncation
    ↓  cutadapt — remove primer sequences
    ↓  DADA2 or vsearch — reads → amplicon sequence variants (ASVs)
    ↓  naive Bayes — variants → species, against the India-curated reference
    ↓  normalizer — QIIME2 output → BioRadar's frozen data contract
    ↓  SHA-256 → chain-of-custody Merkle ledger
    ↓  intelligence engines — forecast, risk, spread, anomalies, NLG brief …
species report + map + forecast + tamper-evident record
```

### The reference database

Species names come from a COI reference assembled from NCBI:

- **33,611 sequences**, **8,020 species**
- **43 % from Indian records**, with the India/global split recorded per phylum
- Audited for cross-order collisions — sequences that cannot belong to the species
  they claim

Rebuild it with `python -m bioradar.build_reference` (~15 minutes, resumable).

---

## 9. Technology stack

| Layer | Technology |
|---|---|
| **Bioinformatics pipeline** | QIIME 2, DADA2, cutadapt, vsearch, R, Snakemake — packaged in an 11.7 GB Docker image |
| **Integration / backend** | Python 3.10+ (standard-library HTTP server; no heavyweight web framework) |
| **AI / analytics** | scikit-learn, NumPy/SciPy, PINN & PVA models, TFLite (CV), LLM agents |
| **Blockchain** | Solidity smart contract (`BiodiversityNFT.sol`) + Python chain client / Merkle ledger |
| **Web app (control panel)** | Vanilla-JS single-page app (feature-registry pattern), Leaflet maps, custom charts, i18n (EN/HI) |
| **Landing page** | React 18 + TypeScript + Tailwind CSS + Framer Motion + Lenis, bundled with esbuild |
| **Deployment** | Docker + Docker Compose |

---

## 10. Quick start (Docker)

> **Requirements:** Docker Desktop, ~40 GB free disk (the scientific image is
> 11.7 GB), 8 GB RAM minimum (16 GB comfortable — DADA2 needs 3–4 GB), and Git.
> Set Docker's memory to **6 GB+** (Settings → Resources) or DADA2 will be killed
> mid-run.

**1. Pull the pipeline image** (the long download — start it first):

```bash
docker pull ghcr.io/omtawde09/bioradar-pipeline:v1.0
```

If the registry is unreachable, build it yourself:

```bash
docker build -f docker/Dockerfile.pipeline -t ghcr.io/omtawde09/bioradar-pipeline:v1.0 .
```

**2. Get BioRadar and extract the classifier** (~30 MB, not stored in git):

```bash
git clone https://github.com/omtawde09/BioRadar.git
cd BioRadar
./scripts/setup.sh          # run from Git Bash on Windows
```

**3. Start the app:**

```bash
docker compose up app
```

Open **<http://localhost:8080>**. To run in the background add `-d`; to stop,
`docker compose down`. Full step-by-step (Docker Desktop GUI included) in
[docs/RUNNING.md](docs/RUNNING.md).

---

## 11. Testing with the sample data

BioRadar's demonstration dataset is **12 samples — 6 real Indian coastal sites,
sampled twice each** (12 MB).

| Site | What is happening there |
|---|---|
| Mandovi Estuary, Goa | *Gambusia holbrooki* (mosquitofish) establishing |
| Vembanad Lake, Kerala | *Oreochromis mossambicus* (tilapia) establishing |
| Kolleru Lake, Andhra Pradesh | *Pterygoplichthys pardalis* (sucker catfish) establishing |
| Kavaratti Lagoon, Lakshadweep | Olive ridley turtle present |
| Gulf of Mannar, Tamil Nadu | Olive ridley + green turtle |
| South Andaman | Clean reference site, no invasives |

Invasive species grow **1.9× between the two rounds**, so temporal comparison has
something real to detect.

> **The demo data is simulated, and labelled as such.** Every read is generated from
> a *real* COI reference sequence, so classifications are genuine; which species
> occur where is invented. See [docs/DEMO_DATASET.md](docs/DEMO_DATASET.md). Do not
> present it as field data.

**To run it:** the bundled demo is not pre-loaded by default (the *Your datasets*
list starts empty so you only ever see what you upload). Re-enable it by moving the
`_examples` entry back into the `datasets` array in
[`data/datasets.json`](data/datasets.json). Then open **Analyze**, pick the demo,
click **Analyze**, and watch **Results** — about **3 minutes**.

Expected: **12 named species, 80 detections, 0 unnamed records, 100 % recall.**

---

## 12. Analysing your own data

BioRadar needs **paired-end FASTQ files** — two per sample, R1 and R2:

```
MySample01_S1_L001_R1_001.fastq.gz
MySample01_S1_L001_R2_001.fastq.gz
```

Other layouts (`SRR123_1.fastq.gz`, `MySample_R1.fastq.gz`) are recognised and
renamed automatically. Sample names must not contain underscores.

**For the map**, drop a `samples.csv` next to the reads:

```csv
sample_id,site_id,latitude,longitude,collected_at
MySample01,MANDOVI,15.4989,73.8278,2026-01-15
```

`sample_id` must match the FASTQ prefix; column names are flexible (`lat`/`lon`,
`decimalLatitude`, …).

**Then:** Analyze → **Select folder** (or drag it in) → name the dataset →
**Upload & analyze**. BioRadar reads your data, configures itself, shows what it
detected, and runs (**3–40 minutes** depending on sample count and depth). Pre-flight
explains any problem before the run starts.

---

## 13. Running the web UI in development

The landing page is a React/TypeScript/Tailwind app that builds into the static
assets the Python webapp serves. Node is only needed to rebuild those assets — the
prebuilt bundle already ships in `bioradar/webapp_static/`.

```bash
npm install          # first time only
npm run build        # build CSS + home bundle + copy assets
npm run dev          # start the Python webapp on :8080
```

Individual build steps: `npm run build:css`, `npm run build:home`,
`npm run build:assets`. Source lives in `src/` (components, i18n, styles); the app
shell (vanilla JS) lives in `bioradar/webapp_static/`.

---

## 14. Troubleshooting

| Symptom | Fix |
|---|---|
| **Port 8080 already in use** | `APP_PORT=8081 docker compose up app` → open `:8081` |
| **Page loads but shows no datasets** | Expected — the list starts empty. Upload data, or restore the demo (see §11). If it's *never* populated, the volume mount is wrong: the container must see the repo at `/bioradar`. |
| **Run fails at "Denoising (DADA2)"** | Almost always memory — raise Docker's limit to 6–8 GB. |
| **`docker: command not found`** | Docker Desktop isn't running / not on PATH. Start it, wait for "Engine running". |
| **Everything comes back `Unassigned`** | The pipeline worked; your reference doesn't cover those organisms. That's a real result. |
| **Results disappeared after restart** | By design — results are session-only so the app opens clean. Files remain under `runs/`. |

More: [docs/RUNNING.md](docs/RUNNING.md), [docs/TESTING.md](docs/TESTING.md).

---

## 15. Project layout

```
bioradar/                    the integration layer
  webapp.py                  the control panel served on :8080
  webapp_static/             app shell (JS/CSS), maps, charts, i18n, built landing bundle
  contract.py                frozen schemas everything else codes against
  preflight.py               input checks that run before a pipeline run
  pipeline_runner.py         run the pipeline from Python, isolated per run
  normalize.py               raw QIIME2 output → contract CSVs
  build_reference.py         assemble the India-curated COI reference
  train_classifier.py        train a classifier inside the container
  mock_community.py          generate the labelled demo dataset
  report.py                  normalized output → readable report
  blockchain_ledger.py       SHA-256 Merkle chain-of-custody ledger
  time_machine.py            round-to-round change at a site
  watchlist.py               India-priority species matching
  verification.py            field verification loop
  exports.py                 CSV / JSON / Darwin Core Archive / report
  notify.py                  multi-channel alerting
  ai/                        forecast, debate, zero-shot, IAS risk, PVA, PINN,
                             spread, sampling optimiser, smart alerts, XAI,
                             knowledge base, NLG, CV verifier
  analytics/                 forecast + streaming anomaly detection
  satellite/                 Sentinel-2 change detection
  blockchain/                BiodiversityNFT.sol + NFT/generative-art engine

src/                         landing page — React + TS + Tailwind (components, i18n, styles)
bioradar-pipeline/           Layer-1 bioinformatics image (see NOTICE)
data/                        reference database, site metadata, demo dataset, uploads
docs/                        running, testing, contracts, pipeline, demo, design, features
tests/  ci/                  76 tests, 15 integration checks
```

---

## 16. For developers

```bash
python -m pytest tests/ -q          # 76 tests, ~8 s, no Docker needed
./ci/check_integration.sh           # 15 checks, ~2 min
./ci/check_integration.sh --fast    # skip the Docker checks
python -m bioradar.mockgen -o mock/ --rounds 3   # realistic data, no run needed
```

Read [docs/CONTRACTS.md](docs/CONTRACTS.md) before coding against BioRadar output.
Three things bite people who skip it:

- `taxon_id` can be empty — not every reference carries an NCBI taxid.
- `species` is empty for genus-level calls; filter on `rank == 'species'`.
- `rank == 'unassigned'` rows are real detections with real read counts, often the
  most interesting ones. Never silently drop them, and never parse the raw `Taxon`
  lineage string yourself — use the normalizer.

---

## 17. Documentation index

| Document | Covers |
|---|---|
| [docs/ADVANCED_FEATURES.md](docs/ADVANCED_FEATURES.md) | The six advanced features — logic and mathematics |
| [docs/RUNNING.md](docs/RUNNING.md) | Every way to run the system |
| [docs/TESTING.md](docs/TESTING.md) | Verifying each layer |
| [docs/CONTRACTS.md](docs/CONTRACTS.md) | Data formats between components |
| [docs/PIPELINE.md](docs/PIPELINE.md) | The bioinformatics itself |
| [docs/DEMO_DATASET.md](docs/DEMO_DATASET.md) | What the sample data is and is not |
| [docs/DESIGN.md](docs/DESIGN.md) | The design system — tokens, components, accessibility |
| [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | What was built, substituted, or left out |
| [README_TEAM.md](README_TEAM.md) | Team onboarding: install, run, test, contribute |

---

## 18. Licence & attribution

Licensed under **Apache-2.0** — see [LICENSE](LICENSE).

BioRadar's Layer-1 bioinformatics is derived from the **eDNA-Container App** by
Wheeler, Brancalion, Kumar and Lintermans (NSW Department of Primary Industries),
published in *Applied Sciences* 2024, 14(6), 2641,
[doi:10.3390/app14062641](https://doi.org/10.3390/app14062641). We forked rather than
rebuilt a validated, peer-reviewed taxonomic pipeline deliberately — that time went
into the translation and intelligence layers instead, the part no existing tool
provides.

QIIME 2 is BSD 3-Clause licensed ([QIIME-license](QIIME-license)). Species
assignments use the MIDORI2 reference database and NCBI sequence data. Full
attribution and a complete list of every change: [NOTICE](NOTICE).
