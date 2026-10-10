/* Charts — flat, high-contrast, colour-blind safe. No chart library.

   Recharts is the guide's assumption and would be fine in a bundled app. Here
   the only chart that needs real geometry is the radar, and a radar chart is
   about forty lines of trigonometry — importing 90 kB to avoid writing them
   would be the wrong trade in an app served from a scientific image.

   Everything here is FLAT by rule: no neumorphic shadow ever touches a data
   mark. Soft shadows on a chart series is the anti-pattern that makes
   neumorphic dashboards unreadable. */

(function (global) {
  "use strict";

  var UI = global.BioRadarUI;

  /* ── Biodiversity comparison radar ────────────────────────────────────

     Ranked #1 in the gap analysis: lowest effort, highest visual reward, and
     it answers the question biodiversity monitoring actually asks — not "what
     is at this site" but "how does this site compare".

     Six dimensions, every one computed from data this pipeline really produces.
     The guide's list names CBI and an Ecosystem Health Index; those belong to
     the analytics layer that is not built yet, so they are absent rather than
     faked. `dimensions` is data, so when that layer lands they are added by
     passing two more entries — no change here. */

  var DIMENSIONS = [
    { key: "richness",  label: "Species richness", hint: "Named species detected" },
    { key: "shannon",   label: "Shannon H'",       hint: "Diversity, accounting for evenness" },
    { key: "evenness",  label: "Evenness",         hint: "Pielou's J' — is one taxon dominating?" },
    { key: "unique",    label: "Unique taxa",      hint: "Found here and nowhere else in this survey" },
    { key: "coverage",  label: "Reference cover",  hint: "Share of reads the database could place" },
    { key: "pressure",  label: "Watchlist load",   hint: "Read share from invasive or introduced taxa" }
  ];

  /* Site metrics from the analysis object. Kept out of the drawing code so it
     can be tested and so the drawing code stays about geometry. */
  function siteMetrics(analysis, watchlistNames) {
    var bySite = {};
    var listed = {};
    (watchlistNames || []).forEach(function (n) { listed[String(n).toLowerCase()] = true; });

    (analysis.samples || []).forEach(function (sample) {
      var site = bySite[sample.site_id] || (bySite[sample.site_id] = {
        site_id: sample.site_id, samples: 0, reads: 0, assigned: 0,
        shannon: 0, species: {}, listedReads: 0
      });
      site.samples += 1;
      site.reads += sample.total_reads || 0;
      site.assigned += (sample.total_reads || 0) - (sample.unassigned_reads || 0);
      site.shannon += sample.shannon || 0;
    });

    (analysis.species || []).forEach(function (entry) {
      var sites = entry.sites || [];
      sites.forEach(function (siteId) {
        var site = bySite[siteId];
        if (!site) return;
        site.species[entry.name] = true;
        if (listed[String(entry.name).toLowerCase()]) {
          // Read counts are per-species across the whole survey, so dividing by
          // the number of sites is an approximation. It is stated here rather
          // than presented as exact.
          site.listedReads += (entry.reads || 0) / sites.length;
        }
      });
    });

    var siteIds = Object.keys(bySite);
    siteIds.forEach(function (id) {
      var site = bySite[id];
      var others = {};
      siteIds.forEach(function (other) {
        if (other !== id) Object.keys(bySite[other].species).forEach(function (n) { others[n] = true; });
      });
      var names = Object.keys(site.species);
      site.richness = names.length;
      site.unique = names.filter(function (n) { return !others[n]; }).length;
      site.shannon = site.samples ? site.shannon / site.samples : 0;
      // Pielou's J' = H' / ln(S). Undefined for a single species, where
      // evenness is not a meaningful question — reported as 0, not as 1.
      site.evenness = site.richness > 1 ? site.shannon / Math.log(site.richness) : 0;
      site.coverage = site.reads ? site.assigned / site.reads : 0;
      site.pressure = site.reads ? site.listedReads / site.reads : 0;
    });

    return siteIds.map(function (id) { return bySite[id]; })
                  .sort(function (a, b) { return a.site_id.localeCompare(b.site_id); });
  }

  /* Each axis is scaled against the maximum across the selected sites, so the
     chart shows relative position. An absolute scale would flatten every site
     into the middle and make the comparison useless — which is the whole point
     of the chart. */
  function normalise(sites) {
    var max = {};
    DIMENSIONS.forEach(function (dim) {
      max[dim.key] = sites.reduce(function (m, s) {
        return Math.max(m, Number(s[dim.key]) || 0);
      }, 0);
    });
    return sites.map(function (site) {
      var values = {};
      DIMENSIONS.forEach(function (dim) {
        var top = max[dim.key];
        values[dim.key] = top > 0 ? (Number(site[dim.key]) || 0) / top : 0;
      });
      return { site_id: site.site_id, values: values, raw: site };
    });
  }

  function formatRaw(key, value) {
    if (key === "coverage" || key === "pressure") return (value * 100).toFixed(1) + "%";
    if (key === "shannon" || key === "evenness") return Number(value).toFixed(2);
    return String(Math.round(value));
  }

  function radar(sites, options) {
    options = options || {};
    if (!sites || sites.length < 1) return "";

    var size = 460, cx = size / 2, cy = size / 2, radius = size * 0.34;
    var axes = DIMENSIONS.length;
    var rings = 4;
    var series = normalise(sites);

    function point(index, value) {
      // Start at 12 o'clock and go clockwise: a radar that starts at 3 o'clock
      // reads as rotated to anybody who has seen one before.
      var angle = (Math.PI * 2 * index) / axes - Math.PI / 2;
      return [cx + Math.cos(angle) * radius * value, cy + Math.sin(angle) * radius * value];
    }

    var parts = [];
    parts.push('<svg class="radar-svg" viewBox="0 0 ' + size + " " + size +
               '" role="img" aria-label="Radar chart comparing ' + series.length + ' sites">');

    for (var ring = 1; ring <= rings; ring++) {
      var polygon = [];
      for (var a = 0; a < axes; a++) polygon.push(point(a, ring / rings).join(","));
      parts.push('<polygon class="radar-web" points="' + polygon.join(" ") + '"/>');
    }

    DIMENSIONS.forEach(function (dim, index) {
      var end = point(index, 1);
      parts.push('<line class="radar-axis" x1="' + cx + '" y1="' + cy +
                 '" x2="' + end[0].toFixed(1) + '" y2="' + end[1].toFixed(1) + '"/>');

      var label = point(index, 1.19);
      var anchor = Math.abs(label[0] - cx) < 6 ? "middle" : (label[0] > cx ? "start" : "end");
      parts.push('<text class="radar-label" x="' + label[0].toFixed(1) + '" y="' +
                 (label[1] + 4).toFixed(1) + '" text-anchor="' + anchor + '">' +
                 UI.esc(dim.label) + "</text>");
    });

    for (var r = 1; r <= rings; r++) {
      var tick = point(0, r / rings);
      parts.push('<text class="radar-tick" x="' + (tick[0] + 5) + '" y="' +
                 (tick[1] + 3).toFixed(1) + '">' + Math.round((r / rings) * 100) + "%</text>");
    }

    series.forEach(function (entry, index) {
      var colour = UI.categoricalAt(index);
      var polygon = DIMENSIONS.map(function (dim, i) {
        return point(i, entry.values[dim.key]).join(",");
      });
      parts.push('<polygon class="radar-series" points="' + polygon.join(" ") +
                 '" fill="' + colour + '" stroke="' + colour + '"/>');
      DIMENSIONS.forEach(function (dim, i) {
        var p = point(i, entry.values[dim.key]);
        parts.push('<circle class="radar-point" cx="' + p[0].toFixed(1) + '" cy="' +
                   p[1].toFixed(1) + '" r="3.5" fill="' + colour + '"><title>' +
                   UI.esc(entry.site_id + " — " + dim.label + ": " +
                          formatRaw(dim.key, entry.raw[dim.key])) + "</title></circle>");
      });
    });

    parts.push("</svg>");

    var legend = '<div class="legend">' + series.map(function (entry, index) {
      return '<div class="legend-item"><span class="legend-swatch" style="background:' +
        UI.categoricalAt(index) + '"></span><span>' + UI.esc(entry.site_id) + "</span></div>";
    }).join("") + '<div class="hint" style="margin-top:12px">' +
      "Each axis is scaled to the highest value among the selected sites, so the " +
      "chart shows relative standing rather than absolute counts. Hover a point " +
      "for the real number.</div></div>";

    return '<div class="radar-wrap">' + parts.join("") + legend + "</div>" +
      (options.table === false ? "" : comparisonTable(series));
  }

  function comparisonTable(series) {
    var head = "<tr><th>Site</th>" + DIMENSIONS.map(function (d) {
      return '<th class="num" title="' + UI.esc(d.hint) + '">' + UI.esc(d.label) + "</th>";
    }).join("") + "</tr>";
    var body = series.map(function (entry, index) {
      return "<tr><td><span class=\"dot-swatch\" style=\"background:" +
        UI.categoricalAt(index) + '"></span>' + UI.esc(entry.site_id) + "</td>" +
        DIMENSIONS.map(function (d) {
          return '<td class="num">' + UI.esc(formatRaw(d.key, entry.raw[d.key])) + "</td>";
        }).join("") + "</tr>";
    }).join("");
    return '<div class="table-wrap" style="margin-top:24px"><table class="data"><thead>' +
      head + "</thead><tbody>" + body + "</tbody></table></div>";
  }

  /**
   * Make the radar draw itself in.
   *
   * The dash length has to be the real perimeter of each polygon, and that is
   * only knowable once the SVG is in the document -- `getTotalLength()` needs
   * layout. So the CSS animation reads `--len`, and this sets it per series
   * after mount. A guessed constant would either clip short outlines or leave
   * long ones visibly waiting.
   */
  function animateRadar(root) {
    if (!root || UI.prefersReducedMotion()) return;
    var svg = root.querySelector(".radar-svg");
    if (!svg) return;

    svg.querySelectorAll(".radar-series").forEach(function (polygon, index) {
      var length = 1200;
      try { length = Math.ceil(polygon.getTotalLength()) || 1200; } catch (e) { /* jsdom */ }
      polygon.style.setProperty("--len", length);
      polygon.style.setProperty("--i", index);
    });
    svg.querySelectorAll(".radar-point").forEach(function (point, index) {
      point.style.setProperty("--i", Math.floor(index / DIMENSIONS.length));
    });
  }

  global.BioRadarCharts = {
    DIMENSIONS: DIMENSIONS,
    siteMetrics: siteMetrics,
    normalise: normalise,
    radar: radar,
    animateRadar: animateRadar
  };
})(window);
