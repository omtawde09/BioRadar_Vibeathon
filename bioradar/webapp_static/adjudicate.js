/* Review — one real sample, an honest answer.

   Sample quality summary -> species split / unknown review queue -> alert -> map ->
   officer report. Plus the data guard, the summer/winter slider, the alert log and
   the threshold table that explains every number. Registered through the same
   feature registry as every other view; nothing in the shell was edited. */

(function () {
  "use strict";

  var Registry = window.BioRadarRegistry;
  var UI = window.BioRadarUI;
  var esc = UI.esc;

  var S = {
    index: null, id: null, result: null, tab: "sample", busy: false,
    guard: null, seasons: null, alerts: null, thresholds: null, provenance: null,
    map: null, seasonMap: null, timer: null
  };

  var REASON_LABEL = {
    invalid_characters: "Not a DNA sequence", too_short: "Short fragment",
    too_many_n: "Too many N bases", low_complexity: "Low complexity / repeat",
    low_quality: "Low base quality", singleton: "Seen once (probable error)",
    human_contamination: "Human contamination", unrelated: "Unrelated to any reference"
  };
  var ROLE_LABEL = {
    mixed: "Mixed community", poor: "Poor quality / low yield",
    unknowns: "Unknown fish & invasive species", field: "Field samples (summer / winter)"
  };
  var LEVEL_CLASS = { CRITICAL: "invasive", HIGH: "high", WATCH: "medium", NONE: "healthy", RETAKE: "info" };

  function api(path, options) {
    return fetch(path, options).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        if (!res.ok) { var e = new Error(body.error || res.statusText); e.body = body; throw e; }
        return body;
      });
    });
  }
  function pct(x, d) { return (100 * x).toFixed(d === undefined ? 1 : d) + "%"; }
  function root() { return document.getElementById("adjRoot"); }

  /* ── view shell ─────────────────────────────────────────────────────── */

  Registry.registerFeature({
    id: "review", name: "Review", slot: "main-view", order: 12, primary: true, icon: "check",
    label: function () { return "Review"; },
    mount: function (container) {
      container.innerHTML =
        '<div class="view-head"><div><h1>Sample review</h1>' +
        "<p>Pick a real public sample. See what was kept, dropped or left unknown, " +
        "why, and what the officer should do.</p></div>" +
        '<div class="segmented" id="adjTabs" role="group" aria-label="Review sections">' +
        [["sample", "Sample"], ["guard", "Data guard"], ["seasons", "Seasons & map"],
         ["alerts", "Alerts"], ["why", "Numbers & sources"]].map(function (t) {
          return '<button type="button" data-adj-tab="' + t[0] + '" aria-pressed="' +
            (S.tab === t[0]) + '">' + t[1] + "</button>";
        }).join("") + "</div></div>" +
        '<div id="adjBanner"></div><div id="adjRoot" class="stack"></div>';
      container.querySelectorAll("[data-adj-tab]").forEach(function (b) {
        b.addEventListener("click", function () { setTab(b.dataset.adjTab); });
      });
    },
    onShow: function () { init(); }
  });

  function setTab(tab) {
    S.tab = tab;
    document.querySelectorAll("[data-adj-tab]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.adjTab === tab));
    });
    render();
  }

  function init() {
    if (S.index) { render(); return; }
    root().innerHTML = UI.card(UI.skeleton("line", 4));
    api("/api/adjudicate/index").then(function (idx) {
      S.index = idx;
      var first = idx.samples.filter(function (s) { return s.role === "mixed"; })[0] || idx.samples[0];
      S.id = first.sample_id;
      render();
      selectSample(S.id);
    }).catch(function (err) {
      root().innerHTML = UI.state("empty", "Results not built yet",
        "Run the one command that processes every real sample, then reload: " +
        "python -m bioradar.adjudicate.runner all  (" + esc(err.message) + ")");
    });
  }

  function render() {
    if (!root()) return;
    if (S.tab === "sample") renderSampleTab();
    else if (S.tab === "guard") loadThen("guard", "/api/adjudicate/guard", renderGuard);
    else if (S.tab === "seasons") loadThen("seasons", "/api/adjudicate/seasons", function (d) {
      ensureAlerts().then(function () { renderSeasons(d); });
    });
    else if (S.tab === "alerts") loadThen("alerts", "/api/adjudicate/alerts", renderAlerts, true);
    else loadWhy();
  }

  function loadThen(key, url, fn, always) {
    if (S[key] && !always) { fn(S[key]); return; }
    root().innerHTML = UI.card(UI.skeleton("line", 4));
    api(url).then(function (d) { S[key] = d; fn(d); }).catch(function (e) {
      root().innerHTML = UI.state("error", "Could not load", e.message);
    });
  }

  /* ── sample tab ─────────────────────────────────────────────────────── */

  function picker() {
    var groups = {};
    S.index.samples.forEach(function (s) { (groups[s.role] = groups[s.role] || []).push(s); });
    var order = ["mixed", "poor", "unknowns", "field"];
    var opts = order.filter(function (r) { return groups[r]; }).map(function (role) {
      return '<optgroup label="' + esc(ROLE_LABEL[role] || role) + '">' +
        groups[role].map(function (s) {
          return '<option value="' + esc(s.sample_id) + '"' + (s.sample_id === S.id ? " selected" : "") + ">" +
            esc(s.label + " - " + s.verdict) + "</option>";
        }).join("") + "</optgroup>";
    }).join("");
    return '<div class="card sm"><div class="row">' +
      '<label for="adjPick" class="hint" style="min-width:90px">Real sample</label>' +
      '<select id="adjPick" class="adj-select">' + opts + "</select>" +
      UI.button("Re-run live", { id: "adjRerun", size: "sm", title: "Run the full analysis now" }) +
      '<span class="hint" id="adjStatus"></span></div>' +
      '<div class="hint" id="adjWhy" style="margin-top:8px"></div></div>';
  }

  function renderSampleTab() {
    root().innerHTML = picker() + '<div id="adjSample" class="stack"></div>';
    var sel = document.getElementById("adjPick");
    sel.addEventListener("change", function () { selectSample(sel.value); });
    document.getElementById("adjRerun").addEventListener("click", function () { selectSample(S.id, true); });
    if (S.result) paintSample(S.result);
    updateWhy();
  }

  function updateWhy() {
    var row = S.index && S.index.samples.filter(function (s) { return s.sample_id === S.id; })[0];
    var el = document.getElementById("adjWhy");
    if (el && row) el.textContent = "Why this sample: " + row.why_chosen;
  }

  function selectSample(id, force) {
    S.id = id;
    var status = document.getElementById("adjStatus");
    var host = document.getElementById("adjSample");
    var t0 = Date.now();
    if (host) host.innerHTML = UI.card(
      '<div class="adj-working"><div class="adj-spin"></div><div><b>' +
      (force ? "Running the full analysis live" : "Loading result") +
      '</b><div class="hint" id="adjElapsed">0.0 s</div></div></div>');
    clearInterval(S.timer);
    S.timer = setInterval(function () {
      var el = document.getElementById("adjElapsed");
      if (el) el.textContent = ((Date.now() - t0) / 1000).toFixed(1) + " s";
    }, 100);
    var request = force ? api("/api/adjudicate/sample/" + encodeURIComponent(id) + "/run", { method: "POST", body: "{}" })
                        : api("/api/adjudicate/sample/" + encodeURIComponent(id));
    request.then(function (r) {
      return ensureProvenance().then(function () { return r; });
    }).then(function (r) {
      clearInterval(S.timer);
      S.result = r;
      if (S.tab === "sample") paintSample(r);
      updateWhy();
      if (status) status.textContent = (r.from_cache ? "pre-run result, loaded in " : "computed live in ") +
        ((Date.now() - t0) / 1000).toFixed(1) + " s";
      showBanner(r);
      if (force) S.alerts = null;
    }).catch(function (e) {
      clearInterval(S.timer);
      if (host) host.innerHTML = UI.state("error", "This sample could not be processed", e.message);
    });
  }

  function ensureProvenance() {
    if (S.provenance) return Promise.resolve(S.provenance);
    return api("/api/adjudicate/provenance").then(function (p) { S.provenance = p; return p; })
      .catch(function () { return null; });
  }

  function invasiveSet() {
    var set = {};
    ((S.alerts && S.alerts.alerts) || []).forEach(function (a) { if (a.kind === "confirmed") set[a.species] = a.level; });
    return set;
  }

  function ensureAlerts() {
    if (S.alerts) return Promise.resolve(S.alerts);
    return api("/api/adjudicate/alerts").then(function (d) { S.alerts = d; return d; }).catch(function () { return null; });
  }

  function refVersion() {
    return S.provenance ? S.provenance.reference.reference_database_version : "not loaded";
  }

  function showBanner(r) {
    var b = document.getElementById("adjBanner");
    if (!b) return;
    var ev = (r.alerts || [])[0];
    if (!ev) {
      var poor = r.verdict === "Retake sample";
      b.innerHTML = '<div class="adj-banner none" role="status"><div class="adj-banner-level">' +
        (poor ? "NOT CHECKED" : "NO TRIGGER") + '</div><div class="adj-banner-main"><b>' +
        (poor ? "Invasive-species rule not evaluated: this sample is a retake."
              : "No listed invasive fish crossed the danger rule in this sample.") + "</b>" +
        '<div class="adj-banner-act">' + (poor
          ? "Too little usable DNA to say anything about invasive fish here."
          : "Rule: a species-level call of a listed invasive fish with at least 10 reads. Not seen here; that does not prove the water is free of them.") +
        "</div></div></div>";
      return;
    }
    b.innerHTML = '<div class="adj-banner ' + LEVEL_CLASS[ev.level] + '" role="alert">' +
      '<div class="adj-banner-level">' + esc(ev.level) + "</div>" +
      '<div class="adj-banner-main"><b>' + esc(ev.headline) + "</b>" +
      "<div>Pin " + pin(ev.pin) + " &middot; " + esc(ev.sample_label) + " &middot; " + UI.num(ev.reads) +
      " reads &middot; match score " + ev.confidence.toFixed(2) + "</div>" +
      '<div class="adj-banner-act">' + esc(ev.action) + "</div></div></div>";
  }

  function pin(p) {
    if (!p || p.latitude === null || p.latitude === undefined) return "not recorded";
    return Number(p.latitude).toFixed(4) + ", " + Number(p.longitude).toFixed(4);
  }

  function paintSample(r) {
    var host = document.getElementById("adjSample");
    if (!host) return;
    var s = r.summary, tot = Math.max(r.reads_total, 1);
    var vcls = r.verdict === "Retake sample" ? "invasive" : r.verdict === "Usable with caution" ? "medium" : "healthy";
    var seg = [["kept", "Kept", "var(--alert-healthy)"], ["unknown", "Unknown / review", "var(--alert-rare)"],
               ["dropped", "Dropped", "var(--alert-invasive)"]];

    var html = "";
    // verdict + quality summary
    html += UI.card(
      '<div class="card-head"><div><div class="hint">Sample quality summary</div>' +
      '<h2 class="adj-h2">' + esc(r.metadata.label) + "</h2></div>" +
      '<span class="badge ' + vcls + '">' + esc(r.verdict) + "</span></div>" +
      '<p class="adj-verdict">' + esc(r.verdict_reasons.join("; ")) + ".</p>" +
      '<div class="adj-stack" role="img" aria-label="Kept, unknown and dropped share of reads">' +
      seg.map(function (x) {
        var w = 100 * s[x[0]].reads / tot;
        return '<div style="width:' + w + "%;background:" + x[2] + '" title="' + x[1] + " " + w.toFixed(1) + '%"></div>';
      }).join("") + "</div>" +
      '<div class="kpis">' + seg.map(function (x) {
        return '<div class="kpi"><div class="k"><span class="adj-dot" style="background:' + x[2] + '"></span>' + x[1] +
          '</div><div class="v">' + pct(s[x[0]].reads / tot, 1) + '</div><div class="hint">' +
          UI.num(s[x[0]].reads) + " reads &middot; " + UI.num(s[x[0]].distinct) + " distinct sequences</div></div>";
      }).join("") + "</div>" +
      '<p class="hint">' + UI.num(r.reads_total) + " reads, " + UI.num(r.distinct_sequences) +
      " distinct sequences. Input read as " + esc(r.input_format.toUpperCase()) + " by content" +
      (r.quality_scores_available ? "" : " (FASTA: no base-quality scores, so the quality filter was skipped)") +
      ". Source: " + esc(r.metadata.bioproject) + " &middot; run " + esc(r.sample_id) +
      " &middot; collected " + esc(r.metadata.collection_date || "n/a") + ".</p>" +
      '<div class="card-foot">' +
      UI.button("Print officer report (PDF)", { variant: "primary", id: "adjPdf", icon: "download" }) +
      (r.dropped_csv ? '<a class="btn sm" href="/api/adjudicate/dropped/' + encodeURIComponent(r.sample_id) +
        '.csv">All dropped sequences (CSV)</a>' : "") +
      '<a class="btn sm" target="_blank" rel="noopener" href="' + esc(sourceUrl(r)) + '">Source record</a></div>');

    html += sourceCard(r);

    // dropped reasons
    var reasons = Object.keys(r.drop_reasons);
    html += UI.card('<div class="card-head"><h2 class="adj-h2">Why sequences were dropped</h2></div>' +
      (reasons.length ? reasonBars(r) : '<p class="hint">Nothing was dropped.</p>') +
      droppedTable(r));

    // species split
    html += UI.card('<div class="card-head"><h2 class="adj-h2">Species found and their shares</h2></div>' +
      speciesChart(r) + (r.metadata.role === "mixed" ? expectedBlock(r) : ""));

    // unknown queue
    html += UI.card('<div class="card-head"><h2 class="adj-h2">Review queue: sequences not called to a species</h2></div>' +
      unknownTable(r));

    // map
    html += UI.card('<div class="card-head"><h2 class="adj-h2">Where this sample was taken</h2></div>' +
      (r.metadata.latitude !== null && r.metadata.latitude !== undefined
        ? '<div id="adjMap" class="adj-map"></div>' +
          (r.metadata.coordinate_note ? '<p class="hint">Note: ' + esc(r.metadata.coordinate_note) + ".</p>" : "")
        : '<p class="hint">This record has no GPS pin, so it cannot be shown on the map.</p>'));

    host.innerHTML = html;
    document.getElementById("adjPdf").addEventListener("click", function () {
      window.open("/api/adjudicate/report/" + encodeURIComponent(r.sample_id) + ".pdf", "_blank");
    });
    drawMap(r);
    UI.animateIn && UI.animateIn(host);
  }

  function sourceUrl(r) { return "https://www.ebi.ac.uk/ena/browser/view/" + encodeURIComponent(r.sample_id); }

  function reasonBars(r) {
    var rows = Object.keys(r.drop_reasons).map(function (k) { return [k, r.drop_reasons[k]]; })
      .sort(function (a, b) { return b[1].reads - a[1].reads; });
    var mx = rows[0][1].reads || 1;
    return '<div class="adj-bars">' + rows.map(function (x) {
      return '<div class="adj-bar-row"><div class="adj-bar-label">' + esc(REASON_LABEL[x[0]] || x[0]) + "</div>" +
        '<div class="adj-bar-track"><div class="adj-bar-fill" style="width:' + (100 * x[1].reads / mx) +
        '%;background:var(--alert-invasive)"></div></div>' +
        '<div class="adj-bar-val">' + UI.num(x[1].reads) + " reads &middot; " + UI.num(x[1].distinct) + " seq</div></div>";
    }).join("") + "</div>";
  }

  function droppedTable(r) {
    var seen = {}, rows = [];
    (r.dropped || []).forEach(function (d) {
      if (rows.length < 8 && (seen[d.reason_code] || 0) < 2) { seen[d.reason_code] = (seen[d.reason_code] || 0) + 1; rows.push(d); }
    });
    if (!rows.length) return "";
    return '<details class="adj-details" open><summary>Examples with the written reason for each (' +
      UI.num(r.dropped_total_listed) + " dropped sequences are listed in the CSV)</summary>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>Reads</th><th>Sequence</th><th>Reason</th></tr></thead><tbody>' +
      rows.map(function (d) {
        return "<tr><td>" + UI.num(d.reads) + '</td><td class="mono adj-seq">' + esc(d.sequence.slice(0, 40)) +
          (d.sequence.length > 40 ? "&hellip;" : "") + "</td><td>" + esc(d.reason) + "</td></tr>";
      }).join("") + "</tbody></table></div></details>";
  }

  function speciesChart(r) {
    if (r.verdict === "Retake sample") {
      return UI.state("empty", "Retake sample", "Too little usable DNA to report which fish are here. Nothing is guessed.");
    }
    var rows = r.species.filter(function (x) { return x.status !== "trace"; }).slice(0, 14);
    if (!rows.length) return '<p class="hint">No species-level detections.</p>';
    var flagged = {};
    (r.alerts || []).forEach(function (a) { flagged[a.species] = a; (a.candidates || []).forEach(function (c) { flagged[c] = a; }); });
    var mx = rows[0].share || 1;
    var den = r.species.reduce(function (sum, x) { return sum + x.reads; }, 0);
    var complexReads = r.species.filter(function (x) { return x.kind === "complex"; })
      .reduce(function (sum, x) { return sum + x.reads; }, 0);
    var novelReads = Math.max(0, r.summary.unknown.reads - complexReads);
    var out = '<div class="adj-bars">' + rows.map(function (x) {
      var bad = x.kind === "species" ? !!flagged[x.species] : (x.members || []).some(function (m) { return flagged[m]; });
      var color = x.kind === "complex" ? "var(--alert-neutral)" : bad ? "var(--alert-invasive)" : "var(--accent-primary)";
      var shown = x.species.length > 58 ? x.species.slice(0, 55) + "… (" + (x.members || []).length + " species)" : x.species;
      return '<div class="adj-bar-row"><div class="adj-bar-label" title="' + esc(x.species) + '"><i>' + esc(shown) + "</i>" +
        (bad ? ' <span class="badge invasive">invasive</span>' : "") +
        (x.kind === "complex" ? ' <span class="badge info">cannot separate</span>' : "") + "</div>" +
        '<div class="adj-bar-track"><div class="adj-bar-fill" style="width:' + (100 * x.share / mx) +
        "%;background:" + color + '"></div></div>' +
        '<div class="adj-bar-val"><b>' + UI.num(x.reads) + "</b> / " + UI.num(den) + " = " + pct(x.share) +
        '<div class="hint">identity ' + pct(x.best_identity) + " &middot; score " + x.confidence.toFixed(2) + "</div></div></div>";
    }).join("") + "</div>";
    var trace = r.species.filter(function (x) { return x.status === "trace"; }).length;
    return out + '<div class="adj-note adj-denominator"><b>How the share is calculated:</b> reads of the species &divide; ' +
      UI.num(den) + " reads that could be named (species-level calls + groups the marker cannot separate). " +
      "Left out of that denominator: " + UI.num(r.summary.dropped.reads) + " dropped reads and " + UI.num(novelReads) +
      " reads of sequences too different from the reference to name, out of " + UI.num(r.reads_total) + " reads in the sample. " +
      "A share is a proportion of DNA reads, not a count of animals or their biomass.</div>" +
      '<p class="hint">Species with fewer than 10 reads (' + trace + ") are listed as trace, not as detections. " +
      "Two species whose 12S sequence cannot be told apart are shown together, never forced to one name. " + scoreNote() + "</p>";
  }

  function scoreNote() {
    return "Match score (0-1) is a heuristic built from identity and the gap to the next-best species: it falls 4 points per " +
      "1% of identity lost, is halved when a different species is almost as close, and is capped (0.99 for a species call, " +
      "0.60 for anything unconfirmed). It is not a calibrated probability.";
  }

  function dateCheck(text) {
    var m = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(String(text || ""));
    if (!m) return { badge: "missing", text: "no collection date recorded" };
    var precision = m[3] ? "day" : m[2] ? "month" : "year";
    var d = new Date(Number(m[1]), m[2] ? Number(m[2]) - 1 : 0, m[3] ? Number(m[3]) : 1);
    if (d.getTime() > Date.now()) return { badge: "high", text: "date is in the future" };
    return { badge: precision === "year" ? "medium" : "healthy",
             text: "not in the future; precision: " + precision +
               (precision === "year" ? " only, so it cannot be assigned to a season" : "") };
  }

  function coordCheck(m) {
    if (m.latitude === null || m.latitude === undefined) return { badge: "missing", text: "no GPS pin recorded" };
    var ok = Math.abs(m.latitude) <= 90 && Math.abs(m.longitude) <= 180;
    return { badge: ok ? (m.coordinate_note ? "medium" : "healthy") : "high",
             text: ok ? "inside valid ranges" + (m.coordinate_note ? "; low precision: " + m.coordinate_note : "")
                      : "outside valid latitude/longitude range" };
  }

  function checkBadge(c) {
    var label = { healthy: "ok", medium: "note", high: "problem", missing: "missing" }[c.badge] || c.badge;
    return '<span class="badge ' + c.badge + '">' + label + '</span> <span class="hint">' + esc(c.text) + "</span>";
  }

  function sourceCard(r) {
    var m = r.metadata, ena = "https://www.ebi.ac.uk/ena/browser/view/";
    var dc = dateCheck(m.collection_date), cc = coordCheck(m);
    function row(k, v) { return "<dt>" + esc(k) + "</dt><dd>" + v + "</dd>"; }
    return UI.card('<div class="card-head"><div><div class="hint">Where this sample comes from</div>' +
      '<h2 class="adj-h2">Source and metadata</h2></div></div>' +
      '<dl class="adj-dl">' +
        row("Dataset", '<a target="_blank" rel="noopener" href="' + ena + encodeURIComponent(m.bioproject) + '">' + esc(m.bioproject) + "</a> &middot; " + esc(m.dataset_title)) +
        row("Run / sample", '<a target="_blank" rel="noopener" href="' + ena + encodeURIComponent(r.sample_id) + '">' + esc(r.sample_id) + "</a>" +
            (m.biosample ? ' &middot; <a target="_blank" rel="noopener" href="' + ena + encodeURIComponent(m.biosample) + '">' + esc(m.biosample) + "</a>" : "") +
            " &middot; alias " + esc(m.alias || "-")) +
        row("Original file", '<span class="mono">' + esc(r.source_file || "-") + "</span> &middot; md5 <span class=\"mono\">" + esc(m.md5 || "-") + "</span>") +
        row("Marker / assay", esc(/12S|COI|16S/.exec(m.dataset_title || "") ? m.dataset_title : "see dataset record")) +
        row("Reference", esc(refVersion())) +
        row("Collected", esc(m.collection_date || "n/a") + " " + checkBadge(dc)) +
        row("Place / pin", esc(m.location || "n/a") + (m.latitude !== null && m.latitude !== undefined ? " (" + Number(m.latitude).toFixed(4) + ", " + Number(m.longitude).toFixed(4) + ")" : "") +
            " " + checkBadge(cc)) +
      "</dl>" +
      '<p class="hint">These checks read only this record\'s own fields. Cross-record checks (duplicate IDs, boundary, species spelling) are in the <b>Data guard</b> tab.</p>');
  }

  function expectedBlock(r) {
    var e = r.expected_check;
    if (!e) return "";
    if (!e.available) return '<div class="adj-note">' + esc(e.note) + "</div>";
    if (e.mode === "count_only") {
      return '<h3 class="adj-h3">Check against what the source says was mixed</h3><p class="hint">' + esc(e.source) + "</p>" +
        "<p><b>" + esc(e.verdict) + "</b> (plus " + e.unresolved_groups + " groups of species that 12S cannot separate)</p>" +
        '<div class="adj-note">' + esc(e.limits) + "</div>";
    }
    return '<h3 class="adj-h3">Check against the source composition</h3><p class="hint">' + esc(e.source) + "</p>" +
      '<p><b>' + esc(e.verdict) + "</b></p>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>Species</th><th>Expected</th><th>Observed</th><th>Result</th></tr></thead><tbody>' +
      e.rows.map(function (x) {
        return "<tr><td><i>" + esc(x.species) + "</i></td><td>" + (x.expected_share ? pct(x.expected_share) : "-") +
          "</td><td>" + pct(x.observed_share) + "</td><td>" + esc(x.status + (x.share_check ? " / " + x.share_check : "") + (x.note ? " - " + x.note : "")) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
  }

  function unknownTable(r) {
    var q = r.unknown_queue || [];
    if (!q.length) return '<p class="hint">Nothing needs review.</p>';
    var rows = q.slice(0, 12);
    return '<p class="hint">' + UI.num(q.length) + " sequences are not confirmed. Each shows its closest reference match, the " +
      "<b>percent identity</b> (a measured similarity, not a probability) and a heuristic match score capped at 0.60, so none can pass as confirmed.</p>" +
      '<div class="adj-note">Reference used: <b>' + esc(refVersion()) + "</b>. Aligned coverage is <b>not provided</b> " +
      "by the analysis (identity is measured over the whole read, so a short overlap lowers it instead of being hidden). " + scoreNote() + "</div>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>Reads</th><th>Closest match</th><th>Identity</th><th>Match score</th><th>Review state</th><th>Why unknown</th><th></th></tr></thead><tbody>' +
      rows.map(function (u) {
        var blast = "https://blast.ncbi.nlm.nih.gov/Blast.cgi?PROGRAM=blastn&PAGE_TYPE=BlastSearch&QUERY=" + encodeURIComponent(u.sequence);
        return "<tr><td>" + UI.num(u.reads) + "</td><td><i>" + esc(u.candidates && u.candidates.length > 1 ? u.candidates.join(" / ") : u.closest_match) +
          "</i></td><td>" + pct(u.identity) + "</td><td>" + u.confidence.toFixed(2) +
          '</td><td><span class="badge medium">' + esc(u.status || "needs review") + "</span></td><td>" + esc(u.reason) + '</td><td><a target="_blank" rel="noopener" href="' + blast + '">Check on NCBI</a></td></tr>';
      }).join("") + "</tbody></table></div>" +
      (q.length > rows.length ? '<p class="hint">Showing the 12 most abundant of ' + UI.num(q.length) + ".</p>" : "");
  }

  function drawMap(r) {
    var el = document.getElementById("adjMap");
    if (!el || !window.L) return;
    if (S.map) { S.map.remove(); S.map = null; }
    var lat = r.metadata.latitude, lon = r.metadata.longitude;
    var m = L.map(el).setView([lat, lon], 9);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap" }).addTo(m);
    var ev = (r.alerts || [])[0];
    var colour = ev ? (ev.level === "CRITICAL" ? "#d5405f" : ev.level === "HIGH" ? "#e0912f" : "#c9a400") : "#2f9e5b";
    L.circleMarker([lat, lon], { radius: 11, color: "#fff", weight: 2, fillColor: colour, fillOpacity: 1 }).addTo(m)
      .bindPopup("<b>" + esc(r.metadata.label) + "</b><br>" + (ev ? esc(ev.headline) : "No invasive fish flagged") +
        "<br>" + esc(r.metadata.collection_date));
    S.map = m;
    setTimeout(function () { m.invalidateSize(); }, 200);
  }

  /* ── data guard ─────────────────────────────────────────────────────── */

  function renderGuard(g) {
    var pc = g.post_check, rules = [
      ["duplicate_id", "Duplicate sample ID"], ["outside_boundary", "GPS pin outside boundary"],
      ["no_coordinates", "No GPS pin"], ["future_date", "Date in the future"], ["double_spelling", "Species, two spellings"]];
    var cards = rules.map(function (x) {
      var c = g.counts_by_rule[x[0]];
      var ex = g.decisions.filter(function (d) { return d.rule === x[0]; })[0];
      var n = c ? c.reject + c.merge : 0;
      return UI.card('<div class="card-head"><h3 class="adj-h3">' + x[1] + "</h3>" +
        '<span class="badge ' + (n ? "high" : "info") + '">' + (n ? n + (c.merge && !c.reject ? " merged" : c.merge ? " handled" : " rejected") : "not in data") + "</span></div>" +
        (ex ? '<p class="hint"><b>' + esc(ex.action) + ":</b> " + esc(ex.reason) +
          (ex.run_accession ? " (" + esc(ex.run_accession) + ")" : "") + "</p>"
            : '<p class="hint">The real records contained no such case, so there is nothing to show. The rule is still active.</p>'),
        { size: "sm" });
    }).join("");
    root().innerHTML =
      UI.card('<div class="card-head"><div><div class="hint">Real archive records, never edited</div>' +
        '<h2 class="adj-h2">Data guard</h2></div><span class="badge ' + (pc.clean ? "healthy" : "invasive") + '">' +
        (pc.clean ? "database clean" : "database NOT clean") + "</span></div>" +
        '<div class="kpis">' + UI.kpi("Records checked", UI.num(g.records_in)) +
        UI.kpi("Kept in clean store", UI.num(g.clean_count), { color: "accent" }) +
        UI.kpi("Rejected", UI.num(g.decisions.filter(function (d) { return d.action === "reject"; }).length)) +
        UI.kpi("Merged", UI.num(g.decisions.filter(function (d) { return d.action === "merge"; }).length)) + "</div>" +
        '<p class="hint">Source: ENA project PRJEB108476 (snapshot md5 ' + esc(g.records_snapshot_md5) + "). Boundary: <b>" +
        esc(g.boundary.name) + "</b> (" + esc(g.boundary.source) + "). Today = " + esc(g.today) + ".</p>" +
        '<p class="hint"><b>Post-check on the clean store:</b> ' + pc.duplicate_sample_ids + " duplicate IDs, " +
        pc.outside_boundary + " outside the boundary, " + pc.future_dated + " future-dated, " +
        pc.unmerged_double_spellings + " unmerged double spellings across " + pc.records_checked + " records.</p>") +
      '<div class="adj-grid">' + cards + "</div>" +
      UI.card('<h3 class="adj-h3">Every decision</h3><div class="table-wrap" style="max-height:340px;overflow:auto"><table class="data"><thead><tr><th>Rule</th><th>Action</th><th>Record</th><th>Reason</th></tr></thead><tbody>' +
        g.decisions.slice(0, 120).map(function (d) {
          return "<tr><td>" + esc(d.rule_label) + "</td><td>" + esc(d.action) + "</td><td class=\"mono\">" + esc(d.run_accession || "-") + "</td><td>" + esc(d.reason) + "</td></tr>";
        }).join("") + "</tbody></table></div><p class=\"hint\">Showing the first 120 of " + UI.num(g.decisions.length) + " decisions.</p>");
  }

  /* ── seasons ────────────────────────────────────────────────────────── */

  function renderSeasons(doc) {
    if (!doc.sites.length) {
      root().innerHTML = UI.state("empty", "No summer/winter pair", "No location in the processed samples has both seasons."); return;
    }
    root().innerHTML = '<div class="card sm"><div class="row"><label class="hint" for="adjSite">Location</label>' +
      '<select id="adjSite" class="adj-select">' + doc.sites.map(function (s, i) {
        return '<option value="' + i + '">' + esc(s.location) + "</option>"; }).join("") + "</select></div></div>" +
      '<div id="adjSeason" class="stack"></div>';
    var sel = document.getElementById("adjSite");
    sel.addEventListener("change", function () { paintSeason(doc, +sel.value, 0); });
    paintSeason(doc, 0, 0);
  }

  function paintSeason(doc, siteIdx, pos) {
    var site = doc.sites[siteIdx], host = document.getElementById("adjSeason");
    var cur = pos === 0 ? "summer" : "winter", other = pos === 0 ? "winter" : "summer";
    var rows = site.species;
    var inCur = rows.filter(function (r) { return r[cur + "_reads"] > 0; });
    var fresh = inCur.filter(function (r) { return r[other + "_reads"] === 0; });
    var missing = rows.filter(function (r) { return r[cur + "_reads"] === 0 && r[other + "_reads"] > 0; });
    var cs = site[cur], os = site[other];
    host.innerHTML =
      UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(site.location) + "</h2></div>" +
        '<div class="adj-slider"><span class="' + (pos === 0 ? "on" : "") + '">Summer ' + esc(site.summer.dates.join(", ")) + "</span>" +
        '<input type="range" min="0" max="1" step="1" value="' + pos + '" id="adjSeasonRange" aria-label="Season">' +
        '<span class="' + (pos === 1 ? "on" : "") + '">Winter ' + esc(site.winter.dates.join(", ")) + "</span></div>" +
        '<div class="kpis">' + UI.kpi("Species detected (" + cur + ")", cs.species_detected, { color: "accent" }) +
        UI.kpi("Species detected (" + other + ")", os.species_detected) +
        UI.kpi("Newly detected vs " + other, fresh.length) +
        UI.kpi("Not detected here, seen in " + other, missing.length) + "</div>" +
        '<p class="hint">' + cs.samples + " replicate sample(s) in " + cur + ", " + os.samples + " in " + other + ". " +
        esc(doc.not_absent_note) + "</p>" +
        '<p class="hint">Season rule (set in thresholds.json): ' + esc(JSON.stringify(doc.season_rule.value)) + ". " +
        esc(doc.season_rule.why) + "</p>" +
        seasonQuality(site) +
        '<div class="card-foot">' + UI.button("Print officer report for this site (PDF)", { variant: "primary", id: "adjSitePdf", icon: "download" }) +
        '<span class="hint">One page: animals, risk, source and dates, uncertainty, what to do.</span></div>' +
        '<div id="adjSeasonMap" class="adj-map short"></div>' +
        (site.coordinate_note ? '<p class="hint">Note: ' + esc(site.coordinate_note) + ".</p>" : "")) +
      UI.card('<div class="adj-two"><div><h3 class="adj-h3">Newly detected in ' + cur + "</h3>" + list(fresh, cur, true) + "</div>" +
        "<div><h3 class=\"adj-h3\">Seen in " + other + ", not detected in " + cur + "</h3>" + list(missing, other, false) + "</div></div>" +
        "<h3 class=\"adj-h3\">Detected in " + cur + " (all)</h3>" + list(inCur, cur, true));
    document.getElementById("adjSeasonRange").addEventListener("input", function (e) { paintSeason(doc, siteIdx, +e.target.value); });
    document.getElementById("adjSitePdf").addEventListener("click", function () {
      window.open("/api/adjudicate/site-report/" + encodeURIComponent(site.location) + ".pdf", "_blank");
    });
    if (window.L) {
      if (S.seasonMap) { S.seasonMap.remove(); S.seasonMap = null; }
      var el = document.getElementById("adjSeasonMap");
      if (site.latitude !== null && site.latitude !== undefined) {
        var m = L.map(el).setView([site.latitude, site.longitude], 8);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap" }).addTo(m);
        L.circleMarker([site.latitude, site.longitude], { radius: 12, color: "#fff", weight: 2,
          fillColor: pos === 0 ? "#e0912f" : "#4a78c4", fillOpacity: 1 }).addTo(m)
          .bindTooltip((pos === 0 ? "Summer: " : "Winter: ") + cs.species_detected + " species", { permanent: true });
        S.seasonMap = m; setTimeout(function () { m.invalidateSize(); }, 200);
      } else { el.outerHTML = '<p class="hint">No GPS pin recorded for this location.</p>'; }
    }
  }

  /* A same-site comparison is only fair if both seasons were read about equally well.
     Verdicts and usable reads come from the pre-run results; nothing is recomputed. */
  function seasonQuality(site) {
    var byId = {};
    ((S.index && S.index.samples) || []).forEach(function (x) { byId[x.sample_id] = x; });
    function agg(season) {
      var ids = site[season].sample_ids || [], kept = 0, verdicts = {};
      ids.forEach(function (id) {
        var x = byId[id]; if (!x) return;
        kept += x.summary.kept.reads;
        verdicts[x.verdict] = (verdicts[x.verdict] || 0) + 1;
      });
      return { kept: kept, verdicts: verdicts, n: ids.length };
    }
    var a = agg("summer"), b = agg("winter");
    function text(g) { return Object.keys(g.verdicts).map(function (k) { return g.verdicts[k] + " " + k; }).join(", ") || "n/a"; }
    var uneven = a.kept && b.kept ? Math.max(a.kept, b.kept) / Math.min(a.kept, b.kept) : 0;
    var notClean = Object.keys(a.verdicts).concat(Object.keys(b.verdicts)).some(function (k) { return k !== "Usable"; });
    if (!notClean && uneven < 2) return "";
    return '<div class="adj-note"><b>Read this comparison with care.</b> Summer samples: ' + esc(text(a)) + " (" + UI.num(a.kept) +
      " reads named). Winter samples: " + esc(text(b)) + " (" + UI.num(b.kept) + " reads named)." +
      (uneven >= 2 ? " Sequencing depth differs about " + uneven.toFixed(1) + "-fold." : "") +
      " A season with poorer reads can show fewer species because of the data, not because of the water.</div>";
  }

  function list(rows, season, showReads) {
    if (!rows.length) return '<p class="hint">None.</p>';
    var listed = invasiveSet();
    return '<ul class="adj-list">' + rows.map(function (r) {
      return "<li><i>" + esc(r.species) + "</i>" +
        (listed[r.species] ? ' <span class="badge invasive" title="Listed invasive fish; confirmed in an alert elsewhere in this project">invasive-listed</span>' : "") +
        " <span class=\"hint\">" + UI.num(r[season + "_reads"]) + " reads, " +
        r[season + "_replicates"] + " replicate(s)</span></li>"; }).join("") + "</ul>";
  }

  /* ── alerts ─────────────────────────────────────────────────────────── */

  function renderAlerts(d) {
    var rows = d.alerts;
    S.alerts = d;
    var pins = {};
    rows.forEach(function (a) {
      if (!a.pin || a.pin.latitude === null || a.pin.latitude === undefined) return;
      var key = a.pin.latitude + "," + a.pin.longitude;
      (pins[key] = pins[key] || { lat: a.pin.latitude, lon: a.pin.longitude, items: [] }).items.push(a);
    });
    var pinList = Object.keys(pins).map(function (k) { return pins[k]; });
    root().innerHTML = (pinList.length ? UI.card('<div class="card-head"><div><div class="hint">One marker per distinct pin; colour = most severe alert there</div>' +
      '<h2 class="adj-h2">Alert map</h2></div></div><div id="adjAlertMap" class="adj-map"></div>' +
      '<p class="hint">' + pinList.length + " pins. Samples whose source gave only a coarse coordinate share one pin.</p>") : "") +
      UI.card('<div class="card-head"><div><div class="hint">Dashboard banner + this log. No SMS or e-mail is sent.</div>' +
      '<h2 class="adj-h2">Alert log</h2></div></div>' +
      (rows.length ? '<div class="table-wrap"><table class="data"><thead><tr><th>Level</th><th>Alert</th><th>Pin</th><th>Sample</th><th>Reads</th><th>Analysis took</th><th>Alert after result</th></tr></thead><tbody>' +
        rows.map(function (a) {
          return '<tr><td><span class="badge ' + LEVEL_CLASS[a.level] + '">' + esc(a.level) + "</span></td><td>" + esc(a.headline) +
            "</td><td class=\"mono\">" + esc(pin(a.pin)) + "</td><td>" + esc(a.sample_label) + "</td><td>" + UI.num(a.reads) + "</td><td>" +
            (a.analysis_seconds === undefined ? "-" : a.analysis_seconds + " s") + "</td><td>" +
            (a.latency_seconds === null ? "-" : a.latency_seconds + " s") + "</td></tr>"; }).join("") + "</tbody></table></div>" +
        '<p class="hint">The alert is written within ' + d.latency_budget_seconds + ' s of the result being ready (budget); the analysis time is shown ' +
        "separately and is not hidden in that figure. Results are pre-run, so opening a sample shows its alert immediately. " +
        "Samples that triggered nothing are not listed: the rule was active but the source sample did not contain a listed invasive fish.</p>"
        : UI.state("empty", "No alerts yet", "No processed real sample crossed the danger rule. The rule is active; nothing is invented.")));
    drawAlertMap(pinList);
  }

  function drawAlertMap(pinList) {
    var el = document.getElementById("adjAlertMap");
    if (!el || !window.L) return;
    if (S.alertMap) { S.alertMap.remove(); S.alertMap = null; }
    var m = L.map(el);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap" }).addTo(m);
    var rank = { CRITICAL: 0, HIGH: 1, WATCH: 2 }, colour = { CRITICAL: "#d5405f", HIGH: "#e0912f", WATCH: "#c9a400" };
    var bounds = [];
    pinList.forEach(function (p) {
      var worst = p.items.slice().sort(function (a, b) { return rank[a.level] - rank[b.level]; })[0];
      var seen = {}, lines = [];
      p.items.forEach(function (a) {
        var k = a.level + a.species;
        if (!seen[k] && lines.length < 6) { seen[k] = 1; lines.push(esc(a.level) + ": " + esc(a.headline)); }
      });
      L.circleMarker([p.lat, p.lon], { radius: 10, color: "#fff", weight: 2, fillColor: colour[worst.level], fillOpacity: 1 })
        .addTo(m).bindPopup("<b>" + p.lat.toFixed(4) + ", " + p.lon.toFixed(4) + "</b><br>" + lines.join("<br>"));
      bounds.push([p.lat, p.lon]);
    });
    if (bounds.length === 1) m.setView(bounds[0], 8); else m.fitBounds(bounds, { padding: [30, 30], maxZoom: 9 });
    S.alertMap = m;
    setTimeout(function () { m.invalidateSize(); }, 200);
  }

  /* ── numbers & sources ──────────────────────────────────────────────── */

  function loadWhy() {
    root().innerHTML = UI.card(UI.skeleton("line", 4));
    Promise.all([api("/api/adjudicate/thresholds"), api("/api/adjudicate/provenance")]).then(function (v) {
      var th = v[0], pr = v[1];
      root().innerHTML =
        UI.card('<h2 class="adj-h2">Every threshold, in one file, with its reason</h2><p class="hint">bioradar/adjudicate/thresholds.json</p>' +
          '<div class="table-wrap"><table class="data"><thead><tr><th>Setting</th><th>Value</th><th>Why this value</th></tr></thead><tbody>' +
          Object.keys(th).map(function (k) {
            var val = typeof th[k].value === "object" ? JSON.stringify(th[k].value) : th[k].value + " " + (th[k].unit || "");
            return "<tr><td class=\"mono\">" + esc(k) + "</td><td>" + esc(val) + "</td><td>" + esc(th[k].why) + "</td></tr>"; }).join("") +
          "</tbody></table></div>") +
        UI.card('<h2 class="adj-h2">Reference list</h2><p>' + esc(pr.reference.name) + " &middot; " + esc(pr.reference.reference_database_version) +
          "</p><p class=\"hint\">" + UI.num(pr.reference.amplicons_extracted) + " sequences, " + UI.num(pr.reference.distinct_species) +
          " species. Query: <code>" + esc(pr.reference.ncbi_query) + "</code>. " + esc(pr.reference.note) + "</p>") +
        UI.card('<h2 class="adj-h2">Real datasets used</h2>' + pr.manifest.datasets.map(function (d) {
          return '<p><b>' + esc(d.bioproject) + "</b> &middot; " + esc(d.title) + " &middot; " + esc(d.centre) +
            '<br><span class="hint">' + esc(d.used_for) + " &middot; " + d.runs.length + ' run(s) &middot; <a target="_blank" rel="noopener" href="' +
            esc(d.ena_url) + '">ENA record</a> &middot; ' + esc(d.publication) + "</span></p>"; }).join("") +
          '<p class="hint">' + esc(pr.manifest.mates_downloaded) + "</p>");
    }).catch(function (e) { root().innerHTML = UI.state("error", "Could not load", e.message); });
  }
})();
