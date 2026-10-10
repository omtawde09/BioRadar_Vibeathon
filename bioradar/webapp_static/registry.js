/* Feature registry — the slot-based extensibility architecture.

   The UI guide calls this "the single most important architectural decision",
   and the test of it is simple: adding the next feature must not require
   editing the shell, the sidebar, the tab bar, or any existing feature.

   A feature is a module that calls registerFeature() once. The shell reads the
   registry and renders whatever is in it. Nothing imports a feature by name.

   The guide's example is React with lazy(). There is no bundler here, so a
   feature supplies `mount(container, ctx)` instead of a component — same
   contract, same isolation, one less toolchain. Views are mounted the first
   time they are shown, which is what lazy() was buying. */

(function (global) {
  "use strict";

  var SLOTS = [
    "sidebar-nav",   // navigation entries (desktop rail)
    "header-action", // appbar controls: theme, language, health
    "main-view",     // full-page views
    "right-panel",   // slide-in detail panel / bottom sheet
    "bottom-tab",    // mobile tab bar
    "overlay"        // modals, command palettes
  ];

  var features = [];

  function registerFeature(feature) {
    if (!feature || !feature.id) {
      throw new Error("registerFeature: a feature needs an id");
    }
    if (SLOTS.indexOf(feature.slot) === -1) {
      throw new Error("registerFeature: unknown slot " + feature.slot);
    }
    if (features.some(function (f) { return f.id === feature.id; })) {
      // Registering twice is always a mistake — a duplicated id silently
      // shadows one of the two features and the symptom appears elsewhere.
      throw new Error("registerFeature: duplicate id " + feature.id);
    }
    features.push({
      id: feature.id,
      name: feature.name || feature.id,
      // Deferred so a feature can register before i18n has a language set.
      label: feature.label || function () { return feature.name || feature.id; },
      slot: feature.slot,
      icon: feature.icon || "",
      order: typeof feature.order === "number" ? feature.order : 100,
      mount: feature.mount || null,
      refresh: feature.refresh || null,
      onShow: feature.onShow || null,
      onHide: feature.onHide || null,
      badge: feature.badge || null,
      mobileOnly: !!feature.mobileOnly,
      desktopOnly: !!feature.desktopOnly,
      primary: !!feature.primary,   // shown in the 4-slot mobile tab bar
      mounted: false,
      node: null
    });
    features.sort(function (a, b) { return a.order - b.order; });
  }

  function bySlot(slot) {
    return features.filter(function (f) { return f.slot === slot; });
  }

  function get(id) {
    return features.filter(function (f) { return f.id === id; })[0] || null;
  }

  global.BioRadarRegistry = {
    SLOTS: SLOTS,
    registerFeature: registerFeature,
    bySlot: bySlot,
    get: get,
    all: function () { return features.slice(); }
  };
})(window);
