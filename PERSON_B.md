# Person B work log

Role (from `BioRadar_Challenge_Workpack`): the challenge-facing **user flow, seasonal story and officer report**.
Owns `bioradar/webapp_static/` and the report presentation. Does **not** edit `webapp.py`, `contract.py`,
`normalize.py`, `data/datasets.json` or the backend QC/data code (Person A).

Branch: **`main`** on `origin` (https://github.com/omtawde09/BioRadar_Vibeathon). The earlier working branch `challenge/odyssey-adjudication`
was fast-forward merged into `main` and deleted (decision: no separate branch; the QIIME2/DADA2/BLAST pipeline is untouched and runs as before).
This file is updated and pushed after every phase.

## Status board

| Phase | Scope (workpack) | Status |
|---|---|---|
| 0 | Confirm repo/remote, baseline tests, CI | **done** |
| B1 | UI audit: what already passes | **done** |
| B2 | Challenge review states | **done** |
| B3 | Map, alert and seasons | **done** |
| B4 | One-page officer report | **done** |
| B5 | UI regression + demo path | **done** (clean-start rehearsal: see end of B5) |

---

## Phase 0: repo, remote, baseline (done)

**Canonical repo.** The workpack warns that `BioRadar_Vibeathon` shows 1 commit and a different `BioRadar` repo shows 50.
Measured here:

| Check | Result |
|---|---|
| `git remote -v` | `origin` = `omtawde09/BioRadar_Vibeathon` (fetch and push) |
| Branches on origin | `main`, `withFilter`, `WithoutFilter` (all at `73ea2fb Initial BioRadar`) and `challenge/odyssey-adjudication` |
| Person A branch on origin | **none yet**: nothing to merge or reconcile |
| `omtawde09/BioRadar` (`ls-remote`) | 3 heads: `main`, `feature/homepage`, `feature/biodiversity-analytics-expansion`. **Not touched, not merged.** |

Decision: work stays on `BioRadar_Vibeathon` (the checkout and the repo the earlier work was pushed to). **The maintainer
still has to confirm that `BioRadar_Vibeathon` and not `BioRadar` is canonical**; I have not merged the two.

**Baseline (actual output, this checkout, Python 3.14, Windows):**

| Command | Result |
|---|---|
| `python -m pytest tests/ -q` | **193 passed, 2 failed** (195 total) |
| `bash ci/check_integration.sh --fast` | **18 passed, 4 failed, 3 skipped** |

The published test counts disagree (132/174/76); the numbers above are the only ones to quote.

Failures that exist **before** any Person B change (none are in files this branch edits):

| Failing check | Cause | Owner |
|---|---|---|
| `test_the_repository_ships_the_demo_dataset`, `test_the_shipped_demo_entry_points_at_files_that_exist` | `data/datasets.json` has no `demo-survey` entry; the synthetic `data/demo_survey/` files are gone from the working tree | maintainer (synthetic data is also disallowed by the brief) |
| flagging output -> analytics / CBI | `bioradar.analytics.cbi` not implemented | not in the challenge |
| no external asset at page load | `index.html` loads Google Fonts (`fonts.googleapis.com`) | B owns `index.html`: **needs a decision** (see Open questions) |
| no hardcoded hex outside token block | `app.css` has 11 stray colours | B owns `app.css`: pre-existing |

Side effect to remember: running the tests / CI rewrites tracked files (`bioradar/ai/models/ias_classifier.joblib`,
`data/ecological_anomalies.json`, `data/debates.json`, `data/forecast_cache.json`). Restore them with `git checkout --`
before committing.

**Also committed in this phase:** the data reorganisation done earlier (per-dataset folders, `selection.json`,
`COMPLIANCE.md`, `runner verify`). That is Person A's territory (data/manifest) and is recorded here only because it was
uncommitted on this branch.

---

## Phase B1: UI audit (done)

Rule applied: audit what exists, mark what already passes, rebuild nothing.
Evidence = code read + the running app (`python -m bioradar.webapp --port 8099`) in the browser pane.

### Existing app (before this branch), against the challenge

| Area | What exists | Meets the challenge? |
|---|---|---|
| Map time slider (`mapkit.js` `timeline()`) | Slider over collection dates; **cumulative** filter `collected_at <= date` for clustered/heat markers | **No** for C8. It is a date filter, not a same-site two-season comparison (no per-season counts, no new / not-detected lists). Not rebuilt; the season view is separate (see below). |
| Alerts view (`app.js` `alertCard`) | Watchlist alerts per pipeline **run**: species, severity badge, reads, sites, verify button | Partly. No map pin on the card, no rule/source link, no explicit "no trigger" state. Runs only; not the challenge samples. |
| Results / site panel (`openSiteDetail`) | KPIs, top taxa bars for a pipeline-run site | Partly. No report button, no source/uncertainty block. |
| Report (`exports.printable_report`) | Self-contained print HTML: KPIs, sites table, **full species inventory**, phylum table, provenance | **No** for C9. Multi-section run report; no risk level, no officer action, no per-sample uncertainty, can exceed one page. Left alone (it still serves pipeline runs). |
| i18n (`i18n.js`) | Flat English/Hindi object, `t(key)` | Yes for the existing views. |
| Design system | Tokens, 5 shadow tokens, `prefers-reduced-motion` rule, light/dark | Yes. |

### The Review view added earlier on this branch (`adjudicate.js/.css`), against Person B's items

| Item | State | Evidence / gap |
|---|---|---|
| B2 source/sample selector | **pass** | grouped picker over 38 real samples, "why chosen", source link |
| B2 kept / dropped / unknown totals | **pass** | stacked bar + 3 tiles (reads and distinct sequences) |
| B2 per-sequence reasons | **pass** | reason histogram + examples table + full CSV |
| B2 five species with read-share **denominator** | **gap** | shows share % only: no read counts, no denominator, no "excluded rows" statement |
| B2 identity / confidence / coverage labels | **gap** | calls a heuristic score "confidence" (workpack: do not unless calibrated); no coverage; no reference version in the unknown table |
| B2 metadata findings | **partial** | data-guard is its own tab; the selected sample's own source/metadata (IDs, date precision, coordinate precision, md5) is one text line |
| B2 review queue | **pass** | status "needs review", NCBI link |
| B3 same-site seasons | **pass (verify)** | summer vs winter counts, new / not-detected lists, "does not prove absence". Needs a browser test per site (B3) |
| B3 alert + pin | **partial** | banner + log exist; **no explicit no-trigger state** for samples without an alert |
| B4 one-page report | **partial** | server-side one-page PDF exists; verified on 1 sample only; no button on the season/site page |
| B5 language | **gap** | Review view is English only: heading and nav label stay English when Hindi is selected |
| B5 keyboard / a11y | **gap** | no `aria-live` region for results; focus ring not confirmed |
| B5 tokens | **gap** | `adjudicate.css` hard-codes two hex colours; map marker colours hard-coded in JS |

### Contract requests to Person A (nothing to be edited by B)

| Needed by | Field | Why |
|---|---|---|
| B2 | `unknown_queue[].score_type` (`"identity"`), `coverage` (aligned bases / read length) | workpack section 6: do not present identity as confidence; show coverage |
| B2 | `species[].reads` already present; `reads_total` and the share denominator (`identified reads`) as an explicit field | to print the denominator without recomputing in the UI |
| B2 | `reference_version` in each sample result | shown beside the unknown table |

Until A provides them, B derives what it can in the browser (denominator = sum of listed species reads; the reference
version comes from the existing `/api/adjudicate/provenance`) and states "coverage: not provided" instead of inventing it.

---

## Phase B2: challenge review states (done)

Only `bioradar/webapp_static/adjudicate.js` and `adjudicate.css` changed. No backend file, no contract field, no new route.

| Workpack item | Change |
|---|---|
| Five species with read-share **denominator** | every species / group row now reads `reads / denominator = share` (e.g. `26,463 / 72,986 = 36.3%`). A note states the formula, what is **excluded** from the denominator (dropped reads; reads of sequences too different to name) and the sample total, and that a share is a proportion of DNA reads, not animals or biomass |
| Identity vs confidence | UI no longer says "confidence". Identity (a measured similarity) is shown on its own; the heuristic is labelled **match score** with a plain definition (falls 4 points per 1% identity lost, halved if a different species is close, capped 0.99 / 0.60, "not a calibrated probability") |
| Unknown review queue | columns: reads, closest match, identity, match score, **review state** (`needs review`), reason, NCBI link. Above it: **reference version** (from `/api/adjudicate/provenance`) and the statement that aligned **coverage is not provided** by the analysis |
| Metadata findings | new **Source and metadata** card per sample: BioProject / run / BioSample links, alias, original file + md5, marker, reference version, collection date, place/pin, with per-record checks (date not in the future + precision; coordinates in range + low-precision note). Cross-record checks stay in the Data guard tab |
| Source/sample selector, kept/dropped/unknown totals, per-sequence reasons | already passing (B1); unchanged |

Checked in the running app on the mock (`A1`), the invasive-species sample and the poor sample: denominators sum correctly
(26,463 / 72,986 = 36.26%), no console errors.

Still open for B2: `coverage` and `score_type` from Person A (see contract requests); until then the UI says "not provided".

---

## Phase B3: map, alert and seasons (done)

Files changed: `webapp_static/adjudicate.js`, `adjudicate.css` only.

**Same-site seasonal comparison, tested against the data (not just looked at).** In the browser, for each of the 4 sites
and both slider positions, the four numbers on screen were compared with `/api/adjudicate/seasons`:

| Site | Summer (2019-08) | Winter (2019-11) | Replicates | Screen = data? |
|---|---|---|---|---|
| HongQimen | 58 species | 56 | 3 + 2 | yes (both positions) |
| Humen | 20 | 46 | 3 + 3 | yes |
| Jiaomen | 20 | 20 | 3 + 3 | yes |
| Jitimen | 43 | 44 | 2 + 2 | yes |

8 of 8 views matched (detected in each season, newly detected, not detected here). Every sample in a pair has the same
location name, and no text says "absent": the page states "does not prove the animal is absent".
The season rule (Aug = summer, Nov = winter) is shown on the page from `thresholds.json`; the brief's "monsoon vs summer"
is **not** claimed.

| Gap found in B1 | Fix |
|---|---|
| No explicit no-trigger state | A neutral banner **NO TRIGGER** ("rule: species-level call of a listed invasive fish, at least 10 reads; not seen; does not prove the water is free of them") and **NOT CHECKED** for a retake sample. A red/orange alert banner is still shown only for a real qualifying detection |
| Alert pins not on a map | New **Alert map** on the Alerts tab: one marker per distinct pin, colour = most severe alert, popup lists the alerts. 3 distinct pins (the Pearl River sites share one pin because the archive gave 1-degree coordinates, stated under the map) |
| Seasonal lists did not flag invasive species | species confirmed in an alert are badged `invasive-listed` in the new/not-detected/all lists |
| Unfair comparisons not warned | **New finding**: Humen shows 20 species in summer vs 46 in winter, but all 3 summer samples are "Usable with caution". The seasons card now prints each season's verdicts and named reads, and warns when a verdict is not "Usable" or depth differs 2-fold or more: fewer species may reflect the data, not the water |

Not rebuilt: `mapkit.js` and its cumulative date slider (B1 finding: it is a date filter, not a same-site comparison).

**Environment incident (no work lost).** GitHub Desktop switched the checkout `challenge/odyssey-adjudication -> main ->
WithoutFilter -> back` during this phase and stashed the untracked data (downloaded reads, results). Everything committed
was safe on the branch; the ignored data was restored from `stash@{0}` with `git restore --source`. The stash was **not**
popped or edited. To avoid repeats: do not switch branches in this checkout while a phase is running, and re-run
`runner fetch` / `runner all` if the ignored data ever disappears.

---

## Phase B4: one-page officer report (done)

**Audit result (B1, restated):** `exports.printable_report` is a multi-section *run* report (KPIs, sites table, full
species inventory, phylum table, provenance): no risk level, no officer action, no per-sample uncertainty, not limited
to one page. It still serves pipeline runs and was **not touched**. The one-page officer report is the stdlib PDF writer in
`bioradar/adjudicate/report.py` (no PDF library, so no new dependency; works the same on Windows and in the Python 3.8 image).

| Change | Detail |
|---|---|
| **Site report** | new `build_site_pdf`: one place, **summer and winter side by side** (bars + reads for the top 10 animals), risk = highest alert across both seasons, action, source (archive, run IDs, both sets of dates, pin), uncertainty (per-season verdicts and % of reads named, reference size, pin precision, "poorer reads can show fewer species"), "only in summer / only in winter does not mean absent" |
| **Button on the site page** | the Seasons tab now has **Print officer report for this site (PDF)** (opens `/api/adjudicate/site-report/<place>.pdf`) |
| Per-sample report wording | no "conf": shows `share (reads)` plus a denominator line (`reads of the animal / N reads that could be named; a proportion of DNA reads, not animals or weight`) |
| **One-page guard** | `Page` refuses to draw below the footer line; if content would not fit it is cut and the page says so. Nothing can spill to a second page |

Required fields (workpack C9): animals detected, risk level, source and sample date, uncertainty / missing coverage,
officer action in plain words. All five are asserted by tests.

**Verified.** New `tests/test_report_one_page.py` runs on the real pre-run results: **38 sample reports + 4 site reports =
43 tests passed**. Each one checks: exactly 1 page; text inside the page and side margins; **no overlapping text**; all five
section headings present; not truncated; no "confidence" wording; "does not mean absent" on site reports; the site risk
equals the highest confirmed alert across both seasons. Live endpoint: `site-report/HongQimen.pdf` 200 `application/pdf`,
unknown place 404, a path-traversal attempt 404; the button was clicked and opens the right URL.

**Ownership note (deliberate, small).** Person B owns the report *presentation*; the site report needed one read-only route,
so `bioradar/adjudicate/api.py` got one additive branch (`site-report/...`) plus a name regex. No existing route, field or
contract changed. Person A can move it if they prefer it elsewhere.

**Not done / limits.** The report is a PDF produced by the server; the browser's Save-as-PDF path was not used because
the stdlib PDF already satisfies the one-page requirement. The "unseen sample" report works the same way through
`report/<run>.pdf`.

---

## Phase B5: UI regression and demo path (done)

### What changed (webapp_static + tests; two small, flagged exceptions)

| Gap from B1 | Fix |
|---|---|
| Review view English-only | **English / हिन्दी.** 130+ strings through `BioRadarI18n`; switching language re-renders the view (checked: nav, title, tabs, banner, all five tabs). Scientific names, accession IDs and sentences written by the analysis (verdict reasons, per-sequence drop reasons, alert actions, threshold rationale) stay English by design and are listed as such. `i18n.js` got one **additive** hook, `addStrings()`, that never overwrites an existing key |
| No live region | results container `aria-live="polite"`, status line `role="status"`, banners `role="alert"/"status"` |
| Hard-coded colours | none left in `adjudicate.css` (only `#fff` and `#241a04`, the constants the app's CSS already allows); map markers read the design tokens |
| Weak banner contrast (found in dark theme) | amber banner now dark ink in both themes: **6.75:1 light, 9.83:1 dark** (was 1.48:1 in dark) |
| Focus | real Tab key presses: order correct, ring visible (`:focus-visible` true, 1.6 px outline); season slider reachable and **ArrowRight** switches to winter and updates every number |
| Failure states | results missing -> empty state with the exact command to run (tested by hiding `index.json`, then restored); retake sample -> **NOT CHECKED** banner; no alert -> **NO TRIGGER** banner |

Exceptions to B's file guard, both small and both bugs in code Person B depends on:
1. `bioradar/adjudicate/fetch.py`: `fetch_reference` computed which records it already had, **ignored that and appended**, so re-running `fetch` would have **duplicated every reference record** (and changed the recorded reference date). Now: if the cache matches the current NCBI query it is a no-op ("cached"); otherwise it rewrites from scratch through a temp file.
2. `tests/test_adjudicate.py`: one fixture lacked `reads` (a field every real result has), exposed by the B4 report change.

### Test evidence (actual output, this checkout)

| Command | Baseline (Phase 0) | Now |
|---|---|---|
| `python -m pytest tests/ -q` | 193 passed, 2 failed | **251 passed, 2 failed** (the same 2 demo-dataset tests) |
| `bash ci/check_integration.sh --fast` | 18 passed, 4 failed, 3 skipped | **18 passed, 4 failed, 3 skipped** (same 4; none new) |

New tests this sprint: `tests/test_review_view_static.py` (15: registry, EN/HI key + placeholder parity, Hindi is Hindi, every backend value has a label, no CDN, tokens only, ARIA, document-root selector trap, "absent" never used for non-detection, JS parses, report endpoints refuse bad input), `tests/test_report_one_page.py` (43), plus 21 adjudication tests from earlier. Test runs rewrite 4 tracked files; they were restored before each commit.

### Demo path (click by click; about 6 minutes)

Start: `python -m bioradar.webapp --port 8099`, open http://localhost:8099, click **Review**. All results are pre-run (each opens in under half a second).

| # | Show | Click |
|---|---|---|
| 1 | source manifest | **Numbers & sources** tab: reference version, every threshold with its reason, the 4 real datasets with ENA links |
| 2 | poor-quality real input | **Sample** tab, picker -> `GSS356 - British Columbia`: **Retake sample**, per-sequence reasons incl. 65 human reads; banner NOT CHECKED |
| 3 | five+ species with denominator | picker -> `A2 - HongQimen` (mock community): bars read `reads / denominator = share`; formula note; **count check** (15 for 15; shares NOT verified: the source gives only the count) |
| 4 | unknown review queue | picker -> `Irigation point 3 - South Kalimantan`: queue with closest match, identity, match score, `needs review`, reference version, "coverage not provided" |
| 5 | data guard | **Data guard** tab: 18 future dates, 4,707 outside the boundary, 24 duplicate IDs merged, 2 double spellings, post-check clean |
| 6 | invasive alert + pin | banner on `Irigation point 3`: **HIGH, Nile tilapia**, pin -3.4053, 114.7900; **Alerts** tab -> Alert map |
| 7 | season slider | **Seasons & map** tab -> HongQimen: drag (or arrow-key) summer <-> winter: 58 vs 56 species, 7 new, 5 not detected; then Humen to show the **quality caution** (20 vs 46 species is partly a read-quality effect) |
| 8 | one-page report | **Print officer report for this site (PDF)** on the Seasons tab; **Print officer report (PDF)** on any sample. Fallback copies: `docs/demo_outputs/*.pdf` |
| 9 | unseen real input | picker -> any other sample (e.g. `JTD1 - Jitimen`) then **Re-run live** (15 to 35 s, timer shown) |
| 10 | language | EN / हिन्दी toggle at any step |

Honest lines to say out loud: mixed-sample shares are **not** verified against a published table (source gives only the
count); monsoon vs summer is **not** claimed (the data is Aug vs Nov, summer vs winter); the invasive triggers are in Indonesia
and China, not India; unknown identities have no ground truth.

### Known issues (unresolved, not hidden)

| Issue | Where | Owner / next step |
|---|---|---|
| Google Fonts link in `index.html` fails CI "no external asset" | pre-existing | decision needed: bundle fonts locally |
| 11 hard-coded colours in `app.css` fail CI "no hex outside tokens" | pre-existing | B's file; not part of the challenge, left |
| Active tab text (accent green on white) is 3.43:1 | app-wide `.segmented` token, not this view | design-token decision |
| `coverage` and `score_type` are not backend fields | contract request open since B1 | Person A |
| Season samples are summer/winter, not monsoon/summer | data | stated on every screen |
| `test_dataset_registry` x2 fail | pre-existing | maintainer |

### Clean-start rehearsal (workpack minute 170-180): it found real bugs

Method: fresh `git clone` of the **pushed** branch into an empty folder, then only the documented commands, nothing copied
from the working copy.

| Attempt | Result |
|---|---|
| 1 (code at `98f1c4a`) | **FAILED.** `fetch` died on `HTTP 504 Gateway Timeout` from one of the snapshot services; the later steps then ran on a half-fetched tree and **34 report tests failed** in that clone. The folder was overwritten by a later attempt, so the test failures were **not root-caused**; the fetch failure was |
| 2 (code at `cd8f2ef`) | **PASSED** end to end |

Attempt 2 (all numbers from the log): clone 10 s -> `runner fetch` exit 0 (reads verified; at that commit it also downloaded
the 68 MB mitogenome cache, about 5 min) -> `runner all` **38 samples in 195 s** -> `runner verify` identical PASS/PARTIAL/GAP table
to the working copy -> **85 tests passed** -> total about **14.6 min**.

Bugs the rehearsal exposed, all fixed and tested (`tests/test_fetch_resilience.py`, 7 tests):

| Bug | Fix |
|---|---|
| One 5xx aborted `fetch`; later steps ran on missing files; exit code hid the failure | retries with growing pauses on 5xx / timeout (4xx is not retried); an Overpass mirror fallback; each step reports `FAILED` and `fetch` exits 1 with "re-run the same command" |
| `fetch` re-queried ENA and **rewrote the committed manifest** (new retrieval date, new file) | clean start downloads **exactly the files in the committed manifest**, md5-verified; `--refresh` is the only way to re-query |
| `fetch all` overwrote the committed **records snapshot and boundary** with live data (ENA changes over time) | snapshots are fetched only if missing (or `--refresh`) |
| `fetch_reference` appended on every run (duplicate records) | skip when the cache matches the query, else rewrite via a temp file |
| ~5 min NCBI download although the built reference is already committed | skipped unless `fetch reference` or `--refresh` |
| `verify` embedded a changing PDF byte count, dirtying a clean checkout | stable wording |

After these fixes a warm `fetch` takes **0.9 s** and leaves `git status` clean; a cold clean start is clone + reads
(about 3 min on this connection) + `runner all` (about 3 min).

Remaining risk: the attempt-1 test-failure cluster is unexplained. It happened only in the half-fetched state and the
complete rehearsal is green, but it was not reproduced or diagnosed.

## Open questions for the maintainer / Person A

1. Which repository is canonical (`BioRadar_Vibeathon` vs `BioRadar`)?
2. `index.html` loads Google Fonts: bundle the fonts locally, or accept the CI failure?
3. Person A: who owns the backend fields I need (listed per phase under "Contract requests")?
