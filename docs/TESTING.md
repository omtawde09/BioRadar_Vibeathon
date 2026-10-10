# Testing BioRadar Layer 1

Six levels, fastest first. Each one is independently runnable — you don't need
Docker to test most of this, and you don't need the pipeline to finish to know
whether your code is correct.

| Level | Command | Time | Needs |
|---|---|---|---|
| 1. Unit tests | `python -m pytest tests/ -q` | ~9 s | nothing |
| 2. Contract checks | `./ci/check_integration.sh --fast` | ~20 s | nothing |
| 3. Full CI | `./ci/check_integration.sh` | ~2 min | Docker |
| 4. Pipeline dry run | `python -m bioradar.pipeline_runner … --dry-run` | ~15 s | Docker |
| 5. Full pipeline run | `python -m bioradar.pipeline_runner …` | ~7 min | Docker + image |
| 6. Indian dataset | see [§6](#6-the-indian-dataset-end-to-end) | ~40 min | Docker + classifier |

Run levels 1–2 before every commit. Run level 3 before every push. Run 5–6 when
you change anything inside `bioradar-pipeline/`.

---

## 1. Unit tests

```bash
python -m pytest tests/ -q
```

**Expect:** `174 passed`.

What they actually protect:

- **Advanced Feature Pipelines** — validates Platts-scaled forecast trends, Isolation Forest anomaly flags, zero-shot DNA k-mer similarity scoring, Sentinel-2 NDVI math, stakeholder debate consensus orchestration, and generative NFT spiral art rendering.
- **Lineage parsing edge cases** (`tests/test_normalize.py`) — every one was
  found in real pipeline output: `c__class_Testudines_8459` (malformed rank
  labels), species names containing spaces, genus-only truncation, `Unassigned3`,
  missing taxids. If one of these breaks, downstream code receives *wrong*
  taxonomy rather than an error, which is the worst failure mode in the system.
- **Hash determinism** — the same payload must always produce the same hash, or
  chain-of-custody verification fails on data that was never tampered with.
- **Run isolation** — two pipeline runs must never share a working directory.
- **Mock/real interchangeability** — mock data must satisfy the same contract.

Run one group while iterating:

```bash
python -m pytest tests/test_normalize.py -q
python -m pytest tests/test_integration.py::TestChainClient -q
python -m pytest tests/test_forecast.py -q
```

---

## 2. Contract checks (fast)

```bash
./ci/check_integration.sh --fast
```

**Expect:** `passed 13, failed 0, skipped 3` (3 skipped = Docker + the two
downstream hooks that activate when Anshika's and Tanay's modules land).

This tests the *boundaries between people*, which is where hackathons actually
break — not any one component's internals:

- the normalizer still emits exactly `contract.TAXONOMY_COLUMNS`
- mock data has not drifted from real pipeline output
- hash → POST → verify round-trips against a live ledger
- **the pipeline still succeeds when the backend is down** (records queue locally)
- every site in `data/sites.csv` is inside India's bounding box

If this fails, do not push. Someone else's code is about to break.

---

## 3. Full CI

```bash
./ci/check_integration.sh
```

**Expect:** `passed 14, failed 0, skipped 2`.

Adds a Snakemake DAG validation inside the real container — it catches a broken
`Snakefile` in 15 seconds instead of 7 minutes into a run.

---

## 4. Pipeline dry run

```bash
python -m bioradar.pipeline_runner testing_data/fastq_data --mode docker --dry-run
```

**Expect:** a 15-job DAG, ending with `normalize_taxonomy` and `emit_hash`.

If your rule doesn't appear here, Snakemake doesn't think it's needed — usually a
mismatch between a rule's declared `output` and the next rule's `input`.

---

## 5. Full pipeline run (bundled test data)

```bash
python -m bioradar.pipeline_runner testing_data/fastq_data \
    --mode docker --sample-id BR-TEST-001
```

**Expect** (~7 minutes, 6 samples):

```
[  7%] Reading sample sheet
[ 14%] Building QIIME2 manifest
...
[ 93%] Normalizing to BioRadar contract
[100%] Recording chain-of-custody hash
```

Then check the outputs:

```bash
ls runs/<run-id>/final_results/
head -2 runs/<run-id>/final_results/taxonomy_normalized.csv
cat  runs/<run-id>/final_results/sample_summary.csv
```

**Known-good values for the bundled test data** — these are a real regression
baseline, verified across two independent runs:

| Check | Expected |
|---|---|
| Rules completed | 15/15 |
| Samples | 6 |
| ASVs | 9 |
| Species-level assignments | 5 per sample |
| `Gambusia holbrooki` taxid | `37273`, confidence > 0.99 |
| `Homo sapiens` | present in `sample4` only (contamination control) |
| taxonomy_normalized.csv sha256 | `e4db8fbd641aaeb4069bf9d6635aa2fa9ac008dfff3cb0cb96c95ed9498398e2` |

That last row is the strongest test in the repo. **The pipeline is
deterministic** — two independent runs produced byte-identical output. If your
hash differs, something changed: classifier, primers, DADA2 parameters, or the
image. That is exactly the property the chain of custody depends on, so treat a
mismatch as a real finding, not noise.

```bash
python -c "
from bioradar.chain_client import sha256_file
from pathlib import Path
print(sha256_file(Path('runs/<run-id>/final_results/taxonomy_normalized.csv')))"
```

### Testing the chain of custody

The pipeline writes its hash record locally first, then tries to POST it. Test
both paths.

**Backend down** (the default during development):

```bash
cat runs/<run-id>/final_results/hash_record.json | python -m json.tool | head -20
ls runs/<run-id>/final_results/_chain_queue/
```

Expect `"committed": false` and one queued `.json`. **The run must still have
succeeded** — a ledger outage must never fail a pipeline run.

**Backend up:**

```bash
python -m integration.mock_backend --port 8000 &
python -m bioradar.chain_client --flush --queue-dir runs/<run-id>/final_results/_chain_queue
curl -s http://127.0.0.1:8000/api/v1/chain/verify/BR-TEST-001
```

Expect `{"sent": 1, "failed": 0, "remaining": 0}` then `"chain_intact": true`.

**Tamper test** — proves verification actually detects modification:

```bash
python -c "
from pathlib import Path
p = Path('runs/<run-id>/final_results/taxonomy_normalized.csv')
p.write_text(p.read_text().replace('Gambusia holbrooki', 'Fake species'))"
```

Re-hash the file: it must differ from the value recorded in `hash_record.json`.
That difference is the tamper evidence. (Restore by re-running the pipeline.)

---

## 6. The Indian dataset end-to-end

The full path: download real Indian samples → build an India-curated reference →
train a classifier → run → report.

```bash
# 1. fetch the Grande Island (Goa) COI data (3 samples, ~290 MB)
python -m bioradar.fetch_data --project PRJNA985590 \
    -o data/india_goa_reef --prefix BR-GOA-REEF

# 1b. check it BEFORE spending an hour on it
python -m bioradar.preflight data/india_goa_reef/fastq \
    --fprimer GGWACWGGWTGAACWGTWTAYCCYCC \
    --rprimer TANACYTCNGGRTGNCCRAARAAYCA \
    --trunc-len-f 210 --trunc-len-r 195 --amplicon-length 313

# 2. build the India-curated COI reference (~15 min, resumable)
python -m bioradar.build_reference -o data/reference_coi_india

# 3. train the classifier inside the container (~20-40 min)
python -m bioradar.train_classifier \
    --reference data/reference_coi_india \
    --output bioradar-pipeline/database/qiime2-qza/classifier-coi-india-2026.qza \
    --marker coi-leray

# 4. run the pipeline
python -m bioradar.pipeline_runner data/india_goa_reef/fastq --mode docker \
    --classifier /db/qiime2-qza/classifier-coi-india-2026.qza \
    --fprimer GGWACWGGWTGAACWGTWTAYCCYCC \
    --rprimer TANACYTCNGGRTGNCCRAARAAYCA

# 5. generate the report
python -m bioradar.report \
    --taxonomy runs/<run-id>/final_results/taxonomy_normalized.csv \
    --samples data/india_goa_reef/samples.csv \
    --title "Grande Island, Goa - coral reef eDNA" \
    -o reports/goa_reef_india.md
```

### Things that will go wrong, and what they mean

**`--match COI` matters.** PRJNA1296846 contains 3 atolls × 2 markers (18S and
COI). Running both together trims with the wrong primers and silently discards
most reads. Always filter to one marker.

**`--swap-mates` matters.** This library was sequenced in reverse orientation:
30% of pairs have the reverse primer on R1 versus 7% the standard way round.
cutadapt runs with `--p-discard-untrimmed`, so without the swap you throw away
four fifths of your usable data. Verify with:

```bash
python -m bioradar.fetch_data --project <ACC> -o <dir> --dry-run
```

**Zero reads after trimming** is the classic symptom of wrong primers. Check
before running:

```bash
python -c "
import gzip, re
IUPAC = {'A':'A','C':'C','G':'G','T':'T','R':'[AG]','Y':'[CT]','S':'[GC]','W':'[AT]',
         'K':'[GT]','M':'[AC]','B':'[CGT]','D':'[AGT]','H':'[ACT]','V':'[ACG]','N':'.'}
rx = re.compile(''.join(IUPAC[c] for c in 'GGWACWGGWTGAACWGTWTAYCCYCC'))
f = 'data/india_goa_reef/fastq/<SAMPLE>_S1_L001_R1_001.fastq.gz'
n = hits = 0
with gzip.open(f,'rt') as fh:
    for i,l in enumerate(fh):
        if i%4==1:
            n += 1; hits += bool(rx.match(l[:30]))
        if n >= 20000: break
print(f'{100*hits/n:.1f}% of reads start with the forward primer')"
```

Below ~5%, your primers are wrong or the mates need swapping.

**Classifier version mismatch.** If `assign_taxonomy` fails with a scikit-learn
error, the classifier was built against a different QIIME2 release. The container
is QIIME2 2023.2 / scikit-learn 0.24.1. Never download a pre-trained classifier —
build it with `bioradar.train_classifier`, which trains *inside* the container so
it is loadable by construction.

**Everything Unassigned.** The pipeline is working; your reference doesn't cover
these organisms. That is a real result, not a bug — report the unassigned
fraction rather than hiding it.

---

## What each teammate should test

| Person | Test |
|---|---|
| **Anshika** | `python -m bioradar.mockgen -o mock --rounds 3` then flag against `mock/taxonomy_normalized.csv`. Your engine must handle `rank == 'unassigned'`, empty `taxon_id`, and genus-only rows without crashing. |
| **Tanay** | Same mock file. Use `total_reads` from `sample_summary.csv` as your diversity denominator, not the sum of assigned reads. |
| **Ishwar** | `mock/samples.csv` has real coordinates. `mock/alerts.example.json` is the alert shape. |
| **Parth** | `python -m integration.mock_backend` is the reference implementation of the two chain endpoints. Your `payload_hash` must match `bioradar.chain_client.canonical_hash` exactly — sorted keys, `separators=(',',':')`, UTF-8. |
| **Jimeet** | `data/reference_coi_india/sources.csv` shows Indian vs global record counts per phylum. `bioradar-pipeline/scripts/qiime-create-database.sh` is the upstream reference for classifier training. |

Once Anshika's and Tanay's modules exist, two currently-skipped CI checks
activate automatically — no one has to remember to switch them on.

---

## Setting up a fresh machine

```bash
./scripts/setup.sh
```

Checks Docker, pulls the image, extracts classifiers, generates `.env` with a
real JWT secret, starts PostGIS, generates mock data, and runs the fast CI. Safe
to re-run.

If Python HTTPS downloads fail with `CERTIFICATE_VERIFY_FAILED` while `curl`
works, antivirus is intercepting TLS: `pip install truststore`.
