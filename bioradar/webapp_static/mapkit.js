/* Professional GIS layer: clustering, heatmap, time-slider, measurement,
   basemaps, fullscreen.

   The gap analysis names five Leaflet plugins — markercluster, heat, timeline,
   measure, draw. None are vendored here, for one reason that decides it: this
   app is served from inside the pipeline image with no network fetch at load,
   so a plugin has to be committed as a vendored file. Vendoring four more
   third-party bundles (~90 kB, four more licences, four more things that go
   stale) to get behaviour that is 60–80 lines each is the wrong trade.

   So each is implemented directly on Leaflet's public API below. The features
   are the ones the analysis asks for; the dependency count stays at one.

   Drawing/annotation is the one omission. It is a data-entry tool whose output
   BioRadar has nowhere to store — a polygon nobody can save is a demo prop.
   Measurement, which answers "how far apart are these sites", is here. */

(function (global) {
  "use strict";

  var UI = global.BioRadarUI;

  /* ── Basemaps ─────────────────────────────────────────────────────────
     Free, no API key. CARTO rebuilds continuously from OpenStreetMap and looks
     current; OSM's own raster style is the dated one. `{r}` requests retina
     tiles so the map is not soft on a laptop display. */

  var BASEMAPS = {
    Dark: {
      url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 20
    },
    Light: {
      url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 20
    },
    Satellite: {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics",
      maxZoom: 19
    },
    Topographic: {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
      attribution: "&copy; Esri, HERE, Garmin, USGS, NGA",
      maxZoom: 19
    }
  };

  function prefersDarkTiles() {
    return document.documentElement.getAttribute("data-theme") !== "light";
  }

  /* ── Fullscreen ───────────────────────────────────────────────────── */

  var FullscreenControl = L.Control.extend({
    options: { position: "topleft" },
    onAdd: function (map) {
      var container = L.DomUtil.create("div", "leaflet-bar leaflet-control");
      var link = L.DomUtil.create("a", "", container);
      link.href = "#";
      link.title = "Toggle fullscreen";
      link.setAttribute("role", "button");
      link.innerHTML = "&#x26F6;";
      L.DomEvent.on(link, "click", function (event) {
        L.DomEvent.stop(event);
        var target = map.getContainer();
        if (document.fullscreenElement) document.exitFullscreen();
        else if (target.requestFullscreen) target.requestFullscreen();
      });

      /* Leaflet caches the container size and only requests tiles for that
         rectangle. Entering fullscreen changes the size without telling it, so
         it keeps painting a small block inside a large empty box. The browser
         also reports the new size a frame or two late, hence several resizes
         rather than one guessed delay. */
      map.__fsHandler = function () {
        [0, 60, 250, 600].forEach(function (delay) {
          setTimeout(function () { map.invalidateSize({ animate: false, pan: false }); }, delay);
        });
      };
      document.addEventListener("fullscreenchange", map.__fsHandler);
      return container;
    },

    // Without this the document-level listener outlives the map it captures.
    // Every rebuild would leak one handler and one whole Leaflet instance,
    // and the leak is invisible until the tab runs out of resources.
    onRemove: function (map) {
      if (map.__fsHandler) {
        document.removeEventListener("fullscreenchange", map.__fsHandler);
        delete map.__fsHandler;
      }
    }
  });

  /* ── Marker clustering ────────────────────────────────────────────────
     Grid clustering in screen space. Without it, 100+ overlapping pins are
     both unreadable and slow — Leaflet keeps a DOM node per marker.

     Screen space rather than geographic distance on purpose: the user's
     complaint is "these pins overlap", which is a pixel problem. Clustering by
     kilometres would still overlap when zoomed out and would over-split when
     zoomed in. */

  var CLUSTER_CELL_PX = 68;

  function ClusterLayer(points, options) {
    this.points = points || [];
    this.options = options || {};
    this.group = L.layerGroup();
    this._map = null;
    this._filter = null;
  }

  ClusterLayer.prototype.addTo = function (map) {
    this._map = map;
    this.group.addTo(map);
    var self = this;
    this._onChange = function () { self.render(); };
    map.on("zoomend moveend", this._onChange);
    this.render();
    return this;
  };

  // Clustering projects coordinates to screen pixels, which Leaflet refuses to
  // do before the map has a centre and zoom ("Set map center and zoom first").
  // Rather than depend on the caller adding layers in the right order -- a
  // constraint that is invisible until it throws -- the layer waits for the
  // view itself.
  ClusterLayer.prototype._ready = function () {
    return !!(this._map && this._map._loaded);
  };

  ClusterLayer.prototype.remove = function () {
    if (this._map) {
      this._map.off("zoomend moveend", this._onChange);
      this._map.removeLayer(this.group);
    }
    return this;
  };

  ClusterLayer.prototype.setFilter = function (fn) {
    this._filter = fn;
    this.render();
    return this;
  };

  ClusterLayer.prototype.visiblePoints = function () {
    var filter = this._filter;
    return this.points.filter(function (p) { return !filter || filter(p); });
  };

  ClusterLayer.prototype.render = function () {
    if (!this._ready()) return;
    var map = this._map;
    this.group.clearLayers();

    var self0 = this;
    var cells = {};
    this.visiblePoints().forEach(function (point, index) {
      if (self0.options.disabled) {
        // Clustering off: every point is its own cell, so the same render path
        // draws both modes and there is no second code path to keep in sync.
        cells["p" + index] = [point];
        return;
      }
      var pixel = map.latLngToContainerPoint([point.latitude, point.longitude]);
      var key = Math.floor(pixel.x / CLUSTER_CELL_PX) + ":" + Math.floor(pixel.y / CLUSTER_CELL_PX);
      (cells[key] || (cells[key] = [])).push(point);
    });

    var self = this;
    Object.keys(cells).forEach(function (key) {
      var members = cells[key];
      if (members.length === 1) {
        self.group.addLayer(self._marker(members[0]));
      } else {
        self.group.addLayer(self._cluster(members));
      }
    });
  };

  /* ── Map Legend ─────────────────────────────────────────────────────── */

  var MapLegendControl = L.Control.extend({
    options: { position: "bottomright" },
    onAdd: function (map) {
      var container = L.DomUtil.create("div", "leaflet-bar map-legend-card");
      container.style.background = "var(--bg-surface, #1e293b)";
      container.style.color = "var(--text-primary, #f8fafc)";
      container.style.padding = "10px 14px";
      container.style.borderRadius = "8px";
      container.style.boxShadow = "0 4px 12px rgba(0,0,0,0.45)";
      container.style.fontSize = "12px";
      container.style.lineHeight = "1.6";
      container.style.border = "1px solid var(--border, #334155)";

      container.innerHTML =
        '<div style="font-weight:700;margin-bottom:6px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;color:var(--text-secondary,#94a3b8)">Map Legend</div>' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">' +
          '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ef4444;box-shadow:0 0 4px #ef4444"></span>' +
          '<span><strong>Invasive Species</strong> (Alert)</span>' +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">' +
          '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f97316;box-shadow:0 0 4px #f97316"></span>' +
          '<span><strong>Threatened Taxa</strong> (Risk)</span>' +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:8px">' +
          '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#10b981;box-shadow:0 0 4px #10b981"></span>' +
          '<span><strong>Native Community</strong> (Normal)</span>' +
        '</div>';
      return container;
    }
  });

  ClusterLayer.prototype._marker = function (point) {
    var colour = "#10b981"; // Normal/Native green
    if (point.has_invasive || point.highest_severity === "invasive") {
      colour = "#ef4444"; // Invasive red
    } else if (point.has_threatened || point.highest_severity === "threatened") {
      colour = "#f97316"; // Threatened orange
    } else if (this.options.colorFor) {
      colour = this.options.colorFor(point) || "#10b981";
    }

    var symbol = (point.has_invasive || point.highest_severity === "invasive") ? "!" :
                 ((point.has_threatened || point.highest_severity === "threatened") ? "🛡" : "•");

    var marker = L.marker([point.latitude, point.longitude], {
      title: point.site_id,
      keyboard: true,
      alt: "Sampling site " + point.site_id,
      icon: L.divIcon({
        className: "site-pin-marker",
        html: '<svg viewBox="0 0 28 38" width="28" height="38" aria-hidden="true" style="filter:drop-shadow(0 3px 6px rgba(0,0,0,0.5))">' +
              '<path d="M14 0C6.27 0 0 6.27 0 14c0 9.8 14 24 14 24s14-14.2 14-24C28 6.27 21.73 0 14 0z" fill="' + colour + '" stroke="#ffffff" stroke-width="1.8"/>' +
              '<circle cx="14" cy="14" r="7.5" fill="#ffffff"/>' +
              '<text x="14" y="18" text-anchor="middle" font-size="11" font-weight="900" fill="' + colour + '">' + symbol + '</text></svg>',
        iconSize: [28, 38], iconAnchor: [14, 38], popupAnchor: [0, -36]
      })
    });
    if (this.options.popupFor) marker.bindPopup(this.options.popupFor(point), { maxWidth: 320 });
    if (this.options.onSelect) {
      marker.on("click", function () { this.options.onSelect(point); }.bind(this));
    }
    return marker;
  };

  ClusterLayer.prototype._cluster = function (members) {
    var lat = 0, lon = 0, species = 0;
    var hasInvasive = false, hasThreatened = false;
    members.forEach(function (m) {
      lat += m.latitude; lon += m.longitude; species += m.species_count || 0;
      if (m.has_invasive || m.highest_severity === "invasive") hasInvasive = true;
      if (m.has_threatened || m.highest_severity === "threatened") hasThreatened = true;
    });
    lat /= members.length; lon /= members.length;

    var colour = hasInvasive ? "#ef4444" : (hasThreatened ? "#f97316" : "#10b981");

    var marker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: "cluster-pin-marker",
        html: '<svg viewBox="0 0 34 46" width="34" height="46" aria-hidden="true" style="filter:drop-shadow(0 4px 8px rgba(0,0,0,0.55))">' +
              '<path d="M17 0C7.6 0 0 7.6 0 17c0 12 17 29 17 29s17-17 17-29C34 7.6 26.4 0 17 0z" fill="' + colour + '" stroke="#ffffff" stroke-width="2"/>' +
              '<circle cx="17" cy="17" r="11" fill="#ffffff"/>' +
              '<text x="17" y="21" text-anchor="middle" font-size="12" font-weight="900" fill="#0f172a">' + members.length + '</text></svg>',
        iconSize: [34, 46], iconAnchor: [17, 46]
      }),
      title: members.length + " sampling sites"
    });

    var self = this;
    marker.on("click", function () {
      var bounds = L.latLngBounds(members.map(function (m) { return [m.latitude, m.longitude]; }));
      if (bounds.getNorthEast().equals(bounds.getSouthWest())) {
        marker.bindPopup(
          '<div class="pop"><div class="pop-site">' + members.length + " sites here</div>" +
          members.map(function (m) {
            return "<div>" + UI.esc(m.site_id) + " &middot; " + (m.species_count || 0) + " species</div>";
          }).join("") + "</div>"
        ).openPopup();
        return;
      }
      self._map.fitBounds(bounds, { padding: [60, 60] });
    });

    marker.bindTooltip(
      members.length + " sites, " + species + " species detections",
      { direction: "top" }
    );
    return marker;
  };


  /* ── Heatmap ──────────────────────────────────────────────────────────
     A canvas overlay: each point paints a radial alpha gradient, the
     accumulated alpha is then mapped through ColorBrewer YlOrRd. Painting
     intensity first and colourising second is what makes overlapping points
     add up instead of just drawing over one another. */

  var HeatLayer = L.Layer.extend({
    initialize: function (points, options) {
      this._points = points || [];
      this._options = L.extend({ radius: 34, weight: null, maxOpacity: 0.75 }, options);
      this._filter = null;
    },

    onAdd: function (map) {
      this._map = map;
      this._canvas = L.DomUtil.create("canvas", "leaflet-layer");
      this._canvas.style.pointerEvents = "none";
      var size = map.getSize();
      this._canvas.width = size.x;
      this._canvas.height = size.y;
      map.getPanes().overlayPane.appendChild(this._canvas);
      map.on("moveend zoomend resize", this._redraw, this);
      this._redraw();
    },

    onRemove: function (map) {
      map.off("moveend zoomend resize", this._redraw, this);
      if (this._canvas && this._canvas.parentNode) {
        this._canvas.parentNode.removeChild(this._canvas);
      }
    },

    setFilter: function (fn) { this._filter = fn; this._redraw(); return this; },

    _redraw: function () {
      // Same constraint as the cluster layer: projecting a coordinate needs a
      // centre and zoom, and asking for one before the view is set throws.
      if (!this._map || !this._map._loaded || !this._canvas) return;
      var map = this._map;
      var size = map.getSize();
      if (this._canvas.width !== size.x || this._canvas.height !== size.y) {
        this._canvas.width = size.x;
        this._canvas.height = size.y;
      }
      L.DomUtil.setPosition(this._canvas, map.containerPointToLayerPoint([0, 0]));

      var ctx = this._canvas.getContext("2d");
      ctx.clearRect(0, 0, size.x, size.y);

      var filter = this._filter;
      var points = this._points.filter(function (p) { return !filter || filter(p); });
      if (!points.length) return;

      var weightOf = this._options.weight || function (p) { return p.species_count || 1; };
      var max = points.reduce(function (m, p) { return Math.max(m, weightOf(p)); }, 0) || 1;
      // Radius grows with zoom so the heat blob tracks the geography instead of
      // staying a fixed screen smudge as the user zooms in.
      var radius = this._options.radius * Math.max(0.6, Math.min(2.2, map.getZoom() / 8));

      ctx.globalCompositeOperation = "source-over";
      points.forEach(function (point) {
        var pixel = map.latLngToContainerPoint([point.latitude, point.longitude]);
        var intensity = Math.max(0.12, weightOf(point) / max);
        var gradient = ctx.createRadialGradient(pixel.x, pixel.y, 0, pixel.x, pixel.y, radius);
        gradient.addColorStop(0, "rgba(0,0,0," + intensity.toFixed(3) + ")");
        gradient.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(pixel.x, pixel.y, radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // Colourise: read back the accumulated alpha and map it through the
      // sequential ramp. Done in one pass over the pixel buffer.
      var image = ctx.getImageData(0, 0, size.x, size.y);
      var data = image.data;
      var ramp = buildRamp();
      var maxOpacity = this._options.maxOpacity;
      for (var i = 0; i < data.length; i += 4) {
        var alpha = data[i + 3];
        if (!alpha) continue;
        var colour = ramp[Math.min(255, alpha)];
        data[i] = colour[0];
        data[i + 1] = colour[1];
        data[i + 2] = colour[2];
        data[i + 3] = Math.round(Math.min(255, alpha * maxOpacity + 40));
      }
      ctx.putImageData(image, 0, 0);
    }
  });

  var _rampCache = null;
  var _rampTheme = null;

  function buildRamp() {
    var theme = document.documentElement.getAttribute("data-theme") || "dark";
    if (_rampCache && _rampTheme === theme) return _rampCache;
    var stops = ["--heat-1", "--heat-2", "--heat-3", "--heat-4", "--heat-5"].map(function (name) {
      return hexToRgb(UI.cssVar(name));
    });
    var ramp = new Array(256);
    for (var i = 0; i < 256; i++) {
      var position = (i / 255) * (stops.length - 1);
      var low = Math.floor(position);
      var high = Math.min(stops.length - 1, low + 1);
      var mix = position - low;
      ramp[i] = [
        Math.round(stops[low][0] + (stops[high][0] - stops[low][0]) * mix),
        Math.round(stops[low][1] + (stops[high][1] - stops[low][1]) * mix),
        Math.round(stops[low][2] + (stops[high][2] - stops[low][2]) * mix)
      ];
    }
    _rampCache = ramp;
    _rampTheme = theme;
    return ramp;
  }

  function hexToRgb(hex) {
    var value = String(hex || "").trim().replace("#", "");
    if (value.length === 3) {
      value = value[0] + value[0] + value[1] + value[1] + value[2] + value[2];
    }
    var int = parseInt(value, 16);
    if (isNaN(int)) return [255, 140, 60];
    return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
  }

  /* ── Measurement ──────────────────────────────────────────────────────
     Click to drop vertices, double-click to finish. Distances are great-circle
     (haversine): planar distance on a Web Mercator map is wrong by roughly the
     secant of the latitude, which at 20°N is already a 6% error. */

  var MeasureControl = L.Control.extend({
    options: { position: "topleft" },
    onAdd: function (map) {
      var container = L.DomUtil.create("div", "leaflet-bar leaflet-control");
      var link = L.DomUtil.create("a", "", container);
      link.href = "#";
      link.title = "Measure distance";
      link.setAttribute("role", "button");
      link.innerHTML = "&#x21D4;";

      var active = false, vertices = [], line = null, readout = null, markers = [];

      function reset() {
        vertices = [];
        markers.forEach(function (m) { map.removeLayer(m); });
        markers = [];
        if (line) { map.removeLayer(line); line = null; }
        if (readout && readout.parentNode) { readout.parentNode.removeChild(readout); readout = null; }
      }

      function total() {
        var metres = 0;
        for (var i = 1; i < vertices.length; i++) {
          metres += map.distance(vertices[i - 1], vertices[i]);
        }
        return metres;
      }

      function show() {
        if (!readout) {
          readout = L.DomUtil.create("div", "measure-readout", map.getContainer());
        }
        var metres = total();
        readout.textContent = vertices.length < 2
          ? "Click to add points, double-click to finish"
          : (metres >= 1000 ? (metres / 1000).toFixed(2) + " km" : Math.round(metres) + " m") +
            " over " + (vertices.length - 1) + " leg(s)";
      }

      function onClick(event) {
        vertices.push(event.latlng);
        markers.push(L.circleMarker(event.latlng, {
          radius: 4, color: UI.cssVar("--accent-primary"),
          fillColor: UI.cssVar("--accent-primary"), fillOpacity: 1, weight: 2
        }).addTo(map));
        if (line) map.removeLayer(line);
        if (vertices.length > 1) {
          line = L.polyline(vertices, {
            color: UI.cssVar("--accent-primary"), weight: 2.5, dashArray: "6 5"
          }).addTo(map);
        }
        show();
      }

      function stop() {
        active = false;
        L.DomUtil.removeClass(link, "active");
        map.off("click", onClick);
        map.off("dblclick", stop);
        map.getContainer().style.cursor = "";
        if (map.doubleClickZoom) map.doubleClickZoom.enable();
      }

      L.DomEvent.on(link, "click", function (event) {
        L.DomEvent.stop(event);
        if (active) { stop(); reset(); return; }
        active = true;
        L.DomUtil.addClass(link, "active");
        reset();
        show();
        map.getContainer().style.cursor = "crosshair";
        // Double-click ends the measurement, so it must not also zoom.
        if (map.doubleClickZoom) map.doubleClickZoom.disable();
        map.on("click", onClick);
        map.on("dblclick", stop);
      });

      return container;
    }
  });

  /* ── Hydro Corridor Network Layer ────────────────────────────────────── */

  var HydroCorridorLayer = L.LayerGroup.extend({
    initialize: function (corridorData, options) {
      L.LayerGroup.prototype.initialize.call(this);
      this.corridors = corridorData || [];
      this.options = options || {};
      this.render();
    },

    render: function () {
      this.clearLayers();
      var self = this;

      (this.corridors || []).forEach(function (corridor) {
        var waypoints = corridor.waypoints || [];
        if (waypoints.length < 2) return;

        for (var i = 1; i < waypoints.length; i++) {
          var p1 = waypoints[i - 1];
          var p2 = waypoints[i];
          var color = p2.color || "#ef4444";
          var widthKm = p2.channel_width_km || 1.8;

          var outerWeight = Math.max(16, Math.min(38, Math.round(widthKm * 14)));

          var outerTube = L.polyline([[p1.lat, p1.lon], [p2.lat, p2.lon]], {
            color: color,
            weight: outerWeight,
            opacity: 0.22,
            lineCap: "round",
            lineJoin: "round"
          });
          self.addLayer(outerTube);

          var innerTube = L.polyline([[p1.lat, p1.lon], [p2.lat, p2.lon]], {
            color: color,
            weight: Math.round(outerWeight * 0.55),
            opacity: 0.50,
            lineCap: "round",
            lineJoin: "round"
          });
          self.addLayer(innerTube);

          var coreLine = L.polyline([[p1.lat, p1.lon], [p2.lat, p2.lon]], {
            color: "#ffffff",
            weight: 2.5,
            opacity: 0.90,
            lineCap: "round",
            lineJoin: "round"
          });

          var timeLabel = p2.arrival_months ? (p2.arrival_months + " Mo Front") : "Spread Front";
          coreLine.bindTooltip(
            "<strong>" + UI.esc(corridor.waterway_name || "Water Corridor") + "</strong><br>" +
            "Arrival Front: <strong>" + timeLabel + "</strong> (" + (p2.distance_from_origin_km || 0) + " km downstream)<br>" +
            "Threat Risk: <span style='color:" + color + ";font-weight:700'>" + (p2.colonisation_risk || "HIGH") + "</span>",
            { direction: "top" }
          );
          self.addLayer(coreLine);

          var nodeMarker = L.circleMarker([p2.lat, p2.lon], {
            radius: 5.5,
            fillColor: color,
            color: "#ffffff",
            weight: 2.0,
            fillOpacity: 1.0
          });

          nodeMarker.bindPopup(
            '<div style="font-size:12px"><strong>' + UI.esc(corridor.waterway_name || "Water Corridor") + '</strong><br>' +
            'Dispersal Distance: <strong>' + (p2.distance_from_origin_km || 0) + ' km downstream</strong><br>' +
            'Estimated Arrival: <strong>' + timeLabel + '</strong><br>' +
            'Colonisation Risk: <span style="color:' + color + ';font-weight:700">' + (p2.colonisation_risk || "HIGH") + '</span></div>'
          );

          self.addLayer(nodeMarker);
        }
      });
    }
  });

  /* ── Time slider ──────────────────────────────────────────────────────
     The temporal dimension of a survey is invisible without one: the analysis
     notes that the Time Machine feature currently has no visual representation
     on the map at all. */

  function timeline(points, onChange) {
    var stamps = points
      .map(function (p) { return p.collected_at; })
      .filter(Boolean)
      .map(function (s) { return String(s).slice(0, 10); });
    var unique = Object.keys(stamps.reduce(function (acc, s) { acc[s] = 1; return acc; }, {})).sort();

    if (unique.length < 2) return null;   // nothing to animate

    var wrap = document.createElement("div");
    wrap.className = "timeline";
    wrap.innerHTML =
      UI.button("", { icon: "activity", size: "sm", className: "icon tl-play",
                      ariaLabel: "Play through time" }) +
      '<input type="range" min="0" max="' + unique.length + '" value="' + unique.length +
      '" step="1" aria-label="Filter sampling sites by collection date">' +
      '<span class="stamp"></span>';

    var slider = wrap.querySelector("input");
    var stamp = wrap.querySelector(".stamp");
    var play = wrap.querySelector(".tl-play");
    var timer = null;

    function apply() {
      var index = Number(slider.value);
      // The last stop is "all dates" rather than the final date, so the slider
      // returns to showing everything instead of stranding the user at one day.
      if (index >= unique.length) {
        stamp.textContent = "All dates";
        onChange(null);
      } else {
        stamp.textContent = unique[index];
        onChange(unique[index]);
      }
    }

    slider.addEventListener("input", function () {
      if (timer) { clearInterval(timer); timer = null; play.classList.remove("loading"); }
      apply();
    });

    play.addEventListener("click", function () {
      if (timer) {
        clearInterval(timer); timer = null; play.classList.remove("loading");
        return;
      }
      play.classList.add("loading");
      slider.value = 0;
      apply();
      timer = setInterval(function () {
        var next = Number(slider.value) + 1;
        if (next > unique.length) {
          clearInterval(timer); timer = null; play.classList.remove("loading");
          slider.value = unique.length;
        } else {
          slider.value = next;
        }
        apply();
      }, 900);
    });

    apply();
    return { node: wrap, dates: unique };
  }

  /* ── Recommended Sampling Site Layer ────────────────────────────────────── */

  var RecommendedSiteLayer = L.LayerGroup.extend({
    initialize: function (recommendations, options) {
      L.LayerGroup.prototype.initialize.call(this);
      this.recs = recommendations || [];
      this.options = options || {};
      this.render();
    },

    render: function () {
      this.clearLayers();
      var self = this;

      (this.recs || []).forEach(function (rec) {
        var lat = rec.latitude;
        var lon = rec.longitude;
        if (!lat || !lon) return;

        var rank = rec.rank || 1;
        var score = rec.composite_priority_score || 85;
        var priorityTag = rec.priority || "RECOMMENDED SITE";
        var priorityColor = rec.priority_color || "#06b6d4";

        var icon = L.divIcon({
          className: "recommended-pin-marker",
          html: '<svg viewBox="0 0 32 44" width="32" height="44" aria-hidden="true" style="filter:drop-shadow(0 4px 10px rgba(6,182,212,0.65))">' +
                '<path d="M16 0C7.2 0 0 7.2 0 16c0 11.2 16 28 16 28s16-16.8 16-28C32 7.2 24.8 0 16 0z" fill="#06b6d4" stroke="#ffffff" stroke-width="2"/>' +
                '<circle cx="16" cy="16" r="10" fill="#0891b2"/>' +
                '<circle cx="16" cy="16" r="6" fill="#ffffff"/>' +
                '<text x="16" y="20" text-anchor="middle" font-size="11" font-weight="900" fill="#ffffff">' + rank + '</text>' +
                '</svg>',
          iconSize: [32, 44],
          iconAnchor: [16, 44]
        });

        var marker = L.marker([lat, lon], { icon: icon, title: rec.site_name || "Recommended Site" });

        var popupHtml =
          '<div style="font-size:12px;min-width:220px">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">' +
          '<span style="background:' + priorityColor + ';color:#ffffff;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:800">' + UI.esc(priorityTag) + '</span>' +
          '<span style="font-weight:900;color:#0891b2;font-size:14px">Score ' + score + '/100</span>' +
          '</div>' +
          '<strong>' + UI.esc(rec.site_name || "Optimal Sampling Site") + '</strong><br>' +
          '<div style="margin-top:6px;font-size:11px;line-height:1.5;color:#475569">' +
          '🎯 <strong>Target Species:</strong> ' + UI.esc(rec.target_species || "Multi-species") + '<br>' +
          '📈 <strong>Beta-Diversity Gain:</strong> ' + (rec.complementarity_gain || 90) + '%<br>' +
          '⚠️ <strong>Bottleneck Risk:</strong> ' + (rec.invasive_bottleneck_risk || 80) + '%<br>' +
          '📉 <strong>Uncertainty Reduction:</strong> ' + (rec.uncertainty_reduction || 85) + '%<br>' +
          '</div>' +
          '<div style="margin-top:8px;font-size:11px;background:#f1f5f9;padding:6px;border-radius:4px;border-left:3px solid #06b6d4">' +
          UI.esc(rec.justification || "Recommended location to maximize biodiversity discovery.") +
          '</div>' +
          '</div>';

        marker.bindPopup(popupHtml);
        marker.bindTooltip("🎯 " + UI.esc(rec.site_name) + " (Score " + score + "/100)", { direction: "top" });

        self.addLayer(marker);
      });
    }
  });


  /* ── PINN eDNA Upstream Origin Layer (Physics-Informed Neural Network) ── */

  var PINNPlumeLayer = L.LayerGroup.extend({
    initialize: function (pinnData, options) {
      L.LayerGroup.prototype.initialize.call(this, [], options);
      this.pinnData = pinnData;
      this.render();
    },

    setPlumeData: function (pinnData) {
      this.pinnData = pinnData;
      this.render();
    },

    render: function () {
      this.clearLayers();
      if (!this.pinnData || !this.pinnData.geojson) return;
      var self = this;
      var pinn = this.pinnData;
      var origin = pinn.predicted_origin || {};

      (pinn.geojson.features || []).forEach(function (feat) {
        var props = feat.properties || {};
        var geom = feat.geometry || {};
        var siteLabel = props.site_id ? " (" + props.site_id + ")" : "";

        if (props.type === "flow_line" && geom.type === "LineString") {
          var latlngs = (geom.coordinates || []).map(function (c) { return [c[1], c[0]]; });
          var line = L.polyline(latlngs, {
            color: "#ec4899",
            weight: 4,
            opacity: 0.9,
            dashArray: "8, 6",
            lineCap: "round"
          });
          line.bindTooltip("⚡ PINN Upstream Flow Path" + siteLabel, { sticky: true });
          self.addLayer(line);
        } else if (props.type === "uncertainty_bounds" && geom.type === "Polygon") {
          var polyCoords = ((geom.coordinates && geom.coordinates[0]) || []).map(function (c) { return [c[1], c[0]]; });
          var poly = L.polygon(polyCoords, {
            color: "#8b5cf6",
            weight: 2,
            dashArray: "4, 4",
            fillColor: "#8b5cf6",
            fillOpacity: 0.25
          });
          poly.bindTooltip("⚠️ Map Data Uncertainty Bounds" + siteLabel, { sticky: true });
          self.addLayer(poly);
        } else if (props.type === "origin_beacon" && geom.type === "Point") {
          var ptCoords = [geom.coordinates[1], geom.coordinates[0]];
          var beaconIcon = L.divIcon({
            className: "pinn-beacon-marker",
            html: '<div style="position:relative;width:36px;height:36px;display:flex;align-items:center;justify-content:center">' +
                  '<span style="position:absolute;width:36px;height:36px;border-radius:50%;background:#ec4899;opacity:0.4;animation:pinnPulse 1.8s infinite ease-out"></span>' +
                  '<span style="position:absolute;width:24px;height:24px;border-radius:50%;background:#8b5cf6;opacity:0.6"></span>' +
                  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#ffffff" stroke-width="2.5"><circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/></svg>' +
                  '</div>',
            iconSize: [36, 36],
            iconAnchor: [18, 18]
          });

          var marker = L.marker(ptCoords, { icon: beaconIcon, title: "PINN Origin Point " + siteLabel });
          var popupHtml =
            '<div style="font-size:12px;min-width:240px;color:var(--text-primary,#f8fafc)">' +
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">' +
            '<span style="background:#ec4899;color:#ffffff;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:900">PINN REVERSE ORIGIN</span>' +
            '<span style="font-weight:800;color:#ec4899;font-size:12px">' + UI.esc(props.site_id || "") + '</span>' +
            '</div>' +
            '<strong>' + UI.esc(props.label || "Upstream eDNA Release Point") + '</strong><br>' +
            '<div style="margin-top:6px;font-size:11px;line-height:1.6;color:var(--text-secondary,#cbd5e1)">' +
            '📍 <strong>Location:</strong> ' + ptCoords[0] + ', ' + ptCoords[1] + '<br>' +
            '⚠️ <strong>Map Uncertainty Margin:</strong> Factored into bounding ellipse<br>' +
            '</div>' +
            '</div>';

          marker.bindPopup(popupHtml);
          marker.bindTooltip("⚡ " + UI.esc(props.label || "PINN Origin"), { direction: "top" });
          self.addLayer(marker);
        }
      });

    }
  });

  global.BioRadarMap = {
    BASEMAPS: BASEMAPS,
    prefersDarkTiles: prefersDarkTiles,
    FullscreenControl: FullscreenControl,
    MeasureControl: MeasureControl,
    MapLegendControl: MapLegendControl,
    ClusterLayer: ClusterLayer,
    HeatLayer: HeatLayer,
    HydroCorridorLayer: HydroCorridorLayer,
    RecommendedSiteLayer: RecommendedSiteLayer,
    PINNPlumeLayer: PINNPlumeLayer,
    timeline: timeline
  };

})(window);



