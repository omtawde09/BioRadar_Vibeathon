# Response to the Critical Feature Gap Analysis

Item-by-item: what was built, what was built differently, and what was not built.

Read the "differently" and "not built" columns first — they are the ones that
matter if you are standing in front of a judge.

---

## One correction to the premise

The analysis describes BioRadar as having "21 features across 5 layers" —
DNA foundation models, RAG querying, a digital twin, satellite and acoustic
fusion, gamification, biodiversity credits, federated learning, a React
dashboard, a FastAPI backend, PostGIS, a blockchain ledger.

**Most of those do not exist in this repository.** The analysis says so itself in
its limitations section: it was written against a design document, not against
the code. What actually exists is Layer 1 — the pipeline, the India-curated
reference, the frozen integration contract, chain-of-custody hashing — plus the
dashboard that drives it.

That matters here because roughly a third of the recommendations assume
infrastructure that would have to be built first. Those are marked below rather
than quietly skipped.

---

## §1 — Unique features

| # | Feature | Status |
|---|---|---|
| 1.1 | GBIF/OBIS publishing (DwC-A) | **Built, minus submission** |
| 1.2 | Live pipeline run monitor | **Built** |
| 1.3 | Field verification feedback loop | **Built** |
| 1.4 | Multi-marker dashboard toggle | **Not built** |
| 1.5 | Biodiversity comparison radar | **Built** |

### 1.1 GBIF/OBIS publishing — built, minus the submit button

[`bioradar/exports.py`](../bioradar/exports.py) produces a complete Darwin Core
Archive: `occurrence.txt`, the GBIF **DNA-derived data extension** (`dna.txt`
with primers, target gene, denoiser and classification method), `meta.xml`,
`eml.xml` and a README. Verified at 425 occurrence records from the
demonstration data, extension correctly joined to the core.

**BioRadar does not submit it.** Publishing to a global public registry is
irreversible, requires a registered publishing organisation and credentials, and
attributes the data to a named person. That decision is the user's, so the app
builds the archive and hands it over.

Two things in the archive are deliberate:

- Unassigned detections are **excluded**. An occurrence record asserts that a
  named organism was present; `Unassigned` asserts nothing, and publishing
  thousands of them to GBIF would be pollution rather than contribution.
- `organismQuantityType` is `DNA sequence reads`, and the README says so again in
  capital letters. Read counts are not individuals. It is the single most
  dangerous misreading of eDNA data.

### 1.2 Live pipeline monitor — built

The Monitor view renders the Snakemake workflow as a DAG with live per-rule
status, elapsed time, percentage and a tail of the real pipeline log.

Delivered over **server-sent events**, not WebSockets. A WebSocket would mean
hand-rolling RFC 6455 framing on top of `BaseHTTPRequestHandler` for a stream
that only ever flows one way, and `EventSource` reconnects by itself. A 6-second
poll sits underneath as a fallback for proxies that buffer SSE.

### 1.3 Field verification loop — built

[`bioradar/verification.py`](../bioradar/verification.py). Four outcomes
(confirmed / not found / misidentified / uncertain), recorded per **species and
site** — the same taxon can be genuinely present at one site and absent 40 km
away.

Three design decisions worth defending out loud:

- **Two independent confirmations before a verdict**, following iNaturalist's
  Research Grade rule. One observer can be mistaken, and eDNA detections are
  precisely the cases where the observer already expects to find something.
- **Append-only.** A record of what somebody observed on a particular day is
  evidence, and evidence that can be silently edited is not evidence.
  Corrections are added, never applied.
- **Verification changes presentation, never the classifier's confidence.** The
  confidence number is a property of the sequence. Rewriting it retroactively
  would break the guarantee that the same input yields the same output — which
  is the only thing that makes the chain-of-custody hash mean anything.

Disagreement surfaces as `CONTESTED` rather than being averaged into a
comfortable middle.

### 1.4 Multi-marker toggle — not built

The analysis rates this Hard (5+ days) and "Optional for hackathon", and its own
suggestion is to fake the non-12S markers with synthetic data. Presenting
invented ecological data as a working feature is not a thing worth doing in front
of judges who may ask where it came from. Skipped as the analysis recommends.

### 1.5 Comparison radar — built

Ranked #1 in the analysis backlog. [`charts.js`](../bioradar/webapp_static/charts.js),
up to five sites over six axes, each scaled against the maximum among the
selected sites so the chart shows relative standing.

The analysis names CBI and an Ecosystem Health Index among its six dimensions.
Both belong to the analytics layer, which does not exist. Rather than invent
them, the six axes are all computed from what the pipeline really produces:

**species richness · Shannon H' · Pielou evenness · unique taxa · reference
coverage · watchlist load**

`DIMENSIONS` is data, so when the analytics layer lands, CBI is added by
appending an entry — not by touching the chart.

Five sites is the ceiling because past that the overlaid fills stack into mud.

---

## §2 — Differentiation ranking

Built 1, 2, 3 and 5. Skipped 4 (multi-marker), as the analysis itself advises.

---

## §3 — Completeness and trust

