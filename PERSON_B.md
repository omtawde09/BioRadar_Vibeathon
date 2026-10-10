# Person B work log

Role (from `BioRadar_Challenge_Workpack`): the challenge-facing **user flow, seasonal story and officer report**.
Owns `bioradar/webapp_static/` and the report presentation. Does **not** edit `webapp.py`, `contract.py`,
`normalize.py`, `data/datasets.json` or the backend QC/data code (Person A).

Branch: `challenge/odyssey-adjudication` on `origin` (https://github.com/omtawde09/BioRadar_Vibeathon).
This file is updated and pushed after every phase.

## Status board

| Phase | Scope (workpack) | Status |
|---|---|---|
| 0 | Confirm repo/remote, baseline tests, CI | **done** |
| B1 | UI audit: what already passes | **done** |
| B2 | Challenge review states | **done** |
| B3 | Map, alert and seasons | **done** |
| B4 | One-page officer report | pending |
| B5 | UI regression + demo path | pending |

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

## Open questions for the maintainer / Person A

1. Which repository is canonical (`BioRadar_Vibeathon` vs `BioRadar`)?
2. `index.html` loads Google Fonts: bundle the fonts locally, or accept the CI failure?
3. Person A: who owns the backend fields I need (listed per phase under "Contract requests")?
