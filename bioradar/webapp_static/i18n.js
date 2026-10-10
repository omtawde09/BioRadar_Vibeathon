/* English / हिन्दी.

   GIGW (Guidelines for Indian Government Websites) requires Hindi, and the
   primary user in this project's own framing is an Indian forest officer who
   may well read Hindi more comfortably than English. The gap analysis marks it
   Essential; it is.

   i18next is the guide's recommendation and would be right in a bundled app.
   Here it would be a 40 kB dependency to look up strings in a flat object, so
   this is the flat object.

   Two rules kept throughout:
     * Scientific names are never translated. Binomial nomenclature is
       language-independent by design and "Gambusia holbrooki" is the same in
       every locale.
     * Technical terms that have no settled Hindi equivalent (FASTQ, DADA2,
       ASV, Darwin Core) stay in Latin script inside a Devanagari sentence.
       Inventing a translation for them would be less clear, not more. */

(function (global) {
  "use strict";

  var STRINGS = {
    en: {
      "app.subtitle": "eDNA Biodiversity Intelligence",
      "nav.home": "Home",
      "nav.analyze": "Analyze",
      "nav.monitor": "Monitor",
      "nav.results": "Results",
      "nav.compare": "Compare",
      "nav.alerts": "Alerts",
      "nav.settings": "Settings",

      "analyze.title": "Upload your DNA files",
      "analyze.lede": "Drop a folder of DNA files from a sequencing machine. BioRadar reads the settings from the files themselves. It then gives you a list of the fish and other animals found, with a map.",
      "analyze.drop": "Drop your folder here",
      "analyze.selectFolder": "Select folder",
      "analyze.selectFiles": "Select files",
      "analyze.note": "Each sample needs two files, named R1 and R2",
      "analyze.datasets": "Your data sets",
      "analyze.datasetsHint": "Each one is checked before it can run",
      "analyze.name": "Dataset name",
      "analyze.location": "Location",
      "analyze.optional": "optional",
      "analyze.advanced": "Advanced: change the automatic settings",
      "analyze.fprimer": "Start marker (forward primer)",
      "analyze.rprimer": "End marker (reverse primer)",
      "analyze.truncF": "Cut the first file at (letters)",
      "analyze.truncR": "Cut the second file at (letters)",
      "analyze.upload": "Upload and analyze",
      "analyze.clear": "Clear",
      "analyze.run": "Analyze",
      "analyze.remove": "Remove",
      "analyze.queue": "Queue",

      "monitor.title": "Progress of the analysis",
      "monitor.lede": "Every step, live. Watch the DNA being cleaned, grouped and matched to animal names.",
      "monitor.noRuns": "Nothing running",
      "monitor.noRunsBody": "Start from the Analyze tab. Each step will show here as it runs.",
      "monitor.cancel": "Cancel run",
      "monitor.log": "Step-by-step log",
      "monitor.queued": "Queued",
      "monitor.position": "position in queue",

      "results.title": "Results",
      "results.lede": "What was found, where, and how sure each match is.",
      "results.namedSpecies": "Animals named",
      "results.phyla": "Animal groups",
      "results.samples": "Samples",
      "results.detections": "Times found",
      "results.unnamed": "Not named yet",
      "results.sites": "Places",
      "results.composition": "Animal groups found",
      "results.inventory": "Full list of animals",
      "results.map": "Where the samples were taken",
      "results.export": "Download",
      "results.provenance": "Where this result came from",
      "results.clear": "Clear results",

      "compare.title": "Site comparison",
      "compare.lede": "Pick up to five places and see how they differ.",
      "compare.pick": "Choose sites to compare",
      "compare.needTwo": "Select at least two sites",
      "compare.needTwoBody": "One place on its own has nothing to be compared with.",

      "alerts.title": "Alerts and field checks",
      "alerts.lede": "Animals that need attention, found in your data, and what field officers saw when they went to look.",
      "alerts.none": "No animals of concern",
      "alerts.noneBody": "Nothing in this analysis matched the watch list. That is a real result.",
      "alerts.verify": "Record field check",
      "alerts.reads": "DNA pieces",
      "alerts.confidence": "how sure",
      "alerts.sites": "sites",

      "verify.title": "Record a field check",
      "verify.species": "Animal",
      "verify.site": "Site",
      "verify.outcome": "What did you find?",
      "verify.confirmed": "Confirmed: the animal is there",
      "verify.notFound": "Searched properly, did not find it",
      "verify.misidentified": "Something else was there",
      "verify.uncertain": "Surveyed, inconclusive",
      "verify.observedName": "What was actually there",
      "verify.observer": "Your name",
      "verify.notes": "Notes",
      "verify.submit": "Save field check",
      "verify.cancel": "Cancel",
      "verify.saved": "Field check recorded",

      "settings.title": "Settings and diagnostics",
      "settings.appearance": "Appearance",
      "settings.theme": "Light mode",
      "settings.themeHint": "Dark is the default — it stays readable in direct sunlight and uses less battery.",
      "settings.language": "भाषा / Language",
      "settings.health": "System health",
      "settings.channels": "Alert channels",
      "settings.errors": "Recent errors",
      "settings.noErrors": "No errors recorded.",

      "state.noData": "No datasets yet",
      "state.noDataBody": "Upload a folder of DNA files above and it will appear here, ready to run.",
      "state.noResults": "No analyses yet",
      "state.noResultsBody": "Results are held in memory for this session only and are not stored between restarts.",
      "state.noSpecies": "No animals found in this sample",
      "state.noSpeciesBody": "Possible reasons: very little DNA, a failed test, or animals that are not in the list of known animals. Consider taking a new sample.",
      "state.lowConfidence": "Every match is weak",
      "state.lowConfidenceBody": "Nothing here is strong enough to act on. Ask an expert before you act.",
      "state.offline": "You are offline. Showing the last data this page received.",
      "state.error": "Could not load this",
      "state.retry": "Retry",
      "state.failed": "The analysis failed",

      "common.close": "Close",
      "common.cancel": "Cancel",
      "common.loading": "Loading",
      "common.of": "of"
    },

    hi: {
      "app.subtitle": "eDNA जैवविविधता इंटेलिजेंस",
      "nav.home": "मुख्य पृष्ठ",
      "nav.analyze": "विश्लेषण",
      "nav.monitor": "निगरानी",
      "nav.results": "परिणाम",
      "nav.compare": "तुलना",
      "nav.alerts": "चेतावनी",
      "nav.settings": "सेटिंग्स",

      "analyze.title": "अपनी DNA फ़ाइलें अपलोड करें",
      "analyze.lede": "सीक्वेंसिंग मशीन से मिली DNA फ़ाइलों का फ़ोल्डर यहाँ छोड़ें। BioRadar सेटिंग फ़ाइलों से खुद पढ़ लेता है। फिर वह मिली मछलियों और दूसरे जानवरों की सूची नक्शे के साथ देता है।",
      "analyze.drop": "अपना फ़ोल्डर यहाँ छोड़ें",
      "analyze.selectFolder": "फ़ोल्डर चुनें",
      "analyze.selectFiles": "फ़ाइलें चुनें",
      "analyze.note": "हर नमूने के लिए दो फ़ाइलें चाहिए, R1 और R2",
      "analyze.datasets": "आपके डेटा सेट",
      "analyze.datasetsHint": "चलाने से पहले हर एक की जाँच होती है",
      "analyze.name": "डेटासेट का नाम",
      "analyze.location": "स्थान",
      "analyze.optional": "वैकल्पिक",
      "analyze.advanced": "उन्नत: अपने आप तय सेटिंग बदलें",
      "analyze.fprimer": "शुरुआती निशान (फ़ॉरवर्ड प्राइमर)",
      "analyze.rprimer": "अंतिम निशान (रिवर्स प्राइमर)",
      "analyze.truncF": "पहली फ़ाइल यहाँ काटें (अक्षर)",
      "analyze.truncR": "दूसरी फ़ाइल यहाँ काटें (अक्षर)",
      "analyze.upload": "अपलोड और विश्लेषण",
      "analyze.clear": "साफ़ करें",
      "analyze.run": "विश्लेषण करें",
      "analyze.remove": "हटाएँ",
      "analyze.queue": "कतार में डालें",

      "monitor.title": "विश्लेषण की प्रगति",
      "monitor.lede": "हर चरण, लाइव। देखें कि DNA कैसे साफ़ होता है, समूहों में बँटता है और जानवरों के नामों से मिलाया जाता है।",
      "monitor.noRuns": "कुछ नहीं चल रहा",
      "monitor.noRunsBody": "विश्लेषण टैब से शुरू करें। हर चरण चलते समय यहाँ दिखेगा।",
      "monitor.cancel": "रन रद्द करें",
      "monitor.log": "चरण-दर-चरण लॉग",
      "monitor.queued": "कतार में",
      "monitor.position": "कतार में स्थान",

      "results.title": "परिणाम",
      "results.lede": "क्या मिला, कहाँ मिला, और हर मेल पर कितना भरोसा है।",
      "results.namedSpecies": "नाम पाए जानवर",
      "results.phyla": "जानवरों के समूह",
      "results.samples": "नमूने",
      "results.detections": "कितनी बार मिले",
      "results.unnamed": "अभी नाम नहीं मिला",
      "results.sites": "स्थान",
      "results.composition": "मिले जानवरों के समूह",
      "results.inventory": "जानवरों की पूरी सूची",
      "results.map": "नमूने कहाँ लिए गए",
      "results.export": "डाउनलोड",
      "results.provenance": "यह परिणाम कहाँ से आया",
      "results.clear": "परिणाम साफ़ करें",

      "compare.title": "स्थलों की तुलना",
      "compare.lede": "पाँच तक स्थान चुनें और देखें कि वे कैसे अलग हैं।",
      "compare.pick": "तुलना के लिए स्थल चुनें",
      "compare.needTwo": "कम से कम दो स्थल चुनें",
      "compare.needTwoBody": "अकेले एक स्थान की तुलना किससे होगी।",

      "alerts.title": "चेतावनी और मौके की जाँच",
      "alerts.lede": "आपके डेटा में मिले ध्यान देने लायक जानवर, और मौके पर जाने पर क्षेत्र अधिकारियों ने क्या देखा।",
      "alerts.none": "चिंता का कोई जानवर नहीं",
      "alerts.noneBody": "इस विश्लेषण में निगरानी सूची से कुछ नहीं मिला। यह एक असली परिणाम है।",
      "alerts.verify": "क्षेत्र जाँच दर्ज करें",
      "alerts.reads": "DNA टुकड़े",
      "alerts.confidence": "कितना भरोसा",
      "alerts.sites": "स्थल",

      "verify.title": "क्षेत्र जाँच दर्ज करें",
      "verify.species": "जानवर",
      "verify.site": "स्थल",
      "verify.outcome": "आपको क्या मिला?",
      "verify.confirmed": "पुष्टि हुई: जानवर वहाँ है",
      "verify.notFound": "ठीक से खोजा, नहीं मिली",
      "verify.misidentified": "वहाँ कुछ और था",
      "verify.uncertain": "सर्वेक्षण किया, अनिर्णीत",
      "verify.observedName": "वास्तव में क्या था",
      "verify.observer": "आपका नाम",
      "verify.notes": "टिप्पणियाँ",
      "verify.submit": "क्षेत्र जाँच सहेजें",
      "verify.cancel": "रद्द करें",
      "verify.saved": "क्षेत्र जाँच दर्ज हुई",

      "settings.title": "सेटिंग्स और निदान",
      "settings.appearance": "रूप",
      "settings.theme": "लाइट मोड",
      "settings.themeHint": "डार्क डिफ़ॉल्ट है — तेज़ धूप में पढ़ने योग्य रहता है और बैटरी कम खर्च करता है।",
      "settings.language": "भाषा / Language",
      "settings.health": "सिस्टम स्वास्थ्य",
      "settings.channels": "चेतावनी चैनल",
      "settings.errors": "हाल की त्रुटियाँ",
      "settings.noErrors": "कोई त्रुटि दर्ज नहीं।",

      "state.noData": "अभी कोई डेटासेट नहीं",
      "state.noDataBody": "ऊपर DNA फ़ाइलों का फ़ोल्डर अपलोड करें; वह यहाँ चलने के लिए तैयार दिखेगा।",
      "state.noResults": "अभी कोई विश्लेषण नहीं",
      "state.noResultsBody": "परिणाम केवल इस सत्र की मेमोरी में रहते हैं, पुनः आरंभ पर सहेजे नहीं जाते।",
      "state.noSpecies": "इस नमूने में कोई जानवर नहीं मिला",
      "state.noSpeciesBody": "संभावित कारण: बहुत कम DNA, असफल जाँच, या ऐसे जानवर जो ज्ञात जानवरों की सूची में नहीं हैं। नया नमूना लेने पर विचार करें।",
      "state.lowConfidence": "हर मेल कमज़ोर है",
      "state.lowConfidenceBody": "यहाँ कुछ भी इतना पक्का नहीं कि उस पर कार्रवाई हो। कार्रवाई से पहले किसी विशेषज्ञ से पूछें।",
      "state.offline": "आप ऑफ़लाइन हैं। पिछला प्राप्त डेटा दिखाया जा रहा है।",
      "state.error": "इसे लोड नहीं कर सके",
      "state.retry": "फिर कोशिश करें",
      "state.failed": "विश्लेषण असफल रहा",

      "common.close": "बंद करें",
      "common.cancel": "रद्द करें",
      "common.loading": "लोड हो रहा है",
      "common.of": "में से"
    }
  };

  var current = "en";

  function t(key, fallback) {
    var table = STRINGS[current] || STRINGS.en;
    if (Object.prototype.hasOwnProperty.call(table, key)) return table[key];
    // Falling back to English rather than showing the raw key: a missing Hindi
    // string should degrade to a readable sentence, not to "alerts.noneBody".
    if (Object.prototype.hasOwnProperty.call(STRINGS.en, key)) return STRINGS.en[key];
    return fallback !== undefined ? fallback : key;
  }

  function setLanguage(lang) {
    var wanted = STRINGS[lang] ? lang : "en";
    // Switching to the language already in use rebuilds the entire shell for
    // no reason. Defence in depth: a stray caller cannot turn a no-op into a
    // full teardown, let alone into a loop.
    if (wanted === current && document.body.getAttribute("data-lang") === wanted) return;
    current = wanted;
    document.body.setAttribute("data-lang", current);
    document.documentElement.setAttribute("lang", current);
    try { localStorage.setItem("bioradar.lang", current); } catch (e) { /* private mode */ }
    document.dispatchEvent(new CustomEvent("bioradar:language", { detail: current }));
  }

  function language() { return current; }

  /* A feature module adds its own strings without editing this file's tables.
     Existing keys are never overwritten. */
  function addStrings(lang, strings) {
    var table = STRINGS[lang];
    if (!table || !strings) return;
    Object.keys(strings).forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(table, key)) table[key] = strings[key];
    });
  }

  function restore() {
    var saved = null;
    try { saved = localStorage.getItem("bioradar.lang"); } catch (e) { /* private mode */ }
    setLanguage(saved || "en");
  }

  global.BioRadarI18n = {
    t: t,
    setLanguage: setLanguage,
    language: language,
    addStrings: addStrings,
    restore: restore,
    available: [
      { code: "en", label: "English", short: "EN" },
      { code: "hi", label: "हिन्दी", short: "हिन्दी" }
    ]
  };
})(window);
