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
| B1 | UI audit: what already passes | pending |
| B2 | Challenge review states | pending |
| B3 | Map, alert and seasons | pending |
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

Side effect to remember: running the tests rewrites two tracked files (`bioradar/ai/models/ias_classifier.joblib`,
`data/ecological_anomalies.json`). Restore them with `git checkout --` before committing.

**Also committed in this phase:** the data reorganisation done earlier (per-dataset folders, `selection.json`,
`COMPLIANCE.md`, `runner verify`). That is Person A's territory (data/manifest) and is recorded here only because it was
uncommitted on this branch.

## Open questions for the maintainer / Person A

1. Which repository is canonical (`BioRadar_Vibeathon` vs `BioRadar`)?
2. `index.html` loads Google Fonts: bundle the fonts locally, or accept the CI failure?
3. Person A: who owns the backend fields I need (listed per phase under "Contract requests")?
