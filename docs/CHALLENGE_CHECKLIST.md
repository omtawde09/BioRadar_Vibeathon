# Challenge checklist: what they asked for vs what BioRadar has

Sources: **Points Noted.pdf** (handwritten notes) and **Challenges BioRadar.pdf** (the ODYSSEY brief: "Prove What Lives in the Water").
Status is taken from the live check `python -m bioradar.adjudicate.runner verify` (writes `data/real_challenge/COMPLIANCE.md`)
and from the running app on `main`. Nothing is marked done unless it was run on real public data.
Last updated after the fish-egg ground truth, the upload path and the plain-language pass. The app screens are now called
**Check samples** (the Review view), **Record check** (data guard) and **Words** (glossary).

**Summary: all 8 challenges and all 5 critical targets are met on real public data. The outsider test and the demo rehearsal were done by the team (as reported by the maintainer). Four limits are stated in section 5.**

Legend: ✅ done on real data · 🟡 partly (the gap is stated) · ❌ not met · ⬜ not done yet · ➕ BioRadar already had it before the challenge

---

## 1. The 8 challenges from the handwritten notes

| # | Challenge (as written) | Status | What BioRadar does | Where to see it |
|---|---|---|---|---|
| 1 | 5 identifiable species with shares (sample from a mixed sample) | ✅ 🟡 | Real fish-egg mock communities whose **species and shares are published** (Duke & Burton 2020, Table 1). Headline `G1` (7 fish): all 7 found, shares within 3 times: 5 of 5. Over all 12 libraries: every fish found in 9, shares within 3 times for **54 of 90 (60%)**; 3 libraries failed and are shown. The 12S Pearl River mixtures still have only a count | Check samples → `G1 - mock MC3 (COI) - authors' own reference` |
| 2 | Poor-quality and noisy samples | ✅ | Per-sequence QC: short fragment, N bases, low quality, low complexity, seen-once, human DNA, unrelated. Real case: 361 reads, 65 human-DNA reads | Review → `GSS356` |
| 3 | 2 samples not in our reference list but actual identity is known | ✅ 🟡 | Same fish-egg library judged against the public RefSeq list, which has no entry for 2 of 4 fish (*Oxyjulis californica*, *Paralichthys californicus*). Their DNA stays **unknown**; the authors' own library names them in an answer-key table. Honest limit: across the 12 libraries 21 fish that were *not* in the mixture were named (some are close relatives of a missing fish) | Check samples → `E1 - mock MC1 (COI) - public RefSeq list` |
| 4 | Retake the sample if noisy or poor data samples are present | ✅ | Verdict **Retake sample** (under 1,000 usable reads, or under 10% usable); "Usable with caution" between | Review → `GSS356`, `GSS471`, water blank |
| 5 | Detect inconsistent, redundant and duplicate samples, with valid reasoning | ✅ | Data guard on 5,119 real archive records: 24 duplicate IDs merged as re-runs, 18 future dates, 4,707 outside boundary, 367 without GPS, 2 species double spellings. Every decision has a written reason; post-check says the clean store is clean | Review → Data guard |
| 6 | Alert the officer about the danger level of invasive species | ✅ | Banner + log + alert map with pin, species, level (CRITICAL / HIGH / WATCH), action and IUCN source link. Real trigger: **HIGH, Nile tilapia and African catfish** (Indonesia). No SMS or e-mail is sent for the challenge path | Review → `Irigation point 3`, Alerts tab |
| 7 | Timeline of the two seasons (summer, winter) for the same location | ✅ | Same-place slider: fish per season, new, not found, repeats, quality caution. Pearl River, 4 places, **Aug vs Nov 2019** (matches the notes: summer / winter) | Check samples → Seasons & map |
| 8 | 1-page conclusion PDF: animal detected, risk level, source and sample date, uncertainty / missing coverage | ✅ | One-page PDF per sample and per site (both seasons), generated live; guarded so it cannot spill to page 2; 43 tests prove one page, no overlap, all fields | "Print officer report" buttons; samples in `docs/demo_outputs/` |

