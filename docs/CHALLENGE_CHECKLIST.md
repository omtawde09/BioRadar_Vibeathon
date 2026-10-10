# Challenge checklist: what they asked for vs what BioRadar has

Sources: **Points Noted.pdf** (handwritten notes) and **Challenges BioRadar.pdf** (the ODYSSEY brief: "Prove What Lives in the Water").
Status is taken from the live check `python -m bioradar.adjudicate.runner verify` (writes `data/real_challenge/COMPLIANCE.md`)
and from the running app on `main`. Nothing is marked done unless it was run on real public data.

Legend: ✅ done on real data · 🟡 partly (the gap is stated) · ❌ not met · ⬜ not done yet · ➕ BioRadar already had it before the challenge

---

## 1. The 8 challenges from the handwritten notes

| # | Challenge (as written) | Status | What BioRadar does | Where to see it |
|---|---|---|---|---|
| 1 | 5 identifiable species with shares (sample from a mixed sample) | 🟡 | Splits a real mock community into species with `reads / denominator = share`; shows indistinguishable species as one group. The source only gives the **count** of fish mixed (15), so the check is count-only: **15 for 15 consistent**; species identities and shares are **not** verified against ground truth | Review → `A2 - HongQimen` |
| 2 | Poor-quality and noisy samples | ✅ | Per-sequence QC: short fragment, N bases, low quality, low complexity, seen-once, human DNA, unrelated. Real case: 361 reads, 65 human-DNA reads | Review → `GSS356` |
| 3 | 2 samples not in our reference list but actual identity is known | 🟡 | Unrecognised sequences are queued with closest match, identity and a capped score. **No ground-truth identity exists** for them in the public data, so "identity known" is not claimed; each has a manual NCBI review link | Review → `Irigation point 3` |
| 4 | Retake the sample if noisy or poor data samples are present | ✅ | Verdict **Retake sample** (under 1,000 usable reads, or under 10% usable); "Usable with caution" between | Review → `GSS356`, `GSS471`, water blank |
| 5 | Detect inconsistent, redundant and duplicate samples, with valid reasoning | ✅ | Data guard on 5,119 real archive records: 24 duplicate IDs merged as re-runs, 18 future dates, 4,707 outside boundary, 367 without GPS, 2 species double spellings. Every decision has a written reason; post-check says the clean store is clean | Review → Data guard |
| 6 | Alert the officer about the danger level of invasive species | ✅ | Banner + log + alert map with pin, species, level (CRITICAL / HIGH / WATCH), action and IUCN source link. Real trigger: **HIGH, Nile tilapia and African catfish** (Indonesia). No SMS or e-mail is sent for the challenge path | Review → `Irigation point 3`, Alerts tab |
| 7 | Timeline of the two seasons (summer, winter) for the same location | ✅ | Same-site slider: species per season, newly detected, not detected, replicates, quality caution. Pearl River, 4 sites, **Aug vs Nov 2019** (matches the notes: summer / winter) | Review → Seasons & map |
| 8 | 1-page conclusion PDF: animal detected, risk level, source and sample date, uncertainty / missing coverage | ✅ | One-page PDF per sample and per site (both seasons), generated live; guarded so it cannot spill to page 2; 43 tests prove one page, no overlap, all fields | "Print officer report" buttons; samples in `docs/demo_outputs/` |

## 2. Critical targets (handwritten)

