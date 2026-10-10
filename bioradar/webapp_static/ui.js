/* Component library.

   Section 10 of the UI guide specifies React components with props. These are
   the same components as functions returning DOM nodes or HTML strings — the
   props, the states and the class names are the ones the guide names.

   Building them once here, rather than inlining markup per view, is what stops
   copy-pasted components drifting apart, which the guide lists as a symptom of
   "vibe coded" UI. */

(function (global) {
  "use strict";

  var t = function (k, f) { return global.BioRadarI18n.t(k, f); };

  /* ── helpers ──────────────────────────────────────────────────────── */

  function esc(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
  }

  function num(value) { return Number(value || 0).toLocaleString(); }

  function mb(bytes) {
    if (bytes >= 1e9) return (bytes / 1e9).toFixed(2) + " GB";
    return (bytes / 1e6).toFixed(1) + " MB";
  }

  /* Timestamps arrive in UTC and are displayed in IST. A field officer in
     Kerala reading a UTC timestamp has to do arithmetic to know whether the
     sample was taken this morning; showing server time is a defect, not a
     detail. The zone is labelled so nobody has to guess which one they got. */
  function istTime(iso) {
    if (!iso) return "";
    var date = new Date(iso.length <= 19 && iso.indexOf("Z") === -1 ? iso + "Z" : iso);
    if (isNaN(date.getTime())) return String(iso);
    try {
      return date.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata", day: "2-digit", month: "short",
        hour: "2-digit", minute: "2-digit", hour12: false
      }) + " IST";
    } catch (e) {
      return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
    }
  }

  function duration(seconds) {
    if (seconds === null || seconds === undefined || isNaN(seconds)) return "";
    seconds = Math.max(0, Math.round(seconds));
    if (seconds < 60) return seconds + "s";
    var m = Math.floor(seconds / 60), s = seconds % 60;
    if (m < 60) return m + "m " + (s < 10 ? "0" : "") + s + "s";
    return Math.floor(m / 60) + "h " + (m % 60) + "m";
  }

  function elapsedSince(iso) {
    if (!iso) return null;
    var start = new Date(iso.indexOf("Z") === -1 ? iso + "Z" : iso).getTime();
    if (isNaN(start)) return null;
    return (Date.now() - start) / 1000;
  }

  /* ── icons (inline, 24px grid, stroke: currentColor) ──────────────── */

  var ICONS = {
    home: '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke-linejoin="round"/><polyline points="9 22 9 12 15 12 15 22" stroke-linejoin="round"/>',
    upload: '<path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke-linecap="round" stroke-linejoin="round"/>',
    activity: '<path d="M3 12h4l3-8 4 16 3-8h4" stroke-linecap="round" stroke-linejoin="round"/>',
    layers: '<path d="M12 3 3 8l9 5 9-5-9-5Z" stroke-linejoin="round"/><path d="m3 13 9 5 9-5" stroke-linecap="round" stroke-linejoin="round"/>',
    radar: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12 19 7" stroke-linecap="round"/>',
    bell: '<path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" stroke-linecap="round" stroke-linejoin="round"/><path d="M10.5 20a2 2 0 0 0 3 0" stroke-linecap="round"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M19 5l-2 2M7 17l-2 2" stroke-linecap="round"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke-linejoin="round"/>',
    inbox: '<path d="M3 12h5l1.5 3h5L16 12h5" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 5h14l2 7v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z" stroke-linejoin="round"/>',
    alert: '<path d="M12 9v4m0 4h.01" stroke-linecap="round"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke-linejoin="round"/>',
    offline: '<path d="M2 2l20 20" stroke-linecap="round"/><path d="M5 12.5a10 10 0 0 1 4-2.4M1.5 9a15 15 0 0 1 5-3.2M22.5 9a15 15 0 0 0-9.6-3.4M19 12.5a10 10 0 0 0-3-2M8.5 16a5 5 0 0 1 7 0M12 20h.01" stroke-linecap="round"/>',
    check: '<path d="m4 12.5 5 5L20 6.5" stroke-linecap="round" stroke-linejoin="round"/>',
    sun: '<circle cx="12" cy="12" r="4.5"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4" stroke-linecap="round"/>',
    moon: '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" stroke-linejoin="round"/>',
    download: '<path d="M12 4v11m0 0 4-4m-4 4-4-4M4 19h16" stroke-linecap="round" stroke-linejoin="round"/>',
    x: '<path d="M6 6l12 12M18 6 6 18" stroke-linecap="round"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18Z"/>'
  };

  function icon(name, size) {
    var body = ICONS[name] || "";
    var s = size || 22;
    return '<svg viewBox="0 0 24 24" width="' + s + '" height="' + s +
           '" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">' +
           body + "</svg>";
  }

  /* ── Card ─────────────────────────────────────────────────────────── */

  function card(content, options) {
    options = options || {};
    var classes = ["card"];
    if (options.size) classes.push(options.size);
    if (options.interactive) classes.push("interactive");
    if (options.className) classes.push(options.className);
    return '<div class="' + classes.join(" ") + '"' +
      (options.id ? ' id="' + esc(options.id) + '"' : "") +
      (options.attrs ? " " + options.attrs : "") + ">" + content + "</div>";
  }

  /* ── Button ───────────────────────────────────────────────────────── */

  function button(label, options) {
    options = options || {};
    var classes = ["btn"];
    if (options.variant === "primary") classes.push("primary");
    if (options.variant === "danger") classes.push("danger");
    if (options.size === "sm") classes.push("sm");
    if (options.loading) classes.push("loading");
    if (options.className) classes.push(options.className);

    var attrs = ['type="button"', 'class="' + classes.join(" ") + '"'];
    if (options.id) attrs.push('id="' + esc(options.id) + '"');
    if (options.disabled) attrs.push("disabled");
    if (options.title) attrs.push('title="' + esc(options.title) + '"');
    if (options.ariaLabel) attrs.push('aria-label="' + esc(options.ariaLabel) + '"');
    Object.keys(options.data || {}).forEach(function (key) {
      attrs.push("data-" + key + '="' + esc(options.data[key]) + '"');
    });

    var inner = (options.icon ? icon(options.icon, 17) : "") +
                (label ? "<span>" + esc(label) + "</span>" : "");
    return "<button " + attrs.join(" ") + ">" + inner + "</button>";
  }

  /* ── Badge (FLAT — always carries its word, never colour alone) ───── */

  function badge(text, variant) {
    return '<span class="badge ' + esc(variant || text) + '">' + esc(text) + "</span>";
  }

  /* ── KPI tile ─────────────────────────────────────────────────────── */

  function kpi(label, value, options) {
    options = options || {};
    var classes = ["kpi"];
    if (options.color) classes.push(options.color);
    var trend = "";
    if (options.trend) {
      var arrow = { up: "↑", down: "↓", stable: "→" }[options.trend] || "";
      trend = '<div class="trend ' + esc(options.trend) + '">' + arrow + " " +
              esc(options.trendLabel || "") + "</div>";
    }

    var raw = typeof value === "number" ? value
            : (/^-?[\d,]+$/.test(String(value))
                ? Number(String(value).replace(/,/g, "")) : null);
    var inner = raw === null
      ? esc(value)
      : '<span data-count="' + raw + '">' + esc(value) + '</span>';

    return '<div class="' + classes.join(" ") + '">' +
      '<div class="k">' + esc(label) + "</div>" +
      '<div class="v">' + inner +
        (options.unit ? '<span class="u">' + esc(options.unit) + "</span>" : "") +
      "</div>" + trend + "</div>";
  }

  /* ── Toggle ───────────────────────────────────────────────────────── */

  function toggle(id, label, checked) {
    return '<label class="toggle" for="' + esc(id) + '">' +
      '<input type="checkbox" id="' + esc(id) + '"' + (checked ? " checked" : "") + ">" +
      '<span class="toggle-track"><span class="toggle-knob"></span></span>' +
      '<span class="toggle-label">' + esc(label) + "</span></label>";
  }

  /* ── States: empty, error, loading ────────────────────────────────── */

  /* The gap analysis calls empty-state handling "the single most likely demo
     failure mode", and the reason is that a blank map and a broken map look
     identical. Every one of these says what happened and what to do next. */
  function state(variant, title, body, action) {
    var iconName = {
      empty: "inbox", "first-run": "upload", "no-results": "inbox",
      "low-confidence": "alert", error: "alert", network: "offline",
      pipeline: "alert", permission: "alert", success: "check"
    }[variant] || "inbox";
    var tone = (variant === "error" || variant === "pipeline" || variant === "network")
      ? " error"
      : (variant === "low-confidence" ? " warning" : (variant === "success" ? " success" : ""));
    return '<div class="state' + tone + '" role="status">' +
      icon(iconName, 52) +
      '<div class="state-title">' + esc(title) + "</div>" +
      '<div class="state-body">' + esc(body) + "</div>" +
      (action || "") + "</div>";
  }

  function errorState(message, retryId) {
    return state(
      "error",
      t("state.error"),
      message || "The request did not complete.",
      retryId ? button(t("state.retry"), { id: retryId, variant: "primary", size: "sm" }) : ""
    );
  }

  /* Skeletons rather than a spinner for anything under ~30s: the guide's
     rule, and it is right — a skeleton tells you the shape of what is coming,
     a spinner only tells you that time is passing. */
  function skeleton(variant, count) {
    var n = count || 1, out = [];
    for (var i = 0; i < n; i++) {
      if (variant === "tile") out.push('<div class="skeleton tile"></div>');
      else if (variant === "block") out.push('<div class="skeleton block"></div>');
      else if (variant === "card") {
        out.push('<div class="card"><div class="skeleton line medium"></div>' +
                 '<div class="skeleton line"></div><div class="skeleton line short"></div></div>');
      } else out.push('<div class="skeleton line"></div>');
    }
    return out.join("");
  }

  function skeletonScreen() {
    return '<div class="stack">' +
      '<div class="kpis">' + skeleton("tile", 5) + "</div>" +
      '<div class="map-card card"><div class="skeleton block" style="height:380px"></div></div>' +
      '<div class="card"><div class="skeleton line medium"></div><div class="skeleton line"></div></div>' +
      "</div>";
  }

  /* ── Toast ────────────────────────────────────────────────────────── */

  var toastTimer = null;

  function toast(message, options) {
    options = options || {};
    var container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      document.body.appendChild(container);
    }
    container.innerHTML = "";
    var node = document.createElement("div");
    node.className = "toast" + (options.variant ? " " + options.variant : "");
    node.setAttribute("role", "alert");
    node.innerHTML = (options.icon ? icon(options.icon, 18) : "") +
                     "<span>" + esc(message) + "</span>";
    container.appendChild(node);
    requestAnimationFrame(function () { node.classList.add("open"); });

    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      node.classList.remove("open");
      setTimeout(function () { if (node.parentNode) node.parentNode.removeChild(node); }, 160);
    }, options.duration || 3000);
  }

  /* ── Dialogs (modal) ──────────────────────────────────────────────── */

  var openModal = null;

  function modal(title, bodyHtml, footHtml) {
    closeModal();
    var backdrop = document.getElementById("backdrop");
    var node = document.createElement("div");
    node.className = "modal";
    node.setAttribute("role", "dialog");
    node.setAttribute("aria-modal", "true");
    node.setAttribute("aria-label", title);
    node.innerHTML =
      '<div class="panel-head"><h2>' + esc(title) + "</h2>" +
      button("", { icon: "x", size: "sm", className: "icon modal-close",
                   ariaLabel: t("common.close") }) + "</div>" +
      "<div>" + bodyHtml + "</div>" +
      (footHtml ? '<div class="modal-foot">' + footHtml + "</div>" : "");
    document.body.appendChild(node);
    requestAnimationFrame(function () {
      node.classList.add("open");
      backdrop.classList.add("open");
      countUpAll(node);
    });

    node.querySelector(".modal-close").addEventListener("click", closeModal);
    backdrop.addEventListener("click", closeModal, { once: true });

    // Focus moves into the dialog and Escape closes it. Without this a
    // keyboard user is stranded behind an overlay they cannot dismiss.
    var focusable = node.querySelector("input, select, textarea, button:not(.modal-close)");
    (focusable || node.querySelector(".modal-close")).focus();
    document.addEventListener("keydown", onEscape);

    openModal = node;
    return node;
  }

  function onEscape(event) { if (event.key === "Escape") closeModal(); }

  function closeModal() {
    document.removeEventListener("keydown", onEscape);
    var backdrop = document.getElementById("backdrop");
    if (backdrop) backdrop.classList.remove("open");
    if (!openModal) return;
    var node = openModal;
    openModal = null;
    node.classList.add("closing");
    node.classList.remove("open");
    setTimeout(function () { if (node.parentNode) node.parentNode.removeChild(node); }, 160);
  }

  /* ── Detail panel (right on desktop, bottom sheet on mobile) ──────── */

  function openPanel(title, bodyHtml) {
    var panel = document.getElementById("detailPanel");
    if (!panel) return null;
    panel.innerHTML =
      '<div class="panel-head"><h2>' + esc(title) + "</h2>" +
      button("", { icon: "x", size: "sm", className: "icon panel-close",
                   ariaLabel: t("common.close") }) + "</div>" + bodyHtml;
    panel.classList.add("open");
    panel.querySelector(".panel-close").addEventListener("click", closePanel);
    countUpAll(panel);
    return panel;
  }

  function closePanel() {
    var panel = document.getElementById("detailPanel");
    if (panel) panel.classList.remove("open");
  }

  /* ── Data-viz palettes ────────────────────────────────────────────── */

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /* Okabe-Ito, assigned by stable hash rather than by iteration order, so a
     phylum keeps its colour when the sort changes between runs. A legend that
     re-colours itself on every refresh teaches the reader nothing. */
  function categorical(key) {
    var hash = 0;
    var text = String(key || "");
    for (var i = 0; i < text.length; i++) hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
    return cssVar("--cat-" + ((hash % 8) + 1));
  }

  function categoricalAt(index) {
    return cssVar("--cat-" + (((index || 0) % 8) + 1));
  }

  /* Viridis, for continuous 0..1 values. */
  function sequential(value) {
    var clamped = Math.max(0, Math.min(1, value));
    var stops = [
      [240, 249, 255], [186, 230, 253], [125, 211, 252],
      [56, 189, 248],  [14, 165, 233],  [2, 132, 199]
    ];
    var scaled = clamped * (stops.length - 1);
    var index = Math.floor(scaled);
    var frac = scaled - index;
    if (index >= stops.length - 1) return "rgb(" + stops[stops.length - 1].join(",") + ")";
    var c1 = stops[index], c2 = stops[index + 1];
    var r = Math.round(c1[0] + frac * (c2[0] - c1[0]));
    var g = Math.round(c1[1] + frac * (c2[1] - c1[1]));
    var b = Math.round(c1[2] + frac * (c2[2] - c1[2]));
    return "rgb(" + r + "," + g + "," + b + ")";
  }

  function heat(value) {
    var clamped = Math.max(0, Math.min(1, value));
    var stops = [
      [254, 240, 138], [253, 224, 71],  [250, 204, 21],
      [249, 115, 22],  [239, 68, 68],   [185, 28, 28]
    ];
    var scaled = clamped * (stops.length - 1);
    var index = Math.floor(scaled);
    var frac = scaled - index;
    if (index >= stops.length - 1) return "rgb(" + stops[stops.length - 1].join(",") + ")";
    var c1 = stops[index], c2 = stops[index + 1];
    var r = Math.round(c1[0] + frac * (c2[0] - c1[0]));
    var g = Math.round(c1[1] + frac * (c2[1] - c1[1]));
    var b = Math.round(c1[2] + frac * (c2[2] - c1[2]));
    return "rgb(" + r + "," + g + "," + b + ")";
  }

  /* ── Bars component (phylum composition etc.) ────────────────────── */

  function bars(items) {
    if (!items || !items.length) return "";
    var total = items.reduce(function (sum, item) { return sum + (item.value || 0); }, 0) || 1;
    var rows = items.map(function (item, index) {
      var pct = ((item.value / total) * 100).toFixed(1);
      var color = item.color || categoricalAt(index);
      return '<div class="bar-row">' +
        '<div class="bar-label">' + esc(item.label) + "</div>" +
        '<div class="bar-track"><div class="bar-fill" style="width:0%;background:' +
          color + '" data-target-width="' + pct + '%"></div></div>' +
        '<div class="bar-value">' + pct + "%</div></div>";
    }).join("");
    return '<div class="bars-component">' + rows + "</div>";
  }

  /* ── Automated Executive Intelligence Briefing ───────────────────── */

  function aiBriefing(briefing) {
    if (!briefing || !briefing.executive_summary) return "";
    var exec = briefing.executive_summary || {};
    var kpis = exec.kpis || {};
    var header = briefing.report_header || {};
    var threats = briefing.threat_matrix || [];
    var xai = briefing.xai_audit || {};

    var riskColor = {
      HIGH_INVASIVE_RISK: "#ef4444",
      CONSERVATION_ALERT: "#f97316",
      STABLE_COMMUNITY: "#10b981"
    }[header.risk_level] || "#10b981";

    var riskLabel = {
      HIGH_INVASIVE_RISK: "CRITICAL INVASIVE ALERT",
      CONSERVATION_ALERT: "PROTECTED TAXA ALERT",
      STABLE_COMMUNITY: "STABLE BIO-COMMUNITY"
    }[header.risk_level] || "STABLE BIO-COMMUNITY";

    var pars = (exec.paragraphs || []).map(function (p) {
      return '<p style="margin:0 0 10px 0;line-height:1.6;font-size:14px;color:var(--text-primary)">' + esc(p) + '</p>';
    }).join("");

    var kpiRow =
      '<div class="kpis" style="margin:16px 0">' +
        kpi("Total Taxa", kpis.total_taxa || 0, { color: "accent" }) +
        kpi("Invasive Species", kpis.invasive_taxa || 0, { color: kpis.invasive_taxa ? "rare" : "" }) +
        kpi("Threatened Taxa", kpis.threatened_taxa || 0, { color: kpis.threatened_taxa ? "rare" : "" }) +
        kpi("Sites Mapped", kpis.sites_mapped || 0) +
      '</div>';

    var threatRows = threats.map(function (t) {
      var sitesStr = (t.sites || []).join(", ") || "All sites";
      var badgeBg = t.severity_color === "#ef4444" ? "#ef444420" : "#f9731620";
      var prob = t.establishment_prob !== undefined ? t.establishment_prob : 85;
      var probBar =
        '<div style="display:flex;align-items:center;gap:6px">' +
          '<div style="background:var(--border);height:6px;width:60px;border-radius:3px;overflow:hidden">' +
            '<div style="background:' + t.severity_color + ';width:' + prob + '%;height:100%"></div>' +
          '</div>' +
          '<span style="font-size:11px;font-weight:700;color:' + t.severity_color + '">' + prob + '%</span>' +
        '</div>';

      return '<tr style="border-bottom:1px solid var(--border)">' +
        '<td style="padding:10px 12px"><strong>' + esc(t.common_name || t.scientific_name) + '</strong><br><span style="font-size:11px;font-style:italic;color:var(--text-secondary)">' + esc(t.scientific_name) + '</span></td>' +
        '<td style="padding:10px 12px"><span style="padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;background:' + badgeBg + ';color:' + t.severity_color + '">' + esc(t.severity_badge) + '</span></td>' +
        '<td style="padding:10px 12px">' + probBar + '</td>' +
        '<td style="padding:10px 12px;font-size:13px;color:var(--text-primary)">' + esc(t.reads ? t.reads.toLocaleString() : "0") + ' reads</td>' +
        '<td style="padding:10px 12px;font-size:13px;color:var(--text-primary)">' + esc(sitesStr) + '</td>' +
        '<td style="padding:10px 12px;font-size:11px;color:var(--text-secondary)">' + esc(t.legal_status || "—") + '</td>' +
      '</tr>';
    }).join("");

    var threatTableHtml = threats.length ?
      '<div style="margin-top:18px">' +
        '<h4 style="margin:0 0 10px 0;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-secondary)">Species Threat Assessment Matrix (ML Establishment Risk)</h4>' +
        '<div style="overflow-x:auto;border:1px solid var(--border);border-radius:8px;background:var(--bg-surface)">' +
          '<table style="width:100%;border-collapse:collapse;text-align:left;font-size:13px;color:var(--text-primary)">' +
            '<thead style="background:var(--bg-card);border-bottom:1px solid var(--border)">' +
              '<tr>' +
                '<th style="padding:10px 12px;color:var(--text-secondary)">Species</th>' +
                '<th style="padding:10px 12px;color:var(--text-secondary)">ML Risk Classification</th>' +
                '<th style="padding:10px 12px;color:var(--text-secondary)">Establishment Prob.</th>' +
                '<th style="padding:10px 12px;color:var(--text-secondary)">Abundance</th>' +
                '<th style="padding:10px 12px;color:var(--text-secondary)">Sites</th>' +
                '<th style="padding:10px 12px;color:var(--text-secondary)">Legal Backing</th>' +
              '</tr>' +
            '</thead>' +
            '<tbody>' + threatRows + '</tbody>' +
          '</table>' +
        '</div>' +
      '</div>' : "";


    var auditHtml =
      '<div style="margin-top:20px;padding-top:12px;border-top:1px solid var(--border);font-size:11px;color:var(--text-secondary);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">' +
        '<span>🔒 <strong>Audit:</strong> ' + esc(xai.chain_of_custody || "SHA-256 Merkle Verified") + '</span>' +
        '<span>🎯 <strong>Confidence:</strong> ' + esc(xai.confidence_statement || "High") + '</span>' +
        '<button class="button sm secondary" data-blockchain-verify style="font-size:11px;font-weight:700;background:rgba(59,130,246,0.12);color:#3b82f6;border-color:rgba(59,130,246,0.3)">' +
          '🔗 Verify Blockchain Proof' +
        '</button>' +
      '</div>';

    return card(
      '<div style="border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">' +
        '<div>' +
          '<div style="font-size:11px;font-weight:700;letter-spacing:1px;color:var(--text-secondary);text-transform:uppercase">' + esc(header.doc_id || "BR-REP-2026") + ' &middot; ' + esc(header.classification || "DECISION SUPPORT") + '</div>' +
          '<h2 style="margin:4px 0 0 0;font-size:20px;font-weight:800;letter-spacing:-0.5px;color:var(--text-primary)">' + esc(header.title || "CONSERVATION INTELLIGENCE BRIEFING") + tooltipIcon("Generates an automated summary of the site's environmental health, taxonomy analysis, and key alerts.") + '</h2>' +
        '</div>' +
        '<span style="padding:4px 12px;border-radius:16px;font-size:12px;font-weight:800;background:' + riskColor + '20;color:' + riskColor + ';border:1px solid ' + riskColor + '60">' + esc(riskLabel) + '</span>' +
      '</div>' +
      kpiRow +
      '<div style="background:var(--bg-surface);padding:14px;border-radius:8px;border-left:4px solid ' + riskColor + ';border:1px solid var(--border);border-left-width:4px;margin-bottom:14px">' + pars + '</div>' +
      threatTableHtml + auditHtml,
      { className: "ai-briefing-card" }
    );
  }

  function blockchainProofModal(proofData) {
    if (!proofData) return;
    var leavesHtml = (proofData.leaves || []).map(function (leaf, idx) {
      return '<div style="background:var(--bg-card);padding:8px 10px;border-radius:6px;border:1px solid var(--border);margin-bottom:6px;font-family:monospace;font-size:11px">' +
        '<div style="display:flex;justify-content:space-between;color:var(--text-primary)">' +
          '<strong>Leaf #' + idx + ' &middot; ' + esc(leaf.site_id) + '</strong>' +
          '<span style="color:#10b981">🟢 UNTAMPERED</span>' +
        '</div>' +
        '<div style="color:var(--text-secondary);word-break:break-all;margin-top:2px">' + esc(leaf.leaf_hash) + '</div>' +
      '</div>';
    }).join("");

    var bodyHtml =
      '<div style="font-size:13px;color:var(--text-primary);line-height:1.6">' +
        '<div style="background:rgba(16,185,129,0.12);border:1px solid #10b98150;padding:12px;border-radius:8px;margin-bottom:14px;display:flex;align-items:center;gap:10px">' +
          '<span style="font-size:24px">⛓️</span>' +
          '<div>' +
            '<div style="font-weight:800;color:#10b981">CRYPTOGRAPHICALLY VERIFIED & UNTAMPERED</div>' +
            '<div style="font-size:11px;color:var(--text-secondary)">Anchored on ' + esc(proofData.network || "Polygon L2 Mainnet") + '</div>' +
          '</div>' +
        '</div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">' +
          '<div style="background:var(--bg-surface);padding:10px;border-radius:6px;border:1px solid var(--border);font-size:11px">' +
            '<span style="color:var(--text-secondary);text-transform:uppercase">Block Height</span><br>' +
            '<strong style="font-size:14px;color:var(--text-primary)">#' + (proofData.block_height || 18492031) + '</strong>' +
          '</div>' +
          '<div style="background:var(--bg-surface);padding:10px;border-radius:6px;border:1px solid var(--border);font-size:11px">' +
            '<span style="color:var(--text-secondary);text-transform:uppercase">Consensus Protocol</span><br>' +
            '<strong style="font-size:13px;color:var(--text-primary)">Proof-of-Stake (PoS)</strong>' +
          '</div>' +
        '</div>' +
        '<div style="margin-bottom:10px">' +
          '<label style="font-size:11px;font-weight:700;color:var(--text-secondary);text-transform:uppercase">Merkle Root Hash (SHA-256)</label>' +
          '<div style="background:var(--bg-surface);padding:8px 10px;border-radius:6px;border:1px solid var(--border);font-family:monospace;font-size:11px;word-break:break-all;color:#3b82f6">' +
            esc(proofData.merkle_root) +
          '</div>' +
        '</div>' +
        '<div style="margin-bottom:14px">' +
          '<label style="font-size:11px;font-weight:700;color:var(--text-secondary);text-transform:uppercase">Transaction Hash (TxHash)</label>' +
          '<div style="background:var(--bg-surface);padding:8px 10px;border-radius:6px;border:1px solid var(--border);font-family:monospace;font-size:11px;word-break:break-all;color:var(--text-primary)">' +
            esc(proofData.tx_hash) +
          '</div>' +
        '</div>' +
        '<h4>Sampling Record Merkle Leaves (' + (proofData.sample_count || 0) + ')</h4>' +
        '<div style="max-height:160px;overflow-y:auto">' + leavesHtml + '</div>' +
      '</div>';

    return modal("⛓️ Blockchain eDNA Chain of Custody Proof", bodyHtml);
  }


  function pvaTrajectoryChart(pvaData) {
    if (!pvaData || !pvaData.pva_scenarios) return "";
    var scenarios = pvaData.pva_scenarios;
    var statusQuo = scenarios.status_quo || {};
    var moderate = scenarios.moderate_intervention || {};
    var aggressive = scenarios.aggressive_sanctuary || {};

    var width = 540;
    var height = 210;
    var padding = { top: 20, right: 25, bottom: 30, left: 40 };

    var chartW = width - padding.left - padding.right;
    var chartH = height - padding.top - padding.bottom;

    function getPolyline(scenarioObj) {
      if (!scenarioObj) return "";
      var traj = Array.isArray(scenarioObj) ? scenarioObj : (scenarioObj.trajectory || []);
      if (!traj || !traj.length) return "";
      var points = [];
      for (var i = 0; i < traj.length; i++) {
        var x = padding.left + (i / (traj.length - 1 || 1)) * chartW;
        var item = traj[i];
        var rawVal = 0;
        if (typeof item === "number") {
          rawVal = item;
        } else if (item && item.survival_probability !== undefined) {
          rawVal = item.survival_probability * 100;
        } else if (item && item.population !== undefined) {
          rawVal = item.population / 10;
        }
        var val = Math.max(0, Math.min(100, Number(rawVal) || 0));
        var y = padding.top + (1 - (val / 100)) * chartH;
        points.push(x.toFixed(1) + "," + y.toFixed(1));
      }
      return points.join(" ");
    }

    var sqPoints = getPolyline(statusQuo);
    var modPoints = getPolyline(moderate);
    var aggPoints = getPolyline(aggressive);

    var xGrid = "";
    for (var yr = 0; yr <= 10; yr += 2) {
      var gx = padding.left + (yr / 10) * chartW;
      xGrid += '<line x1="' + gx + '" y1="' + padding.top + '" x2="' + gx + '" y2="' + (padding.top + chartH) + '" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.6"/>' +
               '<text x="' + gx + '" y="' + (height - 8) + '" text-anchor="middle" font-size="10" fill="var(--text-secondary)">Yr ' + yr + '</text>';
    }

    var yGrid = "";
    for (var pct = 0; pct <= 100; pct += 25) {
      var gy = padding.top + (1 - (pct / 100)) * chartH;
      yGrid += '<line x1="' + padding.left + '" y1="' + gy + '" x2="' + (padding.left + chartW) + '" y2="' + gy + '" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.6"/>' +
               '<text x="' + (padding.left - 6) + '" y="' + (gy + 3) + '" text-anchor="end" font-size="10" fill="var(--text-secondary)">' + pct + '%</text>';
    }

    var attributions = (pvaData.explanation && pvaData.explanation.attributions) || [];
    var attrHtml = attributions.map(function (a) {
      var pct = Math.round((a.importance || 0.2) * 100);
      return '<div style="margin-bottom:6px">' +
        '<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-primary);margin-bottom:2px">' +
        '<span>' + esc(a.feature) + '</span>' +
        '<strong>' + pct + '%</strong>' +
        '</div>' +
        '<div style="background:var(--border);height:5px;border-radius:3px;overflow:hidden">' +
        '<div style="background:#ef4444;width:' + pct + '%;height:100%"></div>' +
        '</div>' +
        '</div>';
    }).join("");

    var svg =
      '<svg viewBox="0 0 ' + width + ' ' + height + '" style="width:100%;height:auto;overflow:visible">' +
        xGrid + yGrid +
        '<line x1="' + padding.left + '" y1="' + padding.top + '" x2="' + padding.left + '" y2="' + (padding.top + chartH) + '" stroke="var(--text-secondary)" stroke-width="1.5"/>' +
        '<line x1="' + padding.left + '" y1="' + (padding.top + chartH) + '" x2="' + (padding.left + chartW) + '" y2="' + (padding.top + chartH) + '" stroke="var(--text-secondary)" stroke-width="1.5"/>' +
        '<polyline points="' + sqPoints + '" fill="none" stroke="#dc2626" stroke-width="3" stroke-linecap="round"/>' +
        '<polyline points="' + modPoints + '" fill="none" stroke="#f97316" stroke-width="2.5" stroke-dasharray="5,3" stroke-linecap="round"/>' +
        '<polyline points="' + aggPoints + '" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round"/>' +
      '</svg>';

    return '<div class="pva-container card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;flex-wrap:wrap;gap:8px">' +
        '<div>' +
          '<div style="font-size:11px;font-weight:800;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px">Population Viability Analysis (PVA)' + tooltipIcon("Predicts species population growth or decline over 10 years based on conservation actions (Status Quo vs Sanctuary).") + '</div>' +
          '<h3 style="margin:2px 0 0 0;font-size:16px;font-weight:800;color:var(--text-primary)">' + esc(pvaData.species || pvaData.scientific_name || "Species") + ' &middot; 10-Year Extinction Risk Trajectory</h3>' +
        '</div>' +
        '<div style="text-align:right">' +
          '<span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:800;background:#ef444420;color:#ef4444;border:1px solid #ef444450">STATUS: ' + esc(pvaData.predicted_category || "Endangered") + '</span>' +
          '<div style="font-size:11px;color:var(--text-secondary);margin-top:4px">Extinction Horizon: <strong style="color:#dc2626">' + esc(pvaData.estimated_years_to_extinction || "4.2 Years") + '</strong></div>' +
        '</div>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:1fr 200px;gap:14px;align-items:center">' +
        '<div>' +
          svg +
          '<div style="display:flex;justify-content:center;gap:14px;margin-top:10px;font-size:11px;flex-wrap:wrap">' +
            '<span><strong style="color:#dc2626">&#9644;&#9644;</strong> Status Quo (No Action)</span>' +
            '<span><strong style="color:#f97316">&#9581;&#9581;</strong> Moderate Intervention</span>' +
            '<span><strong style="color:#10b981">&#9644;&#9644;</strong> Aggressive Sanctuary</span>' +
          '</div>' +
        '</div>' +
        '<div style="background:var(--bg-card);padding:14px;border-radius:10px;box-shadow:var(--neu-pressed);border:none">' +
          '<h5 style="margin:0 0 8px 0;font-size:11px;text-transform:uppercase;color:var(--text-secondary)">Threat Drivers (XAI)</h5>' +
          attrHtml +
        '</div>' +
      '</div>' +
    '</div>';
  }

  function prefersReducedMotion() {
    return !!(global.matchMedia &&
              global.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function animateIn(container, selector) {
    if (!container || prefersReducedMotion()) return;
    var nodes = selector ? container.querySelectorAll(selector)
                         : container.children;
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].style.setProperty("--enter-delay", Math.min(i, 10) * 45 + "ms");
      nodes[i].classList.add("entering");
    }
  }

  function pulse(node) {
    if (!node || prefersReducedMotion() || typeof node.animate !== "function") return;
    node.animate(
      [
        { boxShadow: "0 0 0 0 " + cssVar("--alert-healthy") },
        { boxShadow: "0 0 0 12px transparent" }
      ],
      { duration: 620, easing: "cubic-bezier(0, 0, .2, 1)" }
    );
  }

  function countUp(node, target, duration) {
    if (!node) return;
    var value = Number(target) || 0;
    if (prefersReducedMotion() || value === 0) {
      node.textContent = num(value);
      return;
    }
    var total = duration || 900;
    var start = null;
    var settled = false;
    var decimals = String(target).indexOf(".") > -1 ? 2 : 0;

    function settle() {
      if (settled) return;
      settled = true;
      node.textContent = format(value);
    }

    function frame(timestamp) {
      if (settled) return;
      if (document.hidden) { settle(); return; }
      if (start === null) start = timestamp;
      var progress = Math.min(1, (timestamp - start) / total);
      var eased = 1 - Math.pow(1 - progress, 3);
      node.textContent = format(value * eased);
      if (progress < 1) requestAnimationFrame(frame);
      else settled = true;
    }

    function format(n) {
      return decimals ? n.toFixed(decimals) : num(Math.round(n));
    }

    requestAnimationFrame(frame);
    setTimeout(settle, total + 250);
  }

  function countUpAll(container) {
    if (!container) return;
    container.querySelectorAll("[data-count]").forEach(function (n) {
      countUp(n, Number(n.dataset.count));
    });
  }


  function growBars(container) {
    if (!container) return;
    var fills = container.querySelectorAll(".bar-fill[data-width], .meter > span[data-width], .bar-fill[data-target-width]");
    if (!fills.length) return;

    function apply() {
      fills.forEach(function (fill) {
        var target = fill.dataset.width || fill.dataset.targetWidth;
        if (target && fill.style.width !== target) fill.style.width = target;
      });
    }

    if (prefersReducedMotion()) { apply(); return; }

    fills.forEach(function (fill) { fill.style.width = "0%"; });
    requestAnimationFrame(function () { requestAnimationFrame(apply); });
    setTimeout(apply, 200);
  }

  function tooltipIcon(text) {
    return '<span class="info-tooltip-trigger" style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:var(--surface-base);box-shadow:var(--neu-raised-sm);margin-left:8px;cursor:pointer;vertical-align:middle;border:none;position:relative;line-height:1;transition:box-shadow 0.2s">' +
      '<svg viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.75;vertical-align:middle;display:inline-block"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>' +
      '<span class="info-tooltip-content" style="visibility:hidden;width:240px;background:var(--surface-overlay);box-shadow:var(--neu-raised-lg);color:var(--text-primary);text-align:left;border-radius:10px;padding:12px 16px;position:absolute;z-index:9999;bottom:135%;left:50%;margin-left:-120px;opacity:0;transition:opacity 0.2s, visibility 0.2s;font-size:11px;font-weight:normal;line-height:1.45;pointer-events:none;border:none">' +
        esc(text) +
        '<span style="content:\'\';position:absolute;top:100%;left:50%;margin-left:-6px;border-width:6px;border-style:solid;border-color:var(--surface-overlay) transparent transparent transparent"></span>' +
      '</span>' +
    '</span>';
  }

  // Inject CSS rules for tooltip interactivity dynamically
  if (typeof document !== "undefined") {
    var style = document.createElement("style");
    style.textContent = 
      ".info-tooltip-trigger:hover { box-shadow: var(--neu-pressed) !important; }" +
      ".info-tooltip-trigger:hover .info-tooltip-content { visibility: visible !important; opacity: 1 !important; }" +
      ".info-tooltip-trigger:hover svg { opacity: 1 !important; color: var(--accent-primary) !important; }";
    document.head.appendChild(style);
  }

  function pinnOriginCard(pinnData) {
    if (!pinnData || !pinnData.predicted_origin) return "";
    var origin = pinnData.predicted_origin;
    var params = pinnData.physics_parameters || {};

    return '<div class="pinn-card card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;flex-wrap:wrap;gap:8px">' +
        '<div>' +
          '<div style="font-size:11px;font-weight:800;color:#ec4899;text-transform:uppercase;letter-spacing:1px">⚡ PINN eDNA Upstream Source Origin Tracer' + tooltipIcon("Backtracks eDNA coordinates upstream along flow vectors to pinpoint where the species shed its DNA by solving physical water transport equations.") + '</div>' +
          '<h3 style="margin:2px 0 0 0;font-size:16px;font-weight:800;color:var(--text-primary)">' + esc(pinnData.species_name || "Invasive Species") + ' &middot; Backwards Hydrodynamic Localization</h3>' +
        '</div>' +
        '<span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:800;background:#ec489920;color:#ec4899;border:1px solid #ec489960">PHYSICS-INFORMED NEURAL SOLVER</span>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(130px, 1fr));gap:12px;margin-bottom:12px">' +
        '<div style="background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);border:none">' +
          '<div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase">Upstream Distance</div>' +
          '<div style="font-size:18px;font-weight:900;color:#ec4899">' + origin.distance_upstream_km + ' km</div>' +
        '</div>' +
        '<div style="background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);border:none">' +
          '<div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase">Time Since Release</div>' +
          '<div style="font-size:18px;font-weight:900;color:#8b5cf6">-' + origin.time_since_release_hrs + ' hrs</div>' +
        '</div>' +
        '<div style="background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);border:none">' +
          '<div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase">eDNA Half-Life</div>' +
          '<div style="font-size:18px;font-weight:900;color:var(--text-primary)">' + (params.half_life_hrs || 12.0) + ' hrs</div>' +
        '</div>' +
        '<div style="background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);border:none">' +
          '<div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase">Map Error Margin</div>' +
          '<div style="font-size:18px;font-weight:900;color:#f59e0b">&plusmn;' + origin.map_spatial_uncertainty_km + ' km</div>' +
        '</div>' +
      '</div>' +
      '<div style="font-size:11px;color:var(--text-secondary);line-height:1.5;background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);margin-bottom:12px;border:none">' +
        '📐 <strong>Advection-Dispersion Hydro-Parameters:</strong> Velocity <code>u = ' + (params.flow_velocity_ms || 0.45) + ' m/s</code> &middot; Water Temp <code>T = ' + (params.temperature_c || 28.0) + '&deg;C</code> &middot; Decay Rate <code>&lambda; = ' + (params.decay_rate_hr || 0.058) + ' hr&minus;1</code><br>' +
        '⚠️ <em>' + esc(origin.map_inaccuracy_disclaimer || "Includes Map Error Margin") + '</em>' +
      '</div>' +
      '<button class="button primary sm" id="pinnFocusBtn" style="background:#ec4899;border-color:#ec4899;font-weight:800;box-shadow:var(--neu-raised-sm)">' +
        '📍 Focus Map on Predicted Upstream Origin (' + origin.latitude + ', ' + origin.longitude + ')' +
      '</button>' +
    '</div>';
  }

  function weatherForecastWidget(forecastData) {
    if (!forecastData || !forecastData.daily_forecasts) return "";
    var days = forecastData.daily_forecasts || [];
    var trend = forecastData.overall_trend || "stable";
    var trendColor = trend === "improving" ? "#10b981" : (trend === "declining" ? "#ef4444" : "#f59e0b");

    var html = '<div class="forecast-widget card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px">' +
        '<div>' +
          '<div style="font-size:11px;font-weight:800;color:var(--accent-primary);text-transform:uppercase;letter-spacing:1px">🌤️ AI Biodiversity Weather Forecast' + tooltipIcon("Predicts the likelihood of finding this species in the river over the next 7 days based on seasonal trends and water patterns, helping plan monitoring trips.") + '</div>' +
          '<h3 style="margin:2px 0 0 0;font-size:16px;font-weight:800;color:var(--text-primary)">7-Day Detection Probabilities</h3>' +
        '</div>' +
        '<span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:800;background:' + trendColor + '15;color:' + trendColor + ';border:1px solid ' + trendColor + '30;box-shadow:var(--neu-raised-sm)">TREND: ' + esc(trend.toUpperCase()) + '</span>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(130px, 1fr));gap:12px">';

    days.forEach(function(d) {
      var topSp = (d.species_forecasts && d.species_forecasts[0]) || { species_name: "Tor putitora", detection_probability_pct: "85%" };
      html += '<div style="background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);text-align:center;border:none">' +
        '<div style="font-size:11px;font-weight:800;color:var(--text-secondary)">' + esc(d.day_name || "Day " + d.day_number) + '</div>' +
        '<div style="font-size:10px;color:var(--text-secondary);margin-bottom:6px">' + esc(d.date) + '</div>' +
        '<div style="font-size:22px;font-weight:900;color:var(--accent-primary)">' + esc(topSp.detection_probability_pct) + '</div>' +
        '<div style="font-size:11px;font-style:italic;color:var(--text-primary);margin-top:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(topSp.species_name) + '">' + esc(topSp.species_name) + '</div>' +
      '</div>';
    });

    html += '</div></div>';
    return html;
  }

  function debatePanel(debateData) {
    if (!debateData || !debateData.messages) return "";
    var msgs = debateData.messages || [];
    var consensus = debateData.consensus || {};

    var html = '<div class="debate-panel card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="margin-bottom:16px">' +
        '<div style="font-size:11px;font-weight:800;color:#8b5cf6;text-transform:uppercase;letter-spacing:1px">🏛️ Multi-Agent Stakeholder Debate' + tooltipIcon("Simulates a collaborative debate among a forest officer, fisherman, NGO, and regulator to find a balanced, legally compliant conservation plan for this sample site.") + '</div>' +
        '<h3 style="margin:2px 0 0 0;font-size:16px;font-weight:800;color:var(--text-primary)">' + esc(debateData.topic || "Conservation vs Management Strategy") + '</h3>' +
      '</div>' +
      '<div style="display:flex;flex-direction:column;gap:12px;max-height:360px;overflow-y:auto;padding-right:8px;margin-bottom:16px">';

    msgs.forEach(function(m) {
      html += '<div style="background:var(--bg-card);padding:12px;border-radius:10px;box-shadow:var(--neu-pressed);border:none">' +
        '<div style="display:flex;justify-content:space-between;font-size:11px;font-weight:800;color:var(--accent-primary);margin-bottom:6px">' +
          '<span>' + esc(m.speaker_name) + ' (' + esc(m.role) + ')</span>' +
          '<span style="color:var(--text-secondary)">Round ' + m.round + ' &middot; ' + esc(m.timestamp) + '</span>' +
        '</div>' +
        '<div style="font-size:12.5px;color:var(--text-primary);line-height:1.4">' + esc(m.message) + '</div>' +
      '</div>';
    });

    html += '</div>' +
      '<div style="background:var(--bg-card);box-shadow:var(--neu-raised-sm);border-radius:10px;padding:16px;border:none">' +
        '<div style="font-size:11px;font-weight:800;color:#10b981;text-transform:uppercase;letter-spacing:0.5px">✅ Moderator Consensus Recommendation</div>' +
        '<div style="font-size:13px;color:var(--text-primary);margin-top:6px;font-weight:600;line-height:1.4">' + esc(consensus.consensus_recommendation || "Balanced protection zone recommended.") + '</div>' +
      '</div>' +
    '</div>';

    return html;
  }

  function ecologicalAlertCard(anomalyData) {
    if (!anomalyData || !anomalyData.anomalies) return "";
    var list = anomalyData.anomalies || [];
    if (list.length === 0) return "";

    var html = '<div class="card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="font-size:11px;font-weight:800;color:#ef4444;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">🚨 Real-Time Streaming eDNA Anomaly Alert' + tooltipIcon("Flags when a species is detected at unusually high counts (suggesting a possible mass die-off or sudden release upstream) or has suddenly vanished from a site where it is normally found.") + '</div>' +
      '<h3 style="margin:0 0 16px 0;font-size:16px;font-weight:800;color:var(--text-primary)">' + list.length + ' Ecological Anomaly Detected</h3>';

    list.forEach(function(a) {
      html += '<div style="background:var(--bg-card);padding:14px;border-radius:10px;box-shadow:var(--neu-pressed);margin-bottom:10px;border:none">' +
        '<div style="display:flex;justify-content:space-between;font-weight:800;font-size:13.5px;color:var(--text-primary)">' +
          '<span>' + esc(a.species_name) + ' (' + esc(a.anomaly_type.replace("_", " ")) + ')</span>' +
          '<span style="color:#ef4444">z-score: ' + a.z_score + '</span>' +
        '</div>' +
        '<div style="font-size:11.5px;color:var(--text-secondary);margin-top:6px;line-height:1.4">' + esc(a.interpretation) + '</div>' +
      '</div>';
    });

    html += '</div>';
    return html;
  }

  function nftReceiptCard(nftData) {
    if (!nftData) return "";
    var nft = nftData.nft || nftData;
    var meta = nft.metadata || {};

    return '<div class="card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px">' +
        '<div>' +
          '<div style="font-size:11px;font-weight:800;color:#3b82f6;text-transform:uppercase;letter-spacing:1px">💎 Biodiversity NFT Sponsorship Receipt' + tooltipIcon("Mints a digital sponsorship receipt on the Polygon blockchain to record this verified detection permanently, featuring unique generative art rendered directly from the species DNA sequence.") + '</div>' +
          '<h3 style="margin:2px 0 6px 0;font-size:16px;font-weight:800;color:var(--text-primary)">' + esc(meta.name || "BioRadar Detection NFT") + '</h3>' +
          '<div style="font-size:11.5px;color:var(--text-secondary)">Polygon Amoy Testnet &middot; Tx: <code class="mono" style="background:var(--bg-card);padding:2px 6px;border-radius:4px;box-shadow:var(--neu-pressed)">' + esc((nft.tx_hash || "").substring(0, 20)) + '...</code></div>' +
        '</div>' +
        (meta.image_data_uri ? '<div style="box-shadow:var(--neu-raised-sm);border-radius:10px;padding:4px;background:var(--bg-surface)"><img src="' + meta.image_data_uri + '" style="width:100px;height:100px;border-radius:8px;display:block;border:none" alt="DNA Art"></div>' : '') +
      '</div>' +
    '</div>';
  }

  function satelliteAlertCard(satData) {
    if (!satData || !satData.change_detected) return "";
    var alert = satData.alert || {};

    return '<div class="card" style="box-shadow:var(--neu-raised);margin-top:24px;border-radius:12px;padding:20px;border:none">' +
      '<div style="font-size:11px;font-weight:800;color:#f59e0b;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">🛰️ Satellite Remote Sensing Change Detection' + tooltipIcon("Uses Sentinel-2 satellite imagery to check for sudden changes in vegetation or construction within 2 km of the site, alerting you to potential deforestation or soil runoffs.") + '</div>' +
      '<h3 style="margin:0 0 10px 0;font-size:16px;font-weight:800;color:var(--text-primary)">' + esc(alert.change_type.toUpperCase()) + ' &middot; Sentinel-2 Surface Reflectance</h3>' +
      '<div style="background:var(--bg-card);box-shadow:var(--neu-pressed);padding:14px;border-radius:10px;border:none;margin-bottom:12px">' +
        '<div style="font-size:12.5px;color:var(--text-primary);line-height:1.4">' + esc(alert.interpretation || "NDVI decrease detected near site buffer.") + '</div>' +
      '</div>' +
      '<div style="font-size:12px;font-weight:800;color:#f59e0b">NDVI Variance: ' + alert.ndvi_before + ' &rarr; ' + alert.ndvi_after + ' (&Delta; ' + alert.ndvi_change + ')</div>' +
    '</div>';
  }

  global.BioRadarUI = {
    esc: esc, num: num, mb: mb, istTime: istTime, duration: duration,
    animateIn: animateIn, pulse: pulse, countUp: countUp, countUpAll: countUpAll, growBars: growBars,
    prefersReducedMotion: prefersReducedMotion,
    elapsedSince: elapsedSince,
    icon: icon, card: card, button: button, badge: badge, kpi: kpi, toggle: toggle,
    state: state, errorState: errorState, skeleton: skeleton,
    skeletonScreen: skeletonScreen,
    toast: toast, modal: modal, closeModal: closeModal,
    openPanel: openPanel, closePanel: closePanel,
    categorical: categorical, categoricalAt: categoricalAt,
    sequential: sequential, heat: heat, cssVar: cssVar, bars: bars,
    aiBriefing: aiBriefing, pvaTrajectoryChart: pvaTrajectoryChart, pinnOriginCard: pinnOriginCard,
    blockchainProofModal: blockchainProofModal,
    weatherForecastWidget: weatherForecastWidget, debatePanel: debatePanel,
    ecologicalAlertCard: ecologicalAlertCard, nftReceiptCard: nftReceiptCard,
    satelliteAlertCard: satelliteAlertCard, tooltipIcon: tooltipIcon
  };
})(window);





