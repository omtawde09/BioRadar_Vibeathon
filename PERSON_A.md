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

## Audit of Person B's branch (what is really there)

The engine in `bioradar/adjudicate/` is a sensible, readable implementation: content-based FASTA/FASTQ
reading, per-sequence reasons, human-contamination detection, ambiguity "complexes", cached runner,
guard, alerts, season comparison and a stdlib PDF report. Findings, in order of consequence:

| # | Finding | Criterion | Status |
|---|---|---|---|
| F1 | `confidence` is a home-made heuristic (identity x margin) shown as "confidence"; the workpack forbids presenting identity-derived scores as calibrated confidence | C4 | **fixed in Phase 1** (`score_type` + `score_note`; key name kept for UI compatibility) |
| F2 | `guard.post_check` hard-coded `unmerged_double_spellings = 0`, a "clean" proof that proved nothing | C6d | **fixed in Phase 1** (measured; `None` means not checked) |
| F3 | Two stale registry tests failing on `main` and on the branch | C11 | **fixed in Phase 1** |
| F4 | `.gitignore` listed `manifest.json` and `invasive_species.json` although both are committed on purpose | C1, C7 | **fixed in Phase 1** |
| F5 | Manifest has MD5 only (what ENA supplies); workpack wants SHA-256 plus marker and reference version per row | C1 | open, Phase 2 |
| F6 | Invasive list is global with no native-range rule: *Cyprinus carpio* (native to China) and *Clarias batrachus* (native to SE Asia) are CRITICAL, so a native fish could raise an "invasive" alarm | C7 | **fixed in Phase 2a**: alert suppressed where the species is native at the sample country and recorded in `native_listed`; `native_in` lists are UNVERIFIED (web tools unavailable), verify before the demo |
| F7 | Spelling guard works on reference-list names by similarity plus sequence agreement; there is no cited synonym source and no original-vs-canonical label pair in the audit event | C6d | open, Phase 3 |
| F8 | Mixed-sample species and shares have **no** source-supported ground truth (only a "15 fish" count) | C2 | open, needs a source table (decision pending) |
| F9 | Seasons are summer (Aug) vs winter (Nov) in the Pearl River Delta; the challenge asks monsoon vs summer | C8 | open, disclosed gap, source search needed |
| F10 | `report.py` never checks the running y-position against the footer, so long content could overflow the one page (the test only checks `/Count 1`) | C9 | handoff to Person B (report layout) |
| F11 | UI labels the score "confidence" / "conf" (`adjudicate.js`, around lines 185, 306, 338) | C4 | handoff to Person B (`webapp_static/` is B's) |

## Challenge status board (C1-C11)

| ID | Criterion | Exists in code? | Evidence status today | Next action |
|---|---|---|---|---|
| C1 | Real public samples + immutable manifest | Yes (`data/real_challenge/manifest.json`, md5-verified fetch) | claimed, unverified (reads not downloaded here); SHA-256 missing | Phase 2 |
| C2 | Five species + shares in one mixed sample | Yes (shares + denominator) | **not verified**: no source species table | decision on source |
| C3 | Poor sample: per-sequence reasons + Retake | Yes (`quality.py`, `adjudicate.py`) | software-test-only; real GSS356 claimed, unverified | Phase 3 run |
| C4 | Two unknowns: nearest match + uncertainty | Yes (review queue) | software-test-only; real unknowns claimed, unverified | Phase 3 run |
| C5 | Unseen input, no crash, not filename-driven | Yes (content sniffing) | software-test-only (the filename test needs the real file) | Phase 3 run |
| C6a | Duplicate sample ID | Yes | software-test-only; 24 merges on PRJEB108476 claimed | verify |
| C6b | GPS outside boundary | Yes (OSM Litoral Norte polygon) | software-test-only; boundary is Portuguese, records span 5 countries (disclosed) | verify |
| C6c | Future date | Yes | software-test-only; 18 real future dates claimed | verify |
| C6d | Spelling / synonym | Partial (heuristic) | software-test-only | Phase 3 |
| C7 | Invasive alert | Yes (`alerts.py`) | claimed (Indonesia tilapia/catfish); native-range gap F6 | Phase 3 |
| C8 | Same-site seasons | Yes (`seasons.py`) | claimed summer/winter; not monsoon/summer | source search |
| C9 | One-page officer report | Yes (stdlib PDF) | software-test-only; overflow not guarded (F10) | handoff to B |
| C10 | Simple review flow | Yes (Review view) | not browser-tested by Person A yet | Phase 4 |
| C11 | Clean start + regression tests | Partial | baseline measured above; clean-start rehearsal pending | Phase 4 |

## Phase log

| Phase | Scope | State |
|---|---|---|
| 0 | R0 decision, clone, baseline, audit, this file | done |
| 1 | Honesty/correctness fixes F1-F4 + tests | done |
| 2a | Native-range alert policy (F6), manifest-driven md5-verified `fetch reads`, SHA-256 `challenge_manifest` tool | done (code) |
| 2b | Real-data reproduction: `runner all`, verify claims, write `data/challenge/manifest.csv` | in progress (download approved, 38 files / ~238 MB) |
| 3 | F6 native-range alerts, F7 synonym audit, C2/C8 source work | planned |
| 4 | Browser smoke test, clean-start rehearsal, final evidence table | planned |

### Phase 1 - changes
* `bioradar/adjudicate/adjudicate.py`: `SCORE_TYPE`, `SCORE_NOTE`; every kept/unknown/species row and the
  result carry `score_type`; kept/unknown rows carry `reference_version`.
* `bioradar/adjudicate/reference.py`: `Reference.version` read from `reference.json`.
* `bioradar/adjudicate/alerts.py`: events carry `score_type`.
* `bioradar/adjudicate/guard.py`: `post_check` measures leftover spelling variants.
* `tests/test_dataset_registry.py`: tests follow the intentional empty-`datasets` design.
* `tests/test_adjudicate.py`: +2 tests (score labelling, post-check honesty).
* `.gitignore`: tracked challenge files are no longer listed as ignored.

### Handoffs to Person B (not edited by Person A)
1. Rename UI labels "confidence"/"conf" to "match score" and show `score_note` (F11).
2. Make the PDF writer stop or shrink before the footer line, and add an overflow test (F10).

### Phase 2a - changes
* `alerts.py`: `sample_country`, `native_here`, `native_policy` (suppress), `native_listed`; `runner.py` stores `native_listed` on every result.
* `data/real_challenge/invasive_species.json`: `native_in` for two species, flagged UNVERIFIED in `native_range_note`.
* `fetch.py`: `fetch reads` downloads exactly the files in the committed manifest, md5-verified, without re-querying ENA or rewriting the manifest.
* `challenge_manifest.py`: writes `data/challenge/manifest.csv` (source URL, accessions, original filename, date/site/coords as deposited, marker, reference version, MD5 + SHA-256, verified flag).
* `tests/test_adjudicate.py`: +3 tests (native suppression, non-native still alerts, manifest never hides a gap).
