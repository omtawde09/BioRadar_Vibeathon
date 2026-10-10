# The BioRadar design system

Neumorphism 2.0, implemented from `BioRadar_UI_Design_Guide v1.0`.

---

## The one substitution

The guide specifies **React 18 + TypeScript + Tailwind CSS v4 + Recharts**. This
app is served from inside the 11.7 GB pipeline image, where there is no Node, no
npm and no build step — a bundler would mean rebuilding that image to change a
button.

So the design system lives in **CSS custom properties and vanilla JS** instead.
That is a change of transport, not of design. Every colour, shadow, radius, type
step, spacing value and animation duration below is the number the guide names,
and the rendered result is the same pixels. The `@theme` block the guide asks for
maps one-to-one onto the `:root` block in
[app.css](../bioradar/webapp_static/app.css).

Where the guide names a library, the equivalent is written directly:

| Guide | Here | Why |
|---|---|---|
| Recharts radar | `charts.js` | A radar chart is ~40 lines of trigonometry; 90 kB to avoid writing them is the wrong trade |
| leaflet.markercluster | `mapkit.js` `ClusterLayer` | Nothing is fetched at page load, so a plugin means vendoring a bundle |
| leaflet.heat | `mapkit.js` `HeatLayer` | Canvas overlay, ~70 lines |
| leaflet-timeline | `mapkit.js` `timeline()` | A range input and a filter |
| leaflet-measure | `mapkit.js` `MeasureControl` | Haversine, via Leaflet's own `map.distance` |
| i18next | `i18n.js` | 40 kB to look up strings in a flat object |
| React `lazy()` | `registry.js` `mount()` | Views mount on first show — what `lazy()` was buying |

---

## The rule everything follows

**Neumorphic chrome, flat data.**

| Neumorphic (soft dual shadow) | Flat (high contrast, no shadow) |
|---|---|
| App bar, sidebar, tab bar | Charts and chart series |
| Cards, KPI tiles, modals | Tables and table rows |
| Secondary buttons | Map markers and clusters |
| Inputs, toggles, sliders | Alert badges |
| Progress tracks, dropzone | **Primary CTAs** |

Applying a neumorphic shadow to a data mark is the anti-pattern that makes
neumorphism unreadable, and applying it to a primary CTA makes the one control
the user came to press indistinguishable from the furniture. Both are enforced by
CI, not by discipline.

---

## Tokens

**35 tokens**, all in `:root`, overridden in `[data-theme="light"]`.

### Surfaces
In neumorphism the element and its parent share a colour — the shadow makes the
shape, never a fill difference.

| Token | Dark (default) | Light |
|---|---|---|
| `--surface-base` / `-raised` / `-pressed` | `#2d3448` | `#e0e5ec` |
| `--surface-overlay` | `#364056` | `#ffffff` |
| `--surface-chart` | `#364056` | `#ffffff` |

### Shadows
Tinted, never pure white or pure black. That is what separates a designed dark
mode from an inverted one.

| Token | Dark | Light |
|---|---|---|
| `--shadow-light` | `#364056` | `#ffffff` |
| `--shadow-dark` | `#1a1f2e` | `#a3b1c6` |
| `--shadow-light-strong` | `#3d4860` | `#ffffff` |
| `--shadow-dark-strong` | `#151926` | `#9caebf` |

### Accents

| Token | Dark | Light |
|---|---|---|
| `--accent-primary` | `#8b83ff` | `#6c63ff` |
| `--accent-hover` | `#a29bff` | `#5a51e0` |
| `--accent-pressed` | `#6c63ff` | `#4a42c0` |
| `--alert-invasive` | `#ff6b5b` | `#e74c3c` |
| `--alert-rare` | `#ffb648` | `#f39c12` |
| `--alert-healthy` | `#3ddc84` | `#27ae60` |
| `--alert-neutral` | `#95a5a6` | `#95a5a6` |
| `--text-primary` | `#e0e5ec` | `#2d3448` |
| `--text-secondary` | `#9caebf` | `#646c7c` |

### The five shadow tokens

Five. Not six.

