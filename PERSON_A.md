# PERSON A - progress log and challenge status board

Owner: Person A (Parth). Updated after every phase; each phase is one commit.
Working branch: `personA/challenge-hardening`, cut from Person B's
`challenge/odyssey-adjudication` (commit `381bd11`). Nothing of Person B's was rewritten.

Evidence vocabulary used below (from the workpack):

| Label | Meaning |
|---|---|
| **real-source pass** | Re-run by Person A on this machine against unchanged public records |
| **software-test-only** | Rule proven by a unit test on a controlled fixture; says nothing about real data |
| **not represented** | The selected public source does not contain the case |
| **claimed, unverified** | Person B's docs say it passes; Person A has not reproduced it yet |

## R0 - canonical repository (resolved)

`https://github.com/omtawde09/BioRadar_Vibeathon` is canonical (instruction from the team, 2026-10-10).
`omtawde09/BioRadar` (50 commits) is **not** merged in and is not touched.

* Local checkout: `C:\Users\Parth\Desktop\eDNA\BioRadar_Vibeathon`
* `main` = one commit (`73ea2fb Initial BioRadar`); `WithoutFilter` and `withFilter` are identical to it.
* `challenge/odyssey-adjudication` = main + Person B's commit `381bd11` (29 files, +17,291 lines).

## Measured baseline (not copied from docs)

Update 2026-10-10 (Phase 2b): Person B phases B0-B4 (56744af) are merged into this branch (d4e4058). They moved the data layout (datasets/<id>/raw, lists/, reference/refseq_fish_12s), relabelled the UI score as match score, added the one-page overflow guard and runner verify -> COMPLIANCE.md. That closes handoffs F10 and F11.

Command: `python -m pytest tests/ -q` on Windows 11, Python 3.14.3, branch point `381bd11`.

| Run | Result |
|---|---|
| Before Person A changes | **2 failed, 190 passed, 3 skipped** |
| Both failures | `tests/test_dataset_registry.py` (2 tests): stale, because `data/datasets.json` ships `datasets: []` on purpose and keeps the demo under `_examples`. Same failure on `main`. |
| 3 skips | `tests/test_adjudicate.py` real-data tests; raw reads are not downloaded yet |

Integration (`ci/check_integration.sh`) needs Docker plus the 11.7 GB pipeline image and has **not** been run.
Python-3.8 syntax check of `bioradar/adjudicate/*.py` (`ast.parse(feature_version=(3,8))`): clean.

Test hygiene finding: running the whole suite rewrites tracked files
(`bioradar/ai/models/ias_classifier.joblib`, `data/debates.json`, `data/forecast_cache.json`,
`data/ecological_anomalies.json`). Do not commit them; restore with `git checkout -- <file>`.

## Reproduction on this machine (Phase 2b)

* Reads: `python -m bioradar.adjudicate.fetch reads` downloaded 38 files (about 238 MB) from
  `ftp.sra.ebi.ac.uk`, each verified against the archive MD5 and size. **38/38 verified.** A DNS drop
  interrupted the first pass; the retry skipped cached files by MD5.
* Pipeline: `python -m bioradar.adjudicate.runner all --force` processed 38 samples in 98-135 s, no crash.
* `python -m bioradar.adjudicate.runner verify` regenerated `data/real_challenge/COMPLIANCE.md`; it agrees
  with Person B's table line for line (PASS x9, PARTIAL x1 = mixed shares, GAP x1 = unknowns with known identity).
* Tests: `tests/test_adjudicate.py` + `tests/test_report_one_page.py` with real data present: **71 passed, 0 skipped**.
  The three real-file tests now run: Retake + human-contamination reason, unknowns never confident,
  file name does not decide the answer.

## Findings and their state

| # | Finding | Criterion | State |
|---|---|---|---|
| F1 | `confidence` is a heuristic (identity x margin) presented as confidence | C4 | fixed: `score_type`, `score_note`; UI now says "match score" (Person B, B2) |
| F2 | `post_check` hard-coded `unmerged_double_spellings = 0` | C6d | fixed: measured, `None` = not checked |
| F3 | Two stale registry tests | C11 | fixed |
| F4 | `.gitignore` listed tracked files | C1, C7 | fixed |
| F5 | Manifest had MD5 only | C1 | fixed: `data/challenge/manifest.csv` has MD5 + SHA-256 + marker + reference version, 38/38 verified |
| F6 | Global invasive list with no native-range rule | C7 | fixed (see F12); `native_in` lists UNVERIFIED |
| F7 | Spelling guard has no cited synonym source and no original/canonical pair | C6d | partly fixed: audit event now carries `original_label`, `canonical_label` and `basis`; a cited synonym authority is still **open** |
| F8 | Mixed-sample species and shares have no source species table | C2 | **open**: needs the paper's table |
| F9 | Seasons are Aug vs Nov (summer/winter), not monsoon vs summer | C8 | **open**, disclosed |
| F10 | PDF could overflow one page | C9 | closed by Person B (B4 guard + 43 tests) |
| F11 | UI said "confidence" | C4 | closed by Person B (B2) |
| F12 | Real run: *Cyprinus carpio* raised a "possible invasive" WATCH in 21 of the 25 China samples (native there), and one species could be both confirmed and possible (up to 6 alerts per sample) | C7 | fixed: native suppression also covers unresolved groups; a confirmed species is never repeated as "possible"; 53 alerts total, max 5 per sample; suppressed cases recorded in `native_listed` |
| F13 | Unknown rows had identity but no aligned coverage (workpack requires it) | C4 | fixed: `coverage` on every match (all 7,925 unknowns in SRR37521672 are >= 0.973) |
| F14 | Person B's tip failed `test_report_is_a_valid_one_page_pdf` (fixture lacked `reads`) | C11 | fixed (fixture) |
| F15 | Whole-suite runs rewrite tracked model/cache files | C11 | open, hygiene: `git checkout -- <file>` before committing |