| § | Item | Status |
|---|---|---|
| 3.1 | Empty-state and error UX | **Built** |
| 3.2 | Async pipeline (Celery + Redis) | **Built differently** |
| 3.3 | Multi-channel alerting | **Built** (SMS via generic webhook) |
| 3.4 | Structured logging + error tracking | **Built** (Sentry substituted) |
| 3.5 | Professional GIS features | **Built** (drawing omitted) |
| 3.6 | Multi-format export | **Built** (PDF via print, no native .xlsx) |

### 3.2 Celery + Redis — the substitution to know about

[`bioradar/jobs.py`](../bioradar/jobs.py) implements a serial queue with
idempotency keys, bounded retries with exponential backoff, soft and hard
timeouts, cancellation and queue-position reporting. It is **not** Celery, and
there is no Redis. Two reasons:

- **There is nowhere to put a broker.** The app runs *inside* the pipeline image
  so `snakemake` is on `PATH`. Adding Redis means either a second container the
  app must reach or a rebuild of an 11.7 GB image.
- **Concurrency is not the goal.** Snakemake is invoked with every available
  core, so two simultaneous runs do not finish sooner — they thrash, and on a
  7 GB container DADA2 gets OOM-killed. Serial execution is the correct
  scheduling policy here, not a limitation being worked around.

What Celery would have bought — and what this therefore does — is the *behaviour*:
work queues instead of being refused (the old code returned HTTP 409), duplicate
submissions collapse onto the original, transient failures retry once, and a
runaway run is killed at 55 minutes instead of holding the queue forever.

Swapping in Celery later touches two functions: `submit()` and the job record.

One real bug came out of building this: cancelling a run used to leave the
Snakemake subprocess orphaned, holding every core while the UI said "cancelled".
`pipeline_runner._execute` now terminates the child, then `SIGKILL`s it after 20
seconds — QIIME 2 spawns R and vsearch children that ignore `SIGTERM`.

### 3.3 Multi-channel alerting — built

[`bioradar/notify.py`](../bioradar/notify.py): structured log (always on), SMTP
email, generic HTTP webhook, and browser notifications pushed over the SSE
stream.

**Nothing sends unless it is configured**, and Settings shows the real state of
each channel. A dashboard that quietly emails people because a default was left
on is worse than one that does not email at all.

Twilio is named in the analysis and is one POST away through the webhook channel.
It is not built in because it needs a paid account and Indian sender registration
(TRAI DLT) — hard-coding it would produce a feature that cannot be demonstrated.
Every Indian SMS gateway takes an HTTP POST, so one generic channel covers all of
them without a vendor lock.

Browser notifications use the Notification API, not a service worker. That
reaches a tab open behind other windows — the realistic case. A closed-tab push
needs a push service and VAPID keys, which is a deployment concern.

Alerts have something real to fire on: [`bioradar/watchlist.py`](../bioradar/watchlist.py)
screens detections against `data/species_pool.csv` by `india_status`. Named
`watchlist` and not `flagging` because `bioradar.flagging` is Anshika's module in
the team split. The bundled list is **18 species, not the NBA's full IAS
register** — the mechanism is real, the coverage is a starting point, and the
UI says so rather than implying otherwise.

A single read never raises an alarm. Read counts in the low single digits are
routinely index-hopping between samples on one flow cell, and alerting on them
trains everybody to ignore alerts.

### 3.4 Structured logging — built, Sentry substituted

[`bioradar/obs.py`](../bioradar/obs.py). One JSON object per line, every request
carrying an `X-Request-ID` that propagates into every log line and every error
response, so a failure in a demo is a text search rather than an investigation.

Sentry's SDK is a third-party package, so unhandled exceptions are captured to
`logs/errors.jsonl` instead — same fields, no image rebuild, `tail -1` shows the
last failure in full. Visible in Settings.

`/api/health` checks static assets, classifiers, the pipeline definition,
`snakemake` on `PATH`, upload writability and free disk, and distinguishes
**degraded** from **unhealthy**. Collapsing those into one boolean would make the
check useless for deciding what to fix.

### 3.5 Professional GIS — built, minus drawing

Marker clustering, heatmap, time-slider, four basemaps, distance measurement,
fullscreen — all in [`mapkit.js`](../bioradar/webapp_static/mapkit.js), written
directly on Leaflet rather than vendoring four plugin bundles for behaviour that
is 60–80 lines each.

Clustering works in **screen space**, because "these pins overlap" is a pixel
problem; clustering by kilometres still overlaps when zoomed out. Cluster bubbles
scale with the square root of the count — area proportional to count, which is
the perceptually honest scaling.

**Drawing/annotation is omitted.** It is a data-entry tool whose output BioRadar
has nowhere to store. A polygon nobody can save is a demo prop.

Distances are great-circle. Planar distance on Web Mercator is wrong by the
secant of the latitude — already 6% at 20°N.

### 3.6 Export — built, with two substitutions

CSV (detections, species, samples), JSON, Darwin Core Archive, and a
**self-contained print-optimised HTML report** — Ctrl-P gives a clean PDF.

