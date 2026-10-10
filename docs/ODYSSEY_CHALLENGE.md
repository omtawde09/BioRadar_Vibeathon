# Odyssey challenge: from a real sample to an honest answer

Branch: `challenge/odyssey-adjudication`. The QIIME2 / DADA2 / BLAST pipeline is
**untouched**. Everything here is new code under `bioradar/adjudicate/` plus one view
(**Review**) in the existing web app. No QIIME2, DADA2 or BLAST is run, no model is trained.

## One command

```bash
python -m bioradar.adjudicate.runner fetch    # download real data + reference, md5-verified (once)
python -m bioradar.adjudicate.runner all      # process every real sample (about 3 min cold, 2 s cached)
python -m bioradar.webapp --port 8099         # open http://localhost:8099 -> Review
```

Results are cached by file md5 + thresholds + reference build, so the demo shows pre-run
output instantly. **Re-run live** in the view recomputes one sample (15-35 s) with a visible timer.

## What was built

| Module | Job |
|---|---|
| `thresholds.json` / `thresholds.py` | Every number in one file, each with its reason. Shown in the app ("Numbers & sources"). |
| `seqio.py` | Reads FASTA/FASTQ (plain/gzip) **by content**. File names play no part. |
| `reference.py` | 12S reference (RefSeq fish mitogenomes cut to the MiFish-U amplicon) + k-mer/identity nearest match. |
| `quality.py` | Per-sequence QC with a written reason for every rejection. |
| `adjudicate.py` | kept / dropped / unknown per sequence, species split, species complexes, sample verdict. |
| `guard.py` | Duplicate ID, GPS outside boundary, future date, two spellings: reject/merge with reason + post-check. |
| `alerts.py` | Invasive list with danger levels and source links; alert event (pin, species, level, action). |
| `seasons.py` | Same-site summer/winter comparison. "Not detected" is never written as "absent". |
| `report.py` | One-page officer PDF, pure stdlib, generated live. |
| `expected.py` | Compares with source-supported composition; says "not checked" if none exists. |
| `api.py`, `webapp_static/adjudicate.{js,css}` | Endpoints and the Review view. |

## Real data used (nothing created or edited)

Manifest with accessions, URLs, md5 and the submitter's metadata: `data/real_challenge/manifest.json`.
Reads are R1 only, stored unmodified.

| Project | What it is | Used for |
|---|---|---|
| PRJNA1059782 (South China Agricultural University; Chen et al. 2025, doi:10.1016/j.gecco.2025.e03906) | 12S MiFish-U. 12 mock fish communities + Pearl River Delta water at 4 sites, Aug 2019 and Nov 2019 | mixed samples; summer vs winter at the same site |
| PRJNA1433820 (Universitas Airlangga) | 12S MiFish-U freshwater fish, Martapura River, Indonesia, Aug 2025 | primer-dimer short fragments; unknown fish; **real invasive Nile tilapia, African catfish, sailfin catfish** |
| PRJNA1269473, PRJNA985779 | 12S MiFish-U, low-yield real samples (361-814 reads), a water blank | **Retake sample**, human contamination |
| PRJEB108476 (5,119 run records, 5 countries) | archive metadata only (no reads analysed) | data guard on real records |
| OpenStreetMap relation 6803599 "Litoral Norte" | protected-area polygon (ODbL) | GPS-boundary rule |

Reference: NCBI RefSeq Actinopteri mitogenomes, retrieved 2026-10-10, 3,799 amplicons /
3,694 species (`data/real_challenge/reference_12s/reference.json` holds the exact query and version).

## Demo map: scenario -> real sample

| Scenario | Open this in Review | What you see |
|---|---|---|
| 1 Poor quality | `GSS356 - British Columbia` | **Retake sample**: 361 reads, 65 human-contamination reads, junk; reason on screen for each |
| 2 Mixed | `A2 - HongQimen` | 15 species with shares; count check against the source's "15 fish" |
| 3 Unknowns | `Irigation point 3 - South Kalimantan` | review queue: closest match, identity, confidence capped at 0.60, "needs review" |
| 4 Bad records | **Data guard** tab | 18 future dates, 4,707 outside boundary, 24 duplicate-ID merges, 2 double spellings (grass carp *idella/idellus*), post-check clean |
| 5 Invasive alert | `Irigation point 3` | banner: HIGH, Nile tilapia, pin -3.4053, 114.7900, action line |
| 6 Season slider | **Seasons & map** tab, HongQimen | summer 58 vs winter 56 species; 7 newly detected, 5 not detected |
| 7 Report | **Print officer report** button | one-page PDF, generated live |
| 8 Unseen input | the picker (38 real samples) | any sample gives verdict, reasons, source and fallback |

## What is NOT claimed (read before standing in front of a judge)

1. **Mixed sample: shares are not verified.** The source only says how many fish were mixed
   (BioSample `samp_size`: A and C = 15, B and D = 30), not which species or proportions. The paper
   with the species table is behind a CAPTCHA and was not retrieved. The engine finds 15 species-level
   calls for the 15-fish mixes (**count consistent**) but only about 14-15 for the 30-fish mixes
   (**reported as FAIL**: reference gaps and indistinguishable pairs). To add a real check, put the
   paper's table in `data/real_challenge/expected_composition.json`:
   `{"samples": {"A2": {"source": "<citation>", "species": [{"name": "Genus species", "expected_share": 0.0667}]}}}`.
2. **"Two sequences not in the reference, identity known"** is not demonstrated with ground truth.
   Unknowns are shown with their closest match and an NCBI link for manual review.
3. **Seasons are summer (Aug) vs winter (Nov) 2019**, not monsoon vs summer. The month-to-season rule is in
   `thresholds.json`. The deposited coordinates have 1-degree precision, so all four sites share one pin.
   HongQimen winter has 2 replicate bottles, not 3.
4. **The invasive list is a starter set** from IUCN GISD, not a national list. The real triggers are in
   Indonesia (tilapia, catfish) and China (tilapia, largemouth bass), not India.
5. **The data guard runs on PRJEB108476's metadata** (Portugal and four other countries), against a Portuguese
   protected-area polygon chosen because real records fall both inside and outside it. Those records'
   reads were not analysed. "Species two spellings" comes from the reference list (real RefSeq names).
6. R1 reads only; read pairs are not merged. Identity is length-normalised ungapped/banded, not BLAST.
7. Only fish in RefSeq can be named; others become unknown. Takifugu and some other pairs are
   indistinguishable on 12S and are shown as a *complex*, never forced to one name.
8. "Retake" depends on thresholds that were revised once after real deep samples showed the first rule
   (proportion of usable reads) was wrong. The reason is recorded in `thresholds.json`.

## Tests

`python -m pytest tests/test_adjudicate.py` (21 tests; 3 run on the real files and skip if absent).
Pre-existing, unrelated: `tests/test_dataset_registry.py::test_the_repository_ships_the_demo_dataset`
fails because `data/datasets.json` has no `demo-survey` entry (and the `data/demo_survey/` files were
deleted from the working tree during this session by something other than this branch's code).