| # | Target | Status | Notes |
|---|---|---|---|
| 1 | Rejected samples have a documented reason | ✅ | reason per dropped sequence on screen; full list as CSV; sample-level reason on the verdict |
| 2 | 5 distinct species from a sample, each shown with its share | 🟡 | shown (all species, not just 5) with counts and denominator; shares not verifiable against a published table (see #1 above) |
| 3 | Unknown sequences reported with a confidence score | ✅ 🟡 | reported with **identity** (measured) and a **match score** capped at 0.60. The score is a documented heuristic, **not** a calibrated probability, and is labelled so |
| 4 | Trigger alert for the forest officer for invasive species | ✅ | see challenge 6 |
| 5 | UI clean and simple, focused on graphs and visuals | ✅ | pipeline Results page now opens with a phylum donut, top-species bars, confidence histogram and per-sample reads / diversity; briefing and species table folded; English + Hindi, light + dark |

## 3. The ODYSSEY brief

### 3A. "One sample, an honest answer"

| Requirement | Status | Notes |
|---|---|---|
| Select 3 real samples from a documented public eDNA dataset | ✅ | 38 real samples from 4 public projects (ENA), 3 designated core samples in `selection.json`. Reads are R1 FASTQ read **by content**; no FASTA file was created |
| Do not write or alter sequences; keep originals and metadata unchanged | ✅ | all 38 files verified by md5 against the archive (0 altered) |
| Mixed sample with 5 identifiable species + source-supported shares | 🟡 | source supports only the count (15/30 fish); the paper with the species table is behind a CAPTCHA. Reported as PARTIAL, not claimed |
| Poor-quality sample (short fragments, many N, unrelated, human DNA) | ✅ | `GSS356` (+ primer-dimer fragments in the Indonesian sample) |
| Sample with 2 sequences not in the reference list, identity known or reviewable | 🟡 | reviewable (NCBI link), **not** known |
| Rejects poor sequences with a reason for every dropped sequence; "Retake sample" if unusable | ✅ | |
| Splits mixed sample into all species and reports estimated shares | 🟡 | splits ✅; verification against source ❌ (above) |
| Marks unrecognised sequences **unknown**, shows closest match and confidence, review queue, never confirmed or full confidence | ✅ | status `needs review`, capped, never 1.0 |
| Does not crash on any input; kept / dropped / unknown summary for each real sample | ✅ | all 38 processed, including 3 pathological ones. See "unseen input" below for arbitrary files |
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
| Two seasons, **same location**, real samples | ✅ 🟡 | 4 sites, summer (Aug) vs winter (Nov) 2019. The brief says **monsoon vs summer**: not claimed, and no India monsoon pair was found in a usable form |
| Leaflet map with a season slider; detected, new, not-detected, counts for both seasons | ✅ | verified against the data for all 4 sites in both positions (8 of 8) |
| "Not detected" is never "absent" | ✅ | stated on the page and in the PDF; a test blocks the word "absent" in user text |
| One button on the site page that prints a one-page PDF | ✅ | animals detected, risk level, source and date, uncertainty / missing coverage, action in plain words |
| Generate the report live for one real site during the demo | ✅ | |

### 3D. The eight scenarios the judge will check

| # | Scenario | Status |
|---|---|---|
| 1 | Poor-quality sample: reasons on screen + retake verdict | ✅ |
| 2 | Mixed sample: all species and their shares, none missing | 🟡 count-only check |
| 3 | Unknown sequences: queue, closest match, confidence, never certain | ✅ |
| 4 | Bad records rejected / merged with reasons; database clean; absent scenarios disclosed | ✅ |
| 5 | Invasive species: real sample raises an alert with pin and threat level | ✅ |
| 6 | Season slider: arrivals / non-detections with counts for both seasons | ✅ |
| 7 | Report button: one-page PDF, action line clear enough to read aloud | ✅ |
| 8 | Unseen input: a judge selects another real sample and understands the result | 🟡 any of the 38 real samples can be selected; **a brand-new file cannot be dropped into the Review view** (uploads go to the QIIME2 pipeline instead) |

### 3E. Implementation guidance and "Definition of Done"

| Item | Status | Notes |
|---|---|---|
| Manifest of filenames, source links, sample IDs, metadata, reference-database version | ✅ | `data/real_challenge/manifest.json`, one per dataset folder; reference version + NCBI query in `reference.json` |
| Every threshold in one place, with its rationale | ✅ | `thresholds.json`, shown in the app ("Numbers & sources") |
| Respect the judging clock: no 5-minute model run; pre-run or recorded | ✅ | all results pre-run; opening a sample takes under half a second |
| Never show fabricated or edited output | ✅ | |
| Report readable by a stranger; **test it with someone outside the team** | ⬜ | wording is plain, but **no outsider has read it yet** |
| Simple interface: sample selection, quality summary, result / confidence, map, alert, report | ✅ | the Review view |
| Everything runs from a clean start with one documented command, or is pre-run on video | ✅ 🟡 | `runner fetch` / `all` / `verify`; rehearsed from a fresh clone (about 6 min warm). No video recorded |
| Show the real dataset manifest and source first; one sentence: what BioRadar showed on slides before vs what ran on real data | ⬜ | the demo path is written (`PERSON_B.md`); the sentence is not rehearsed. Suggested: *"Before today our slides showed 100% recall on a simulated community; today the same platform ran 38 real public samples and told us when to retake, what is unknown, and where invasive fish were detected."* |

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

## 5. Still open (honest list)

1. ❌ Mixed-sample **shares** not verified: needs the paper's species table (paywalled / CAPTCHA). Paste it into `data/real_challenge/expected_composition.json` and it becomes a full check.
2. ❌ "Identity known" for unknown sequences: no ground truth available.
3. 🟡 **Monsoon vs summer** not shown (data is Aug vs Nov, summer vs winter). Matches the handwritten notes, not the brief's wording.
4. 🟡 Invasive triggers are in **Indonesia and China**, boundary is in **Portugal**: real, but not India / forest.
5. 🟡 A brand-new file cannot be dropped into the Review view (only the 38 prepared real samples).
6. ⬜ Nobody outside the team has read the report yet.
7. ⬜ The one-sentence "slides vs real data" line is not rehearsed; no video fallback recorded.
8. Person A's branch `personA/challenge-hardening` holds further hardening work (alert policy, coverage, spelling audit) **not yet merged** into `main`.