```css
--neu-raised:    6px 6px 12px  var(--shadow-dark), -6px -6px 12px  var(--shadow-light);
--neu-raised-lg: 10px 10px 20px var(--shadow-dark), -10px -10px 20px var(--shadow-light);
--neu-raised-sm: 3px 3px 6px   var(--shadow-dark), -3px -3px 6px   var(--shadow-light);
--neu-pressed:   inset 4px 4px 8px  var(--shadow-dark), inset -4px -4px 8px  var(--shadow-light);
--neu-input:     inset 5px 5px 10px var(--shadow-dark), inset -5px -5px 10px var(--shadow-light);
```

**Single light source, top-left, always.** Light offset negative, dark offset
positive, on every element without exception. Inconsistent light source is the
amateur neumorphism tell, so `ci/check_integration.sh` fails the build if the
token list ever grows a sixth entry or if a hex colour appears outside the token
block.

### Radius, spacing, type

- Radius `8 / 12 / 20 / 28px`. Never `50%` on a neumorphic surface — a pill
  breaks the extrusion.
- Spacing on a **4px base**: `4 8 12 16 24 32 48`. No 7px, no 13px, no 22px.
- Type: Major Third (1.250) from a **16px base** — `12 14 16 20 25 31 39`. Below
  16px, iOS Safari zooms inputs on focus and the layout jumps under the user's
  thumb.
- Inter (body), JetBrains Mono (ids, hashes, logs), Noto Sans Devanagari (Hindi),
  each with a system fallback. Nothing is fetched from a font CDN.

### Data-visualisation palettes

Deliberately *not* the accent colours.

| Data | Palette |
|---|---|
| Categorical (phyla, sites) | **Okabe-Ito**, 8 colours, built for colour-blind accessibility |
| Continuous 0–1 (species density) | **Viridis** — perceptually uniform, survives greyscale |
| Density (heatmap) | **ColorBrewer YlOrRd** |

Okabe-Ito's eighth colour is black, which is invisible on a dark surface; in dark
mode it becomes near-white. Same role, same separation, still CUD-safe.

Categorical colours are assigned by a stable hash of the label, not by iteration
order, so a phylum keeps its colour when the sort changes between runs. A legend
that re-colours itself on every refresh teaches the reader nothing.

---

## Extensibility: the feature registry

The guide calls this the single most important architectural decision, and the
test is concrete: **adding a feature must not require editing the shell.**

```js
BioRadarRegistry.registerFeature({
  id: "compare",
  slot: "main-view",
  icon: "radar",
  order: 40,
  label: () => t("nav.compare"),
  mount: (container) => { /* build once */ },
  refresh: () => { /* on new data */ }
});
```

That is the whole integration. The sidebar entry, the mobile tab, the view
container, the ARIA wiring and the routing all follow from the registry.
`index.html` contains no feature markup at all — it is an empty shell.

Six slots: `sidebar-nav`, `header-action`, `main-view`, `right-panel`,
`bottom-tab`, `overlay`.

The six shipped views — Analyze, Monitor, Results, Compare, Alerts, Settings —
are registered exactly this way and reference nothing about each other.

---

## Layout

**Desktop (≥1024px)** — app bar 64px, icon rail 72px, fluid workspace, 380px
slide-in detail panel.

**Mobile (<1024px)** — app bar 56px, no rail, four-item bottom tab bar 56px, and
the detail panel becomes a **bottom sheet**. A 380px side panel on a 6-inch
screen is a full-screen takeover with extra steps.

Touch targets are 44px on desktop (WCAG 2.5.5) and **48px on mobile** — field use
means gloves.

---

## Six states, every interactive element

| | Neumorphic button | Input | Interactive card | Flat primary CTA |
|---|---|---|---|---|
| Default | `neu-raised-sm` | `neu-input` | `neu-raised` | accent + `0 1px 2px` |
| Hover | `neu-raised` | — | `neu-raised-lg` | accent-hover |
| Focus | 2px accent ring, 2px offset | same | same | same |
| Active | `neu-pressed` | — | `neu-pressed` | accent-pressed + inset |
| Disabled | opacity .5, **shadow kept** | opacity .5 | opacity .5 | opacity .5 |
| Loading | opacity .75 + spinner | — | — | opacity .75 + spinner |