## 2. Critical targets (handwritten)

| # | Target | Status | Notes |
|---|---|---|---|
| 1 | Rejected samples have a documented reason | ✅ | reason per dropped sequence on screen; full list as CSV; sample-level reason on the verdict |
| 2 | 5 distinct species from a sample, each shown with its share | ✅ | `G1`: 7 fish, each with its share and the published share beside it; shares are within 3 times for 5 of 5 (60% over all 12 libraries) |
| 3 | Unknown sequences reported with a confidence score | ✅ 🟡 | reported with **match** (measured) and a **match score** capped at 0.60. The score is a documented rule of thumb, **not** a calibrated probability, and is labelled so |
| 4 | Trigger alert for the forest officer for invasive species | ✅ | see challenge 6 |
| 5 | UI clean and simple, focused on graphs and visuals | ✅ | Results page opens with a plain-words summary, a donut, top-animal bars, a sureness histogram and per-sample DNA / variety charts; briefing and animal table folded; every page has an "In plain words" box and a Words page; English + Hindi |

## 3. The ODYSSEY brief

### 3A. "One sample, an honest answer"

| Requirement | Status | Notes |
|---|---|---|
| Select 3 real samples from a documented public eDNA dataset | ✅ | 50 real libraries from 5 public projects (ENA and Zenodo), core samples named in `selection.json`. Files are read **by content**; no FASTA file was created |
| Do not write or alter sequences; keep originals and metadata unchanged | ✅ | all 51 files (50 libraries + the authors' reference library) verified by md5 against the archive (0 altered) |
| Mixed sample with 5 identifiable species + source-supported shares | ✅ | `G1` (7 fish) against the paper's published proportions. The paper itself sits behind a CAPTCHA, so the proportions come from the open-access PMC text and the supplementary table (Europe PMC), and Zenodo mirrors the data. Built by `build_truth` with checks that each community sums to 1 and has the printed species count |
| Poor-quality sample (short fragments, many N, unrelated, human DNA) | ✅ | `GSS356` (+ primer-dimer fragments in the Indonesian sample) |
| Sample with 2 sequences not in the reference list, identity known or reviewable | ✅ | known (answer key) **and** reviewable (NCBI link) for `E1 - public RefSeq list` |
| Rejects poor sequences with a reason for every dropped sequence; "Retake sample" if unusable | ✅ | |
| Splits mixed sample into all species and reports estimated shares | ✅ 🟡 | splits ✅; verified against the source ✅ for the headline sample; overall accuracy is modest (60% of shares within 3 times) and is stated |
| Marks unrecognised sequences **unknown**, shows closest match and confidence, review queue, never confirmed or full confidence | ✅ | status `needs review`, capped, never 1.0 |
| Does not crash on any input; kept / dropped / unknown summary for each real sample | ✅ | all 62 analyses done (50 libraries; the 12 fish-egg ones twice). Empty, non-DNA, picture, broken-gzip and gzip-bomb files get a plain message |
| File name must not decide the answer | ✅ | format read from content; a test copies a real file under a misleading name and gets the same result |

### 3B. "Data guard and risk alert"

| Requirement | Status | Notes |
|---|---|---|
| Duplicate sample ID | ✅ | real: 24 shared IDs merged as technical re-runs (same biological sample); ID *collisions* (two samples, one ID) are rejected by rule but **do not occur** in the real data |
| GPS pin outside the selected forest boundary | ✅ 🟡 | real polygon (OpenStreetMap "Litoral Norte" protected area): 4,707 outside, 27 inside. It is a coastal protected area in Portugal, chosen because real records fall both inside and outside; not a forest in India |
| Future collection date | ✅ | real: 18 records dated 2027 / 2028 |
| Species name with two spellings | ✅ | real: grass carp *idella / idellus*; *Megalobrama skolkovii / skolokovii* (sequence must agree, so look-alike different species are left alone) |
| Reject or merge each bad record with a reason; database stays clean; do not edit the source | ✅ | source TSV untouched (md5 recorded); post-check on the clean store passes |
| If a condition is absent from real data, say so | ✅ | the page states "no such case" per rule |
| Documented invasive-species list with danger levels and source references | ✅ | 15 species, 3 levels, IUCN GISD links. A starter list, not a national one |
| Alert within seconds, with map pin, species and threat level, from a real sample; do not invent | ✅ 🟡 | pre-run: instant (alert written about 0 s after the result). Live re-run of a sample takes 15–35 s |
| Dashboard banner + log, no real SMS | ✅ | |

### 3C. "Map, seasonal comparison and report"

| Requirement | Status | Notes |
|---|---|---|
| Two seasons, **same location**, real samples | ✅ 🟡 | 4 places, summer (Aug) vs winter (Nov) 2019, southern China. The brief says **monsoon vs summer** (and ideally India): not claimed. The ENA searches I ran found no usable Indian pair (see ODYSSEY_CHALLENGE.md) |
| Leaflet map with a season slider; detected, new, not-detected, counts for both seasons | ✅ | verified against the data for all 4 sites in both positions (8 of 8) |
| "Not detected" is never "absent" | ✅ | stated on the page and in the PDF; a test blocks the word "absent" in user text |
| One button on the site page that prints a one-page PDF | ✅ | animals detected, risk level, source and date, uncertainty / missing coverage, action in plain words |
| Generate the report live for one real site during the demo | ✅ | |

### 3D. The eight scenarios the judge will check

| # | Scenario | Status |
|---|---|---|
| 1 | Poor-quality sample: reasons on screen + retake verdict | ✅ |
| 2 | Mixed sample: all species and their shares, none missing | ✅ `G1`; 🟡 overall (9 of 12 libraries complete) |
| 3 | Unknown sequences: queue, closest match, confidence, never certain | ✅ with a known-identity answer key |
| 4 | Bad records rejected / merged with reasons; database clean; absent scenarios disclosed | ✅ |
| 5 | Invasive species: real sample raises an alert with pin and threat level | ✅ |
| 6 | Season slider: arrivals / non-detections with counts for both seasons | ✅ |
| 7 | Report button: one-page PDF, action line clear enough to read aloud | ✅ |
| 8 | Unseen input: a judge selects another real sample and understands the result | ✅ any of the 62 analyses can be selected, **and a brand-new FASTA/FASTQ file (plain or .gz, up to 12 MB) can be dropped into "Try your own file"**; it is checked by content, analysed and deleted. No PDF or composition check for it (no published answer) |

### 3E. Implementation guidance and "Definition of Done"

| Item | Status | Notes |
|---|---|---|
| Manifest of filenames, source links, sample IDs, metadata, reference-database version | ✅ | `data/real_challenge/manifest.json`, one per dataset folder; reference version + NCBI query in `reference.json` |
| Every threshold in one place, with its rationale | ✅ | `thresholds.json`, rationale in plain words, shown in the app ("Numbers & words") |
| Respect the judging clock: no 5-minute model run; pre-run or recorded | ✅ | all results pre-run; opening a sample takes under half a second |
| Never show fabricated or edited output | ✅ | |
| Report readable by a stranger; **test it with someone outside the team** | ✅ | every screen has an "In plain words" box, a Words page explains 14 terms, jargon is replaced; `tests/test_plain_language.py` holds the English to a reading grade (mean grade 2.9, hardest string 8.8, limit 10) and a jargon list. Outsider read-through done by the team (reported by the maintainer; no written notes are in the repo) |
| Simple interface: sample selection, quality summary, result / confidence, map, alert, report | ✅ | the Review view |
| Everything runs from a clean start with one documented command, or is pre-run on video | ✅ 🟡 | `runner fetch` / `all` / `verify`; rehearsed from a fresh clone before the fish-egg data was added (about 6 min warm); a full run is now about 11 min cold. No video recorded |
| Show the real dataset manifest and source first; one sentence: what BioRadar showed on slides before vs what ran on real data | ✅ | `docs/DEMO_SCRIPT.md` opens on the manifest and gives the sentence. Edit its first half to match the slide you actually showed; rehearsed by the team (reported by the maintainer) |

### 3F. What they said NOT to build

| Rule | Status |
|---|---|
| Do not run real QIIME2, DADA2 or BLAST in this task (existing scripts may stand in) | ✅ the challenge path is pure Python; the real pipeline is untouched and still runs (verified in Docker) |
| Do not redesign the platform UI; the existing map page + a review/report flow is enough | ✅ one new view added through the existing registry; the Results page was restructured, not rebuilt |
| Do not train an ML or DNA model | ✅ nothing trained |
| Public, real datasets; do not create or modify sequences or records | ✅ |
| Do not use another team's prepared test pack; document your own selection | ✅ `selection.json`; the upstream `testing_data/` pack and the synthetic `demo_survey` are excluded |

---

## 4. Everything BioRadar already has, and how it relates to the challenge

These ➕ features existed **before** the challenge. They run on the **QIIME2 / DADA2 pipeline path** (paired-end COI FASTQ, India reference). The challenge path above was added alongside, and the pipeline was not changed.

| BioRadar capability | What it is | Relevant to the challenge? |
|---|---|---|
| ➕ Real pipeline | QIIME2 + DADA2 (vsearch fallback), cutadapt, naive-Bayes classifier; self-configuring (marker, primers, lengths) | Not to be used in this task; **verified still working** end to end in Docker |
| ➕ India COI reference | 33,611 sequences, 8,020 species | Reference for the pipeline path (the challenge path uses a 12S fish reference of 3,799 RefSeq sequences) |
| ➕ Pre-flight | file-level integrity, flat-quality, primer, truncation checks | Whole-file level; the challenge needed **per-sequence** reasons, which are new |
| ➕ Normalised contract | frozen `taxonomy_normalized.csv` schema, `normalize.py` | Used by the pipeline path only |
| ➕ Map | Leaflet with clustering, heat layer, basemaps, cumulative date slider | Date filter only; the **same-site season comparison is new** |
| ➕ Watchlist + notifications | 18-species list, email / webhook alerts, dashboard alerts | Alert idea reused; the challenge list, levels, sources and pin are new |
| ➕ Field verification loop | confirmed / not found / misidentified / uncertain, append-only | Not needed by the brief |
| ➕ Compare radar | up to 5 sites over 6 diversity axes | Not needed by the brief |
| ➕ Exports | CSV, JSON, Darwin Core Archive, print HTML report | Print report is a multi-section run report; the **one-page officer report is new** |
| ➕ Provenance | SHA-256 per artifact, Merkle chain-of-custody, deterministic runs | Supports "unchanged originals"; the challenge path also verifies md5 per file |
| ➕ Intelligence engines | forecast, anomaly, multi-agent debate, zero-shot taxonomy, NFT receipt, Sentinel-2 change detection, invasive risk, extinction (PVA), spread, sampling optimiser, PINN origin, smart alerts, knowledge base, NLG briefing, XAI, CV verification | Not required. Kept, but the briefing is folded on the Results page so it no longer buries the answer. The brief forbids training a model, so none was added |
| ➕ App | stdlib server + vanilla-JS dashboard, English / Hindi, light / dark | Reused as is |
| ➕➕ New for the challenge | `bioradar/adjudicate/` (QC, 12S reference match, data guard, alerts, seasons, one-page PDF, compliance check), Review view, 38-sample real data folder, charts on the Results page | |

## 5. Known limits (stated on screen and in the docs)

1. Shares are only roughly right: 60% of measurable shares are within 3 times of the published share; 3 of 12 libraries miss fish.
2. 21 fish that were not in the mixtures were named across the 12 unknown-identity libraries (close relatives and stray DNA).
3. Seasons are summer vs winter (Aug/Nov, southern China), not monsoon vs summer in India: no usable Indian same-place pair was found in the ENA searches run.
4. Alerts are in Indonesia and China and the area line is in Portugal: real data, not India / forest.
5. Uploaded files get no PDF and no composition check (no published answer).
6. Person A's branch `personA/challenge-hardening` is not merged into `main`; running the pipeline natively on Windows fails (Docker is fine).
