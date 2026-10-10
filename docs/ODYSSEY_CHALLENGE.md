# Odyssey challenge: from a real sample to an honest answer

Lives on `main`. The QIIME2 / DADA2 / BLAST pipeline is **untouched**. Everything here is new code under
`bioradar/adjudicate/` plus one view (**Check samples**, the Review view) and one small helper (`plain.js`) in the existing web app.
No QIIME2, DADA2 or BLAST is run, no model is trained. Demo script: [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Checklist: [CHALLENGE_CHECKLIST.md](CHALLENGE_CHECKLIST.md).

## One command

```bash
python -m bioradar.adjudicate.runner fetch    # download real data + reference, md5-verified (once)
python -m bioradar.adjudicate.runner all      # process every real sample (about 11 min cold, seconds cached)
python -m bioradar.adjudicate.runner verify   # check every condition of the brief -> data/real_challenge/COMPLIANCE.md
python -m bioradar.webapp --port 8099         # open http://localhost:8099 -> Check samples
```

Results are cached by file md5 + thresholds + reference build, so the demo shows pre-run output instantly.
**Check again now** recomputes one sample (10 to 150 s) with a visible timer. **Try your own file** analyses a new file and deletes it.

## What was built

| Module | Job |
|---|---|
| `thresholds.json` / `thresholds.py` | Every number in one file, each with its reason in plain words. Shown in the app ("Numbers & words"). Species cutoff depends on the gene region (12S 98.5%, COI and 16S 97%). |
| `seqio.py` | Reads FASTA/FASTQ (plain/gzip) **by content**. File names play no part. |
| `reference.py` | Reference lists (RefSeq fish mitogenomes cut to the 12S, COI or 16S region) + k-mer/identity nearest match. Profiles: `refseq_12s`, `refseq_coi_16s`, `fish_egg_paper` (the authors' own library). |
| `quality.py` | Per-sequence QC with a written reason for every rejection. Ambiguity codes (R, Y, ...) count as unclear letters, not as "not DNA". |
| `adjudicate.py` | kept / dropped / unknown per sequence, species split, look-alike groups, sample verdict. The "seen once = mistake" rule is skipped when most reads are all different (trimmed reads), and the result says so. |
| `guard.py` | Same ID twice, map point outside the area, future date, two spellings: reject/merge with reason + post-check. |
| `alerts.py` | Harmful-fish list with danger levels and source links; alert event (place, fish, level, action). |
| `seasons.py` | Same-place summer/winter comparison. "Not detected" is never written as "absent". |
| `report.py` | One-page officer PDF (per sample and per place), pure stdlib, generated live. |
| `expected.py` | Compares with a published recipe (shares within 3 times) or a published count; says "not checked" if neither exists. |
| `upload.py` | **New file path**: raw upload (12 MB cap, 80 MB unpacked cap), format by content, analysed with the same engine, deleted at once, never logged. |
| `readability.py` | Flesch-Kincaid grade and a jargon list: the objective stand-in for "can an outsider read this?" |
| `api.py`, `webapp_static/adjudicate.{js,css}`, `plain.{js,css}` | Endpoints, the Check samples view, the "In plain words" boxes and the Words page. |

## Real data used (nothing created or edited)

Layout, selection and compliance: [data/real_challenge/README.md](../data/real_challenge/README.md), `selection.json`, `COMPLIANCE.md`.
Manifest with accessions, URLs, md5 and the submitter's metadata: `data/real_challenge/manifest.json` (and one per dataset folder).
Reads are R1 only for the 12S projects; the fish-egg files are already merged read pairs (FASTA). All stored unmodified.

| Project | What it is | Used for |
|---|---|---|
| **Zenodo 4025362** (Duke & Burton 2020, Ecology and Evolution, doi:10.1002/ece3.6144; CC0) | 12 pooled libraries of 6 **fish-egg mock communities with published proportions**, COI and 16S; plus the authors' own reference library | **mixed samples with a known answer** and **unknown fish whose true identity is published** |
| PRJNA1059782 (South China Agricultural University; Chen et al. 2025, doi:10.1016/j.gecco.2025.e03906) | 12S MiFish-U. 12 mock fish communities (count only) + Pearl River Delta water at 4 sites, Aug 2019 and Nov 2019 | summer vs winter at the same place |
| PRJNA1433820 (Universitas Airlangga) | 12S MiFish-U freshwater fish, Martapura River, Indonesia, Aug 2025 | many short pieces; unknown fish; **real harmful fish: Nile tilapia, African catfish, sailfin catfish** |
| PRJNA1269473, PRJNA985779 | 12S MiFish-U, low-yield real samples (361-814 reads), a water blank | **Collect a new sample**, human contamination |
| PRJEB108476 (5,119 run records, 5 countries) | archive metadata only (no reads analysed) | record check (data guard) on real records |
| OpenStreetMap relation 6803599 "Litoral Norte" | protected-area polygon (ODbL) | map-point-outside-area rule |

References: NCBI RefSeq Actinopteri mitogenomes, retrieved 2026-10-10: 12S list 3,799 regions / 3,694 species; COI+16S list 2,319 COI and 3,901 16S regions / 3,810 species
(`data/real_challenge/reference/*/reference.json` hold the exact query and version).

## Demo map: scenario -> real sample

| Scenario | Open this | What you see |
|---|---|---|
| 1 Poor quality | `GSS356 - British Columbia` | **Collect a new sample**: 361 pieces, 65 human-DNA pieces; a reason for each |
| 2 Mixed, with shares | `G1 - mock MC3 (COI) - authors' own reference` | 7 fish; **all 7 found**; shares within 3 times of the published shares: 5 of 5; 2 extra fish named (the paper lists the same) |
| 3 Unknowns | `Irigation point 3 - South Kalimantan` | queue: closest fish, match, score capped at 0.60, "needs a check" |
| 3b Unknowns with a known identity | `E1 - mock MC1 (COI) - public RefSeq list` | 2 of 4 fish missing from the list; their DNA stays unknown; the answer-key table names them |
| 4 Bad records | **Record check** tab | 18 future dates, 4,707 outside the area, 24 same-ID merges, 2 double spellings, database clean |
| 5 Harmful fish alert | `Irigation point 3` | banner: SERIOUS, Nile tilapia, place, action line |
| 6 Season slider | **Seasons & map** tab, HongQimen | summer 58 vs winter 56 fish; 7 new, 5 not found |
| 7 Report | **Print a one-page report** | one-page PDF, generated live |
| 8 Unseen input | **Try your own file** | any FASTA/FASTQ (plain or .gz), checked and deleted |

## What is NOT claimed (read before standing in front of a judge)

1. **Mixed samples: shares are only roughly right.** Across the 12 pooled libraries every expected fish was found in **9**, and only **54 of 90** measurable
   shares were within 3 times of the published share (60%). Three libraries failed: B2 (14 of 17), F1 (6 of 9), H2 (16 of 17). They stay in the picker.
   The headline sample G1 passes (7 of 7, 5 of 5 shares). It was chosen from the documented mapping, not for passing; the figures above are the honest overall result.
   The 12S "Pearl River" mock communities still have only a count published (15 or 30 fish), so they are not verified.
2. **Wrong names happen.** When the public list lacks a fish, a close relative on the list is sometimes named (for example *Paralichthys adspersus* for *P. californicus*).
   Across the 12 unknown-identity libraries, **21 fish that were not in the mixture were named**. The page shows them in an amber note. Some may also be small amounts of other DNA; the paper reports the same kind of false hits.
3. **Seasons are summer (Aug) vs winter (Nov) 2019 in southern China, not monsoon vs summer in India.** In the ENA searches I ran I found no usable same-place Indian
   seasonal pair (the Lakshadweep run list shows only February samples; the Tuticorin run listed is a single date; the Sundarbans fish project covers Oct to Dec). Not claimed.
   The month-to-season rule is in `thresholds.json`. The deposited coordinates have 1-degree precision, so all four places share one pin.
4. **The harmful-fish list is a starter set** from IUCN GISD, not a national list. The real alerts are in Indonesia (tilapia, catfish) and China (tilapia, largemouth bass), not India.
5. **The record check runs on PRJEB108476's metadata** (Portugal and four other countries), against a Portuguese protected-area polygon chosen because real records fall both
   inside and outside it. It is not an Indian forest. "Fish name spelt two ways" comes from the reference list (real RefSeq names).
6. R1 reads only for the 12S data; identity is length-normalised ungapped/banded, not BLAST. Only fish in RefSeq can be named; others become unknown. Takifugu and some other
   pairs look the same in the 12S region and are shown as **look-alikes**, never forced to one name.
7. The fish-egg reads are merged pairs trimmed at different places, so exact copies say nothing about mistakes; the "seen once" rule is skipped for them (stated on screen).
8. "Collect a new sample" depends on thresholds that were revised once after real deep samples showed the first rule was wrong. The reason is in `thresholds.json`.
9. **Plain language is checked by a program, not by a person.** `tests/test_plain_language.py` holds every English screen string to a reading grade and a jargon list.
   No one outside the team has read the app yet. That is still the better test, and it is still open.
10. An uploaded file has no published answer and no map point, so it gets no composition check and no PDF. With dereplicated FASTA (every code seen once) the "seen once" rule is skipped, as for the fish-egg data.

## Tests

`python -m pytest tests/test_adjudicate.py tests/test_fish_egg.py tests/test_upload.py tests/test_plain_language.py tests/test_review_view_static.py tests/test_report_one_page.py tests/test_fetch_resilience.py tests/test_results_visuals_static.py`
(153 tests; the ones that read real files skip if the data is not downloaded).
Pre-existing, unrelated: `tests/test_dataset_registry.py::test_the_repository_ships_the_demo_dataset` fails because `data/datasets.json` has no `demo-survey` entry.