## Challenge status board (C1-C11), evidence from Person A's own run

| ID | Status | Evidence | Honest limits |
|---|---|---|---|
| C1 | **real-source pass** | 38 files, MD5 + size match the archive, SHA-256 in `data/challenge/manifest.csv`, reference version recorded | R1 reads only; the archive supplies MD5, so SHA-256 is computed locally |
| C2 | **partial** | A2 (SRR27401753): 15 species-level calls for "15 fish" = count consistent; 6 unresolved groups, 4 trace; share denominator 75,985 reads (kept + unresolved groups) of 127,829 total | No species table in the archive, so identities and shares are NOT verified. Design check (note "equal concentration"): only 4 of 15 detected species are within 3-fold of 1/15, so shares track the design loosely. The 30-fish mixes report FAIL honestly |
| C3 | **real-source pass** | GSS356 (SRR33845265): 361 reads, 174 distinct sequences each with a written reason (160 singleton, 65 human reads, 131 unrelated, 3 short, 2 low quality); verdict Retake sample. Two more real Retake samples (SRR33845234, SRR25108818) | FASTQ quality is used only where scores exist |
| C4 | **real-source pass** | SRR37521672: 7,925 unknown sequences queued with closest match, identity, coverage, score type, reference version and "needs review"; max score 0.60 | Score is heuristic, not calibrated. No ground-truth identity exists for any unknown (3b stays a GAP) |
| C5 | **real-source pass** | All 38 real inputs processed without a crash; the filename test passes on a real file | |
| C6a | **real-source pass** | 24 duplicate-ID merges on 5,119 PRJEB108476 records | |
| C6b | **real-source pass (caveat)** | 4,707 outside the boundary, 367 without GPS | Boundary is a Portuguese OSM polygon but the records span 5 countries, so 92% fail the rule and only 3 records stay in the clean store. Valid rule demo, weak ecological meaning |
| C6c | **real-source pass** | 18 real future-dated records rejected (today = 2026-10-10) | |
| C6d | **partial** | 2 spelling merges (grass carp idella/idellus) from name similarity + sequence agreement; audit event keeps original and canonical label plus its basis; post-check measured | No cited synonym authority was consulted (stated in the event's `basis`) |
| C7 | **real-source pass** | SRR37521672 (Indonesia, -3.405272, 114.789995): HIGH *Oreochromis niloticus* and HIGH *Clarias gariepinus* with source links and action; Pearl River: CRITICAL *Micropterus salmoides* | List is a GISD starter set; `native_in` for 2 species unverified; real triggers are in Indonesia/China, not India |
| C8 | **real-source pass (as summer vs winter)** | 4 sites with both seasons, e.g. HongQimen summer 58 vs winter 56 species, 7 summer-only, 5 winter-only; "not detected", never "absent" | Aug vs Nov, not monsoon vs summer; all four sites share one 1-degree pin |
| C9 | **pass (Person B)** | One-page PDF with overflow guard, 43 report tests | Not yet printed from a browser by Person A |
| C10 | **not yet checked by Person A** | | Phase 4 browser smoke test |
| C11 | **partial** | Full suite `python -m pytest tests/ -q` with real data present: **248 passed, 0 failed, 0 skipped** (baseline was 2 failed / 190 passed / 3 skipped) | Clean-start rehearsal and `ci/check_integration.sh` (needs Docker) not run |

## Phase log

| Phase | Scope | State |
|---|---|---|
| 0 | R0 decision, clone, baseline, audit | done |
| 1 | F1-F4 fixes + tests | done, pushed `7181c06` |
| 2a | Native-range policy, `fetch reads`, SHA-256 manifest tool | done, pushed `fb5981d` |
| 2b | Merge Person B B0-B4; real-data reproduction; F12-F14; coverage; design share check; evidence board | done, pushed `012ce96` |
| 3a | F7 audit labels; full-suite run (248 passed); parallel research/review agents launched | done (this commit) |
| 3 | F7 cited synonym audit; C2 species table; C8 monsoon source | needs sources (open questions) |
| 4 | Browser smoke test of the Review view, clean-start rehearsal, full suite, final table | planned |

## Open questions for the team

1. **C2 species table.** Chen et al. 2025 (doi:10.1016/j.gecco.2025.e03906) holds the mock-community species
   list; Person B reported it is behind a CAPTCHA. Someone with browser access could export it into
   `data/real_challenge/expected_composition.json` (format in `docs/ODYSSEY_CHALLENGE.md`), after which
   `expected.py` runs the full composition check.
2. **C8 monsoon vs summer.** Needs a same-site pair with a monsoon and a pre-monsoon sample, ideally Indian and
   amplicon-based. Chilika (PRJNA691704) is shotgun and tens of GB.
3. **Native ranges.** Verify `native_in` for *Cyprinus carpio* and *Clarias batrachus* against the GISD pages.

## Change log (Person A)

* Phase 1: score labelling, post-check, registry tests, `.gitignore`.
* Phase 2a: `native_policy` (suppress), `native_listed`, `fetch reads`, `challenge_manifest.py`.
* Phase 2b: native range also covers unresolved groups; no confirmed+possible duplicates; `coverage` on matches;
  `design_share_check`; fixture fix; `ENGINE_VERSION` 4 so cached results refresh; `COMPLIANCE.md` regenerated;
  `data/challenge/manifest.csv`.
