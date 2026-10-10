# BioRadar integration contracts

**Frozen. Changing anything here breaks somebody else's code.**

Every format below is produced by Layer 1 and consumed by at least two other team
members. These are derived from what the pipeline *actually emits* — verified
against a real run, not designed on paper. `ci/check_integration.sh` fails if any
of them drifts.

Machine-readable definitions live in [`bioradar/contract.py`](../bioradar/contract.py).
That file is the authority; this document explains it.

---

## Why the raw pipeline output cannot be used directly

The pipeline emits one row per ASV with one column per sample, and the entire
lineage packed into a single string:

```
Feature_ID,sample1,...,sample6,Taxon,Confidence
a595...,499.0,...,486.0,k__Eukaryota_2759;...;s__Gambusia holbrooki_37273,0.9959
```

Three problems for downstream consumers:

1. **Wide, not long.** Flagging, analytics and the dashboard all work per sample.
2. **Lineage is a string.** No rank columns, no separate taxid.
3. **It has sharp edges.** Truncated lineages (`...;g__Carassius_7956` with no
   species), malformed labels (`c__class_Testudines_8459`), species names
   containing spaces, `Unassigned` / `Unassigned3`, counts as floats.

`bioradar/normalize.py` handles all of it. **Nobody else should parse the raw
`Taxon` string.** If you find yourself splitting on `;`, stop and use the
normalizer.

---

## Contract 1 — `taxonomy_normalized.csv`

**Om → Anshika (flagging), Tanay (analytics), Parth (storage)**

One row per `(sample_id, asv_id)` detection. Rows with zero reads are omitted:
an ASV with no reads in a sample is an absence, not a detection.

| Column | Type | Notes |
|---|---|---|
| `sample_id` | string | BioRadar sample code, e.g. `BR-2026-GOA-MANDOVI-R01` |
| `asv_id` | string | md5 from DADA2; stable across runs for identical sequence |
| `taxon_id` | string | NCBI taxid of the deepest assigned rank. **May be empty** |
| `scientific_name` | string | name at the deepest assigned rank |
| `rank` | enum | `kingdom`…`species`, or `unassigned` |
| `kingdom`…`species` | string | seven rank columns; empty where unassigned |
| `confidence` | float | 0.0–1.0, classifier confidence |
| `read_count` | int | reads for this ASV in this sample, > 0 |
| `rel_abundance` | float | `read_count` ÷ sample total, 6 dp |
| `classification_method` | enum | `sklearn` or `blast` |
| `lineage_raw` | string | original lineage string, kept for provenance |

### Things that will bite you

- **`taxon_id` can be empty.** Some references carry no taxid. Join on it where
  present, fall back to `scientific_name`. Never assume it is populated.
- **`species` is empty for genus-level calls.** In the real test data, 3 of 9
  ASVs stop at genus. Filter on `rank == 'species'` when you need species.
- **`rank == 'unassigned'` means every rank column is empty.** These are real
  detections with real read counts — often the most interesting ones, since they
  are candidate novel taxa. Do not silently drop them.
- **The same species can appear as several ASVs** in one sample. Aggregate by
  `species` or `taxon_id`, not by row count, for richness.
- **`confidence` in 0.70–0.85** is Anshika's AI-second-opinion trigger band. The
  mock data deliberately populates it.

### Getting it

```bash
python -m bioradar.normalize runs/<run-id>/final_results -o out/
python -m bioradar.normalize testing_data/final_results.zip -o out/   # no Docker needed
```

```python
from bioradar.normalize import normalize_results
written = normalize_results(Path("runs/abc/final_results"), Path("out"))
```

---

## Contract 2 — `sample_summary.csv`

**Om → Tanay (diversity denominators), Ishwar (dashboard header numbers)**

| Column | Notes |
|---|---|
| `sample_id` | matches Contract 1 |
| `total_reads` | all ASV reads including unassigned — use this as the denominator |
| `asv_count` | distinct ASVs with > 0 reads |
| `species_count` | distinct species-level assignments |
| `genus_count` | distinct genus-level assignments |
| `unassigned_reads` | reads whose lineage was `Unassigned` |
| `unassigned_fraction` | the reference-gap number worth showing judges |

---

## Contract 3 — chain-of-custody record

**Om → Parth**, `POST /api/v1/chain/record`