Native PDF (ReportLab/WeasyPrint) and `.xlsx` (openpyxl) both need third-party
libraries, and this package is stdlib-only so it can be imported inside the
pipeline image. The print stylesheet produces a publication-quality PDF through
the browser and Excel opens the CSV, so neither substitution costs the user
anything real.

CSVs carry a UTF-8 BOM. Without it, Excel on Windows reads them as the system
codepage and mangles every accented species name.

---

## §4 — UX, reliability, scalability, edge cases

### 4.1 UX — all eight built

Marker clustering · heatmap · time-slider · basemap switching · **Hindi toggle**
· 48px touch targets and high contrast · designed empty states · loading
skeletons.

On Hindi: scientific names are never translated — binomial nomenclature is
language-independent by design. Technical terms with no settled Hindi equivalent
(FASTQ, DADA2, ASV, Darwin Core) stay in Latin script inside a Devanagari
sentence; inventing translations for them would be less clear, not more.

### 4.2 Reliability — six of seven

Built: Celery-equivalent queue · idempotency keys · exponential backoff ·
**FASTQ validation** · `/health` · graceful degradation (the UI keeps its last
good data and says so when the server is unreachable).

Not built: **PgBouncer connection pooling** — there is no PostgreSQL in this
application. The `db` service exists in `docker-compose.yml` for the backend that
has not been written.

FASTQ validation ([`preflight.check_integrity`](../bioradar/preflight.py)) is the
one worth calling out. It verifies gzip magic bytes, decompresses the whole file
so gzip's CRC32 catches truncation, checks the first character is `@`, and
requires enough reads for DADA2 to fit an error model. A truncated download is
the most common cause of a run that dies half an hour later with an error from
inside R that nobody can read.

### 4.3 Scalability — one of five

Built: **pagination on every list endpoint**.

Not built, all for the same reason — they are database and infrastructure
concerns and this application has no database: Redis response caching (the
existing fingerprint cache already took the dataset list from 48.8s to 0.19s),
S3 object storage, read replicas, CDN.

### 4.4 Edge cases — all eight built

| Edge case | Handling |
|---|---|
| Empty result set | Designed state naming the three likely causes |
| All low-confidence | Explicit "expert review recommended before field action" |
| Pipeline timeout | Soft 55min / hard 60min, then a clear message |
| FASTQ corruption | Caught pre-flight by gzip CRC, before the run starts |
| Duplicate submission | Idempotency key over dataset + file fingerprint + parameters |
| Unicode species names | UTF-8 throughout, BOM on CSV, covered by a test |
| Timezone | Stored UTC, displayed **IST and labelled as IST** |
| Concurrent runs | Queued with position, not refused |

---

## §5 — Solidification steps

| Step | Status |
|---|---|
| End-to-end run and fix every bug | **Done** — see below |
| Eight edge-case handlers | **Done** |
| Five GIS features | **Done** |
| Structured logging + `/health` | **Done** |
| Multi-format export | **Done** |
| Async pipeline | **Done** (substituted) |
| Comparison radar | **Done** |
| Multi-channel alerting | **Done** |
| Deployment guide | **Already exists** — [README](../README.md), [RUNNING](RUNNING.md) |
| Rehearse on a clean machine | **Yours to do** — nobody can do this for you |

Two real bugs found and fixed during verification:

1. **Cancelling a run orphaned the Snakemake subprocess**, which kept every core
   while the UI reported the run as cancelled — so the next run could never
   start.
2. **The map layers projected coordinates before the map had a centre**, throwing
   Leaflet's "Set map center and zoom first" from inside the cluster layer, which
   an over-broad `catch` then turned into "No coordinates for this dataset"
   painted over a working map. The view is now set first, and both custom layers
   refuse to render before the map is ready rather than depending on callers
   adding layers in the right order.

---

## §6 — Features deliberately not built

All ten skipped, for the reasons the analysis gives: computer-vision auto-ID,
full FAIR/PID/PROV-O, LIMS integration, 3D terrain, offline-first PWA with
conflict resolution, Kubernetes, Citus sharding, TNFD/CSRD/GRI reporting,
iNaturalist-scale moderation, WMS/WFS.

---

## Verification

- **132 tests** pass, 56 of them new (exports, verification, job queue,
  watchlist, file integrity).
- **19 integration checks** pass, including four new front-end ones that fail the
  build if a sixth shadow token appears, if a hardcoded hex colour escapes the
  token block, if `index.html` references a file that does not exist, or if it
  ever loads an external script or stylesheet.
- Exercised end-to-end against contract-shaped data across 18 sites and 54
  samples: 425 DwC occurrences, 10 watchlist alerts, 12 map clusters, all five
  exports served with correct MIME types, verification promoting a species to
  `verified` after two confirmations and to `contested` after a contradiction.

## What is still missing

Honest list, so nothing is a surprise:

- **No backend, no database.** Everything is in-process and session-scoped.
- **The watchlist is 18 species**, not a national register.
- **Email and webhook channels are untested against a live server** — they need
  credentials this repository does not and should not contain.
- **Never rehearsed on a clean machine.** That one is on you, and the analysis is
  right that it is where environment-specific problems surface.
