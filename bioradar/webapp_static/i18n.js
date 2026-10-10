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

      "analyze.title": "Upload your sequencing data",
      "analyze.lede": "Drop a folder of paired-end FASTQ files. BioRadar reads the primers, read length and quality encoding from the data itself, configures the pipeline, and returns a species report with a map.",
      "analyze.drop": "Drop your dataset folder here",
      "analyze.selectFolder": "Select folder",
      "analyze.selectFiles": "Select files",
      "analyze.note": "Paired-end FASTQ — an R1 and an R2 file for every sample",
      "analyze.datasets": "Your datasets",
      "analyze.datasetsHint": "Checked automatically before they can run",
      "analyze.name": "Dataset name",
      "analyze.location": "Location",
      "analyze.optional": "optional",
      "analyze.advanced": "Advanced — override auto-detection",
      "analyze.fprimer": "Forward primer",
      "analyze.rprimer": "Reverse primer",
      "analyze.truncF": "Truncate forward",
      "analyze.truncR": "Truncate reverse",
      "analyze.upload": "Upload and analyze",
      "analyze.clear": "Clear",
      "analyze.run": "Analyze",
      "analyze.remove": "Remove",
      "analyze.queue": "Queue",

      "monitor.title": "Pipeline monitor",
      "monitor.lede": "Every step of the bioinformatics workflow, live. Watch primers being trimmed, reads denoised into sequence variants, and taxonomy assigned.",
      "monitor.noRuns": "Nothing running",
      "monitor.noRunsBody": "Start an analysis from the Analyze tab and each pipeline step will appear here as it executes.",
      "monitor.cancel": "Cancel run",
      "monitor.log": "Pipeline log",
      "monitor.queued": "Queued",
      "monitor.position": "position in queue",

      "results.title": "Results",
      "results.lede": "What was found, where, and how confident the classifier was.",
      "results.namedSpecies": "Named species",
      "results.phyla": "Phyla",
      "results.samples": "Samples",
      "results.detections": "Detections",
      "results.unnamed": "Unnamed sp.",
      "results.sites": "Sites",
      "results.composition": "Composition by phylum",
      "results.inventory": "Species inventory",
      "results.map": "Sampling sites",
      "results.export": "Export",
      "results.provenance": "Provenance",
      "results.clear": "Clear results",

      "compare.title": "Site comparison",
      "compare.lede": "Biodiversity is a comparative question. Pick up to five sites and see how they differ across six dimensions at once.",
      "compare.pick": "Choose sites to compare",
      "compare.needTwo": "Select at least two sites",
      "compare.needTwoBody": "A radar chart of one site is a shape with nothing to compare it to.",

      "alerts.title": "Alerts and verification",
      "alerts.lede": "Species of concern detected in your data, and what field officers found when they went to look.",
      "alerts.none": "No species of concern",
      "alerts.noneBody": "Nothing in this analysis matched the watchlist. That is a result, not an absence of one.",
      "alerts.verify": "Record field check",
      "alerts.reads": "reads",
      "alerts.confidence": "confidence",
      "alerts.sites": "sites",

      "verify.title": "Record a field check",
      "verify.species": "Species",
      "verify.site": "Site",
      "verify.outcome": "What did you find?",
      "verify.confirmed": "Confirmed — the species is there",
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
      "state.noDataBody": "Upload a folder of FASTQ files above and it will appear here, configured and ready to run.",
      "state.noResults": "No analyses yet",
      "state.noResultsBody": "Results are held in memory for this session only and are not stored between restarts.",
      "state.noSpecies": "No species detected in this sample",
      "state.noSpeciesBody": "This can mean low DNA concentration, a failed extraction, or that the reference database does not cover what is present. Consider resampling, or check the unassigned read fraction.",
      "state.lowConfidence": "All detections are low-confidence",
      "state.lowConfidenceBody": "Nothing here clears the threshold for field action. Expert review is recommended before acting on any of it.",
      "state.offline": "You are offline. Showing the last data this page received.",
      "state.error": "Could not load this",
      "state.retry": "Retry",
      "state.failed": "Pipeline failed",

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

      "analyze.title": "अपना सीक्वेंसिंग डेटा अपलोड करें",
      "analyze.lede": "पेयर्ड-एंड FASTQ फ़ाइलों का फ़ोल्डर यहाँ छोड़ें। BioRadar डेटा से ही प्राइमर, रीड लंबाई और क्वालिटी एन्कोडिंग पढ़ता है, पाइपलाइन कॉन्फ़िगर करता है, और नक्शे के साथ प्रजाति रिपोर्ट देता है।",
      "analyze.drop": "अपना डेटासेट फ़ोल्डर यहाँ छोड़ें",
      "analyze.selectFolder": "फ़ोल्डर चुनें",
      "analyze.selectFiles": "फ़ाइलें चुनें",
      "analyze.note": "पेयर्ड-एंड FASTQ — हर सैंपल के लिए एक R1 और एक R2 फ़ाइल",
      "analyze.datasets": "आपके डेटासेट",
      "analyze.datasetsHint": "चलाने से पहले अपने आप जाँचे जाते हैं",
      "analyze.name": "डेटासेट का नाम",
      "analyze.location": "स्थान",
      "analyze.optional": "वैकल्पिक",
      "analyze.advanced": "उन्नत — स्वतः-पहचान बदलें",
      "analyze.fprimer": "फ़ॉरवर्ड प्राइमर",
      "analyze.rprimer": "रिवर्स प्राइमर",
      "analyze.truncF": "फ़ॉरवर्ड ट्रंकेट",
      "analyze.truncR": "रिवर्स ट्रंकेट",
      "analyze.upload": "अपलोड और विश्लेषण",
      "analyze.clear": "साफ़ करें",
      "analyze.run": "विश्लेषण करें",
      "analyze.remove": "हटाएँ",
      "analyze.queue": "कतार में डालें",

      "monitor.title": "पाइपलाइन निगरानी",
      "monitor.lede": "बायोइन्फ़ॉर्मैटिक्स वर्कफ़्लो का हर चरण, लाइव। प्राइमर ट्रिमिंग, रीड डीनॉइज़िंग और वर्गीकरण होते हुए देखें।",
      "monitor.noRuns": "कुछ नहीं चल रहा",
      "monitor.noRunsBody": "विश्लेषण टैब से विश्लेषण शुरू करें; हर चरण यहाँ दिखाई देगा।",
      "monitor.cancel": "रन रद्द करें",
      "monitor.log": "पाइपलाइन लॉग",
      "monitor.queued": "कतार में",
      "monitor.position": "कतार में स्थान",

      "results.title": "परिणाम",
      "results.lede": "क्या मिला, कहाँ मिला, और वर्गीकरणकर्ता कितना आश्वस्त था।",
      "results.namedSpecies": "नामित प्रजातियाँ",
      "results.phyla": "संघ",
      "results.samples": "सैंपल",
      "results.detections": "पहचानें",
      "results.unnamed": "अनामित sp.",
      "results.sites": "स्थल",
      "results.composition": "संघ के अनुसार संरचना",
      "results.inventory": "प्रजाति सूची",
      "results.map": "नमूना स्थल",
      "results.export": "निर्यात",
      "results.provenance": "उद्गम",
      "results.clear": "परिणाम साफ़ करें",

      "compare.title": "स्थलों की तुलना",
      "compare.lede": "जैवविविधता तुलनात्मक प्रश्न है। पाँच तक स्थल चुनें और छह आयामों में अंतर एक साथ देखें।",
      "compare.pick": "तुलना के लिए स्थल चुनें",
      "compare.needTwo": "कम से कम दो स्थल चुनें",
      "compare.needTwoBody": "एक ही स्थल का रडार चार्ट तुलना के लिए कुछ नहीं देता।",

      "alerts.title": "चेतावनी और सत्यापन",
      "alerts.lede": "आपके डेटा में मिली चिंताजनक प्रजातियाँ, और क्षेत्र अधिकारियों को मौके पर क्या मिला।",
      "alerts.none": "कोई चिंताजनक प्रजाति नहीं",
      "alerts.noneBody": "इस विश्लेषण में वॉचलिस्ट से कुछ मेल नहीं खाया। यह भी एक परिणाम है।",
      "alerts.verify": "क्षेत्र जाँच दर्ज करें",
      "alerts.reads": "रीड्स",
      "alerts.confidence": "विश्वास",
      "alerts.sites": "स्थल",

      "verify.title": "क्षेत्र जाँच दर्ज करें",
      "verify.species": "प्रजाति",
      "verify.site": "स्थल",
      "verify.outcome": "आपको क्या मिला?",
      "verify.confirmed": "पुष्टि — प्रजाति वहाँ है",
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
      "state.noDataBody": "ऊपर FASTQ फ़ाइलों का फ़ोल्डर अपलोड करें; वह यहाँ कॉन्फ़िगर होकर दिखेगा।",
      "state.noResults": "अभी कोई विश्लेषण नहीं",
      "state.noResultsBody": "परिणाम केवल इस सत्र की मेमोरी में रहते हैं, पुनः आरंभ पर सहेजे नहीं जाते।",
      "state.noSpecies": "इस सैंपल में कोई प्रजाति नहीं मिली",
      "state.noSpeciesBody": "इसका अर्थ कम DNA सांद्रता, असफल निष्कर्षण, या यह हो सकता है कि संदर्भ डेटाबेस में ये प्रजातियाँ नहीं हैं। पुनः नमूना लेने पर विचार करें।",
      "state.lowConfidence": "सभी पहचानें कम-विश्वास वाली हैं",
      "state.lowConfidenceBody": "यहाँ कुछ भी क्षेत्रीय कार्रवाई की सीमा पार नहीं करता। कार्रवाई से पहले विशेषज्ञ समीक्षा लें।",
      "state.offline": "आप ऑफ़लाइन हैं। पिछला प्राप्त डेटा दिखाया जा रहा है।",
      "state.error": "इसे लोड नहीं कर सके",
      "state.retry": "फिर कोशिश करें",
      "state.failed": "पाइपलाइन विफल",

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

  function restore() {
    var saved = null;
    try { saved = localStorage.getItem("bioradar.lang"); } catch (e) { /* private mode */ }
    setLanguage(saved || "en");
  }

  global.BioRadarI18n = {
    t: t,
    setLanguage: setLanguage,
    language: language,
    restore: restore,
    available: [
      { code: "en", label: "English", short: "EN" },
      { code: "hi", label: "हिन्दी", short: "हिन्दी" }
    ]
  };
})(window);
