/* Visuals for the pipeline Results page: charts first, text second.

   Pure SVG / CSS, no library and no network. Colours come from the design tokens (and the
   existing categorical palette for phyla), so light/dark and any retheme apply for free.
   Every chart carries a plain-text equivalent (role="img" + aria-label, and the numbers are
   printed next to the marks) so nothing depends on colour alone.

   Data in: the run's `report` (phyla_breakdown, top_species) and, when loaded, the run's
   `analysis` (per-sample reads, richness, Shannon). Nothing is recomputed from raw reads. */

(function (global) {
  "use strict";

  var UI = global.BioRadarUI;
  var I18n = global.BioRadarI18n;
  var esc = UI.esc;

  var TXT = {
    en: {
      "vz.glance": "Who lives here, at a glance",
      "vz.phylum": "Share of DNA by animal group",
      "vz.phylaWord": "groups",
      "vz.other": "Other groups",
      "vz.topSpecies": "Most common animals",
      "vz.reads": "DNA pieces",
      "vz.noSpecies": "No named animals to chart.",
      "vz.confidence": "How sure is each identification?",
      "vz.confHint": "How many kinds fall in each band of sureness (from 0 to 1).",
      "vz.taxa": "kinds",
      "vz.samples": "DNA pieces in each sample",
      "vz.named": "named",
      "vz.unassigned": "no match found",
      "vz.samplesHint": "Each bar is one sample. The green part matched a known animal. The grey part did not.",
      "vz.richness": "Variety in each sample",
      "vz.richHint": "The bar shows how many kinds of animals. The number after it is the Shannon score. A higher score means a more even mix.",
      "vz.species": "kinds",
      "vz.shannon": "Shannon",
      "vz.loading": "Loading the charts for each sample",
      "vz.briefing": "Written summary and extra notes",
      "vz.briefingHint": "A short summary, dangers, forecasts and extras. Open to read.",
      "vz.table": "Full list of animals",
      "vz.risk.invasive": "Harmful animal alert", "vz.risk.protected": "Protected animals", "vz.risk.stable": "Steady",
      "vz.band.low": "under 0.70", "vz.band.mid": "0.70 to 0.85", "vz.band.high": "0.85 to 0.95", "vz.band.top": "0.95 and above"
    },
    hi: {
      "vz.glance": "एक नज़र में: यहाँ कौन रहता है",
      "vz.phylum": "जानवरों के समूह के अनुसार DNA का हिस्सा",
      "vz.phylaWord": "समूह",
      "vz.other": "अन्य समूह",
      "vz.topSpecies": "सबसे आम जानवर",
      "vz.reads": "DNA टुकड़े",
      "vz.noSpecies": "चार्ट के लिए कोई नाम पाया जानवर नहीं।",
      "vz.confidence": "हर पहचान कितनी पक्की है?",
      "vz.confHint": "हर भरोसे-श्रेणी (0 से 1) में कितने प्रकार आते हैं।",
      "vz.taxa": "प्रकार",
      "vz.samples": "हर नमूने में DNA टुकड़े",
      "vz.named": "नामित",
      "vz.unassigned": "कोई मेल नहीं मिला",
      "vz.samplesHint": "हर पट्टी एक नमूना है। हरा भाग किसी जानी हुई प्रजाति से मिला। धूसर भाग नहीं मिला।",
      "vz.richness": "हर नमूने में विविधता",
      "vz.richHint": "पट्टी बताती है कि कितने प्रकार के जानवर हैं। उसके बाद की संख्या Shannon स्कोर है। ज़्यादा स्कोर का मतलब ज़्यादा बराबर मिश्रण।",
      "vz.species": "प्रकार",
      "vz.shannon": "Shannon",
      "vz.loading": "हर नमूने के चार्ट खुल रहे हैं",
      "vz.briefing": "लिखित सारांश और अतिरिक्त बातें",
      "vz.briefingHint": "छोटा सारांश, खतरे, पूर्वानुमान और अन्य बातें। पढ़ने के लिए खोलें।",
      "vz.table": "जानवरों की पूरी सूची",
      "vz.risk.invasive": "हानिकारक जानवर की चेतावनी", "vz.risk.protected": "संरक्षित जानवर", "vz.risk.stable": "स्थिर",
      "vz.band.low": "0.70 से कम", "vz.band.mid": "0.70 से 0.85", "vz.band.high": "0.85 से 0.95", "vz.band.top": "0.95 और अधिक"
    }
  };
  if (I18n && I18n.addStrings) { I18n.addStrings("en", TXT.en); I18n.addStrings("hi", TXT.hi); }

  function T(key) { return I18n ? I18n.t(key, TXT.en[key] || key) : (TXT.en[key] || key); }
  function pct(x, d) { return (100 * x).toFixed(d === undefined ? 0 : d) + "%"; }

  /* ── donut ──────────────────────────────────────────────────────────── */

  function donut(items, centerValue, centerLabel) {
    var total = items.reduce(function (s, i) { return s + i.value; }, 0);
    if (!total) return "";
    var R = 56, C = 2 * Math.PI * R, offset = 0;
    var rings = items.map(function (it) {
      var len = C * it.value / total;
      var circle = '<circle cx="80" cy="80" r="' + R + '" fill="none" stroke="' + it.color + '" stroke-width="26"' +
        ' stroke-dasharray="' + len.toFixed(2) + " " + (C - len).toFixed(2) + '" stroke-dashoffset="' + (-offset).toFixed(2) +
        '" transform="rotate(-90 80 80)"><title>' + esc(it.label) + ": " + UI.num(it.value) + " (" + pct(it.value / total, 1) + ")</title></circle>";
      offset += len;
      return circle;
    }).join("");
    var legend = items.map(function (it) {
      return '<li><span class="vz-swatch" style="background:' + it.color + '"></span><span class="vz-leg-name">' + esc(it.label) +
        '</span><span class="vz-leg-val">' + pct(it.value / total, 1) + "</span></li>";
    }).join("");
    var label = items.map(function (it) { return it.label + " " + pct(it.value / total, 0); }).join(", ");
    return '<div class="vz-donut-wrap"><svg class="vz-donut" viewBox="0 0 160 160" role="img" aria-label="' + esc(label) + '">' +
      '<circle cx="80" cy="80" r="' + R + '" fill="none" stroke="var(--surface-pressed)" stroke-width="26"></circle>' + rings +
      '<text x="80" y="78" text-anchor="middle" class="vz-donut-num">' + esc(centerValue) + '</text>' +
      '<text x="80" y="96" text-anchor="middle" class="vz-donut-lbl">' + esc(centerLabel) + "</text></svg>" +
      '<ul class="vz-legend">' + legend + "</ul></div>";
  }

  /* ── horizontal bars ────────────────────────────────────────────────── */

  function hbars(rows, opts) {
    opts = opts || {};
    var mx = rows.reduce(function (m, r) { return Math.max(m, r.value); }, 0) || 1;
    return '<div class="vz-bars">' + rows.map(function (r) {
      return '<div class="vz-row"><div class="vz-name" title="' + esc(r.label) + '"><i>' + esc(r.label) + "</i></div>" +
        '<div class="vz-track"><div class="vz-fill" style="width:' + (100 * r.value / mx).toFixed(1) + "%;background:" + r.color + ";opacity:" +
        (r.opacity === undefined ? 1 : r.opacity) + '"></div></div><div class="vz-val">' + (opts.fmt ? opts.fmt(r) : UI.num(r.value)) + "</div></div>";
    }).join("") + "</div>";
  }

  function stacked(rows) {
    var mx = rows.reduce(function (m, r) { return Math.max(m, r.total); }, 0) || 1;
    return '<div class="vz-bars">' + rows.map(function (r) {
      var w = 100 * r.total / mx, named = r.total ? 100 * r.named / r.total : 0;
      return '<div class="vz-row"><div class="vz-name" title="' + esc(r.label) + '">' + esc(r.label) + "</div>" +
        '<div class="vz-track"><div class="vz-stack" style="width:' + w.toFixed(1) + '%"><span class="vz-seg named" style="width:' + named.toFixed(1) +
        '%"></span><span class="vz-seg none" style="width:' + (100 - named).toFixed(1) + '%"></span></div></div>' +
        '<div class="vz-val">' + UI.num(r.total) + " <small>" + pct(1 - (r.total ? r.named / r.total : 0), 0) + "</small></div></div>";
    }).join("") + "</div>";
  }

  /* ── confidence histogram ───────────────────────────────────────────── */

  function histogram(species) {
    var bins = [
      { key: "vz.band.low", n: 0, color: "var(--alert-neutral)" },
      { key: "vz.band.mid", n: 0, color: "var(--alert-rare)" },
      { key: "vz.band.high", n: 0, color: "var(--accent-primary)" },
      { key: "vz.band.top", n: 0, color: "var(--alert-healthy)" }
    ];
    species.forEach(function (s) {
      var c = Number(s.confidence || s.max_confidence || 0);
      bins[c < 0.70 ? 0 : c < 0.85 ? 1 : c < 0.95 ? 2 : 3].n++;
    });
    var mx = bins.reduce(function (m, b) { return Math.max(m, b.n); }, 0) || 1;
    var label = bins.map(function (b) { return T(b.key) + ": " + b.n; }).join(", ");
    return '<div class="vz-hist" role="img" aria-label="' + esc(label) + '">' + bins.map(function (b) {
      return '<div class="vz-col"><div class="vz-colval">' + b.n + '</div><div class="vz-colbar"><span style="height:' + (100 * b.n / mx).toFixed(1) +
        "%;background:" + b.color + '"></span></div><div class="vz-collbl">' + esc(T(b.key)) + "</div></div>";
    }).join("") + "</div>";
  }

  /* ── public ─────────────────────────────────────────────────────────── */

  function card(title, hint, body, cls) {
    return '<div class="card vz-card ' + (cls || "") + '"><h2>' + esc(title) + "</h2>" +
      (hint ? '<p class="hint vz-hint">' + esc(hint) + "</p>" : "") + body + "</div>";
  }

  function overview(report, runId) {
    var phyla = (report.phyla_breakdown || []).slice();
    var top = (report.top_species || []).filter(function (s) { return !s.placeholder; }).slice(0, 8);
    var all = report.top_species || [];

    var main = phyla.slice(0, 5), rest = phyla.slice(5);
    var items = main.map(function (p) { return { label: p.name, value: p.reads, color: UI.categorical(p.name) }; });
    if (rest.length) items.push({ label: T("vz.other"), value: rest.reduce(function (s, p) { return s + p.reads; }, 0), color: "var(--alert-neutral)" });

    var html = '<section class="vz" aria-label="' + esc(T("vz.glance")) + '"><div class="vz-grid">' +
      card(T("vz.phylum"), "", donut(items, report.phyla, T("vz.phylaWord")), "vz-donutcard") +
      card(T("vz.topSpecies"), "", top.length ? hbars(top.map(function (s) {
        return { label: s.name, value: s.reads, color: UI.categorical(s.phylum), opacity: 0.55 + 0.45 * Math.min(1, Number(s.confidence || 0)) };
      }), { fmt: function (r) { return UI.num(r.value) + " <small>" + esc(T("vz.reads")) + "</small>"; } })
        : '<p class="hint">' + esc(T("vz.noSpecies")) + "</p>") +
      card(T("vz.confidence"), T("vz.confHint"), all.length ? histogram(all) : '<p class="hint">' + esc(T("vz.noSpecies")) + "</p>") +
      "</div>" +
      '<div class="vz-grid" id="vz-samples-' + esc(runId) + '">' +
        card(T("vz.samples"), "", '<p class="hint">' + esc(T("vz.loading")) + "…</p>") + "</div></section>";
    return html;
  }

  function samples(analysis) {
    var rows = (analysis.samples || []).slice().sort(function (a, b) { return b.total_reads - a.total_reads; }).slice(0, 10);
    if (!rows.length) return "";
    var reads = stacked(rows.map(function (s) {
      return { label: s.sample_id, total: s.total_reads, named: Math.max(0, s.total_reads - (s.unassigned_reads || 0)) };
    }));
    var legend = '<div class="vz-key"><span><i class="vz-swatch named"></i>' + esc(T("vz.named")) + '</span><span><i class="vz-swatch none"></i>' + esc(T("vz.unassigned")) + "</span></div>";
    var mx = rows.reduce(function (m, s) { return Math.max(m, s.species_count); }, 0) || 1;
    var rich = '<div class="vz-bars">' + rows.slice().sort(function (a, b) { return b.species_count - a.species_count; }).map(function (s) {
      return '<div class="vz-row"><div class="vz-name" title="' + esc(s.sample_id) + '">' + esc(s.sample_id) + "</div>" +
        '<div class="vz-track"><div class="vz-fill" style="width:' + (100 * s.species_count / mx).toFixed(1) + '%;background:var(--accent-primary)"></div></div>' +
        '<div class="vz-val">' + s.species_count + " <small>" + esc(T("vz.shannon")) + " " + Number(s.shannon).toFixed(2) + "</small></div></div>";
    }).join("") + "</div>";
    return card(T("vz.samples"), T("vz.samplesHint"), legend + reads) + card(T("vz.richness"), T("vz.richHint"), rich);
  }

  global.BioRadarVisuals = { overview: overview, samples: samples, text: T };
})(window);