Disabled keeps its shadow on purpose: removing it makes the control vanish into
the background instead of reading as unavailable.

The **focus ring is not optional**. Neumorphism's native focus is a shadow change
of roughly 1:1 contrast — invisible to a keyboard user, which is why pure
neumorphism fails WCAG 2.4.7 by construction. The ring fixes it without touching
the aesthetic.

---

## Empty, loading and error states

Every view handles all of them. The gap analysis calls empty-state handling the
single most likely demo failure, and the reason is that a blank map and a broken
map look identical.

| State | What is shown |
|---|---|
| No datasets | Illustration, explanation, and the action that fixes it |
| No species detected | "This can mean low DNA concentration, a failed extraction, or that the reference database does not cover what is present" |
| All low-confidence | "Nothing here clears the threshold for field action. Expert review is recommended" |
| Loading < 2s | Inline skeleton |
| Loading 2–30s | Full skeleton screen |
| Pipeline running | Determinate progress + live DAG + elapsed time |
| Queued | Position in the queue, and why runs are serial |
| Failed | The error, plus a quotable error id |
| Offline | Banner naming the timestamp of the data still on screen |
| No coordinates | Exactly which columns a `samples.csv` needs |

Skeletons, not spinners, below 30 seconds: a spinner says "waiting"; a skeleton
says "waiting, and this is the shape of what arrives". The pulse runs at 0.67 Hz,
safely under the WCAG 2.3.1 three-flashes threshold.

---

## Performance

Smoothness here is mostly about **not doing work**, not about doing it faster.

**Nothing re-renders unless its data changed.** Every view keeps a signature of
what it last drew and returns immediately if it still matches. Before this, the
Compare view recomputed metrics for eighteen sites and rebuilt a 460px SVG every
six seconds; Alerts rebuilt ten cards; Settings rebuilt four cards *and* fired
two extra API calls. A repeat render now costs **0.02 ms**.

The exception that proves the rule: opening a view always repaints, because
`mount()` has just replaced the container the previous render wrote into.

**Renders are coalesced into one frame.** A poll response, a progress event and a
view switch arriving together paint once, not three times.

**The live pipeline updates in place.** A running job emits a progress event
every few seconds. Rebuilding eleven DAG nodes from `innerHTML` each time was
both expensive and self-defeating — it restarted every CSS transition mid-flight,
so the progress bar could never actually animate. Structure is rebuilt only when
the set of runs changes; progress moves through direct DOM updates.

**Polling follows the work.** 2.5 s while a run is active, 12 s idle, and
**nothing at all when the tab is hidden**, with an immediate catch-up on return.
Server-sent events carry anything urgent, so the poll is only a safety net.

**Uploads report real bytes.** `fetch` cannot report upload progress, so uploads
go through `XMLHttpRequest`, which has had `upload.onprogress` for fifteen years.
Per-file bars, an aggregate bar weighted by bytes rather than file count, live
throughput and an ETA. After the bytes land, a four-step checklist covers the
server-side work — integrity, primer detection, configuration — which previously
left a disabled button and no explanation for several seconds.

### The bug that made every click slower than the last

`<body>` carries `data-lang` as the *active* language. The language switcher
bound its click handler with `document.querySelectorAll("[data-lang]")` — which
**also matches `<body>`**.

Every click anywhere in the app therefore bubbled into that handler, which
switched the language, which rebuilt the shell, which bound another handler to
`<body>`. Clicks doubled on every interaction: 1, 2, 4, 8 … 256. Measured click
latency went 3.4 ms → 1449 ms over twelve clicks, and then the tab stopped
responding entirely.

Nothing about it was visible in review — the selector is ordinary, the handler is
three lines, and the symptom looks like "the app is just slow". The fix is a
distinct attribute (`data-set-lang`) and a scoped root, and
`ci/check_integration.sh` now fails the build if any document-wide `[data-*]`
selector collides with an attribute on `<html>` or `<body>`.

Two smaller multipliers found alongside it:

