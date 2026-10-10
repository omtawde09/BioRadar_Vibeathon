/* Review — one real sample, an honest answer.

   Sample quality summary -> species split / unknown review queue -> alert -> map ->
   officer report. Plus the data guard, the summer/winter slider, the alert log and
   the threshold table that explains every number. Registered through the same
   feature registry as every other view; nothing in the shell was edited.

   Language: every label goes through BioRadarI18n (English / हिन्दी). Scientific names,
   accession IDs and the sentences the analysis itself writes (verdict reasons, per-sequence
   drop reasons, alert actions) are shown as produced, in English. */

(function () {
  "use strict";

  var Registry = window.BioRadarRegistry;
  var UI = window.BioRadarUI;
  var I18n = window.BioRadarI18n;
  var esc = UI.esc;

  /* ── strings ────────────────────────────────────────────────────────── */

  var TXT = {
    en: {
      "rv.nav": "Review",
      "rv.title": "Sample review",
      "rv.lede": "Pick a real public sample. See what was kept, dropped or left unknown, why, and what the officer should do.",
      "rv.tabs.label": "Review sections",
      "rv.tab.sample": "Sample", "rv.tab.guard": "Data guard", "rv.tab.seasons": "Seasons & map",
      "rv.tab.alerts": "Alerts", "rv.tab.why": "Numbers & sources",
      "rv.notBuilt": "Results not built yet",
      "rv.notBuiltBody": "Run the one command that processes every real sample, then reload: python -m bioradar.adjudicate.runner all",
      "rv.couldNotLoad": "Could not load",
      "rv.couldNotProcess": "This sample could not be processed",
      "rv.realSample": "Real sample", "rv.rerun": "Re-run live", "rv.rerunTitle": "Run the full analysis now",
      "rv.whySample": "Why this sample:",
      "rv.running": "Running the full analysis live", "rv.loading": "Loading result",
      "rv.preRun": "pre-run result, loaded in {s} s", "rv.live": "computed live in {s} s",
      "rv.role.mixed": "Mixed community", "rv.role.poor": "Poor quality / low yield",
      "rv.role.unknowns": "Unknown fish & invasive species", "rv.role.field": "Field samples (summer / winter)",
      "rv.verdict.Usable": "Usable", "rv.verdict.Usable with caution": "Usable with caution", "rv.verdict.Retake sample": "Retake sample",
      "rv.level.CRITICAL": "CRITICAL", "rv.level.HIGH": "HIGH", "rv.level.WATCH": "WATCH",
      "rv.noTrigger": "NO TRIGGER", "rv.notChecked": "NOT CHECKED",
      "rv.noTrigger.head": "No listed invasive fish crossed the danger rule in this sample.",
      "rv.noTrigger.body": "Rule: a species-level call of a listed invasive fish with at least 10 reads. Not seen here; that does not prove the water is free of them.",
      "rv.notChecked.head": "Invasive-species rule not evaluated: this sample is a retake.",
      "rv.notChecked.body": "Too little usable DNA to say anything about invasive fish here.",
      "rv.pin": "Pin", "rv.reads": "reads", "rv.matchScore": "match score", "rv.notRecorded": "not recorded",
      "rv.summary": "Sample quality summary",
      "rv.kept": "Kept", "rv.unknown": "Unknown / review", "rv.dropped": "Dropped",
      "rv.distinct": "distinct sequences",
      "rv.stackLabel": "Kept, unknown and dropped share of reads",
      "rv.readsLine": "{reads} reads, {distinct} distinct sequences. Input read as {fmt} by content",
      "rv.noQuality": " (FASTA: no base-quality scores, so the quality filter was skipped)",
      "rv.sourceLine": ". Source: {project} · run {run} · collected {date}.",
      "rv.print": "Print officer report (PDF)", "rv.csv": "All dropped sequences (CSV)", "rv.sourceRecord": "Source record",
      "rv.dropWhy": "Why sequences were dropped", "rv.nothingDropped": "Nothing was dropped.",
      "rv.examples": "Examples with the written reason for each ({n} dropped sequences are listed in the CSV)",
      "rv.col.reads": "Reads", "rv.col.sequence": "Sequence", "rv.col.reason": "Reason",
      "rv.seq": "seq",
      "rv.reason.invalid_characters": "Not a DNA sequence", "rv.reason.too_short": "Short fragment",
      "rv.reason.too_many_n": "Too many N bases", "rv.reason.low_complexity": "Low complexity / repeat",
      "rv.reason.low_quality": "Low base quality", "rv.reason.singleton": "Seen once (probable error)",
      "rv.reason.human_contamination": "Human contamination", "rv.reason.unrelated": "Unrelated to any reference",
      "rv.speciesHead": "Species found and their shares",
      "rv.retake.head": "Retake sample", "rv.retake.body": "Too little usable DNA to report which fish are here. Nothing is guessed.",
      "rv.noSpecies": "No species-level detections.",
      "rv.invasive": "invasive", "rv.cannotSeparate": "cannot separate", "rv.identity": "identity", "rv.score": "score",
      "rv.speciesCount": "species",
      "rv.denom": "<b>How the share is calculated:</b> reads of the species ÷ {den} reads that could be named (species-level calls + groups the marker cannot separate). Left out of that denominator: {dropped} dropped reads and {novel} reads of sequences too different from the reference to name, out of {total} reads in the sample. A share is a proportion of DNA reads, not a count of animals or their biomass.",
      "rv.traceNote": "Species with fewer than 10 reads ({n}) are listed as trace, not as detections. Two species whose 12S sequence cannot be told apart are shown together, never forced to one name.",
      "rv.scoreNote": "Match score (0-1) is a heuristic built from identity and the gap to the next-best species: it falls 4 points per 1% of identity lost, is halved when a different species is almost as close, and is capped (0.99 for a species call, 0.60 for anything unconfirmed). It is not a calibrated probability.",
      "rv.src.title": "Source and metadata", "rv.src.sub": "Where this sample comes from",
      "rv.src.dataset": "Dataset", "rv.src.run": "Run / sample", "rv.src.alias": "alias",
      "rv.src.file": "Original file", "rv.src.marker": "Marker / assay", "rv.src.markerFallback": "see dataset record",
      "rv.src.reference": "Reference", "rv.src.collected": "Collected", "rv.src.place": "Place / pin",
      "rv.src.note": "These checks read only this record's own fields. Cross-record checks (duplicate IDs, boundary, species spelling) are in the Data guard tab.",
      "rv.chk.ok": "ok", "rv.chk.note": "note", "rv.chk.problem": "problem", "rv.chk.missing": "missing",
      "rv.chk.noDate": "no collection date recorded", "rv.chk.future": "date is in the future",
      "rv.chk.dateOk": "not in the future; precision: {p}", "rv.chk.yearOnly": " only, so it cannot be assigned to a season",
      "rv.chk.noPin": "no GPS pin recorded", "rv.chk.pinOk": "inside valid ranges", "rv.chk.pinLow": "; low precision: {n}",
      "rv.chk.pinBad": "outside valid latitude/longitude range",
      "rv.prec.day": "day", "rv.prec.month": "month", "rv.prec.year": "year",
      "rv.queue.head": "Review queue: sequences not called to a species",
      "rv.queue.none": "Nothing needs review.",
      "rv.queue.intro": "{n} sequences are not confirmed. Each shows its closest reference match, the <b>percent identity</b> (a measured similarity, not a probability) and a heuristic match score capped at 0.60, so none can pass as confirmed.",
      "rv.queue.ref": "Reference used: <b>{ref}</b>. Aligned coverage is <b>not provided</b> by the analysis (identity is measured over the whole read, so a short overlap lowers it instead of being hidden).",
      "rv.queue.closest": "Closest match", "rv.queue.state": "Review state", "rv.queue.whyUnknown": "Why unknown",
      "rv.queue.needsReview": "needs review", "rv.queue.check": "Check on NCBI", "rv.queue.showing": "Showing the 12 most abundant of {n}.",
      "rv.exp.count": "Check against what the source says was mixed", "rv.exp.comp": "Check against the source composition",
      "rv.exp.groups": "(plus {n} groups of species that 12S cannot separate)",
      "rv.exp.species": "Species", "rv.exp.expected": "Expected", "rv.exp.observed": "Observed", "rv.exp.result": "Result",
      "rv.map.head": "Where this sample was taken", "rv.map.noPin": "This record has no GPS pin, so it cannot be shown on the map.",
      "rv.map.note": "Note:", "rv.map.noFlag": "No invasive fish flagged",
      "rv.guard.title": "Data guard", "rv.guard.sub": "Real archive records, never edited",
      "rv.guard.clean": "database clean", "rv.guard.notClean": "database NOT clean",
      "rv.guard.checked": "Records checked", "rv.guard.kept": "Kept in clean store", "rv.guard.rejected": "Rejected", "rv.guard.merged": "Merged",
      "rv.guard.source": "Source: ENA project PRJEB108476 (snapshot md5 {md5}). Boundary: <b>{b}</b> ({src}). Today = {today}.",
      "rv.guard.post": "<b>Post-check on the clean store:</b> {dup} duplicate IDs, {out} outside the boundary, {fut} future-dated, {sp} unmerged double spellings across {n} records.",
      "rv.guard.rule.duplicate_id": "Duplicate sample ID", "rv.guard.rule.outside_boundary": "GPS pin outside boundary",
      "rv.guard.rule.no_coordinates": "No GPS pin", "rv.guard.rule.future_date": "Date in the future",
      "rv.guard.rule.double_spelling": "Species, two spellings",
      "rv.guard.nCase": "{n} {what}", "rv.guard.w.merged": "merged", "rv.guard.w.handled": "handled", "rv.guard.w.rejected": "rejected",
      "rv.guard.absent": "not in data",
      "rv.guard.noCase": "The real records contained no such case, so there is nothing to show. The rule is still active.",
      "rv.guard.every": "Every decision", "rv.guard.col.rule": "Rule", "rv.guard.col.action": "Action", "rv.guard.col.record": "Record",
      "rv.guard.first": "Showing the first 120 of {n} decisions.",
      "rv.season.none": "No summer/winter pair", "rv.season.noneBody": "No location in the processed samples has both seasons.",
      "rv.season.location": "Location", "rv.season.summer": "Summer", "rv.season.winter": "Winter",
      "rv.season.detectedIn": "Species detected ({s})", "rv.season.newVs": "Newly detected vs {s}", "rv.season.missing": "Not detected here, seen in {s}",
      "rv.season.reps": "{a} replicate sample(s) in {sa}, {b} in {sb}.",
      "rv.season.rule": "Season rule (set in thresholds.json):",
      "rv.season.print": "Print officer report for this site (PDF)", "rv.season.printHint": "One page: animals, risk, source and dates, uncertainty, what to do.",
      "rv.season.noPin": "No GPS pin recorded for this location.",
      "rv.season.newIn": "Newly detected in {s}", "rv.season.seenNot": "Seen in {o}, not detected in {s}", "rv.season.allIn": "Detected in {s} (all)",
      "rv.season.sLabel": "Season", "rv.season.speciesTip": "{s}: {n} species",
      "rv.season.care": "<b>Read this comparison with care.</b> Summer samples: {a} ({ar} reads named). Winter samples: {b} ({br} reads named).",
      "rv.season.depth": " Sequencing depth differs about {x}-fold.",
      "rv.season.careEnd": " A season with poorer reads can show fewer species because of the data, not because of the water.",
      "rv.season.none2": "None.", "rv.season.repl": "{r} reads, {n} replicate(s)",
      "rv.season.listed": "invasive-listed", "rv.season.listedTip": "Listed invasive fish; confirmed in an alert elsewhere in this project",
      "rv.alerts.mapHint": "One marker per distinct pin; colour = most severe alert there", "rv.alerts.mapHead": "Alert map",
      "rv.alerts.pins": "{n} pins. Samples whose source gave only a coarse coordinate share one pin.",
      "rv.alerts.logHint": "Dashboard banner + this log. No SMS or e-mail is sent.", "rv.alerts.logHead": "Alert log",
      "rv.alerts.col.level": "Level", "rv.alerts.col.alert": "Alert", "rv.alerts.col.pin": "Pin", "rv.alerts.col.sample": "Sample",
      "rv.alerts.col.analysis": "Analysis took", "rv.alerts.col.after": "Alert after result",
      "rv.alerts.foot": "The alert is written within {b} s of the result being ready (budget); the analysis time is shown separately and is not hidden in that figure. Results are pre-run, so opening a sample shows its alert immediately. Samples that triggered nothing are not listed: the rule was active but the source sample did not contain a listed invasive fish.",
      "rv.alerts.none": "No alerts yet", "rv.alerts.noneBody": "No processed real sample crossed the danger rule. The rule is active; nothing is invented.",
      "rv.why.thresholds": "Every threshold, in one file, with its reason", "rv.why.col.setting": "Setting", "rv.why.col.value": "Value", "rv.why.col.why": "Why this value",
      "rv.why.reference": "Reference list", "rv.why.refLine": "{n} sequences, {s} species. Query:",
      "rv.why.datasets": "Real datasets used", "rv.why.run": "run(s)", "rv.why.ena": "ENA record"
    },
    hi: {
      "rv.nav": "समीक्षा",
      "rv.title": "नमूना समीक्षा",
      "rv.lede": "एक वास्तविक सार्वजनिक नमूना चुनें। देखें कि क्या रखा गया, क्या हटाया गया और क्या अज्ञात रहा, क्यों, और अधिकारी को क्या करना चाहिए।",
      "rv.tabs.label": "समीक्षा अनुभाग",
      "rv.tab.sample": "नमूना", "rv.tab.guard": "डेटा जाँच", "rv.tab.seasons": "मौसम और नक्शा",
      "rv.tab.alerts": "अलर्ट", "rv.tab.why": "संख्याएँ और स्रोत",
      "rv.notBuilt": "परिणाम अभी तैयार नहीं हैं",
      "rv.notBuiltBody": "सभी वास्तविक नमूनों को संसाधित करने वाला कमांड चलाएँ, फिर पेज दोबारा लोड करें: python -m bioradar.adjudicate.runner all",
      "rv.couldNotLoad": "लोड नहीं हो सका",
      "rv.couldNotProcess": "इस नमूने को संसाधित नहीं किया जा सका",
      "rv.realSample": "वास्तविक नमूना", "rv.rerun": "अभी फिर चलाएँ", "rv.rerunTitle": "पूरा विश्लेषण अभी चलाएँ",
      "rv.whySample": "यह नमूना क्यों:",
      "rv.running": "पूरा विश्लेषण अभी चल रहा है", "rv.loading": "परिणाम लोड हो रहा है",
      "rv.preRun": "पहले से चला परिणाम, {s} सेकंड में लोड", "rv.live": "अभी {s} सेकंड में गणना की गई",
      "rv.role.mixed": "मिश्रित समुदाय", "rv.role.poor": "खराब गुणवत्ता / कम डेटा",
      "rv.role.unknowns": "अज्ञात मछलियाँ और आक्रामक प्रजातियाँ", "rv.role.field": "क्षेत्र नमूने (गर्मी / सर्दी)",
      "rv.verdict.Usable": "उपयोग योग्य", "rv.verdict.Usable with caution": "सावधानी के साथ उपयोग योग्य", "rv.verdict.Retake sample": "नमूना दोबारा लें",
      "rv.level.CRITICAL": "अति गंभीर", "rv.level.HIGH": "उच्च", "rv.level.WATCH": "निगरानी",
      "rv.noTrigger": "कोई अलर्ट नहीं", "rv.notChecked": "जाँच नहीं हुई",
      "rv.noTrigger.head": "इस नमूने में सूचीबद्ध कोई आक्रामक मछली खतरे के नियम तक नहीं पहुँची।",
      "rv.noTrigger.body": "नियम: सूचीबद्ध आक्रामक मछली की प्रजाति-स्तर पर पहचान, कम से कम 10 रीड के साथ। यहाँ नहीं मिली; इसका मतलब यह नहीं कि पानी उनसे मुक्त है।",
      "rv.notChecked.head": "आक्रामक प्रजाति नियम की जाँच नहीं हुई: यह नमूना दोबारा लेना है।",
      "rv.notChecked.body": "यहाँ आक्रामक मछलियों के बारे में कुछ कहने लायक उपयोगी DNA बहुत कम है।",
      "rv.pin": "स्थान", "rv.reads": "रीड", "rv.matchScore": "मिलान स्कोर", "rv.notRecorded": "दर्ज नहीं",
      "rv.summary": "नमूना गुणवत्ता सारांश",
      "rv.kept": "रखा गया", "rv.unknown": "अज्ञात / समीक्षा", "rv.dropped": "हटाया गया",
      "rv.distinct": "अलग-अलग अनुक्रम",
      "rv.stackLabel": "रखे गए, अज्ञात और हटाए गए रीड का हिस्सा",
      "rv.readsLine": "{reads} रीड, {distinct} अलग-अलग अनुक्रम। इनपुट सामग्री से {fmt} के रूप में पढ़ा गया",
      "rv.noQuality": " (FASTA में बेस-गुणवत्ता स्कोर नहीं होते, इसलिए गुणवत्ता फ़िल्टर छोड़ा गया)",
      "rv.sourceLine": "। स्रोत: {project} · रन {run} · संग्रह {date}।",
      "rv.print": "अधिकारी रिपोर्ट छापें (PDF)", "rv.csv": "सभी हटाए गए अनुक्रम (CSV)", "rv.sourceRecord": "स्रोत रिकॉर्ड",
      "rv.dropWhy": "अनुक्रम क्यों हटाए गए", "rv.nothingDropped": "कुछ भी नहीं हटाया गया।",
      "rv.examples": "हर एक के लिखित कारण के साथ उदाहरण ({n} हटाए गए अनुक्रम CSV में हैं)",
      "rv.col.reads": "रीड", "rv.col.sequence": "अनुक्रम", "rv.col.reason": "कारण",
      "rv.seq": "अनु.",
      "rv.reason.invalid_characters": "DNA अनुक्रम नहीं", "rv.reason.too_short": "छोटा टुकड़ा",
      "rv.reason.too_many_n": "बहुत अधिक N बेस", "rv.reason.low_complexity": "कम जटिलता / दोहराव",
      "rv.reason.low_quality": "कम बेस गुणवत्ता", "rv.reason.singleton": "केवल एक बार दिखा (संभावित त्रुटि)",
      "rv.reason.human_contamination": "मानव DNA का संदूषण", "rv.reason.unrelated": "किसी संदर्भ से संबंधित नहीं",
      "rv.speciesHead": "मिली प्रजातियाँ और उनका हिस्सा",
      "rv.retake.head": "नमूना दोबारा लें", "rv.retake.body": "यहाँ कौन सी मछलियाँ हैं, यह बताने लायक उपयोगी DNA बहुत कम है। कोई अनुमान नहीं लगाया गया।",
      "rv.noSpecies": "प्रजाति-स्तर की कोई पहचान नहीं।",
      "rv.invasive": "आक्रामक", "rv.cannotSeparate": "अलग नहीं की जा सकतीं", "rv.identity": "समानता", "rv.score": "स्कोर",
      "rv.speciesCount": "प्रजातियाँ",
      "rv.denom": "<b>हिस्सा कैसे निकाला गया:</b> प्रजाति के रीड ÷ {den} रीड जिन्हें नाम दिया जा सका (प्रजाति-स्तर की पहचान + वे समूह जिन्हें यह मार्कर अलग नहीं कर सकता)। इस हर से बाहर: {dropped} हटाए गए रीड और {novel} ऐसे अनुक्रमों के रीड जो संदर्भ से इतने अलग थे कि नाम नहीं दिया जा सका; नमूने में कुल {total} रीड थे। हिस्सा DNA रीड का अनुपात है, जानवरों की संख्या या उनका वजन नहीं।",
      "rv.traceNote": "10 से कम रीड वाली प्रजातियाँ ({n}) अल्प मात्रा के रूप में दिखाई गई हैं, पहचान के रूप में नहीं। जिन दो प्रजातियों का 12S अनुक्रम अलग नहीं किया जा सकता, उन्हें साथ दिखाया गया है, किसी एक नाम पर थोपा नहीं गया।",
      "rv.scoreNote": "मिलान स्कोर (0-1) एक अनुमानात्मक संख्या है जो समानता और अगली सबसे नज़दीकी प्रजाति से अंतर पर बनी है: समानता में हर 1% कमी पर यह 4 अंक घटती है, दूसरी प्रजाति लगभग उतनी ही नज़दीक हो तो आधी हो जाती है, और सीमित है (प्रजाति की पहचान के लिए 0.99, अपुष्ट के लिए 0.60)। यह प्रमाणित संभावना नहीं है।",
      "rv.src.title": "स्रोत और मेटाडेटा", "rv.src.sub": "यह नमूना कहाँ से आया",
      "rv.src.dataset": "डेटासेट", "rv.src.run": "रन / नमूना", "rv.src.alias": "उपनाम",
      "rv.src.file": "मूल फ़ाइल", "rv.src.marker": "मार्कर / परख", "rv.src.markerFallback": "डेटासेट रिकॉर्ड देखें",
      "rv.src.reference": "संदर्भ", "rv.src.collected": "संग्रह तिथि", "rv.src.place": "स्थान / पिन",
      "rv.src.note": "ये जाँचें केवल इस रिकॉर्ड के अपने क्षेत्र देखती हैं। रिकॉर्ड के बीच की जाँचें (दोहराए ID, सीमा, प्रजाति की वर्तनी) डेटा जाँच टैब में हैं।",
      "rv.chk.ok": "ठीक", "rv.chk.note": "टिप्पणी", "rv.chk.problem": "समस्या", "rv.chk.missing": "अनुपस्थित",
      "rv.chk.noDate": "संग्रह तिथि दर्ज नहीं", "rv.chk.future": "तिथि भविष्य की है",
      "rv.chk.dateOk": "भविष्य की नहीं; सटीकता: {p}", "rv.chk.yearOnly": " मात्र, इसलिए इसे किसी मौसम से नहीं जोड़ा जा सकता",
      "rv.chk.noPin": "GPS पिन दर्ज नहीं", "rv.chk.pinOk": "मान्य सीमा के भीतर", "rv.chk.pinLow": "; कम सटीकता: {n}",
      "rv.chk.pinBad": "अक्षांश/देशांतर की मान्य सीमा से बाहर",
      "rv.prec.day": "दिन", "rv.prec.month": "महीना", "rv.prec.year": "वर्ष",
      "rv.queue.head": "समीक्षा कतार: वे अनुक्रम जिन्हें किसी प्रजाति से नहीं जोड़ा गया",
      "rv.queue.none": "किसी समीक्षा की आवश्यकता नहीं।",
      "rv.queue.intro": "{n} अनुक्रम अपुष्ट हैं। हर एक अपना सबसे नज़दीकी संदर्भ मिलान, <b>प्रतिशत समानता</b> (मापी गई समानता, संभावना नहीं) और 0.60 पर सीमित अनुमानात्मक मिलान स्कोर दिखाता है, इसलिए कोई भी पुष्ट नहीं माना जा सकता।",
      "rv.queue.ref": "उपयोग किया गया संदर्भ: <b>{ref}</b>। संरेखित कवरेज विश्लेषण द्वारा <b>उपलब्ध नहीं कराया गया</b> (समानता पूरे रीड पर मापी जाती है, इसलिए कम ओवरलैप उसे छिपाता नहीं, घटाता है)।",
      "rv.queue.closest": "सबसे नज़दीकी मिलान", "rv.queue.state": "समीक्षा स्थिति", "rv.queue.whyUnknown": "अज्ञात क्यों",
      "rv.queue.needsReview": "समीक्षा आवश्यक", "rv.queue.check": "NCBI पर जाँचें", "rv.queue.showing": "{n} में से सबसे अधिक वाले 12 दिखाए गए।",
      "rv.exp.count": "स्रोत के अनुसार जो मिलाया गया था, उससे जाँच", "rv.exp.comp": "स्रोत की संरचना से जाँच",
      "rv.exp.groups": "(साथ में {n} प्रजाति-समूह जिन्हें 12S अलग नहीं कर सकता)",
      "rv.exp.species": "प्रजाति", "rv.exp.expected": "अपेक्षित", "rv.exp.observed": "प्राप्त", "rv.exp.result": "परिणाम",
      "rv.map.head": "यह नमूना कहाँ लिया गया", "rv.map.noPin": "इस रिकॉर्ड में GPS पिन नहीं है, इसलिए इसे नक्शे पर नहीं दिखाया जा सकता।",
      "rv.map.note": "टिप्पणी:", "rv.map.noFlag": "किसी आक्रामक मछली का संकेत नहीं",
      "rv.guard.title": "डेटा जाँच", "rv.guard.sub": "वास्तविक अभिलेखागार रिकॉर्ड, कभी संपादित नहीं",
      "rv.guard.clean": "डेटाबेस साफ़", "rv.guard.notClean": "डेटाबेस साफ़ नहीं",
      "rv.guard.checked": "जाँचे गए रिकॉर्ड", "rv.guard.kept": "साफ़ भंडार में रखे गए", "rv.guard.rejected": "अस्वीकृत", "rv.guard.merged": "मिलाए गए",
      "rv.guard.source": "स्रोत: ENA परियोजना PRJEB108476 (स्नैपशॉट md5 {md5})। सीमा: <b>{b}</b> ({src})। आज = {today}।",
      "rv.guard.post": "<b>साफ़ भंडार की बाद-जाँच:</b> {n} रिकॉर्ड में {dup} दोहराए ID, {out} सीमा से बाहर, {fut} भविष्य की तिथि, {sp} बिना मिलाई दोहरी वर्तनी।",
      "rv.guard.rule.duplicate_id": "दोहराया नमूना ID", "rv.guard.rule.outside_boundary": "GPS पिन सीमा से बाहर",
      "rv.guard.rule.no_coordinates": "GPS पिन नहीं", "rv.guard.rule.future_date": "भविष्य की तिथि",
      "rv.guard.rule.double_spelling": "प्रजाति, दो वर्तनी",
      "rv.guard.nCase": "{n} {what}", "rv.guard.w.merged": "मिलाए गए", "rv.guard.w.handled": "निपटाए गए", "rv.guard.w.rejected": "अस्वीकृत",
      "rv.guard.absent": "डेटा में नहीं",
      "rv.guard.noCase": "वास्तविक रिकॉर्ड में ऐसा कोई मामला नहीं था, इसलिए दिखाने को कुछ नहीं। नियम फिर भी सक्रिय है।",
      "rv.guard.every": "हर निर्णय", "rv.guard.col.rule": "नियम", "rv.guard.col.action": "कार्रवाई", "rv.guard.col.record": "रिकॉर्ड",
      "rv.guard.first": "{n} निर्णयों में से पहले 120 दिखाए गए।",
      "rv.season.none": "गर्मी/सर्दी का जोड़ा नहीं", "rv.season.noneBody": "संसाधित नमूनों में किसी स्थान के दोनों मौसम उपलब्ध नहीं हैं।",
      "rv.season.location": "स्थान", "rv.season.summer": "गर्मी", "rv.season.winter": "सर्दी",
      "rv.season.detectedIn": "पहचानी गई प्रजातियाँ ({s})", "rv.season.newVs": "{s} की तुलना में नई पहचानी गई", "rv.season.missing": "यहाँ नहीं मिलीं, {s} में मिली थीं",
      "rv.season.reps": "{sa} में {a} प्रतिकृति नमूने, {sb} में {b}।",
      "rv.season.rule": "मौसम नियम (thresholds.json में तय):",
      "rv.season.print": "इस स्थान की अधिकारी रिपोर्ट छापें (PDF)", "rv.season.printHint": "एक पन्ना: जानवर, जोखिम, स्रोत और तिथियाँ, अनिश्चितता, क्या करना है।",
      "rv.season.noPin": "इस स्थान के लिए GPS पिन दर्ज नहीं।",
      "rv.season.newIn": "{s} में नई पहचानी गई", "rv.season.seenNot": "{o} में मिलीं, {s} में नहीं मिलीं", "rv.season.allIn": "{s} में पहचानी गई (सभी)",
      "rv.season.sLabel": "मौसम", "rv.season.speciesTip": "{s}: {n} प्रजातियाँ",
      "rv.season.care": "<b>इस तुलना को सावधानी से पढ़ें।</b> गर्मी के नमूने: {a} ({ar} रीड को नाम मिला)। सर्दी के नमूने: {b} ({br} रीड को नाम मिला)।",
      "rv.season.depth": " अनुक्रमण की गहराई में लगभग {x} गुना अंतर है।",
      "rv.season.careEnd": " जिस मौसम के रीड कमज़ोर हों, उसमें कम प्रजातियाँ डेटा की वजह से दिख सकती हैं, पानी की वजह से नहीं।",
      "rv.season.none2": "कोई नहीं।", "rv.season.repl": "{r} रीड, {n} प्रतिकृति",
      "rv.season.listed": "आक्रामक-सूचीबद्ध", "rv.season.listedTip": "सूचीबद्ध आक्रामक मछली; इस परियोजना में कहीं अलर्ट में पुष्ट",
      "rv.alerts.mapHint": "हर अलग पिन के लिए एक चिह्न; रंग = वहाँ का सबसे गंभीर अलर्ट", "rv.alerts.mapHead": "अलर्ट नक्शा",
      "rv.alerts.pins": "{n} पिन। जिन नमूनों के स्रोत ने केवल मोटा निर्देशांक दिया, वे एक पिन साझा करते हैं।",
      "rv.alerts.logHint": "डैशबोर्ड बैनर + यह लॉग। कोई SMS या ई-मेल नहीं भेजा जाता।", "rv.alerts.logHead": "अलर्ट लॉग",
      "rv.alerts.col.level": "स्तर", "rv.alerts.col.alert": "अलर्ट", "rv.alerts.col.pin": "स्थान", "rv.alerts.col.sample": "नमूना",
      "rv.alerts.col.analysis": "विश्लेषण में लगा समय", "rv.alerts.col.after": "परिणाम के बाद अलर्ट",
      "rv.alerts.foot": "परिणाम तैयार होने के {b} सेकंड के भीतर अलर्ट लिखा जाता है (सीमा); विश्लेषण का समय अलग दिखाया गया है और उस संख्या में छिपाया नहीं गया। परिणाम पहले से चले हुए हैं, इसलिए नमूना खोलते ही उसका अलर्ट दिखता है। जिन नमूनों ने कुछ ट्रिगर नहीं किया वे सूची में नहीं हैं: नियम सक्रिय था पर स्रोत नमूने में कोई सूचीबद्ध आक्रामक मछली नहीं थी।",
      "rv.alerts.none": "अभी कोई अलर्ट नहीं", "rv.alerts.noneBody": "किसी संसाधित वास्तविक नमूने ने खतरे का नियम पार नहीं किया। नियम सक्रिय है; कुछ भी गढ़ा नहीं गया।",
      "rv.why.thresholds": "हर सीमा-मान, एक फ़ाइल में, कारण के साथ", "rv.why.col.setting": "सेटिंग", "rv.why.col.value": "मान", "rv.why.col.why": "यह मान क्यों",
      "rv.why.reference": "संदर्भ सूची", "rv.why.refLine": "{n} अनुक्रम, {s} प्रजातियाँ। क्वेरी:",
      "rv.why.datasets": "उपयोग किए गए वास्तविक डेटासेट", "rv.why.run": "रन", "rv.why.ena": "ENA रिकॉर्ड"
    }
  };

  if (I18n && I18n.addStrings) { I18n.addStrings("en", TXT.en); I18n.addStrings("hi", TXT.hi); }

  /* t(key, {vars}) with {name} placeholders. Falls back to English, then to the key. */
  function T(key, vars) {
    var s = I18n ? I18n.t(key, TXT.en[key] !== undefined ? TXT.en[key] : key) : (TXT.en[key] || key);
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(String(vars[k])); });
    return s;
  }

  var S = {
    index: null, id: null, result: null, tab: "sample", busy: false,
    guard: null, seasons: null, alerts: null, thresholds: null, provenance: null,
    map: null, seasonMap: null, alertMap: null, timer: null
  };

  var LEVEL_CLASS = { CRITICAL: "invasive", HIGH: "high", WATCH: "medium", NONE: "healthy", RETAKE: "info" };

  /* Colours come from the design tokens, so light/dark and any future retheme apply to map markers too. */
  function tok(name, fallback) { return (UI.cssVar && UI.cssVar(name)) || fallback; }
  function levelColour(level) {
    return level === "CRITICAL" ? tok("--alert-invasive", "#d5405f")
         : level === "HIGH" ? tok("--alert-rare", "#e0912f") : tok("--alert-neutral", "#8a95a0");
  }

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
    label: function () { return T("rv.nav"); },
    mount: function (container) {
      container.innerHTML =
        '<div class="view-head"><div><h1>' + esc(T("rv.title")) + "</h1>" +
        "<p>" + esc(T("rv.lede")) + "</p></div>" +
        '<div class="segmented" id="adjTabs" role="group" aria-label="' + esc(T("rv.tabs.label")) + '">' +
        ["sample", "guard", "seasons", "alerts", "why"].map(function (k) {
          return '<button type="button" data-adj-tab="' + k + '" aria-pressed="' +
            (S.tab === k) + '">' + esc(T("rv.tab." + k)) + "</button>";
        }).join("") + "</div></div>" +
        '<div id="adjBanner"></div><div id="adjRoot" class="stack" aria-live="polite"></div>';
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
    if (S.index) { render(); if (S.result) showBanner(S.result); return; }
    root().innerHTML = UI.card(UI.skeleton("line", 4));
    api("/api/adjudicate/index").then(function (idx) {
      S.index = idx;
      var first = idx.samples.filter(function (s) { return s.role === "mixed"; })[0] || idx.samples[0];
      S.id = first.sample_id;
      render();
      selectSample(S.id);
    }).catch(function (err) {
      root().innerHTML = UI.state("empty", T("rv.notBuilt"), T("rv.notBuiltBody") + " (" + esc(err.message) + ")");
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
      root().innerHTML = UI.state("error", T("rv.couldNotLoad"), e.message);
    });
  }

  /* ── sample tab ─────────────────────────────────────────────────────── */

  function picker() {
    var groups = {};
    S.index.samples.forEach(function (s) { (groups[s.role] = groups[s.role] || []).push(s); });
    var order = ["mixed", "poor", "unknowns", "field"];
    var opts = order.filter(function (r) { return groups[r]; }).map(function (role) {
      return '<optgroup label="' + esc(T("rv.role." + role)) + '">' +
        groups[role].map(function (s) {
          return '<option value="' + esc(s.sample_id) + '"' + (s.sample_id === S.id ? " selected" : "") + ">" +
            esc(s.label + " - " + T("rv.verdict." + s.verdict)) + "</option>";
        }).join("") + "</optgroup>";
    }).join("");
    return '<div class="card sm"><div class="row">' +
      '<label for="adjPick" class="hint" style="min-width:90px">' + esc(T("rv.realSample")) + "</label>" +
      '<select id="adjPick" class="adj-select">' + opts + "</select>" +
      UI.button(T("rv.rerun"), { id: "adjRerun", size: "sm", title: T("rv.rerunTitle") }) +
      '<span class="hint" id="adjStatus" role="status"></span></div>' +
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
    if (el && row) el.textContent = T("rv.whySample") + " " + row.why_chosen;
  }

  function selectSample(id, force) {
    S.id = id;
    var status = document.getElementById("adjStatus");
    var host = document.getElementById("adjSample");
    var t0 = Date.now();
    if (host) host.innerHTML = UI.card(
      '<div class="adj-working"><div class="adj-spin"></div><div><b>' +
      esc(force ? T("rv.running") : T("rv.loading")) +
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
      var sec = ((Date.now() - t0) / 1000).toFixed(1);
      status = document.getElementById("adjStatus") || status;
      if (status) status.textContent = T(r.from_cache ? "rv.preRun" : "rv.live", { s: sec });
      showBanner(r);
      if (force) S.alerts = null;
    }).catch(function (e) {
      clearInterval(S.timer);
      if (host) host.innerHTML = UI.state("error", T("rv.couldNotProcess"), e.message);
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
    return S.provenance ? S.provenance.reference.reference_database_version : "-";
  }

  function showBanner(r) {
    var b = document.getElementById("adjBanner");
    if (!b) return;
    var ev = (r.alerts || [])[0];
    if (!ev) {
      var poor = r.verdict === "Retake sample";
      b.innerHTML = '<div class="adj-banner none" role="status"><div class="adj-banner-level">' +
        esc(poor ? T("rv.notChecked") : T("rv.noTrigger")) + '</div><div class="adj-banner-main"><b>' +
        esc(poor ? T("rv.notChecked.head") : T("rv.noTrigger.head")) + "</b>" +
        '<div class="adj-banner-act">' + esc(poor ? T("rv.notChecked.body") : T("rv.noTrigger.body")) +
        "</div></div></div>";
      return;
    }
    b.innerHTML = '<div class="adj-banner ' + LEVEL_CLASS[ev.level] + '" role="alert">' +
      '<div class="adj-banner-level">' + esc(T("rv.level." + ev.level)) + "</div>" +
      '<div class="adj-banner-main"><b>' + esc(ev.headline) + "</b>" +
      "<div>" + esc(T("rv.pin")) + " " + pin(ev.pin) + " &middot; " + esc(ev.sample_label) + " &middot; " + UI.num(ev.reads) +
      " " + esc(T("rv.reads")) + " &middot; " + esc(T("rv.matchScore")) + " " + ev.confidence.toFixed(2) + "</div>" +
      '<div class="adj-banner-act">' + esc(ev.action) + "</div></div></div>";
  }

  function pin(p) {
    if (!p || p.latitude === null || p.latitude === undefined) return esc(T("rv.notRecorded"));
    return Number(p.latitude).toFixed(4) + ", " + Number(p.longitude).toFixed(4);
  }

  function paintSample(r) {
    var host = document.getElementById("adjSample");
    if (!host) return;
    var s = r.summary, tot = Math.max(r.reads_total, 1);
    var vcls = r.verdict === "Retake sample" ? "invasive" : r.verdict === "Usable with caution" ? "medium" : "healthy";
    var seg = [["kept", T("rv.kept"), "var(--alert-healthy)"], ["unknown", T("rv.unknown"), "var(--alert-rare)"],
               ["dropped", T("rv.dropped"), "var(--alert-invasive)"]];

    var html = "";
    html += UI.card(
      '<div class="card-head"><div><div class="hint">' + esc(T("rv.summary")) + "</div>" +
      '<h2 class="adj-h2">' + esc(r.metadata.label) + "</h2></div>" +
      '<span class="badge ' + vcls + '">' + esc(T("rv.verdict." + r.verdict)) + "</span></div>" +
      '<p class="adj-verdict">' + esc(r.verdict_reasons.join("; ")) + ".</p>" +
      '<div class="adj-stack" role="img" aria-label="' + esc(T("rv.stackLabel")) + '">' +
      seg.map(function (x) {
        var w = 100 * s[x[0]].reads / tot;
        return '<div style="width:' + w + "%;background:" + x[2] + '" title="' + esc(x[1]) + " " + w.toFixed(1) + '%"></div>';
      }).join("") + "</div>" +
      '<div class="kpis">' + seg.map(function (x) {
        return '<div class="kpi"><div class="k"><span class="adj-dot" style="background:' + x[2] + '"></span>' + esc(x[1]) +
          '</div><div class="v">' + pct(s[x[0]].reads / tot, 1) + '</div><div class="hint">' +
          UI.num(s[x[0]].reads) + " " + esc(T("rv.reads")) + " &middot; " + UI.num(s[x[0]].distinct) + " " + esc(T("rv.distinct")) + "</div></div>";
      }).join("") + "</div>" +
      '<p class="hint">' + esc(T("rv.readsLine", { reads: UI.num(r.reads_total), distinct: UI.num(r.distinct_sequences), fmt: r.input_format.toUpperCase() })) +
      (r.quality_scores_available ? "" : esc(T("rv.noQuality"))) +
      esc(T("rv.sourceLine", { project: r.metadata.bioproject, run: r.sample_id, date: r.metadata.collection_date || "n/a" })) + "</p>" +
      '<div class="card-foot">' +
      UI.button(T("rv.print"), { variant: "primary", id: "adjPdf", icon: "download" }) +
      (r.dropped_csv ? '<a class="btn sm" href="/api/adjudicate/dropped/' + encodeURIComponent(r.sample_id) +
        '.csv">' + esc(T("rv.csv")) + "</a>" : "") +
      '<a class="btn sm" target="_blank" rel="noopener" href="' + esc(sourceUrl(r)) + '">' + esc(T("rv.sourceRecord")) + "</a></div>");

    html += sourceCard(r);

    var reasons = Object.keys(r.drop_reasons);
    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.dropWhy")) + "</h2></div>" +
      (reasons.length ? reasonBars(r) : '<p class="hint">' + esc(T("rv.nothingDropped")) + "</p>") +
      droppedTable(r));

    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.speciesHead")) + "</h2></div>" +
      speciesChart(r) + (r.metadata.role === "mixed" ? expectedBlock(r) : ""));

    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.queue.head")) + "</h2></div>" +
      unknownTable(r));

    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.map.head")) + "</h2></div>" +
      (r.metadata.latitude !== null && r.metadata.latitude !== undefined
        ? '<div id="adjMap" class="adj-map"></div>' +
          (r.metadata.coordinate_note ? '<p class="hint">' + esc(T("rv.map.note")) + " " + esc(r.metadata.coordinate_note) + ".</p>" : "")
        : '<p class="hint">' + esc(T("rv.map.noPin")) + "</p>"));

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
      return '<div class="adj-bar-row"><div class="adj-bar-label">' + esc(T("rv.reason." + x[0])) + "</div>" +
        '<div class="adj-bar-track"><div class="adj-bar-fill" style="width:' + (100 * x[1].reads / mx) +
        '%;background:var(--alert-invasive)"></div></div>' +
        '<div class="adj-bar-val">' + UI.num(x[1].reads) + " " + esc(T("rv.reads")) + " &middot; " + UI.num(x[1].distinct) + " " + esc(T("rv.seq")) + "</div></div>";
    }).join("") + "</div>";
  }

  function droppedTable(r) {
    var seen = {}, rows = [];
    (r.dropped || []).forEach(function (d) {
      if (rows.length < 8 && (seen[d.reason_code] || 0) < 2) { seen[d.reason_code] = (seen[d.reason_code] || 0) + 1; rows.push(d); }
    });
    if (!rows.length) return "";
    return '<details class="adj-details" open><summary>' + esc(T("rv.examples", { n: UI.num(r.dropped_total_listed) })) + "</summary>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>' + esc(T("rv.col.reads")) + "</th><th>" + esc(T("rv.col.sequence")) +
      "</th><th>" + esc(T("rv.col.reason")) + "</th></tr></thead><tbody>" +
      rows.map(function (d) {
        return "<tr><td>" + UI.num(d.reads) + '</td><td class="mono adj-seq">' + esc(d.sequence.slice(0, 40)) +
          (d.sequence.length > 40 ? "&hellip;" : "") + "</td><td>" + esc(d.reason) + "</td></tr>";
      }).join("") + "</tbody></table></div></details>";
  }

  function speciesChart(r) {
    if (r.verdict === "Retake sample") {
      return UI.state("empty", T("rv.retake.head"), T("rv.retake.body"));
    }
    var rows = r.species.filter(function (x) { return x.status !== "trace"; }).slice(0, 14);
    if (!rows.length) return '<p class="hint">' + esc(T("rv.noSpecies")) + "</p>";
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
      var shown = x.species.length > 58 ? x.species.slice(0, 55) + "… (" + (x.members || []).length + " " + T("rv.speciesCount") + ")" : x.species;
      return '<div class="adj-bar-row"><div class="adj-bar-label" title="' + esc(x.species) + '"><i>' + esc(shown) + "</i>" +
        (bad ? ' <span class="badge invasive">' + esc(T("rv.invasive")) + "</span>" : "") +
        (x.kind === "complex" ? ' <span class="badge info">' + esc(T("rv.cannotSeparate")) + "</span>" : "") + "</div>" +
        '<div class="adj-bar-track"><div class="adj-bar-fill" style="width:' + (100 * x.share / mx) +
        "%;background:" + color + '"></div></div>' +
        '<div class="adj-bar-val"><b>' + UI.num(x.reads) + "</b> / " + UI.num(den) + " = " + pct(x.share) +
        '<div class="hint">' + esc(T("rv.identity")) + " " + pct(x.best_identity) + " &middot; " + esc(T("rv.score")) + " " + x.confidence.toFixed(2) + "</div></div></div>";
    }).join("") + "</div>";
    var trace = r.species.filter(function (x) { return x.status === "trace"; }).length;
    return out + '<div class="adj-note adj-denominator">' + T("rv.denom", {
        den: UI.num(den), dropped: UI.num(r.summary.dropped.reads), novel: UI.num(novelReads), total: UI.num(r.reads_total) }) + "</div>" +
      '<p class="hint">' + esc(T("rv.traceNote", { n: trace })) + " " + esc(T("rv.scoreNote")) + "</p>";
  }

  function dateCheck(text) {
    var m = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(String(text || ""));
    if (!m) return { badge: "missing", text: T("rv.chk.noDate") };
    var precision = m[3] ? "day" : m[2] ? "month" : "year";
    var d = new Date(Number(m[1]), m[2] ? Number(m[2]) - 1 : 0, m[3] ? Number(m[3]) : 1);
    if (d.getTime() > Date.now()) return { badge: "high", text: T("rv.chk.future") };
    return { badge: precision === "year" ? "medium" : "healthy",
             text: T("rv.chk.dateOk", { p: T("rv.prec." + precision) }) + (precision === "year" ? T("rv.chk.yearOnly") : "") };
  }

  function coordCheck(m) {
    if (m.latitude === null || m.latitude === undefined) return { badge: "missing", text: T("rv.chk.noPin") };
    var ok = Math.abs(m.latitude) <= 90 && Math.abs(m.longitude) <= 180;
    return { badge: ok ? (m.coordinate_note ? "medium" : "healthy") : "high",
             text: ok ? T("rv.chk.pinOk") + (m.coordinate_note ? T("rv.chk.pinLow", { n: m.coordinate_note }) : "")
                      : T("rv.chk.pinBad") };
  }

  function checkBadge(c) {
    var key = { healthy: "ok", medium: "note", high: "problem", missing: "missing" }[c.badge] || "note";
    return '<span class="badge ' + c.badge + '">' + esc(T("rv.chk." + key)) + '</span> <span class="hint">' + esc(c.text) + "</span>";
  }

  function sourceCard(r) {
    var m = r.metadata, ena = "https://www.ebi.ac.uk/ena/browser/view/";
    var dc = dateCheck(m.collection_date), cc = coordCheck(m);
    function row(k, v) { return "<dt>" + esc(k) + "</dt><dd>" + v + "</dd>"; }
    return UI.card('<div class="card-head"><div><div class="hint">' + esc(T("rv.src.sub")) + "</div>" +
      '<h2 class="adj-h2">' + esc(T("rv.src.title")) + "</h2></div></div>" +
      '<dl class="adj-dl">' +
        row(T("rv.src.dataset"), '<a target="_blank" rel="noopener" href="' + ena + encodeURIComponent(m.bioproject) + '">' + esc(m.bioproject) + "</a> &middot; " + esc(m.dataset_title)) +
        row(T("rv.src.run"), '<a target="_blank" rel="noopener" href="' + ena + encodeURIComponent(r.sample_id) + '">' + esc(r.sample_id) + "</a>" +
            (m.biosample ? ' &middot; <a target="_blank" rel="noopener" href="' + ena + encodeURIComponent(m.biosample) + '">' + esc(m.biosample) + "</a>" : "") +
            " &middot; " + esc(T("rv.src.alias")) + " " + esc(m.alias || "-")) +
        row(T("rv.src.file"), '<span class="mono">' + esc(r.source_file || "-") + '</span> &middot; md5 <span class="mono">' + esc(m.md5 || "-") + "</span>") +
        row(T("rv.src.marker"), esc(/12S|COI|16S/.exec(m.dataset_title || "") ? m.dataset_title : T("rv.src.markerFallback"))) +
        row(T("rv.src.reference"), esc(refVersion())) +
        row(T("rv.src.collected"), esc(m.collection_date || "n/a") + " " + checkBadge(dc)) +
        row(T("rv.src.place"), esc(m.location || "n/a") + (m.latitude !== null && m.latitude !== undefined ? " (" + Number(m.latitude).toFixed(4) + ", " + Number(m.longitude).toFixed(4) + ")" : "") +
            " " + checkBadge(cc)) +
      "</dl>" +
      '<p class="hint">' + esc(T("rv.src.note")) + "</p>");
  }

  function expectedBlock(r) {
    var e = r.expected_check;
    if (!e) return "";
    if (!e.available) return '<div class="adj-note">' + esc(e.note) + "</div>";
    if (e.mode === "count_only") {
      return '<h3 class="adj-h3">' + esc(T("rv.exp.count")) + '</h3><p class="hint">' + esc(e.source) + "</p>" +
        "<p><b>" + esc(e.verdict) + "</b> " + esc(T("rv.exp.groups", { n: e.unresolved_groups })) + "</p>" +
        '<div class="adj-note">' + esc(e.limits) + "</div>";
    }
    return '<h3 class="adj-h3">' + esc(T("rv.exp.comp")) + '</h3><p class="hint">' + esc(e.source) + "</p>" +
      "<p><b>" + esc(e.verdict) + "</b></p>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>' + esc(T("rv.exp.species")) + "</th><th>" + esc(T("rv.exp.expected")) +
      "</th><th>" + esc(T("rv.exp.observed")) + "</th><th>" + esc(T("rv.exp.result")) + "</th></tr></thead><tbody>" +
      e.rows.map(function (x) {
        return "<tr><td><i>" + esc(x.species) + "</i></td><td>" + (x.expected_share ? pct(x.expected_share) : "-") +
          "</td><td>" + pct(x.observed_share) + "</td><td>" + esc(x.status + (x.share_check ? " / " + x.share_check : "") + (x.note ? " - " + x.note : "")) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
  }

  function unknownTable(r) {
    var q = r.unknown_queue || [];
    if (!q.length) return '<p class="hint">' + esc(T("rv.queue.none")) + "</p>";
    var rows = q.slice(0, 12);
    return '<p class="hint">' + T("rv.queue.intro", { n: UI.num(q.length) }) + "</p>" +
      '<div class="adj-note">' + T("rv.queue.ref", { ref: esc(refVersion()) }) + " " + esc(T("rv.scoreNote")) + "</div>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>' + esc(T("rv.col.reads")) + "</th><th>" + esc(T("rv.queue.closest")) +
      "</th><th>" + esc(T("rv.identity")) + "</th><th>" + esc(T("rv.matchScore")) + "</th><th>" + esc(T("rv.queue.state")) +
      "</th><th>" + esc(T("rv.queue.whyUnknown")) + "</th><th></th></tr></thead><tbody>" +
      rows.map(function (u) {
        var blast = "https://blast.ncbi.nlm.nih.gov/Blast.cgi?PROGRAM=blastn&PAGE_TYPE=BlastSearch&QUERY=" + encodeURIComponent(u.sequence);
        return "<tr><td>" + UI.num(u.reads) + "</td><td><i>" + esc(u.candidates && u.candidates.length > 1 ? u.candidates.join(" / ") : u.closest_match) +
          "</i></td><td>" + pct(u.identity) + "</td><td>" + u.confidence.toFixed(2) +
          '</td><td><span class="badge medium">' + esc(T("rv.queue.needsReview")) + "</span></td><td>" + esc(u.reason) +
          '</td><td><a target="_blank" rel="noopener" href="' + blast + '">' + esc(T("rv.queue.check")) + "</a></td></tr>";
      }).join("") + "</tbody></table></div>" +
      (q.length > rows.length ? '<p class="hint">' + esc(T("rv.queue.showing", { n: UI.num(q.length) })) + "</p>" : "");
  }

  function drawMap(r) {
    var el = document.getElementById("adjMap");
    if (!el || !window.L) return;
    if (S.map) { S.map.remove(); S.map = null; }
    var lat = r.metadata.latitude, lon = r.metadata.longitude;
    var m = L.map(el).setView([lat, lon], 9);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap" }).addTo(m);
    var ev = (r.alerts || [])[0];
    var colour = ev ? levelColour(ev.level) : tok("--alert-healthy", "#2f9e5b");
    L.circleMarker([lat, lon], { radius: 11, color: tok("--surface-raised", "#fff"), weight: 2, fillColor: colour, fillOpacity: 1 }).addTo(m)
      .bindPopup("<b>" + esc(r.metadata.label) + "</b><br>" + (ev ? esc(ev.headline) : esc(T("rv.map.noFlag"))) +
        "<br>" + esc(r.metadata.collection_date));
    S.map = m;
    setTimeout(function () { m.invalidateSize(); }, 200);
  }

  /* ── data guard ─────────────────────────────────────────────────────── */

  function renderGuard(g) {
    var pc = g.post_check, rules = ["duplicate_id", "outside_boundary", "no_coordinates", "future_date", "double_spelling"];
    var cards = rules.map(function (key) {
      var c = g.counts_by_rule[key];
      var ex = g.decisions.filter(function (d) { return d.rule === key; })[0];
      var n = c ? c.reject + c.merge : 0;
      var what = c ? (c.merge && !c.reject ? "merged" : c.merge ? "handled" : "rejected") : "";
      return UI.card('<div class="card-head"><h3 class="adj-h3">' + esc(T("rv.guard.rule." + key)) + "</h3>" +
        '<span class="badge ' + (n ? "high" : "info") + '">' + esc(n ? T("rv.guard.nCase", { n: n, what: T("rv.guard.w." + what) }) : T("rv.guard.absent")) + "</span></div>" +
        (ex ? '<p class="hint"><b>' + esc(ex.action) + ":</b> " + esc(ex.reason) +
          (ex.run_accession ? " (" + esc(ex.run_accession) + ")" : "") + "</p>"
            : '<p class="hint">' + esc(T("rv.guard.noCase")) + "</p>"),
        { size: "sm" });
    }).join("");
    root().innerHTML =
      UI.card('<div class="card-head"><div><div class="hint">' + esc(T("rv.guard.sub")) + "</div>" +
        '<h2 class="adj-h2">' + esc(T("rv.guard.title")) + '</h2></div><span class="badge ' + (pc.clean ? "healthy" : "invasive") + '">' +
        esc(pc.clean ? T("rv.guard.clean") : T("rv.guard.notClean")) + "</span></div>" +
        '<div class="kpis">' + UI.kpi(T("rv.guard.checked"), UI.num(g.records_in)) +
        UI.kpi(T("rv.guard.kept"), UI.num(g.clean_count), { color: "accent" }) +
        UI.kpi(T("rv.guard.rejected"), UI.num(g.decisions.filter(function (d) { return d.action === "reject"; }).length)) +
        UI.kpi(T("rv.guard.merged"), UI.num(g.decisions.filter(function (d) { return d.action === "merge"; }).length)) + "</div>" +
        '<p class="hint">' + T("rv.guard.source", { md5: esc(g.records_snapshot_md5), b: esc(g.boundary.name), src: esc(g.boundary.source), today: esc(g.today) }) + "</p>" +
        '<p class="hint">' + T("rv.guard.post", { dup: pc.duplicate_sample_ids, out: pc.outside_boundary, fut: pc.future_dated,
          sp: pc.unmerged_double_spellings, n: pc.records_checked }) + "</p>") +
      '<div class="adj-grid">' + cards + "</div>" +
      UI.card('<h3 class="adj-h3">' + esc(T("rv.guard.every")) + '</h3><div class="table-wrap" style="max-height:340px;overflow:auto"><table class="data"><thead><tr><th>' +
        esc(T("rv.guard.col.rule")) + "</th><th>" + esc(T("rv.guard.col.action")) + "</th><th>" + esc(T("rv.guard.col.record")) + "</th><th>" + esc(T("rv.col.reason")) + "</th></tr></thead><tbody>" +
        g.decisions.slice(0, 120).map(function (d) {
          return "<tr><td>" + esc(d.rule_label) + "</td><td>" + esc(d.action) + '</td><td class="mono">' + esc(d.run_accession || "-") + "</td><td>" + esc(d.reason) + "</td></tr>";
        }).join("") + '</tbody></table></div><p class="hint">' + esc(T("rv.guard.first", { n: UI.num(g.decisions.length) })) + "</p>");
  }

  /* ── seasons ────────────────────────────────────────────────────────── */

  function renderSeasons(doc) {
    if (!doc.sites.length) {
      root().innerHTML = UI.state("empty", T("rv.season.none"), T("rv.season.noneBody")); return;
    }
    root().innerHTML = '<div class="card sm"><div class="row"><label class="hint" for="adjSite">' + esc(T("rv.season.location")) + "</label>" +
      '<select id="adjSite" class="adj-select">' + doc.sites.map(function (s, i) {
        return '<option value="' + i + '">' + esc(s.location) + "</option>"; }).join("") + "</select></div></div>" +
      '<div id="adjSeason" class="stack"></div>';
    var sel = document.getElementById("adjSite");
    sel.addEventListener("change", function () { paintSeason(doc, +sel.value, 0); });
    paintSeason(doc, 0, 0);
  }

  function seasonName(key) { return T(key === "summer" ? "rv.season.summer" : "rv.season.winter"); }

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
        '<div class="adj-slider"><span class="' + (pos === 0 ? "on" : "") + '">' + esc(T("rv.season.summer")) + " " + esc(site.summer.dates.join(", ")) + "</span>" +
        '<input type="range" min="0" max="1" step="1" value="' + pos + '" id="adjSeasonRange" aria-label="' + esc(T("rv.season.sLabel")) + '">' +
        '<span class="' + (pos === 1 ? "on" : "") + '">' + esc(T("rv.season.winter")) + " " + esc(site.winter.dates.join(", ")) + "</span></div>" +
        '<div class="kpis">' + UI.kpi(T("rv.season.detectedIn", { s: seasonName(cur) }), cs.species_detected, { color: "accent" }) +
        UI.kpi(T("rv.season.detectedIn", { s: seasonName(other) }), os.species_detected) +
        UI.kpi(T("rv.season.newVs", { s: seasonName(other) }), fresh.length) +
        UI.kpi(T("rv.season.missing", { s: seasonName(other) }), missing.length) + "</div>" +
        '<p class="hint">' + esc(T("rv.season.reps", { a: cs.samples, sa: seasonName(cur), b: os.samples, sb: seasonName(other) })) + " " +
        esc(doc.not_absent_note) + "</p>" +
        '<p class="hint">' + esc(T("rv.season.rule")) + " " + esc(JSON.stringify(doc.season_rule.value)) + ". " +
        esc(doc.season_rule.why) + "</p>" +
        seasonQuality(site) +
        '<div class="card-foot">' + UI.button(T("rv.season.print"), { variant: "primary", id: "adjSitePdf", icon: "download" }) +
        '<span class="hint">' + esc(T("rv.season.printHint")) + "</span></div>" +
        '<div id="adjSeasonMap" class="adj-map short"></div>' +
        (site.coordinate_note ? '<p class="hint">' + esc(T("rv.map.note")) + " " + esc(site.coordinate_note) + ".</p>" : "")) +
      UI.card('<div class="adj-two"><div><h3 class="adj-h3">' + esc(T("rv.season.newIn", { s: seasonName(cur) })) + "</h3>" + list(fresh, cur) + "</div>" +
        '<div><h3 class="adj-h3">' + esc(T("rv.season.seenNot", { o: seasonName(other), s: seasonName(cur) })) + "</h3>" + list(missing, other) + "</div></div>" +
        '<h3 class="adj-h3">' + esc(T("rv.season.allIn", { s: seasonName(cur) })) + "</h3>" + list(inCur, cur));
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
        L.circleMarker([site.latitude, site.longitude], { radius: 12, color: tok("--surface-raised", "#fff"), weight: 2,
          fillColor: pos === 0 ? tok("--alert-rare", "#e0912f") : tok("--accent-secondary", "#bd3b67"), fillOpacity: 1 }).addTo(m)
          .bindTooltip(T("rv.season.speciesTip", { s: seasonName(cur), n: cs.species_detected }), { permanent: true });
        S.seasonMap = m; setTimeout(function () { m.invalidateSize(); }, 200);
      } else { el.outerHTML = '<p class="hint">' + esc(T("rv.season.noPin")) + "</p>"; }
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
    function text(g) { return Object.keys(g.verdicts).map(function (k) { return g.verdicts[k] + " " + T("rv.verdict." + k); }).join(", ") || "n/a"; }
    var uneven = a.kept && b.kept ? Math.max(a.kept, b.kept) / Math.min(a.kept, b.kept) : 0;
    var notClean = Object.keys(a.verdicts).concat(Object.keys(b.verdicts)).some(function (k) { return k !== "Usable"; });
    if (!notClean && uneven < 2) return "";
    return '<div class="adj-note">' + T("rv.season.care", { a: esc(text(a)), ar: UI.num(a.kept), b: esc(text(b)), br: UI.num(b.kept) }) +
      (uneven >= 2 ? esc(T("rv.season.depth", { x: uneven.toFixed(1) })) : "") + esc(T("rv.season.careEnd")) + "</div>";
  }

  function list(rows, season) {
    if (!rows.length) return '<p class="hint">' + esc(T("rv.season.none2")) + "</p>";
    var listed = invasiveSet();
    return '<ul class="adj-list">' + rows.map(function (r) {
      return "<li><i>" + esc(r.species) + "</i>" +
        (listed[r.species] ? ' <span class="badge invasive" title="' + esc(T("rv.season.listedTip")) + '">' + esc(T("rv.season.listed")) + "</span>" : "") +
        ' <span class="hint">' + esc(T("rv.season.repl", { r: UI.num(r[season + "_reads"]), n: r[season + "_replicates"] })) + "</span></li>"; }).join("") + "</ul>";
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
    root().innerHTML = (pinList.length ? UI.card('<div class="card-head"><div><div class="hint">' + esc(T("rv.alerts.mapHint")) + "</div>" +
      '<h2 class="adj-h2">' + esc(T("rv.alerts.mapHead")) + '</h2></div></div><div id="adjAlertMap" class="adj-map"></div>' +
      '<p class="hint">' + esc(T("rv.alerts.pins", { n: pinList.length })) + "</p>") : "") +
      UI.card('<div class="card-head"><div><div class="hint">' + esc(T("rv.alerts.logHint")) + "</div>" +
      '<h2 class="adj-h2">' + esc(T("rv.alerts.logHead")) + "</h2></div></div>" +
      (rows.length ? '<div class="table-wrap"><table class="data"><thead><tr><th>' + esc(T("rv.alerts.col.level")) + "</th><th>" + esc(T("rv.alerts.col.alert")) +
        "</th><th>" + esc(T("rv.alerts.col.pin")) + "</th><th>" + esc(T("rv.alerts.col.sample")) + "</th><th>" + esc(T("rv.col.reads")) +
        "</th><th>" + esc(T("rv.alerts.col.analysis")) + "</th><th>" + esc(T("rv.alerts.col.after")) + "</th></tr></thead><tbody>" +
        rows.map(function (a) {
          return '<tr><td><span class="badge ' + LEVEL_CLASS[a.level] + '">' + esc(T("rv.level." + a.level)) + "</span></td><td>" + esc(a.headline) +
            '</td><td class="mono">' + pin(a.pin) + "</td><td>" + esc(a.sample_label) + "</td><td>" + UI.num(a.reads) + "</td><td>" +
            (a.analysis_seconds === undefined ? "-" : a.analysis_seconds + " s") + "</td><td>" +
            (a.latency_seconds === null ? "-" : a.latency_seconds + " s") + "</td></tr>"; }).join("") + "</tbody></table></div>" +
        '<p class="hint">' + esc(T("rv.alerts.foot", { b: d.latency_budget_seconds })) + "</p>"
        : UI.state("empty", T("rv.alerts.none"), T("rv.alerts.noneBody"))));
    drawAlertMap(pinList);
  }

  function drawAlertMap(pinList) {
    var el = document.getElementById("adjAlertMap");
    if (!el || !window.L) return;
    if (S.alertMap) { S.alertMap.remove(); S.alertMap = null; }
    var m = L.map(el);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap" }).addTo(m);
    var rank = { CRITICAL: 0, HIGH: 1, WATCH: 2 };
    var bounds = [];
    pinList.forEach(function (p) {
      var worst = p.items.slice().sort(function (a, b) { return rank[a.level] - rank[b.level]; })[0];
      var seen = {}, lines = [];
      p.items.forEach(function (a) {
        var k = a.level + a.species;
        if (!seen[k] && lines.length < 6) { seen[k] = 1; lines.push(esc(T("rv.level." + a.level)) + ": " + esc(a.headline)); }
      });
      L.circleMarker([p.lat, p.lon], { radius: 10, color: tok("--surface-raised", "#fff"), weight: 2, fillColor: levelColour(worst.level), fillOpacity: 1 })
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
        UI.card('<h2 class="adj-h2">' + esc(T("rv.why.thresholds")) + '</h2><p class="hint">bioradar/adjudicate/thresholds.json</p>' +
          '<div class="table-wrap"><table class="data"><thead><tr><th>' + esc(T("rv.why.col.setting")) + "</th><th>" + esc(T("rv.why.col.value")) +
          "</th><th>" + esc(T("rv.why.col.why")) + "</th></tr></thead><tbody>" +
          Object.keys(th).map(function (k) {
            var val = typeof th[k].value === "object" ? JSON.stringify(th[k].value) : th[k].value + " " + (th[k].unit || "");
            return '<tr><td class="mono">' + esc(k) + "</td><td>" + esc(val) + "</td><td>" + esc(th[k].why) + "</td></tr>"; }).join("") +
          "</tbody></table></div>") +
        UI.card('<h2 class="adj-h2">' + esc(T("rv.why.reference")) + "</h2><p>" + esc(pr.reference.name) + " &middot; " + esc(pr.reference.reference_database_version) +
          '</p><p class="hint">' + esc(T("rv.why.refLine", { n: UI.num(pr.reference.amplicons_extracted), s: UI.num(pr.reference.distinct_species) })) +
          " <code>" + esc(pr.reference.ncbi_query) + "</code>. " + esc(pr.reference.note) + "</p>") +
        UI.card('<h2 class="adj-h2">' + esc(T("rv.why.datasets")) + "</h2>" + pr.manifest.datasets.map(function (d) {
          return "<p><b>" + esc(d.bioproject) + "</b> &middot; " + esc(d.title) + " &middot; " + esc(d.centre) +
            '<br><span class="hint">' + esc(d.used_for) + " &middot; " + d.runs.length + " " + esc(T("rv.why.run")) + ' &middot; <a target="_blank" rel="noopener" href="' +
            esc(d.ena_url) + '">' + esc(T("rv.why.ena")) + "</a> &middot; " + esc(d.publication) + "</span></p>"; }).join("") +
          '<p class="hint">' + esc(pr.manifest.mates_downloaded) + "</p>");
    }).catch(function (e) { root().innerHTML = UI.state("error", T("rv.couldNotLoad"), e.message); });
  }
})();