```json
{
  "sample_id": "BR-2026-GOA-001",
  "pipeline_run_id": "run-20260803T073819-1a2b3c4d",
  "timestamp": "2026-08-03T07:45:17Z",
  "event_type": "pipeline_complete",
  "actor": "bioradar-pipeline",
  "payload_hash": "dcc75e84a9def652f84994ee9dd26eb14880a925fe886ad64444ae0ff7a56e98",
  "payload": {
    "artifacts": {
      "taxonomy": { "sha256": "e4db8f…", "bytes": 14972, "filename": "taxonomy_normalized.csv" },
      "biom":     { "sha256": "973fa4…", "bytes": 606,   "filename": "asv-table.tsv" }
    },
    "classifier": "/db/qiime2-qza/MIDORI2_…qza",
    "fprimer": "ACACCGCCCGTCACTCT",
    "rprimer": "CTTCCGGTACACTTACCATG"
  }
}
```

### Rules the backend must follow

1. **`payload_hash` is SHA-256 of the canonical JSON of `payload`**, serialised
   as `json.dumps(payload, sort_keys=True, separators=(',', ':'))` encoded UTF-8.
   Any other serialisation — different separators, indentation, key order —
   produces a different hash and verification fails on correct data. Use
   `bioradar.chain_client.canonical_hash` on both sides.
2. **Each artifact is hashed separately**, so a verifier can say *which* file was
   tampered with.
3. **`previous_hash` is assigned by the backend**, not the pipeline: the
   `payload_hash` of the previous record for the same `sample_id`, or null for
   the genesis record.
4. **The pipeline never fails because the ledger is down.** Records are written
   locally first and queued. `python -m bioradar.chain_client --flush` replays
   them, oldest first — order matters, since each links to its predecessor.

Valid `event_type` values are in `contract.CHAIN_EVENT_TYPES`. A reference
implementation of both endpoints is in
[`integration/mock_backend.py`](../integration/mock_backend.py) — a test double
for CI, **not** a substitute for Parth's backend.

---

## Contract 4 — Time Machine diff

**Om + Jimeet → Ishwar (Trends view)**, `GET /api/v1/samples/{id}/trends`

```json
{
  "site_id": "GOA-MANDOVI",
  "rank": "species",
  "appeared": [ { "name": "...", "taxon_id": "...", "read_count": 120, "rel_abundance": 0.08 } ],
  "disappeared": [ ... ],
  "changed": [ { "name": "Gambusia holbrooki", "rel_abundance_change": 1.1591,
                 "log2_fold_change": 1.11, "direction": "increased" } ],
  "stable": [ ... ],
  "summary": {
    "appeared_count": 0, "disappeared_count": 1, "changed_count": 4,
    "richness_delta": -1, "shannon_before": 1.3815, "shannon_after": 1.0737,
    "shannon_delta": -0.3078, "turnover": 0.1429
  }
}
```

Two deliberate decisions:

- **Comparison is at species level, not ASV level.** ASV hashes are
  sequence-exact — a one-base difference creates a new ASV for what is
  biologically the same organism, so ASV-level diffs report constant churn.
- **Changes are relative, not raw.** Sequencing depth varies between runs; raw
  counts are not comparable. A run with twice the depth would otherwise look like
  every species doubled. Changes below `noise_threshold` (default 0.25) are
  reported as `stable`.

---

## Sample identity

The pipeline derives the sample id from the FASTQ filename — everything before
the first underscore (`sample=${R1%%_*}` in `scripts/create_metadata_file.sh`).

**So name FASTQ files by BioRadar sample code:**

```
BR-2026-GOA-MANDOVI-R01_S1_L001_R1_001.fastq.gz
BR-2026-GOA-MANDOVI-R01_S1_L001_R2_001.fastq.gz
```

Sample codes must not contain underscores. Use `contract.sample_id_from_fastq()`
to predict the id before the run finishes.

---

## Mock data

Everything above is available as mock data that is byte-compatible with real
output, so nobody waits on Docker:

```bash
python -m bioradar.mockgen -o mock/ --rounds 3
```

| File | For |
|---|---|
| `mock/samples.csv` | Parth (samples table), Ishwar (map pins with lat/long) |
| `mock/taxonomy_normalized.csv` | Anshika, Tanay |
| `mock/sample_summary.csv` | Tanay, Ishwar |
| `mock/alerts.example.json` | Anshika (target shape), Ishwar (render against it) |
| `mock/by_sample/<id>.csv` | Time Machine input |

Deterministic for a given seed, so two people generating "the same" mock data get
identical bytes, and CI can assert on it.

**One caveat:** only taxids marked `taxid_verified=yes` in
[`data/species_pool.csv`](../data/species_pool.csv) came from real pipeline
output. The rest are **blank on purpose** — inventing plausible NCBI taxids would
silently corrupt every join against Jimeet's reference tables. Filling them in is
Jimeet's deliverable.
