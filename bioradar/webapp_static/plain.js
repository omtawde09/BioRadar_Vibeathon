/* Plain words: a short "In plain words" box at the top of each page, and a glossary page.

   Written for a reader who is not a scientist. Every page gets one box that says what the page
   shows and what to do with it. The Results page gets a second, computed from the run itself.
   The Review view writes its own boxes (adjudicate.js), because they depend on the open tab.

   Nothing in the shell was edited to do this: the glossary is a normal registry feature, and the
   boxes are added by watching the view host. English and Hindi go through BioRadarI18n. */

(function (global) {
  "use strict";

  var Registry = global.BioRadarRegistry;
  var UI = global.BioRadarUI;
  var I18n = global.BioRadarI18n;
  var esc = UI.esc;

  var TXT = {
    en: {
      "plain.head": "In plain words",
      "plain.analyze": "Here you give BioRadar your DNA files. It finds out which fish and other animals left their DNA in the water. Drop a folder, press Analyze, then open Results.",
      "plain.monitor": "This page shows the analysis while it runs, step by step. You do not need to do anything. When it is done, the answer is on the Results page.",
      "plain.compare": "Pick two or more places and see how alike they are. A place with many different animals is usually healthier.",
      "plain.alerts": "This page lists animals that need attention, such as fish that do not belong in local water. After you visit a place, you can record what you found.",
      "plain.settings": "Change how the app looks, pick English or Hindi, and check that everything is working.",
      "plain.results.main": "This analysis looked at {samples} samples. It named {named} kinds of animals, in {groups} animal groups. The most common one was {top}.",
      "plain.results.unnamed": "The DNA of {n} other kind(s) could not be named yet.",
      "plain.results.care": "A match is a best match from a list of known animals, so check any important finding in the field before you act.",
      "plain.results.none": "No animals could be named in this analysis.",
      "plain.nav.words": "Words",
      "plain.words.title": "Words explained",
      "plain.words.lede": "The short meaning of every special word used in this app.",
      "plain.words.how": "How to read the numbers",
      "plain.words.how1": "A share is a share of DNA, not a count of animals.",
      "plain.words.how2": "A match score near 1 means a strong match. It is a rule of thumb, not a true chance.",
      "plain.words.how3": "\"Not found\" does not mean \"not there\". A place can hold an animal that left too little DNA to be seen.",
      "plain.words.how4": "Anything marked \"needs a check\" is never counted as found until a person checks it."
    },
    hi: {
      "plain.head": "सरल शब्दों में",
      "plain.analyze": "यहाँ आप BioRadar को अपनी DNA फ़ाइलें देते हैं। वह पता लगाता है कि किन मछलियों और दूसरे जानवरों ने पानी में अपना DNA छोड़ा। फ़ोल्डर छोड़ें, विश्लेषण दबाएँ, फिर परिणाम खोलें।",
      "plain.monitor": "यह पन्ना चलते समय विश्लेषण को चरण-दर-चरण दिखाता है। आपको कुछ करना नहीं है। पूरा होने पर उत्तर परिणाम पन्ने पर मिलेगा।",
      "plain.compare": "दो या अधिक स्थान चुनें और देखें कि वे कितने मिलते-जुलते हैं। जहाँ बहुत तरह के जानवर हों, वह जगह आमतौर पर ज़्यादा स्वस्थ होती है।",
      "plain.alerts": "यह पन्ना ध्यान देने लायक जानवरों की सूची देता है, जैसे वे मछलियाँ जो स्थानीय पानी की नहीं हैं। किसी स्थान पर जाने के बाद आप वहाँ जो मिला वह दर्ज कर सकते हैं।",
      "plain.settings": "ऐप का रूप बदलें, अंग्रेज़ी या हिंदी चुनें, और जाँचें कि सब कुछ ठीक चल रहा है।",
      "plain.results.main": "इस विश्लेषण ने {samples} नमूने देखे। इसने जानवरों के {groups} समूहों में {named} तरह के जानवरों के नाम बताए। सबसे आम {top} था।",
      "plain.results.unnamed": "{n} और तरह के DNA को अभी नाम नहीं दिया जा सका।",
      "plain.results.care": "मेल जाने-पहचाने जानवरों की सूची से सबसे अच्छा मेल है, इसलिए किसी भी ज़रूरी बात पर कार्रवाई से पहले मौके पर जाँच लें।",
      "plain.results.none": "इस विश्लेषण में किसी जानवर का नाम नहीं बताया जा सका।",
      "plain.nav.words": "शब्द",
      "plain.words.title": "शब्दों के अर्थ",
      "plain.words.lede": "इस ऐप में आने वाले हर खास शब्द का छोटा अर्थ।",
      "plain.words.how": "संख्याएँ कैसे पढ़ें",
      "plain.words.how1": "हिस्सा DNA का हिस्सा है, जानवरों की गिनती नहीं।",
      "plain.words.how2": "1 के पास मिलान स्कोर का मतलब मज़बूत मेल है। यह मोटा अंदाज़ा है, सच्ची संभावना नहीं।",
      "plain.words.how3": "\"नहीं मिला\" का मतलब \"वहाँ नहीं है\" नहीं होता। हो सकता है किसी जानवर ने इतना कम DNA छोड़ा हो कि वह दिखा ही नहीं।",
      "plain.words.how4": "\"जाँच ज़रूरी\" लिखी कोई भी चीज़ तब तक मिली हुई नहीं गिनी जाती जब तक कोई व्यक्ति उसे जाँच न ले।"
    }
  };
  if (I18n && I18n.addStrings) { I18n.addStrings("en", TXT.en); I18n.addStrings("hi", TXT.hi); }

  function T(key, vars) {
    var s = I18n ? I18n.t(key, TXT.en[key] !== undefined ? TXT.en[key] : key) : (TXT.en[key] || key);
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(String(vars[k])); });
    return s;
  }

  function box(html) {
    return '<aside class="plain-box" aria-label="' + esc(T("plain.head")) + '"><b>' + esc(T("plain.head")) +
      "</b><p>" + html + "</p></aside>";
  }

  /* A sentence about this run, built only from numbers the report already holds. */
  function resultsBox(report) {
    var top = (report.top_species || []).filter(function (s) { return !s.placeholder; })[0];
    if (!report.named_species || !top) return box(esc(T("plain.results.none")) + " " + esc(T("plain.results.care")));
    var parts = [T("plain.results.main", { samples: report.samples, named: report.named_species, groups: report.phyla, top: top.name })];
    if (report.placeholders) parts.push(T("plain.results.unnamed", { n: report.placeholders }));
    parts.push(T("plain.results.care"));
    return box(parts.map(esc).join(" "));
  }

  var GLOSSARY = ["edna", "piece", "marker", "list", "match", "score", "unknown", "dropped", "complex", "invasive", "retake", "mock", "share", "boundary"];

  function glossaryList() {
    return '<dl class="plain-gloss">' + GLOSSARY.map(function (id) {
      return "<dt>" + esc(T("rv.gl." + id + ".t")) + "</dt><dd>" + esc(T("rv.gl." + id + ".d")) + "</dd>";
    }).join("") + "</dl>";
  }

  Registry.registerFeature({
    id: "words", name: "Words", slot: "main-view", order: 70, icon: "inbox",
    label: function () { return T("plain.nav.words"); },
    mount: function (container) {
      container.innerHTML = '<div class="view-head"><div><h1>' + esc(T("plain.words.title")) + "</h1><p>" +
        esc(T("plain.words.lede")) + "</p></div></div>" +
        UI.card('<h2>' + esc(T("plain.words.how")) + "</h2><ul class=\"plain-list\"><li>" + esc(T("plain.words.how1")) + "</li><li>" +
          esc(T("plain.words.how2")) + "</li><li>" + esc(T("plain.words.how3")) + "</li><li>" + esc(T("plain.words.how4")) + "</li></ul>") +
        UI.card(glossaryList());
    }
  });

  /* The one-line box for each page that has no computed summary. */
  var PAGES = ["analyze", "monitor", "compare", "alerts", "settings"];

  function addBoxes() {
    PAGES.forEach(function (id) {
      var view = document.getElementById("view-" + id);
      if (!view || view.querySelector(":scope > .plain-box")) return;
      var head = view.querySelector(":scope > .view-head");
      if (!head) return;
      head.insertAdjacentHTML("afterend", box(esc(T("plain." + id))));
    });
  }

  var queued = false;
  function schedule() {
    if (queued) return;
    queued = true;
    setTimeout(function () { queued = false; addBoxes(); }, 0);  // not requestAnimationFrame: it never fires in a hidden tab
  }

  function watch() {
    var host = document.getElementById("viewHost");
    if (!host || !global.MutationObserver) return;
    new MutationObserver(schedule).observe(host, { childList: true, subtree: true });
    schedule();
  }
  // A language change keeps some views as they are, so the boxes are written again in the new language.
  document.addEventListener("bioradar:language", function () {
    setTimeout(function () {
      document.querySelectorAll(".view > .plain-box").forEach(function (node) { node.remove(); });
      addBoxes();
    }, 60);
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", watch);
  else watch();
  // The shell is built after this file loads; look again once the page has finished loading.
  global.addEventListener("load", watch);

  global.BioRadarPlain = { box: box, resultsBox: resultsBox, glossaryList: glossaryList };
})(window);