- **Every caller of `poll()` went straight to the network.** Six of them, none
  aware of the others — and `visibilitychange` fired one unthrottled request
  pair per event. Focus changes arrive in bursts, which exhausted Chrome's
  six-connection budget for the origin; after that every request failed
  instantly with `ERR_INSUFFICIENT_RESOURCES`. All callers now pass through one
  gate that coalesces concurrent calls and enforces a minimum gap, with a
  `force` flag for the user actions that must not be throttled.
- **Opening a view rebuilt it.** The navigation fix for a blank-panel bug had
  invalidated the signature on every `showView`, which tore down and rebuilt the
  Leaflet map — re-downloading every tile — each time the user clicked back to
  Results. Invalidation belongs at mount, where the container is genuinely new.

### One rule learned the hard way

**An animation may never be the only thing that produces a correct value.**

`requestAnimationFrame` does not fire in a backgrounded tab, and does not fire at
all in some embedded browser panes. A count-up that stalls does not merely lose
its animation — it leaves a KPI tile reading **0 when the answer is 16**. A
render scheduler that queues on rAF alone latches its flag on the first missed
frame and the UI never updates again.

So `countUp`, `growBars` and `scheduleRender` all reach their end state through a
timeout backstop as well as through frames, and `ci/check_integration.sh` fails
the build if any of them loses it.

---

## Motion

100–300ms, `ease-out`, or `cubic-bezier(.4,0,.2,1)` for panels. Never bounce —
springy easing reads as a toy in a tool someone makes decisions with.

Motion answers one of three questions — *did that register?*, *where did this come
from?*, *is it still working?* — and nothing animates that answers none of them.

| Interaction | Duration |
|---|---|
| Button press (scale .97) | 100ms |
| Button/card hover | 150ms / 200ms |
| Modal open / close | 200ms / 150ms |
| Right panel | 250ms |
| Bottom sheet, toast, theme cross-fade | 300ms |
| View entrance | 250ms |
| List stagger | 45ms per item, capped at 10 |
| KPI count-up | 900ms, ease-out cubic |
| Bar and meter fill | 620ms |
| Radar draw-in | 900ms, 110ms apart per series |
| Map pin drop | 340ms |
| DAG node completion pulse | 620ms |
| Progress sheen | 1600ms loop |
| Skeleton pulse | 1500ms loop |

Two details worth knowing:

- **The stagger is capped.** Past about ten items a per-item delay stops reading
  as "the list is arriving" and starts reading as "the app is slow".
- **The radar's dash length is measured, not guessed.** `getTotalLength()` needs
  layout, so the CSS reads a `--len` custom property that JS sets after mount. A
  constant would clip short outlines and leave long ones visibly waiting.

All of it is switched off under `prefers-reduced-motion` (WCAG 2.3.3). Nothing
here carries information, so it can go wholesale without loss.

---

## Accessibility

- Every text colour meets 4.5:1; `--text-primary` is 12.5:1.
- Visible focus on every interactive element, 3:1 minimum.
- 44px targets, 48px on mobile.
- **Colour is never the only signal** — every badge carries its word
  (`INVASIVE`, `VERIFIED`, `HIGH`) as well as its colour.
- Charts use colour-blind-safe palettes and label every point.
- Full keyboard navigation. The dropzone is focusable and Enter/Space opens the
  picker — a drag-and-drop-only upload is unusable without a mouse.
- Modals trap focus, close on Escape, and return focus on close.
- Skip link, landmark roles, `aria-current` on navigation, `aria-live` on toasts.
- `prefers-reduced-motion` and `prefers-color-scheme` respected.
- **Windows High Contrast**: `forced-colors` strips `box-shadow` entirely, which
  in a neumorphic UI removes every visual boundary at once. A border fallback
  restores them.

---

## Dark by default

Dark is the default because the guide makes it a field decision, not a taste one:
it stays readable in direct sunlight and costs less battery on OLED. Light is one
click away in the app bar and in Settings, and the choice persists.

Dark mode is designed, not inverted — its own tinted shadows, its own accent
brightness, and its own map basemap. A dark dashboard wrapped around a bright
white basemap is the most jarring thing a map UI can do, so the tiles follow the
theme automatically.
