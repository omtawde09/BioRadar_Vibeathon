# BioRadar — team guide

Everything you need to get BioRadar running on your laptop, test it, change it,
and get your work into the main repository.

Written for the BioRadar team (SIH 2026, SIH25042). If you are not on the team,
[README.md](README.md) is the general install guide.

**Every step below is given twice — once for the graphical apps, once for the
terminal.** Use whichever you prefer. They do the same thing.

---

## Contents

| Part | What it covers | Who needs it |
|---|---|---|
| [1. What you are installing](#1-what-you-are-installing) | The five-minute mental model | Everyone |
| [2. Install Docker](#2-install-docker) | Windows, macOS, Linux | Everyone |
| [3. Get the pipeline image](#3-get-the-pipeline-image) | Pull, build, or copy from a USB stick | Everyone |
| [4. Get the code](#4-get-the-code) | Clone, GUI and CLI | Everyone |
| [5. First-time setup](#5-first-time-setup) | Classifiers, `.env`, dependencies | Everyone |
| [6. Run the application](#6-run-the-application) | Three ways, GUI and CLI | Everyone |
| [7. Test it on the sample data](#7-test-it-on-the-sample-data) | The full demo run, and what to expect | Everyone |
| [8. Run the automated tests](#8-run-the-automated-tests) | 132 unit tests + 21 integration checks | Anyone changing code |
| [9. Making changes and getting them in](#9-making-changes-and-getting-them-in) | Git workflow, GUI and CLI | Anyone changing code |
| [10. If you are working on the UI](#10-if-you-are-working-on-the-ui) | Where the files are, the rules CI enforces | Ishwar and anyone on the front end |
| [11. Rules that will fail your commit](#11-rules-that-will-fail-your-commit) | Read this before your first push | Anyone changing code |
| [12. Troubleshooting](#12-troubleshooting) | Every error we have actually hit | Everyone |

---

## 1. What you are installing

Three things, and it helps to know which is which when something breaks.

| Piece | What it is | Size |
|---|---|---|
| **Docker Desktop** | Runs Linux containers on your laptop | ~600 MB |
| **The pipeline image** | A prepared Linux system containing QIIME 2, DADA2, cutadapt, vsearch and R — the actual DNA analysis software | **11.8 GB** |
| **The BioRadar repository** | Our code: the workflow, the web dashboard, the reference data | ~35 MB |

The image is big because reproducible bioinformatics is big. QIIME 2 alone pulls
in hundreds of scientific Python and R packages that must be *exact* versions —
if your DADA2 and mine differ, our results differ, and the whole
chain-of-custody argument collapses. You download it once.

The code is mounted **into** the container at run time, not copied into it. That
means you can edit a Python file or a stylesheet and just refresh the browser —
you never rebuild the 11.8 GB image to change a button.

---

## 2. Install Docker

### Windows

**Before anything else:** Docker on Windows needs WSL 2 and virtualisation
enabled in your BIOS. On most laptops from the last five years this is already
on. If Docker complains later, this is why — see
[§12](#12-troubleshooting).

**GUI method**

1. Go to <https://www.docker.com/products/docker-desktop/>
2. Click **Download for Windows** (choose **AMD64** unless you have an ARM
   laptop such as a Snapdragon X)
3. Run `Docker Desktop Installer.exe`
4. Leave **Use WSL 2 instead of Hyper-V** ticked
5. Restart when it asks. It genuinely needs the restart.
6. Open Docker Desktop from the Start menu. Accept the licence.
7. Skip the sign-in — you do not need a Docker Hub account for any of this.
8. Wait until the whale icon in the system tray stops animating and the bottom
   left of the window says **Engine running**

**CLI method** (if you have winget)

```bash
winget install --id Docker.DockerDesktop -e
```

Then start Docker Desktop from the Start menu once, so it can finish setting up
WSL 2.

### macOS

**GUI method**

1. <https://www.docker.com/products/docker-desktop/>
2. Pick the right build — **Apple silicon** for M1/M2/M3/M4, **Intel chip**
   otherwise. Getting this wrong gives you a very slow emulated Docker.
3. Open the `.dmg`, drag Docker to Applications
4. Launch it, grant the privileged-helper permission when macOS asks
5. Wait for the whale in the menu bar to stop animating

**CLI method**

```bash
brew install --cask docker
```

Then open Docker from Applications once.

### Linux (Ubuntu / Debian)

**CLI method** — the only sensible one here:

```bash
curl -fsSL https://get.docker.com | sudo sh
```

Then let yourself run Docker without `sudo`:

```bash
sudo usermod -aG docker $USER
```

**Log out and back in** for that to take effect. Not doing this is the single
most common Linux stumble.

### Check it works — everyone

**GUI:** Docker Desktop shows **Engine running** at the bottom left.

**CLI:**

```bash
docker run --rm hello-world
```

You should see *"Hello from Docker!"*. If you do, Docker is fine and any later
problem is ours, not Docker's.

### Give Docker enough memory

The pipeline needs about 7 GB of RAM. Docker Desktop's default on Windows is
often lower, and DADA2 gets killed halfway through a run with no useful message.

**GUI:** Docker Desktop → ⚙ **Settings** → **Resources** → set **Memory** to
**8 GB** or more → **Apply & restart**.

On Linux there is no limit to raise — containers use the host's RAM directly.

---

## 3. Get the pipeline image

Three routes. **Read all three before starting** — route C is often the fastest
for a team sitting in the same room.

### Route A: pull from the registry

**GUI:** Docker Desktop → **Images** → **Pull** (or the search bar at the top) →
paste:

```
ghcr.io/omtawde09/bioradar-pipeline:v1.0
```

**CLI:**

```bash
docker pull ghcr.io/omtawde09/bioradar-pipeline:v1.0
```

GitHub Container Registry packages are **private by default**. If you get
`denied` or `unauthorized`, either the package is still private or you are not
signed in. Sign in with a GitHub personal access token that has `read:packages`:

```bash
docker login ghcr.io -u YOUR_GITHUB_USERNAME
```

Paste the token as the password. (Create one at GitHub → Settings → Developer
settings → Personal access tokens → Tokens (classic).)

If it stays denied, ask Om to make the package public — GitHub → your profile →
**Packages** → `bioradar-pipeline` → **Package settings** → **Change visibility**.

### Route B: build it yourself

This works even if the package was never published, and takes a couple of
minutes because it only adds a thin layer on top of a base image.

**CLI only** (there is no GUI for a build with a custom Dockerfile path):

```bash
docker build -f docker/Dockerfile.pipeline -t ghcr.io/omtawde09/bioradar-pipeline:v1.0 .
```

Run this from inside the cloned repo, so do [§4](#4-get-the-code) first.

### Route C: copy from a teammate

Six people pulling 11.8 GB over the same connection is painful. One person
pulls or builds, then exports it to a USB drive:

```bash
docker save ghcr.io/omtawde09/bioradar-pipeline:v1.0 -o bioradar-pipeline.tar
```

That produces a ~11.8 GB file. Everyone else:

**GUI:** Docker Desktop → **Images** → **⋮** (top right) → **Import** → choose
the `.tar`.

**CLI:**

```bash
docker load -i bioradar-pipeline.tar
```

### Confirm you have it

**GUI:** Docker Desktop → **Images** → `ghcr.io/omtawde09/bioradar-pipeline`
should be listed at about 11.8 GB.

**CLI:**

```bash
docker images ghcr.io/omtawde09/bioradar-pipeline
```

---

## 4. Get the code

You have been added as a **collaborator**, which means you can push to the
repository directly. You do **not** need to fork it.

### GUI method — GitHub Desktop

1. Install GitHub Desktop from <https://desktop.github.com/>
2. **File → Options → Accounts → Sign in** with your GitHub account
3. **File → Clone repository → GitHub.com**
4. Find `omtawde09/BioRadar` in the list (it appears because you are a
   collaborator)
5. Choose a local path — **avoid OneDrive, Dropbox or Google Drive folders**.
   They sync files mid-write and corrupt git's internal state. Something like
   `C:\dev\BioRadar` or `~/dev/BioRadar` is right.
6. **Clone**

### GUI method — VS Code

1. `Ctrl+Shift+P` → **Git: Clone**
2. Paste `https://github.com/omtawde09/BioRadar.git`
3. Pick a folder, then **Open**

### CLI method

```bash
git clone https://github.com/omtawde09/BioRadar.git
cd BioRadar
```

First push will ask for credentials. Modern GitHub does **not** accept your
account password — use a **personal access token** as the password, or install
the [GitHub CLI](https://cli.github.com/) and run `gh auth login` once, which
handles it permanently.

### Tell git who you are

Only needed once per machine, and without it your commits show up with the wrong
author.

**GUI:** GitHub Desktop → **File → Options → Git**.

**CLI:**

```bash
git config --global user.name "Your Name"
git config --global user.email "your-github-email@example.com"
```

Use the email attached to your GitHub account, otherwise your commits will not
be linked to your profile and will not count as contributions.

---

## 5. First-time setup

Two things the repository deliberately does not contain: the **trained
classifiers** (~22 MB of binary model files, extracted from the image instead of
version-controlled) and your `.env`.

### CLI method — one command

```bash
./scripts/setup.sh
```

On Windows run that from **Git Bash**, not PowerShell or CMD. Git Bash comes with
Git for Windows, which you already have.

It checks Docker, extracts the classifiers, creates `.env` with a generated
secret, generates mock data, starts the database, and runs the fast integration
checks. It is safe to re-run — every step checks before acting.

### GUI / manual method

If the script will not run, do the two things it actually matters for by hand.

**Extract the classifiers.** Docker Desktop cannot copy files out of an image
through the UI, so this bit needs a terminal:

```bash
docker create --name tmp ghcr.io/omtawde09/bioradar-pipeline:v1.0
docker cp tmp:/opt/bioradar/classifiers/. bioradar-pipeline/database/qiime2-qza/
docker rm tmp
```

**Create `.env`.** Copy `.env.example` to `.env` in your file manager or editor.
You can leave the defaults; only the backend needs `JWT_SECRET`, and the backend
does not exist yet.

### About the classifiers

`setup.sh` pulls two classifiers **out of the Docker image** — the upstream 12S
ones. The third, **`classifier-coi-india-2026.qza`**, is the one our demo
dataset needs, and it is **committed to the repository**, so you already have it
after cloning. Nothing to do.

It is the one binary file we track on purpose. It is not in the image, and
retraining it takes 10–40 minutes, so excluding it meant every fresh clone
opened with the demo dataset blocked and no obvious reason why.

If you ever need to rebuild it — say you have extended the reference database:

```bash
docker compose run --rm --entrypoint python app -m bioradar.train_classifier     --reference data/reference_coi_india     --output bioradar-pipeline/database/qiime2-qza/classifier-coi-india-2026.qza
```

It has to run **inside the container**: a `.qza` embeds a pickled scikit-learn
model, and QIIME 2 refuses to load one built against a different scikit-learn
version, so a classifier trained on your host Python would fail several minutes
into a run with a version mismatch.

### Do you need Python on the host?

Only if you want to run the tests or the CLI tools outside Docker. The
application itself runs entirely inside the container.

If you do want it: Python 3.9+ from <https://python.org> (tick **Add Python to
PATH** on Windows), then:

```bash
pip install pytest truststore
```

`truststore` matters if your machine has antivirus that inspects HTTPS — without
it, every download from Python fails while your browser works fine, which is a
maddening thing to debug.

---

## 6. Run the application

Three ways. Pick one.

### A. Docker Desktop, no terminal at all

The image needs a custom entrypoint, which Docker Desktop's Run dialog cannot
set — so build the small app image once (this takes seconds, it adds nothing to
the 11.8 GB base):

```bash
docker build -f Dockerfile.app -t bioradar/app:latest .
```

After that it is pure clicking, every time:

1. Docker Desktop → **Images** → `bioradar/app` → **▶ Run**
2. Expand **Optional settings**
3. Fill in:

   | Field | Value |
   |---|---|
   | Container name | `bioradar-app` |
   | Host port | `8080` |
   | Host path | the folder you cloned into |
   | Container path | `/bioradar` |

4. **Run**
5. Open <http://localhost:8080>

To stop it: **Containers** → `bioradar-app` → **■**. To start it again:
**Containers** → **▶**. It keeps your settings.

### B. Docker Compose — one command

```bash
docker compose up app
```

Open <http://localhost:8080>. `Ctrl+C` stops it.

Add `-d` to run it in the background; `docker compose down` stops it.

### C. Straight Python — fastest loop for UI work

If you have Python on the host, you can skip Docker entirely **for front-end
work**:

```bash
python -m bioradar.webapp --port 8080
```

The dashboard, the map, the charts, the language switch and all the views work.
What will *not* work is actually running the pipeline — that needs `snakemake`,
which only exists inside the container. The Settings page will honestly show
**degraded** with `snakemake: not on PATH`, which is expected and correct.

For editing CSS and JS this is by far the nicest loop: save the file, refresh
the browser, done.

### Confirm it is up

Open <http://localhost:8080>. You should see the BioRadar dashboard with a
sidebar (ANALYZE, MONITOR, RESULTS, COMPARE, ALERTS, SETTINGS) and a green or
amber dot at the top right.

- **Green / healthy** — everything present
- **Amber / degraded** — running, but something is missing. Click **SETTINGS**
  to see exactly what. Running outside the container always shows degraded.
- **Red / unhealthy** — see [§12](#12-troubleshooting)

---

## 7. Test it on the sample data

The repository ships a **12-sample, 6-site demonstration dataset** covering the
Indian coast, sampled in two rounds. It is in `data/demo_survey/` and is about
12 MB, so you already have it.

> **Say this out loud in the demo.** The reads are *simulated* — generated from
> real COI reference sequences, so the classifications are genuine, but which
> species occurs at which site is invented. Ground truth is in
> `data/demo_survey/truth.json`. Details in
> [docs/DEMO_DATASET.md](docs/DEMO_DATASET.md). Never present it as field data;
> a judge who asks where the samples came from deserves a straight answer.

### The run — GUI

1. Open <http://localhost:8080>
2. **ANALYZE** tab. Under **Your datasets** you will see
   **Indian coastal survey (SIMULATED demonstration data)** with a green
   **ready** badge and *12 sample(s), pre-flight clean*
3. Click **Analyze**
4. You are taken to **MONITOR**. Watch the pipeline work: importing reads,
   trimming primers with cutadapt, denoising into sequence variants with DADA2,
   assigning taxonomy. Each step ticks green as it completes.
5. About **3 minutes** later, click **See results**

### The run — CLI

```bash
docker compose run --rm --entrypoint python app -m bioradar.pipeline_runner \
    data/demo_survey/fastq --mode local \
    --classifier bioradar-pipeline/database/qiime2-qza/classifier-coi-india-2026.qza \
    --fprimer GGWACWGGWTGAACWGTWTAYCCYCC \
    --rprimer TANACYTCNGGRTGNCCRAARAAYCA \
    --trunc-len-f 220 --trunc-len-r 205
```

### What you should see

| Tab | What is there |
|---|---|
| **RESULTS** | KPI tiles counting up, an interactive map of the six sites, composition by phylum, the species inventory, and export buttons |
| **COMPARE** | A radar chart comparing up to five sites across six biodiversity dimensions |
| **ALERTS** | Species from the watchlist that turned up, ranked by severity |
| **MONITOR** | The completed pipeline, every step green |

On the map: scroll to zoom, drag to pan, click a cluster to expand it, click a
pin for the site's species. The **⛶** button goes fullscreen, **⇔** measures
distance between points, and the layers control at the top right switches
between Dark, Light, Satellite and Topographic.

### Check the exports work

On **RESULTS**, scroll to **Export** and try each button:

- **CSV — detections** opens in Excel with species names intact
- **Printable report** opens a new tab; `Ctrl+P` gives you a clean PDF
- **Darwin Core Archive** downloads a `.zip` — this is the format GBIF and OBIS
  ingest, and it is one of the things that makes us different

### Sanity-check the result

You should get roughly **16 named species across 1–3 phyla in 12 samples**. If
you get zero named species, something is wrong — check that the classifier
actually got extracted in [§5](#5-first-time-setup).

---

## 8. Run the automated tests

Do this **before every push**. It takes about fifteen seconds and it is the
difference between a working demo and a broken one.

### Unit tests — 132 of them

```bash
python -m pytest tests/ -q
```

Expect `132 passed`.

### Integration checks — 21 of them

```bash
./ci/check_integration.sh --fast
```

Expect `passed 21, failed 0, skipped 4`. The four skips are components that do
not exist yet (Anshika's flagging engine, Tanay's analytics) plus the Docker
checks that `--fast` deliberately skips.

Drop `--fast` to include the Docker checks — that also verifies the code imports
under the container's **Python 3.8**, which matters (see
[§11](#11-rules-that-will-fail-your-commit)).

```bash
./ci/check_integration.sh
```

### Run one test file while working

```bash
python -m pytest tests/test_exports.py -v
```

More detail in [docs/TESTING.md](docs/TESTING.md).

---

## 9. Making changes and getting them in

You are a collaborator, so you can push to `main` directly. Here is how, plus
the safer alternative and when to use it.

### Before you start — always pull first

Somebody else has almost certainly pushed since you last looked.

**GUI (GitHub Desktop):** click **Fetch origin**, then **Pull origin** if it
offers.

**GUI (VS Code):** the sync icon in the bottom status bar, or
`Ctrl+Shift+P` → **Git: Pull**.

**CLI:**

```bash
git pull
```

### Option 1 — commit straight to main

Fine for small, self-contained changes: a copy fix, a colour tweak, a bug fix in
your own area.

**GUI (GitHub Desktop):**

1. Make your edits and save
2. GitHub Desktop lists them under **Changes**
3. Tick the files you want to include
4. Write a summary in the bottom-left box — say *what changed and why*, not
   "update"
5. **Commit to main**
6. **Push origin**

**GUI (VS Code):**

1. **Source Control** panel (`Ctrl+Shift+G`)
2. **+** next to each file to stage it
3. Type a message, `Ctrl+Enter` to commit
4. **Sync Changes**

**CLI:**

```bash
git add .
git commit -m "Fix the species table sort order on the Results tab"
git push
```

### Option 2 — branch and pull request

Use this for anything that touches shared files, takes more than an afternoon,
or that you want a second pair of eyes on. Six people pushing straight to `main`
in the last days before a hackathon is how a working demo becomes a broken one
at 2 a.m. — a branch costs you thirty seconds and cannot break anyone else.

**GUI (GitHub Desktop):**

1. **Current branch → New branch**, name it `ishwar/map-legend`
2. Make your changes, commit as above
3. **Publish branch**
4. **Create Pull Request** — opens your browser
5. Describe what you did, then **Create pull request**
6. When it is approved, **Merge pull request**

**CLI:**

```bash
git checkout -b ishwar/map-legend
# ... make changes ...
git add .
git commit -m "Add a legend to the sampling-sites map"
git push -u origin ishwar/map-legend
```

Then open the link git prints, or:

```bash
gh pr create --fill
```

### If your push is rejected

```
! [rejected]  main -> main (fetch first)
```

Somebody pushed while you were working. Pull, then push:

```bash
git pull --rebase
git push
```

`--rebase` replays your commits on top of theirs, which keeps the history
readable instead of littering it with merge commits.

### If you get a merge conflict

Git marks the clashing region in the file:

```
<<<<<<< HEAD
their version
=======
your version
>>>>>>> your-branch
```

**GUI:** VS Code shows **Accept Current** / **Accept Incoming** / **Accept Both**
buttons directly above the conflict. GitHub Desktop offers to open the file in
your editor.

**CLI:** edit the file so it contains what you actually want, delete the
`<<<<<<<`, `=======` and `>>>>>>>` markers, then:

```bash
git add the-file.js
git rebase --continue
```

Read both sides before choosing. "Accept mine" on a file a teammate just fixed
silently deletes their fix.

### If the demo dataset disappears from the app

Pressing **Remove** on the bundled demo survey hides it **on your machine only**
— it writes an id into `data/.hidden_datasets.json`, which is gitignored. Nothing
tracked changes, so your teammates are unaffected.

To bring it back:

```bash
python -m bioradar.webapp --restore-datasets
```

If `data/datasets.json` itself ever shows up in `git status` as modified, do not
commit it. An earlier version of the Remove button edited that file directly,
which meant a click in the UI became a source-code change — it reached the public
repository once, and every fresh clone opened with an empty dataset list. Restore
it with `git checkout data/datasets.json`. A test now fails if the demo entry
goes missing.

### Never commit these

`.gitignore` already covers them, but so you know why:

| Path | Why not |
|---|---|
| `runs/` | Pipeline output — large, regenerable, one directory per run |
| `data/uploads/` | Whatever you dragged in while testing |
| `data/verifications.jsonl` | Field observations, and they contain observer names |
| `.env` | Secrets |
| `logs/` | Diagnostics from your machine only |
| `*.qza` | 22 MB of binary classifiers — extracted from the image, not tracked |

---

## 10. If you are working on the UI

### Where things are

```
bioradar/webapp_static/
├── index.html     the empty app shell — contains no feature markup at all
├── app.css        the entire design system: ~35 tokens, then every component
├── registry.js    the feature registry (see below)
├── i18n.js        English and Hindi strings
├── ui.js          components: card, button, badge, KPI, toggle, states, motion
├── charts.js      the comparison radar, drawn as SVG
├── mapkit.js      map clustering, heatmap, time slider, measurement
└── app.js         the six views and everything that wires them together
```

There is **no build step**. No npm, no bundler, no compile. Edit a file, refresh
the browser, done. That is deliberate — the app is served from inside an 11.8 GB
scientific image, and a bundler would mean rebuilding that image to change a
button.

**Read [docs/DESIGN.md](docs/DESIGN.md) before your first change.** It is the
design system: every colour, shadow, spacing value and animation duration, and
the reasoning for each.

### Adding a whole new view

You do not touch the shell, the sidebar, the tab bar, or any other feature. You
register:

```js
BioRadarRegistry.registerFeature({
  id: "trends",
  slot: "main-view",
  icon: "activity",
  order: 45,
  label: function () { return BioRadarI18n.t("nav.trends"); },
  mount: function (container) {
    container.innerHTML = "<h1>Trends</h1><div id='trendsBody'></div>";
  },
  refresh: function () { /* called when data changes */ }
});
```

That is the whole integration. The nav entry, the mobile tab, the view
container, the ARIA wiring and the routing all follow from it.

### The two rules that matter most

**1. Neumorphic chrome, flat data.**

Soft dual shadows go on the shell, cards, buttons, inputs, toggles and modals.
Charts, tables, map markers, alert badges and **primary buttons** are flat and
high-contrast. A soft shadow on a chart series makes the data unreadable; a soft
shadow on a primary button makes the one control the user came to press
indistinguishable from the furniture.

**2. Use the tokens.**

```css
/* yes */
color: var(--text-secondary);
box-shadow: var(--neu-raised);
padding: var(--space-4);

/* no — CI will fail this */
color: #8b95a8;
box-shadow: 4px 4px 9px #111;
padding: 15px;
```

There are **exactly five** shadow tokens. Not six. Adding one is how a
neumorphic UI starts looking improvised, so the build fails if the count changes.

### Performance rules, learned the hard way

Three real bugs we have already hit. Please do not reintroduce them.

- **Never read a layout property in a loop.** `node.offsetWidth`,
  `getBoundingClientRect()` and `getComputedStyle()` force a full synchronous
  layout. Doing that once per item in a ten-item list measured over a second on
  a single click.
- **Never make an animation the only path to a correct value.**
  `requestAnimationFrame` does not fire in a background tab. A count-up that
  stalls does not lose an animation — it leaves a tile reading `0` when the
  answer is `16`. Always have a `setTimeout` backstop.
- **Never use `document.querySelectorAll("[data-something]")` when `<body>`
  carries that attribute.** `<body>` has `data-lang`. A handler bound that way
  catches every click in the app, and if it rebuilds the shell you get
  exponential listener growth: 1, 2, 4, 8 … 256 handlers, then the tab freezes.
  Scope your selector to a container.

CI checks all three.

### Testing your UI change

```bash
python -m bioradar.webapp --port 8080
```

Then in the browser, check:

- Both themes — the sun/moon button in the top right
- Both languages — the English/हिन्दी toggle
- Mobile — `F12`, then the device-toolbar icon, choose a phone
- Keyboard only — `Tab` through the page; every control must show a visible
  focus ring
- The empty states — they matter more than they look. Click **Clear results**
  and confirm every tab still says something sensible instead of going blank.

---

## 11. Rules that will fail your commit

Run `./ci/check_integration.sh --fast` before pushing and you will catch all of
these in fifteen seconds.

**Python must run on 3.8.** The container ships Python 3.8. Anything under
`bioradar/` gets imported inside it, so:

```python
# breaks on 3.8 at runtime
Handler = Callable[[dict[str, Any]], None]

# fine
from typing import Callable, Dict, Any
Handler = Callable[[Dict[str, Any]], None]
```

Annotations are fine either way because every module has
`from __future__ import annotations` — it is subscripting a builtin at *runtime*
that fails.

**No third-party Python imports in `bioradar/`.** Standard library only. Adding
a dependency means rebuilding an 11.8 GB image.

**No external assets in `index.html`.** No Google Fonts, no CDN scripts. The app
must work on conference wifi that is actively hostile, and a font that fails to
load at the wrong moment is a blank page in front of judges.

**Shell scripts need LF line endings.** `.gitattributes` handles this
automatically. If you see `set: pipefail: invalid option name`, your editor
saved CRLF into a `.sh` file.

**Every export format has a test.** If you change `bioradar/exports.py`, run
`python -m pytest tests/test_exports.py -v`. A Darwin Core Archive that GBIF
rejects is worse than no export at all — it looks like a working feature right
up until somebody tries to publish with it.

---

## 12. Troubleshooting

### `docker: command not found`

Docker Desktop is installed but not running, or your terminal predates the
install. Start Docker Desktop, wait for **Engine running**, open a **new**
terminal.

### `Cannot connect to the Docker daemon`

Same thing — the engine is not up yet. On Linux you may also have skipped
`sudo usermod -aG docker $USER` and the log-out that makes it take effect.

### `denied` or `unauthorized` pulling the image

The GHCR package is private, or you are not signed in. See
[§3 Route A](#route-a-pull-from-the-registry),
or just use Route B or C — neither needs a registry.

### `port is already allocated`

Something else is on 8080.

```bash
docker compose down
```

Or run on a different port: `python -m bioradar.webapp --port 8090`, or set
`APP_PORT=8090` in `.env` before `docker compose up app`.

### The dataset card says `blocked`

Click it and read the reason — it will tell you exactly what is wrong.

| Message | What it means |
|---|---|
| `Classifier ... not built yet` (any other) | Re-run `./scripts/setup.sh`, or extract the classifiers by hand ([§5](#5-first-time-setup)) |
| `named .gz but is not gzip data` | The file is corrupt or was decompressed and renamed. Re-transfer it. |
| `truncated or corrupt` | The download or upload was cut short. gzip's checksum caught it — which is the whole point, because otherwise it fails half an hour into DADA2 with an error nobody can read. |
| `only N distinct quality value` | The dataset was published with quality scores stripped. DADA2 cannot work on it; the app will route it to vsearch automatically. |

### The pipeline dies partway with no message

Almost always memory. Docker Desktop → **Settings → Resources → Memory** → 8 GB
or more → **Apply & restart**.

### The map is empty but the species list is fine

FASTQ files contain sequences, not coordinates. Those live in a `samples.csv`
next to the reads with `sample_id`, `latitude` and `longitude` columns, and the
sample ids have to match the FASTQ filename prefixes. The map's empty state says
this too.

### The health dot is amber

Click **SETTINGS** — it lists every check and what failed. Running outside the
container always shows `snakemake: not on PATH`, which is expected.

### Everything is slow / the tab freezes

If it started after a change of yours, re-read the performance rules in
[§10](#10-if-you-are-working-on-the-ui). Open DevTools (`F12`) → **Console** for
errors, then **Network** — a flood of repeated requests means something is
polling in a loop.

### Git says my push was rejected

See [§9](#if-your-push-is-rejected). Short version: `git pull --rebase` then
`git push`.

### I committed something I should not have

If you have not pushed yet:

```bash
git reset --soft HEAD~1
```

That undoes the commit and keeps your changes. If you already pushed, tell the
team before rewriting anything — force-pushing shared history breaks everyone
else's clone.

---

## Who owns what

| Area | Owner | Main files |
|---|---|---|
| Pipeline, Docker, dashboard | **Om** | `bioradar-pipeline/`, `bioradar/`, `docker/` |
| Reference data, classifiers | **Jimeet** | `data/reference_coi_india/`, `bioradar/build_reference.py` |
| Flagging, invasive detection | **Anshika** | `bioradar/flagging/` (to be created) |
| Analytics, CBI | **Tanay** | `bioradar/analytics/` (to be created) |
| Front end | **Ishwar** | `bioradar/webapp_static/` |
| Backend, API | **Parth** | `backend/` (to be created) |

The two "to be created" modules have integration checks waiting for them in
`ci/check_integration.sh` — they currently skip, and start enforcing the moment
the module exists. Nobody has to remember to switch them on.

**Read [docs/CONTRACTS.md](docs/CONTRACTS.md) before writing code that consumes
pipeline output.** The column names are frozen; parsing the raw QIIME 2 lineage
string yourself will break.

---

## Further reading

| Document | What it covers |
|---|---|
| [README.md](README.md) | The general install guide |
| [docs/RUNNING.md](docs/RUNNING.md) | Every way to run the system, including real Indian datasets |
| [docs/TESTING.md](docs/TESTING.md) | How to verify each layer |
| [docs/CONTRACTS.md](docs/CONTRACTS.md) | The frozen data formats between components |
| [docs/PIPELINE.md](docs/PIPELINE.md) | The bioinformatics itself |
| [docs/DESIGN.md](docs/DESIGN.md) | The design system — read before touching the UI |
| [docs/DEMO_DATASET.md](docs/DEMO_DATASET.md) | What the sample data is, and what it is not |
| [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | What was built, substituted, and deliberately skipped |

Stuck on something not covered here? Ask in the group before losing an hour to
it — the answer is usually one line, and somebody has probably already hit it.
