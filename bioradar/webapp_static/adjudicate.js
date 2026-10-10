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
      "rv.nav": "Check samples",
      "rv.title": "Check a water sample",
      "rv.lede": "Pick a real water sample. See which fish were found, what was set aside and why, and what to do next.",
      "rv.tabs.label": "Sections of this page",
      "rv.tab.sample": "Sample", "rv.tab.guard": "Record check", "rv.tab.seasons": "Seasons & map",
      "rv.tab.alerts": "Alerts", "rv.tab.why": "Numbers & words",
      "rv.notBuilt": "Results are not ready yet",
      "rv.notBuiltBody": "Run this one command to check every real sample, then reload the page: python -m bioradar.adjudicate.runner all",
      "rv.couldNotLoad": "Could not load this",
      "rv.couldNotProcess": "This sample could not be checked",
      "rv.realSample": "Real sample", "rv.rerun": "Check again now", "rv.rerunTitle": "Run the full check again, right now",
      "rv.whySample": "Why we picked it:",
      "rv.running": "Checking the sample now", "rv.loading": "Loading the result",
      "rv.preRun": "Result was ready before. Loaded in {s} s.", "rv.live": "Checked just now in {s} s.",
      "rv.role.mixed": "Fish mixtures (only the count is known)", "rv.role.mixed_truth": "Fish mixtures with a known recipe",
      "rv.role.unknown_truth": "Mixtures with fish missing from the public list", "rv.role.poor": "Too little good DNA",
      "rv.role.unknowns": "Unknown fish and harmful fish", "rv.role.field": "Field water samples (summer and winter)",
      "rv.verdict.Usable": "Good to use", "rv.verdict.Usable with caution": "Use with care", "rv.verdict.Retake sample": "Collect a new sample",
      "rv.level.CRITICAL": "ACT NOW", "rv.level.HIGH": "SERIOUS", "rv.level.WATCH": "KEEP WATCHING",
      "rv.noTrigger": "ALL CLEAR", "rv.notChecked": "NOT CHECKED",
      "rv.noTrigger.head": "No harmful fish from our list were found in this sample.",
      "rv.noTrigger.body": "The rule: a harmful fish is named for sure and at least 10 pieces of its DNA are found. None here. This does not prove the water is free of them.",
      "rv.notChecked.head": "We did not look for harmful fish, because this sample needs to be collected again.",
      "rv.notChecked.body": "There is too little good DNA to say anything about harmful fish.",
      "rv.pin": "Place", "rv.reads": "DNA pieces", "rv.matchScore": "match score", "rv.notRecorded": "not written down",
      "rv.summary": "How good is this sample?",
      "rv.kept": "Matched a fish", "rv.unknown": "Fish we could not name", "rv.dropped": "Set aside",
      "rv.distinct": "different codes",
      "rv.stackLabel": "Share of DNA pieces that matched a fish, could not be named, or were set aside",
      "rv.readsLine": "{reads} DNA pieces, {distinct} different codes. The file type is {fmt}, found by looking inside the file.",
      "rv.noQuality": " This file has no quality marks, so the quality check was skipped.",
      "rv.sourceLine": " Source: {project}, run {run}.", "rv.sourceDate": " Collected {date}.",
      "rv.src.lab": "Made in a lab, so there is no collection date or place",
      "rv.ref.refseq_12s": "NCBI RefSeq fish list for 12S ({v})", "rv.ref.refseq_coi_16s": "NCBI RefSeq fish list for COI and 16S ({v})",
      "rv.ref.fish_egg_paper": "The authors' own fish DNA library for these mixtures",
      "rv.print": "Print a one-page report (PDF)", "rv.csv": "All set-aside DNA (CSV file)", "rv.sourceRecord": "Where it came from",
      "rv.dropWhy": "Why some DNA was set aside", "rv.nothingDropped": "Nothing was set aside.",
      "rv.examples": "Examples, each with its reason ({n} set-aside pieces are in the CSV file)",
      "rv.col.reads": "DNA pieces", "rv.col.sequence": "DNA code", "rv.col.reason": "Reason",
      "rv.seq": "codes",
      "rv.reason.invalid_characters": "Not DNA", "rv.reason.too_short": "Too short",
      "rv.reason.too_many_n": "Too many unreadable letters", "rv.reason.low_complexity": "Same letters repeated",
      "rv.reason.low_quality": "Poor quality", "rv.reason.singleton": "Seen only once (maybe a mistake)",
      "rv.reason.human_contamination": "Human DNA", "rv.reason.unrelated": "Not like any fish on the list",
      "rv.speciesHead": "Fish found and their share",
      "rv.retake.head": "Collect a new sample", "rv.retake.body": "There is too little good DNA to say which fish live here. We do not guess.",
      "rv.noSpecies": "No fish could be named for sure.",
      "rv.invasive": "harmful fish", "rv.cannotSeparate": "look-alikes", "rv.identity": "match", "rv.score": "score",
      "rv.speciesCount": "fish",
      "rv.denom": "<b>How a share is worked out:</b> the DNA pieces of one fish, divided by {den} pieces that could be named. Not counted: {dropped} pieces that were set aside, and {novel} pieces too different from any fish on the list to name. The sample held {total} pieces in all. A share is a share of DNA. It is not a count of animals and not their weight.",
      "rv.traceNote": "Fish with fewer than 10 DNA pieces ({n}) are shown as \"trace\", not as found. Two fish with the same DNA in this gene region are shown together. We never pick one of them by guess.",
      "rv.scoreNote": "The match score runs from 0 to 1. It goes down as the match gets weaker, and it is halved when another fish matches almost as well. It never goes above 0.99 for a named fish or 0.60 for anything not confirmed. It is a rule of thumb, not a true chance.",
      "rv.src.title": "Where this sample comes from", "rv.src.sub": "Source and details",
      "rv.src.dataset": "Data set", "rv.src.run": "Run / sample", "rv.src.alias": "other name",
      "rv.src.file": "Original file", "rv.src.marker": "Gene region", "rv.src.markerFallback": "see the data set record",
      "rv.src.reference": "Known-fish list", "rv.src.collected": "Collected on", "rv.src.place": "Place",
      "rv.src.note": "These checks only look at this one record. Checks across many records are on the Record check tab.",
      "rv.chk.ok": "ok", "rv.chk.note": "note", "rv.chk.problem": "problem", "rv.chk.missing": "missing",
      "rv.chk.noDate": "no collection date written down", "rv.chk.future": "the date is in the future",
      "rv.chk.dateOk": "not in the future; exact to the {p}", "rv.chk.yearOnly": ". Only the year is known, so it cannot be placed in a season",
      "rv.chk.noPin": "no map point written down", "rv.chk.pinOk": "a possible place on Earth", "rv.chk.pinLow": "; not very exact: {n}",
      "rv.chk.pinBad": "not a possible place on Earth",
      "rv.prec.day": "day", "rv.prec.month": "month", "rv.prec.year": "year",
      "rv.queue.head": "To check by a person: DNA we did not name",
      "rv.queue.none": "Nothing needs a second look.",
      "rv.queue.intro": "{n} kinds of DNA are not confirmed. Each row shows the closest fish on the list and how alike they are (a measured amount, not a chance). The match score stops at 0.60, so none of these can pass as confirmed.",
      "rv.queue.ref": "Known-fish list used: <b>{ref}</b>. The checker does not report how much of the DNA overlapped. A short overlap lowers the match, so it is not hidden.",
      "rv.queue.closest": "Closest fish", "rv.queue.state": "Status", "rv.queue.whyUnknown": "Why we did not name it",
      "rv.queue.needsReview": "needs a check", "rv.queue.check": "Check on NCBI", "rv.queue.showing": "Showing the 12 with the most DNA, out of {n}.",
      "rv.exp.count": "Check against what the source says was mixed", "rv.exp.comp": "Check against the recipe",
      "rv.exp.groups": "(and {n} groups of look-alike fish)",
      "rv.exp.species": "Fish", "rv.exp.expected": "Should be", "rv.exp.observed": "We found", "rv.exp.result": "Result",
      "rv.exp.tol": "Shares within {x} times of the real share: {n} of {m}.",
      "rv.exp.extra": "Also found, but not in the mixture: {n}. The authors report {k} of these as false hits in their own paper.",
      "rv.exp.more": "More about this check",
      "rv.count.head": "How the DNA was counted",
      "rv.ug.head": "What the unknown DNA really is",
      "rv.ug.intro": "These fish are missing from the public list, so the checker does not name them. The scientists who made this mixture published what is in it. The checker never saw that answer. It is shown here only so that you can judge the result.",
      "rv.ug.truth": "Closest fish in the authors' library", "rv.ug.pieces": "DNA pieces", "rv.ug.closest": "Closest fish on the public list",
      "rv.ug.inMix": "In the mixture?", "rv.ug.yes": "yes", "rv.ug.no": "no", "rv.ug.share": "Real share",
      "rv.ug.wrong": "Careful: {n} kinds of fish that were not in the mixture were named. Some are close relatives of a missing fish. A relative can look almost the same in this gene region. Some may be small amounts of other DNA.",
      "rv.ug.none": "No unknown groups to explain.",
      "rv.map.head": "Where the water was taken", "rv.map.noPin": "No map point was written down for this sample, so it cannot be shown on the map.",
      "rv.map.note": "Note:", "rv.map.noFlag": "No harmful fish found",
      "rv.guard.title": "Record check", "rv.guard.sub": "Real records from a public archive. They are never edited.",
      "rv.guard.clean": "database is clean", "rv.guard.notClean": "database is NOT clean",
      "rv.guard.checked": "Records checked", "rv.guard.kept": "Kept in the clean database", "rv.guard.rejected": "Turned away", "rv.guard.merged": "Merged",
      "rv.guard.source": "Source: ENA project PRJEB108476 (copy fingerprint {md5}). Area line: <b>{b}</b> ({src}). Today is {today}.",
      "rv.guard.post": "<b>Final check of the clean database:</b> {n} records. Repeated IDs: {dup}. Outside the area: {out}. Dates in the future: {fut}. Fish names with two spellings left: {sp}.",
      "rv.guard.rule.duplicate_id": "Same sample ID twice", "rv.guard.rule.outside_boundary": "Map point outside the area",
      "rv.guard.rule.no_coordinates": "No map point", "rv.guard.rule.future_date": "Date in the future",
      "rv.guard.rule.double_spelling": "Fish name spelt two ways",
      "rv.guard.nCase": "{n} {what}", "rv.guard.w.merged": "merged", "rv.guard.w.handled": "handled", "rv.guard.w.rejected": "turned away",
      "rv.guard.absent": "not in the data",
      "rv.guard.noCase": "The real records had no such case, so there is nothing to show. The rule is still on.",
      "rv.guard.every": "Every decision", "rv.guard.col.rule": "Rule", "rv.guard.col.action": "What was done", "rv.guard.col.record": "Record",
      "rv.guard.first": "Showing the first 120 of {n} decisions.",
      "rv.season.none": "No summer and winter pair", "rv.season.noneBody": "No place in the checked samples has both seasons.",
      "rv.season.location": "Place", "rv.season.summer": "Summer", "rv.season.winter": "Winter",
      "rv.season.detectedIn": "Fish found ({s})", "rv.season.newVs": "New compared with {s}", "rv.season.missing": "Not found now, but found in {s}",
      "rv.season.reps": "{a} repeat sample(s) in {sa}, {b} in {sb}.",
      "rv.season.rule": "How seasons are decided (set in thresholds.json):",
      "rv.season.print": "Print a one-page report for this place (PDF)", "rv.season.printHint": "One page: the animals, the risk, the source and dates, what we are unsure about, and what to do.",
      "rv.season.noPin": "No map point was written down for this place.",
      "rv.season.newIn": "New in {s}", "rv.season.seenNot": "Seen in {o}, not found in {s}", "rv.season.allIn": "Found in {s} (all)",
      "rv.season.sLabel": "Season", "rv.season.speciesTip": "{s}: {n} fish",
      "rv.season.care": "<b>Read this comparison with care.</b> Summer samples: {a} ({ar} DNA pieces named). Winter samples: {b} ({br} DNA pieces named).",
      "rv.season.depth": " One season has about {x} times more DNA than the other.",
      "rv.season.careEnd": " A season with less DNA can show fewer fish because of the data, not because of the water.",
      "rv.season.none2": "None.", "rv.season.repl": "{r} DNA pieces, {n} repeat(s)",
      "rv.season.listed": "harmful fish", "rv.season.listedTip": "A fish on our harmful-fish list, confirmed in an alert elsewhere in this project",
      "rv.alerts.mapHint": "One dot for each place. The colour shows the worst alert there.", "rv.alerts.mapHead": "Alert map",
      "rv.alerts.pins": "{n} places. Samples that gave only a rough position share one dot.",
      "rv.alerts.logHint": "A banner on screen and this list. No text message or e-mail is sent.", "rv.alerts.logHead": "List of alerts",
      "rv.alerts.col.level": "How serious", "rv.alerts.col.alert": "Alert", "rv.alerts.col.pin": "Place", "rv.alerts.col.sample": "Sample",
      "rv.alerts.col.analysis": "Check took", "rv.alerts.col.after": "Alert after result",
      "rv.alerts.foot": "The alert is written within {b} s of the result being ready. The time the check took is shown on its own. It is not hidden inside that number. Results are made ahead of time, so an alert shows as soon as you open the sample. Samples with no alert are not listed. The rule was on, but they held no harmful fish from the list.",
      "rv.alerts.none": "No alerts yet", "rv.alerts.noneBody": "No real sample has crossed the danger rule. The rule is on. Nothing is made up.",
      "rv.why.thresholds": "Every rule number, in one file, with the reason", "rv.why.col.setting": "Rule", "rv.why.col.value": "Number", "rv.why.col.why": "Why this number",
      "rv.why.reference": "Known-fish list", "rv.why.refLine": "{n} DNA codes, {s} fish. How it was built:",
      "rv.why.datasets": "Real data sets used", "rv.why.run": "run(s)", "rv.why.ena": "Archive record",
      "rv.plain.head": "In plain words",
      "rv.plain.main": "This water sample held {total} pieces of DNA. {kept} matched a known fish. {unknown} came from fish we could not name. {dropped} was set aside because it was broken, too short or not from a fish.",
      "rv.plain.v.Usable": "The sample is good enough to trust.",
      "rv.plain.v.Usable with caution": "A lot of the DNA was set aside, so read the fish list with care.",
      "rv.plain.v.Retake sample": "There is too little good DNA to say which fish live here. Please collect a new water sample.",
      "rv.plain.alert": "Harmful fish were found: {names}. See the box at the top of the page.",
      "rv.plain.noAlert": "No harmful fish from the list were found.",
      "rv.plain.guard": "Before a record goes into the database, it is checked. A record with a repeated ID, a place outside the area, a date in the future or a fish name spelt two ways is merged or turned away. The reason is written down. The original data is never changed.",
      "rv.plain.seasons": "This page compares one place in two seasons. It shows which fish were found in one season but not the other. A different list does not always mean the fish moved. The sample may simply hold less DNA.",
      "rv.plain.alerts": "When a fish that harms local waters is found, an alert is written here. It gives the place, the fish and how serious it is.",
      "rv.plain.why": "Every rule the checker uses is kept in one file, with the reason for it. Below you will find those rules, the list of known fish DNA, the data used, and a short list of words explained.",
      "rv.gloss.head": "Words explained",
      "rv.gl.edna.t": "eDNA (DNA in water)",
      "rv.gl.edna.d": "Tiny bits of DNA that animals leave in water. We test the water instead of catching the fish.",
      "rv.gl.piece.t": "DNA piece (read)",
      "rv.gl.piece.d": "One short piece of DNA read by the machine. One sample holds thousands.",
      "rv.gl.marker.t": "Gene region (marker)",
      "rv.gl.marker.d": "A short part of the DNA that differs from fish to fish, like a name tag. 12S, COI and 16S are three such parts.",
      "rv.gl.list.t": "Known-fish list (reference list)",
      "rv.gl.list.d": "A list of fish DNA that scientists have already named. Each piece of DNA is compared with this list.",
      "rv.gl.match.t": "Match (identity)",
      "rv.gl.match.d": "How alike two pieces of DNA are. 100% means exactly the same.",
      "rv.gl.score.t": "Match score",
      "rv.gl.score.d": "A number from 0 to 1 that shows how sure the checker is. It is a rule of thumb, not a true chance.",
      "rv.gl.unknown.t": "Unknown",
      "rv.gl.unknown.d": "DNA that matched no fish on the list well enough. It is never named by guess. A person checks it.",
      "rv.gl.dropped.t": "Set aside",
      "rv.gl.dropped.d": "DNA we did not use, because it was too short, broken, human, or not from a fish. Each piece has a written reason.",
      "rv.gl.complex.t": "Look-alike fish",
      "rv.gl.complex.d": "Some fish have the same DNA in the gene region we read. We show them together and do not guess one.",
      "rv.gl.invasive.t": "Harmful fish (invasive species)",
      "rv.gl.invasive.d": "A fish that came from another place and harms local fish and water.",
      "rv.gl.retake.t": "Collect a new sample",
      "rv.gl.retake.d": "The sample has too little good DNA. Take new water and test again.",
      "rv.gl.mock.t": "Mock mixture",
      "rv.gl.mock.d": "A mixture made on purpose from fish with known names. It is used to test the checker.",
      "rv.gl.share.t": "Share",
      "rv.gl.share.d": "The part of the named DNA that belongs to one fish. It is a share of DNA, not a count of animals.",
      "rv.gl.boundary.t": "Area line (boundary)",
      "rv.gl.boundary.d": "The line on the map around the protected area. A record outside it is turned away.",
      "rv.up.head": "Try your own file",
      "rv.up.body": "Bring a file of DNA pieces (FASTA or FASTQ). It is checked the same way as the samples above. The file is read once and deleted. It is not saved.",
      "rv.up.marker": "Gene region in your file",
      "rv.up.markerHelp": "If you are not sure, choose 12S.",
      "rv.up.choose": "Choose a file", "rv.up.none": "No file chosen",
      "rv.up.run": "Check my file", "rv.up.working": "Checking your file",
      "rv.up.limit": "Files up to {max} MB. Only the first {reads} DNA pieces are checked.",
      "rv.up.tooBig": "That file is {mb} MB. The limit is {max} MB.",
      "rv.up.done": "Done in {s} s. Your file was not saved.",
      "rv.up.failed": "Your file could not be checked.",
      "rv.up.source": "Your own file",
      "rv.up.note": "This is your own file, so there is no published answer to compare it with, and no map point.",
      "rv.up.tag": "your file"
    },
    hi: {
      "rv.nav": "नमूने जाँचें",
      "rv.title": "पानी का नमूना जाँचें",
      "rv.lede": "पानी का एक असली नमूना चुनें। देखें कि कौन सी मछलियाँ मिलीं, क्या अलग रखा गया और क्यों, और आगे क्या करना है।",
      "rv.tabs.label": "इस पन्ने के भाग",
      "rv.tab.sample": "नमूना", "rv.tab.guard": "रिकॉर्ड जाँच", "rv.tab.seasons": "मौसम और नक्शा",
      "rv.tab.alerts": "चेतावनी", "rv.tab.why": "संख्याएँ और शब्द",
      "rv.notBuilt": "परिणाम अभी तैयार नहीं हैं",
      "rv.notBuiltBody": "सभी असली नमूने जाँचने के लिए यह एक कमांड चलाएँ, फिर पन्ना दोबारा खोलें: python -m bioradar.adjudicate.runner all",
      "rv.couldNotLoad": "यह लोड नहीं हो सका",
      "rv.couldNotProcess": "इस नमूने की जाँच नहीं हो सकी",
      "rv.realSample": "असली नमूना", "rv.rerun": "अभी फिर जाँचें", "rv.rerunTitle": "पूरी जाँच अभी दोबारा चलाएँ",
      "rv.whySample": "इसे क्यों चुना:",
      "rv.running": "नमूने की जाँच चल रही है", "rv.loading": "परिणाम खुल रहा है",
      "rv.preRun": "परिणाम पहले से तैयार था। {s} सेकंड में खुला।", "rv.live": "अभी जाँचा गया, {s} सेकंड में।",
      "rv.role.mixed": "मछलियों के मिश्रण (केवल संख्या पता है)", "rv.role.mixed_truth": "मछलियों के मिश्रण, जिनकी विधि पता है",
      "rv.role.unknown_truth": "ऐसे मिश्रण जिनकी कुछ मछलियाँ सार्वजनिक सूची में नहीं", "rv.role.poor": "अच्छा DNA बहुत कम",
      "rv.role.unknowns": "अज्ञात मछलियाँ और हानिकारक मछलियाँ", "rv.role.field": "खेत या जल-स्थल के नमूने (गर्मी और सर्दी)",
      "rv.verdict.Usable": "उपयोग के लिए ठीक", "rv.verdict.Usable with caution": "सावधानी से उपयोग करें", "rv.verdict.Retake sample": "नया नमूना लें",
      "rv.level.CRITICAL": "अभी कार्रवाई करें", "rv.level.HIGH": "गंभीर", "rv.level.WATCH": "नज़र रखें",
      "rv.noTrigger": "सब ठीक", "rv.notChecked": "जाँच नहीं हुई",
      "rv.noTrigger.head": "इस नमूने में हमारी सूची की कोई हानिकारक मछली नहीं मिली।",
      "rv.noTrigger.body": "नियम: हानिकारक मछली पक्के तौर पर पहचानी जाए और उसके कम से कम 10 DNA टुकड़े मिलें। यहाँ ऐसा नहीं हुआ। इसका मतलब यह नहीं कि पानी उनसे मुक्त है।",
      "rv.notChecked.head": "हमने हानिकारक मछली नहीं खोजी, क्योंकि इस नमूने को दोबारा लेना है।",
      "rv.notChecked.body": "हानिकारक मछलियों के बारे में कुछ कहने लायक अच्छा DNA बहुत कम है।",
      "rv.pin": "स्थान", "rv.reads": "DNA टुकड़े", "rv.matchScore": "मिलान स्कोर", "rv.notRecorded": "लिखा नहीं गया",
      "rv.summary": "यह नमूना कितना अच्छा है?",
      "rv.kept": "मछली से मेल खाया", "rv.unknown": "जिनका नाम नहीं बता सके", "rv.dropped": "अलग रखा गया",
      "rv.distinct": "अलग-अलग कोड",
      "rv.stackLabel": "DNA टुकड़ों का हिस्सा: मछली से मेल खाए, नाम नहीं दिया जा सका, या अलग रखे गए",
      "rv.readsLine": "{reads} DNA टुकड़े, {distinct} अलग-अलग कोड। फ़ाइल का प्रकार {fmt} है, जो फ़ाइल के अंदर देखकर पता चला।",
      "rv.noQuality": " इस फ़ाइल में गुणवत्ता के निशान नहीं हैं, इसलिए गुणवत्ता जाँच छोड़ दी गई।",
      "rv.sourceLine": " स्रोत: {project}, रन {run}।", "rv.sourceDate": " संग्रह की तारीख {date}।",
      "rv.src.lab": "प्रयोगशाला में बनाया गया, इसलिए संग्रह की तारीख या स्थान नहीं है",
      "rv.ref.refseq_12s": "12S के लिए NCBI RefSeq मछली सूची ({v})", "rv.ref.refseq_coi_16s": "COI और 16S के लिए NCBI RefSeq मछली सूची ({v})",
      "rv.ref.fish_egg_paper": "इन मिश्रणों के लिए लेखकों की अपनी मछली DNA लाइब्रेरी",
      "rv.print": "एक पन्ने की रिपोर्ट छापें (PDF)", "rv.csv": "अलग रखे सभी DNA (CSV फ़ाइल)", "rv.sourceRecord": "यह कहाँ से आया",
      "rv.dropWhy": "कुछ DNA क्यों अलग रखा गया", "rv.nothingDropped": "कुछ भी अलग नहीं रखा गया।",
      "rv.examples": "उदाहरण, हर एक का कारण साथ में ({n} अलग रखे टुकड़े CSV फ़ाइल में हैं)",
      "rv.col.reads": "DNA टुकड़े", "rv.col.sequence": "DNA कोड", "rv.col.reason": "कारण",
      "rv.seq": "कोड",
      "rv.reason.invalid_characters": "DNA नहीं है", "rv.reason.too_short": "बहुत छोटा",
      "rv.reason.too_many_n": "बहुत से अपठनीय अक्षर", "rv.reason.low_complexity": "एक ही अक्षर बार-बार",
      "rv.reason.low_quality": "खराब गुणवत्ता", "rv.reason.singleton": "केवल एक बार दिखा (शायद गलती)",
      "rv.reason.human_contamination": "मानव DNA", "rv.reason.unrelated": "सूची की किसी मछली जैसा नहीं",
      "rv.speciesHead": "मिली मछलियाँ और उनका हिस्सा",
      "rv.retake.head": "नया नमूना लें", "rv.retake.body": "यह बताने लायक अच्छा DNA बहुत कम है कि यहाँ कौन सी मछलियाँ रहती हैं। हम अंदाज़ा नहीं लगाते।",
      "rv.noSpecies": "किसी मछली का पक्का नाम नहीं बताया जा सका।",
      "rv.invasive": "हानिकारक मछली", "rv.cannotSeparate": "एक जैसी दिखने वाली", "rv.identity": "मेल", "rv.score": "स्कोर",
      "rv.speciesCount": "मछलियाँ",
      "rv.denom": "<b>हिस्सा कैसे निकाला जाता है:</b> एक मछली के DNA टुकड़े, भाग उन {den} टुकड़ों से जिनका नाम बताया जा सका। गिनती में नहीं: अलग रखे गए {dropped} टुकड़े, और {novel} टुकड़े जो सूची की किसी मछली से इतने अलग थे कि नाम नहीं दिया जा सका। नमूने में कुल {total} टुकड़े थे। हिस्सा DNA का हिस्सा है। यह जानवरों की गिनती या उनका वज़न नहीं है।",
      "rv.traceNote": "10 से कम DNA टुकड़ों वाली मछलियाँ ({n}) \"थोड़ी मात्रा\" के रूप में दिखाई गई हैं, मिली हुई के रूप में नहीं। जिन दो मछलियों का DNA इस जीन क्षेत्र में एक जैसा है, उन्हें साथ दिखाया गया है। हम उनमें से किसी एक को अंदाज़े से नहीं चुनते।",
      "rv.scoreNote": "मिलान स्कोर 0 से 1 के बीच होता है। मेल कमज़ोर होने पर यह घटता है, और जब कोई दूसरी मछली लगभग उतनी ही मेल खाए तो आधा हो जाता है। नाम पाई मछली के लिए यह 0.99 से और अपुष्ट के लिए 0.60 से ऊपर कभी नहीं जाता। यह मोटा अंदाज़ा है, सच्ची संभावना नहीं।",
      "rv.src.title": "यह नमूना कहाँ से आया", "rv.src.sub": "स्रोत और ब्योरा",
      "rv.src.dataset": "डेटा सेट", "rv.src.run": "रन / नमूना", "rv.src.alias": "दूसरा नाम",
      "rv.src.file": "मूल फ़ाइल", "rv.src.marker": "जीन क्षेत्र", "rv.src.markerFallback": "डेटा सेट का रिकॉर्ड देखें",
      "rv.src.reference": "ज्ञात मछलियों की सूची", "rv.src.collected": "संग्रह की तारीख", "rv.src.place": "स्थान",
      "rv.src.note": "ये जाँचें केवल इसी एक रिकॉर्ड को देखती हैं। कई रिकॉर्डों की जाँचें रिकॉर्ड जाँच टैब में हैं।",
      "rv.chk.ok": "ठीक", "rv.chk.note": "ध्यान दें", "rv.chk.problem": "समस्या", "rv.chk.missing": "नहीं है",
      "rv.chk.noDate": "संग्रह की तारीख लिखी नहीं गई", "rv.chk.future": "तारीख भविष्य की है",
      "rv.chk.dateOk": "भविष्य की नहीं; सटीकता: {p}", "rv.chk.yearOnly": "। केवल साल पता है, इसलिए इसे किसी मौसम में नहीं रखा जा सकता",
      "rv.chk.noPin": "नक्शे का बिंदु लिखा नहीं गया", "rv.chk.pinOk": "पृथ्वी पर संभव स्थान", "rv.chk.pinLow": "; बहुत सटीक नहीं: {n}",
      "rv.chk.pinBad": "पृथ्वी पर संभव स्थान नहीं",
      "rv.prec.day": "दिन", "rv.prec.month": "महीना", "rv.prec.year": "साल",
      "rv.queue.head": "किसी व्यक्ति को जाँचना है: जिस DNA का नाम नहीं दिया",
      "rv.queue.none": "किसी को दोबारा देखने की ज़रूरत नहीं।",
      "rv.queue.intro": "{n} तरह के DNA की पुष्टि नहीं हुई। हर पंक्ति में सूची की सबसे नज़दीकी मछली और दोनों कितने मिलते हैं, यह दिखता है (मापी गई मात्रा, संभावना नहीं)। मिलान स्कोर 0.60 पर रुक जाता है, इसलिए इनमें से कोई पुष्ट नहीं माना जा सकता।",
      "rv.queue.ref": "उपयोग की गई ज्ञात मछलियों की सूची: <b>{ref}</b>। जाँचकर्ता यह नहीं बताता कि DNA कितना ऊपर-ऊपर मिला। कम मिलने पर मेल घटता है, इसलिए यह छिपता नहीं।",
      "rv.queue.closest": "सबसे नज़दीकी मछली", "rv.queue.state": "स्थिति", "rv.queue.whyUnknown": "नाम क्यों नहीं दिया",
      "rv.queue.needsReview": "जाँच ज़रूरी", "rv.queue.check": "NCBI पर जाँचें", "rv.queue.showing": "{n} में से सबसे अधिक DNA वाले 12 दिखाए गए।",
      "rv.exp.count": "स्रोत के अनुसार जो मिलाया गया था, उससे जाँच", "rv.exp.comp": "विधि से जाँच",
      "rv.exp.groups": "(और एक जैसी दिखने वाली मछलियों के {n} समूह)",
      "rv.exp.species": "मछली", "rv.exp.expected": "होना चाहिए", "rv.exp.observed": "हमें मिला", "rv.exp.result": "परिणाम",
      "rv.exp.tol": "असली हिस्से के {x} गुना के भीतर के हिस्से: {m} में से {n}।",
      "rv.exp.extra": "और भी मिलीं जो मिश्रण में नहीं थीं: {n}। लेखक अपने शोध-पत्र में इनमें से {k} को गलत संकेत बताते हैं।",
      "rv.exp.more": "इस जाँच के बारे में और",
      "rv.count.head": "DNA की गिनती कैसे की गई",
      "rv.ug.head": "अज्ञात DNA असल में क्या है",
      "rv.ug.intro": "ये मछलियाँ सार्वजनिक सूची में नहीं हैं, इसलिए जाँचकर्ता इनका नाम नहीं देता। यह मिश्रण बनाने वाले वैज्ञानिकों ने बताया है कि इसमें क्या है। जाँचकर्ता ने वह उत्तर कभी नहीं देखा। उसे यहाँ केवल इसलिए दिखाया गया है कि आप परिणाम को परख सकें।",
      "rv.ug.truth": "लेखकों की लाइब्रेरी की सबसे नज़दीकी मछली", "rv.ug.pieces": "DNA टुकड़े", "rv.ug.closest": "सार्वजनिक सूची की सबसे नज़दीकी मछली",
      "rv.ug.inMix": "क्या मिश्रण में थी?", "rv.ug.yes": "हाँ", "rv.ug.no": "नहीं", "rv.ug.share": "असली हिस्सा",
      "rv.ug.wrong": "सावधान: {n} ऐसी मछलियों के नाम बताए गए जो मिश्रण में थीं ही नहीं। कुछ किसी गायब मछली की करीबी रिश्तेदार हैं। इस जीन क्षेत्र में रिश्तेदार लगभग एक जैसा दिख सकता है। कुछ दूसरे DNA की थोड़ी मात्रा भी हो सकती हैं।",
      "rv.ug.none": "समझाने के लिए कोई अज्ञात समूह नहीं।",
      "rv.map.head": "पानी कहाँ से लिया गया", "rv.map.noPin": "इस नमूने के लिए नक्शे का बिंदु लिखा नहीं गया, इसलिए इसे नक्शे पर नहीं दिखाया जा सकता।",
      "rv.map.note": "ध्यान दें:", "rv.map.noFlag": "कोई हानिकारक मछली नहीं मिली",
      "rv.guard.title": "रिकॉर्ड जाँच", "rv.guard.sub": "सार्वजनिक अभिलेखागार के असली रिकॉर्ड। इन्हें कभी बदला नहीं जाता।",
      "rv.guard.clean": "डेटाबेस साफ़ है", "rv.guard.notClean": "डेटाबेस साफ़ नहीं है",
      "rv.guard.checked": "जाँचे गए रिकॉर्ड", "rv.guard.kept": "साफ़ डेटाबेस में रखे गए", "rv.guard.rejected": "लौटाए गए", "rv.guard.merged": "मिलाए गए",
      "rv.guard.source": "स्रोत: ENA परियोजना PRJEB108476 (प्रति की पहचान {md5})। क्षेत्र की रेखा: <b>{b}</b> ({src})। आज की तारीख {today} है।",
      "rv.guard.post": "<b>साफ़ डेटाबेस की अंतिम जाँच:</b> {n} रिकॉर्ड। दोहराए ID: {dup}। क्षेत्र के बाहर: {out}। भविष्य की तारीखें: {fut}। दो वर्तनी वाले मछली नाम बचे: {sp}।",
      "rv.guard.rule.duplicate_id": "एक ही नमूना ID दो बार", "rv.guard.rule.outside_boundary": "नक्शे का बिंदु क्षेत्र के बाहर",
      "rv.guard.rule.no_coordinates": "नक्शे का बिंदु नहीं", "rv.guard.rule.future_date": "भविष्य की तारीख",
      "rv.guard.rule.double_spelling": "मछली का नाम दो तरह से लिखा",
      "rv.guard.nCase": "{n} {what}", "rv.guard.w.merged": "मिलाए गए", "rv.guard.w.handled": "निपटाए गए", "rv.guard.w.rejected": "लौटाए गए",
      "rv.guard.absent": "डेटा में नहीं",
      "rv.guard.noCase": "असली रिकॉर्ड में ऐसा कोई मामला नहीं था, इसलिए दिखाने को कुछ नहीं। नियम फिर भी चालू है।",
      "rv.guard.every": "हर फ़ैसला", "rv.guard.col.rule": "नियम", "rv.guard.col.action": "क्या किया गया", "rv.guard.col.record": "रिकॉर्ड",
      "rv.guard.first": "{n} फ़ैसलों में से पहले 120 दिखाए गए।",
      "rv.season.none": "गर्मी और सर्दी का जोड़ा नहीं", "rv.season.noneBody": "जाँचे गए नमूनों में किसी स्थान के दोनों मौसम नहीं हैं।",
      "rv.season.location": "स्थान", "rv.season.summer": "गर्मी", "rv.season.winter": "सर्दी",
      "rv.season.detectedIn": "मिली मछलियाँ ({s})", "rv.season.newVs": "{s} की तुलना में नई", "rv.season.missing": "अब नहीं मिलीं, पर {s} में मिली थीं",
      "rv.season.reps": "{sa} में {a} दोहराए नमूने, {sb} में {b}।",
      "rv.season.rule": "मौसम कैसे तय होता है (thresholds.json में तय):",
      "rv.season.print": "इस स्थान की एक पन्ने की रिपोर्ट छापें (PDF)", "rv.season.printHint": "एक पन्ना: जानवर, जोखिम, स्रोत और तारीखें, जिनमें हमें पक्का भरोसा नहीं, और क्या करना है।",
      "rv.season.noPin": "इस स्थान के लिए नक्शे का बिंदु लिखा नहीं गया।",
      "rv.season.newIn": "{s} में नई", "rv.season.seenNot": "{o} में मिलीं, {s} में नहीं मिलीं", "rv.season.allIn": "{s} में मिलीं (सभी)",
      "rv.season.sLabel": "मौसम", "rv.season.speciesTip": "{s}: {n} मछलियाँ",
      "rv.season.care": "<b>इस तुलना को सावधानी से पढ़ें।</b> गर्मी के नमूने: {a} ({ar} DNA टुकड़ों को नाम मिला)। सर्दी के नमूने: {b} ({br} DNA टुकड़ों को नाम मिला)।",
      "rv.season.depth": " एक मौसम में दूसरे से लगभग {x} गुना अधिक DNA है।",
      "rv.season.careEnd": " जिस मौसम में DNA कम हो, वहाँ कम मछलियाँ दिख सकती हैं। इसका कारण डेटा है, पानी नहीं।",
      "rv.season.none2": "कोई नहीं।", "rv.season.repl": "{r} DNA टुकड़े, {n} दोहराव",
      "rv.season.listed": "हानिकारक मछली", "rv.season.listedTip": "हमारी हानिकारक मछलियों की सूची की मछली, जो इस परियोजना में कहीं चेतावनी में पक्की हुई",
      "rv.alerts.mapHint": "हर स्थान के लिए एक बिंदु। रंग वहाँ की सबसे गंभीर चेतावनी दिखाता है।", "rv.alerts.mapHead": "चेतावनी का नक्शा",
      "rv.alerts.pins": "{n} स्थान। जिन नमूनों में केवल मोटा स्थान मिला, वे एक बिंदु साझा करते हैं।",
      "rv.alerts.logHint": "स्क्रीन पर एक पट्टी और यह सूची। कोई SMS या ई-मेल नहीं भेजा जाता।", "rv.alerts.logHead": "चेतावनियों की सूची",
      "rv.alerts.col.level": "कितनी गंभीर", "rv.alerts.col.alert": "चेतावनी", "rv.alerts.col.pin": "स्थान", "rv.alerts.col.sample": "नमूना",
      "rv.alerts.col.analysis": "जाँच में लगा समय", "rv.alerts.col.after": "परिणाम के बाद चेतावनी",
      "rv.alerts.foot": "परिणाम तैयार होने के {b} सेकंड के भीतर चेतावनी लिखी जाती है। जाँच में लगा समय अलग दिखाया गया है, उस संख्या में छिपाया नहीं गया। परिणाम पहले से बने होते हैं, इसलिए नमूना खोलते ही चेतावनी दिखती है। जिन नमूनों में चेतावनी नहीं थी वे सूची में नहीं हैं। नियम चालू था, पर उनमें सूची की कोई हानिकारक मछली नहीं थी।",
      "rv.alerts.none": "अभी कोई चेतावनी नहीं", "rv.alerts.noneBody": "किसी असली नमूने ने खतरे का नियम पार नहीं किया। नियम चालू है। कुछ भी गढ़ा नहीं गया।",
      "rv.why.thresholds": "हर नियम की संख्या, एक फ़ाइल में, कारण के साथ", "rv.why.col.setting": "नियम", "rv.why.col.value": "संख्या", "rv.why.col.why": "यह संख्या क्यों",
      "rv.why.reference": "ज्ञात मछलियों की सूची", "rv.why.refLine": "{n} DNA कोड, {s} मछलियाँ। यह कैसे बनी:",
      "rv.why.datasets": "उपयोग किए गए असली डेटा सेट", "rv.why.run": "रन", "rv.why.ena": "अभिलेखागार का रिकॉर्ड",
      "rv.plain.head": "सरल शब्दों में",
      "rv.plain.main": "पानी के इस नमूने में DNA के {total} टुकड़े थे। {kept} एक जानी हुई मछली से मेल खाए। {unknown} ऐसी मछलियों के थे जिनका नाम हम नहीं बता सके। {dropped} को अलग रखा गया, क्योंकि वे टूटे हुए, बहुत छोटे या मछली के नहीं थे।",
      "rv.plain.v.Usable": "यह नमूना भरोसे लायक है।",
      "rv.plain.v.Usable with caution": "काफ़ी DNA अलग रखना पड़ा, इसलिए मछलियों की सूची सावधानी से पढ़ें।",
      "rv.plain.v.Retake sample": "यह बताने लायक अच्छा DNA बहुत कम है कि यहाँ कौन सी मछलियाँ रहती हैं। कृपया पानी का नया नमूना लें।",
      "rv.plain.alert": "हानिकारक मछलियाँ मिलीं: {names}। पन्ने के ऊपर का डिब्बा देखें।",
      "rv.plain.noAlert": "सूची की कोई हानिकारक मछली नहीं मिली।",
      "rv.plain.guard": "कोई रिकॉर्ड डेटाबेस में जाने से पहले जाँचा जाता है। जिस रिकॉर्ड में ID दोहराया हो, स्थान क्षेत्र के बाहर हो, तारीख भविष्य की हो या मछली का नाम दो तरह से लिखा हो, उसे मिला दिया जाता है या लौटा दिया जाता है। कारण लिख दिया जाता है। मूल डेटा कभी नहीं बदला जाता।",
      "rv.plain.seasons": "यह पन्ना एक ही स्थान की दो मौसमों में तुलना करता है। यह दिखाता है कि कौन सी मछलियाँ एक मौसम में मिलीं और दूसरे में नहीं। सूची अलग होने का मतलब हमेशा यह नहीं कि मछलियाँ चली गईं। हो सकता है नमूने में बस DNA कम हो।",
      "rv.plain.alerts": "जब स्थानीय पानी को नुकसान पहुँचाने वाली मछली मिलती है, तो यहाँ चेतावनी लिखी जाती है। उसमें स्थान, मछली और खतरा कितना गंभीर है, यह होता है।",
      "rv.plain.why": "जाँचकर्ता के सभी नियम एक फ़ाइल में कारण के साथ रखे हैं। नीचे वे नियम, ज्ञात मछलियों के DNA की सूची, उपयोग किया गया डेटा और कुछ शब्दों के अर्थ मिलेंगे।",
      "rv.gloss.head": "शब्दों के अर्थ",
      "rv.gl.edna.t": "eDNA (पानी में मिला DNA)",
      "rv.gl.edna.d": "DNA के बहुत छोटे अंश जो जानवर पानी में छोड़ते हैं। हम मछली पकड़ने के बजाय पानी की जाँच करते हैं।",
      "rv.gl.piece.t": "DNA टुकड़ा (रीड)",
      "rv.gl.piece.d": "मशीन से पढ़ा गया DNA का एक छोटा टुकड़ा। एक नमूने में हज़ारों होते हैं।",
      "rv.gl.marker.t": "जीन क्षेत्र (मार्कर)",
      "rv.gl.marker.d": "DNA का एक छोटा हिस्सा जो हर मछली में अलग होता है, नाम की पर्ची की तरह। 12S, COI और 16S ऐसे तीन हिस्से हैं।",
      "rv.gl.list.t": "ज्ञात मछलियों की सूची (संदर्भ सूची)",
      "rv.gl.list.d": "मछलियों के DNA की सूची जिन्हें वैज्ञानिक पहले ही नाम दे चुके हैं। हर DNA टुकड़े की इस सूची से तुलना होती है।",
      "rv.gl.match.t": "मेल (identity)",
      "rv.gl.match.d": "DNA के दो टुकड़े कितने मिलते-जुलते हैं। 100% का मतलब बिल्कुल एक जैसे।",
      "rv.gl.score.t": "मिलान स्कोर",
      "rv.gl.score.d": "0 से 1 के बीच की संख्या जो बताती है कि जाँचकर्ता को कितना भरोसा है। यह मोटा अंदाज़ा है, सच्ची संभावना नहीं।",
      "rv.gl.unknown.t": "अज्ञात",
      "rv.gl.unknown.d": "ऐसा DNA जो सूची की किसी मछली से ठीक से नहीं मिला। इसका नाम अंदाज़े से कभी नहीं दिया जाता। कोई व्यक्ति इसे जाँचता है।",
      "rv.gl.dropped.t": "अलग रखा गया",
      "rv.gl.dropped.d": "वह DNA जो हमने उपयोग नहीं किया, क्योंकि वह बहुत छोटा, टूटा हुआ, मानव का, या मछली का नहीं था। हर टुकड़े का कारण लिखा है।",
      "rv.gl.complex.t": "एक जैसी दिखने वाली मछलियाँ",
      "rv.gl.complex.d": "कुछ मछलियों का DNA हमारे पढ़े गए जीन क्षेत्र में एक जैसा होता है। हम उन्हें साथ दिखाते हैं और किसी एक का अंदाज़ा नहीं लगाते।",
      "rv.gl.invasive.t": "हानिकारक मछली (आक्रामक प्रजाति)",
      "rv.gl.invasive.d": "दूसरी जगह से आई मछली जो स्थानीय मछलियों और पानी को नुकसान पहुँचाती है।",
      "rv.gl.retake.t": "नया नमूना लें",
      "rv.gl.retake.d": "नमूने में अच्छा DNA बहुत कम है। नया पानी लें और फिर जाँचें।",
      "rv.gl.mock.t": "बनावटी मिश्रण",
      "rv.gl.mock.d": "जाने-पहचाने नाम वाली मछलियों से जानबूझकर बनाया गया मिश्रण। इससे जाँचकर्ता को परखा जाता है।",
      "rv.gl.share.t": "हिस्सा",
      "rv.gl.share.d": "नाम पाए DNA का वह भाग जो किसी एक मछली का है। यह DNA का हिस्सा है, जानवरों की गिनती नहीं।",
      "rv.gl.boundary.t": "क्षेत्र की रेखा (सीमा)",
      "rv.gl.boundary.d": "नक्शे पर संरक्षित क्षेत्र के चारों ओर की रेखा। इसके बाहर का रिकॉर्ड लौटा दिया जाता है।",
      "rv.up.head": "अपनी फ़ाइल आज़माएँ",
      "rv.up.body": "DNA टुकड़ों की एक फ़ाइल (FASTA या FASTQ) लाएँ। उसकी जाँच ऊपर के नमूनों की तरह ही होती है। फ़ाइल एक बार पढ़ी जाती है और तुरंत मिटा दी जाती है। वह सहेजी नहीं जाती।",
      "rv.up.marker": "आपकी फ़ाइल का जीन क्षेत्र",
      "rv.up.markerHelp": "पक्का न हो तो 12S चुनें।",
      "rv.up.choose": "फ़ाइल चुनें", "rv.up.none": "कोई फ़ाइल नहीं चुनी",
      "rv.up.run": "मेरी फ़ाइल जाँचें", "rv.up.working": "आपकी फ़ाइल जाँची जा रही है",
      "rv.up.limit": "{max} MB तक की फ़ाइलें। केवल पहले {reads} DNA टुकड़ों की जाँच होती है।",
      "rv.up.tooBig": "वह फ़ाइल {mb} MB की है। सीमा {max} MB है।",
      "rv.up.done": "{s} सेकंड में पूरा हुआ। आपकी फ़ाइल सहेजी नहीं गई।",
      "rv.up.failed": "आपकी फ़ाइल की जाँच नहीं हो सकी।",
      "rv.up.source": "आपकी अपनी फ़ाइल",
      "rv.up.note": "यह आपकी अपनी फ़ाइल है, इसलिए तुलना के लिए कोई प्रकाशित उत्तर नहीं है और नक्शे का कोई बिंदु भी नहीं।",
      "rv.up.tag": "आपकी फ़ाइल"
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
        '<div id="adjPlain"></div><div id="adjBanner"></div><div id="adjRoot" class="stack" aria-live="polite"></div>';
      container.querySelectorAll("[data-adj-tab]").forEach(function (b) {
        b.addEventListener("click", function () { setTab(b.dataset.adjTab); });
      });
    },
    onShow: function () { init(); }
  });

  /* "In plain words": one short box at the top of every tab, written for someone who is not a scientist. */
  function plainBox(html) {
    return '<aside class="plain-box" aria-label="' + esc(T("rv.plain.head")) + '"><b>' + esc(T("rv.plain.head")) +
      "</b><p>" + html + "</p></aside>";
  }
  function setPlain(html) {
    var el = document.getElementById("adjPlain");
    if (el) el.innerHTML = html ? plainBox(html) : "";
  }
  function plainForSample(r) {
    var tot = Math.max(r.reads_total, 1), s = r.summary;
    var bits = [T("rv.plain.main", { total: UI.num(r.reads_total), kept: pct(s.kept.reads / tot, 0),
                                     unknown: pct(s.unknown.reads / tot, 0), dropped: pct(s.dropped.reads / tot, 0) }),
                T("rv.plain.v." + r.verdict)];
    if (r.verdict !== "Retake sample") {
      var names = [];
      (r.alerts || []).forEach(function (a) { if (a.kind === "confirmed" && names.indexOf(a.common_name) < 0) names.push(a.common_name); });
      bits.push(names.length ? T("rv.plain.alert", { names: names.join(", ") }) : T("rv.plain.noAlert"));
    }
    return bits.map(esc).join(" ");
  }

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
      var first = idx.samples.filter(function (s) { return s.sample_id === "ZEN-G1"; })[0] ||
        idx.samples.filter(function (s) { return s.role === "mixed_truth"; })[0] || idx.samples[0];
      S.id = first.sample_id;
      render();
      selectSample(S.id);
    }).catch(function (err) {
      root().innerHTML = UI.state("empty", T("rv.notBuilt"), T("rv.notBuiltBody") + " (" + esc(err.message) + ")");
    });
  }

  function render() {
    if (!root()) return;
    if (S.tab === "sample") setPlain(S.result ? plainForSample(S.result) : "");
    else setPlain(esc(T("rv.plain." + S.tab)));
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
    var order = ["mixed_truth", "unknown_truth", "mixed", "poor", "unknowns", "field"];
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
      '<div class="hint" id="adjWhy" style="margin-top:8px"></div></div>' + uploadCard();
  }

  /* ── bring your own file ────────────────────────────────────────────── */

  var MAX_UPLOAD_MB = 12, UPLOAD_READS = 60000;

  function uploadCard() {
    return '<div class="card sm adj-upload"><h2 class="adj-h2">' + esc(T("rv.up.head")) + "</h2>" +
      "<p>" + esc(T("rv.up.body")) + "</p>" +
      '<div class="row">' +
      '<label for="adjUpMarker" class="hint">' + esc(T("rv.up.marker")) + "</label>" +
      '<select id="adjUpMarker" class="adj-select" aria-describedby="adjUpHelp"><option value="12S">12S</option><option value="COI">COI</option><option value="16S">16S</option></select>' +
      '<input type="file" id="adjUpFile" class="adj-file" accept=".fa,.fasta,.fna,.fq,.fastq,.gz,.txt" aria-label="' + esc(T("rv.up.choose")) + '">' +
      UI.button(T("rv.up.run"), { id: "adjUpRun", variant: "primary", size: "sm" }) + "</div>" +
      '<p class="hint" id="adjUpHelp">' + esc(T("rv.up.markerHelp")) + " " +
      esc(T("rv.up.limit", { max: MAX_UPLOAD_MB, reads: UI.num(UPLOAD_READS) })) + "</p>" +
      '<p class="hint" id="adjUpStatus" role="status"></p></div>';
  }

  function wireUpload() {
    var btn = document.getElementById("adjUpRun");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var input = document.getElementById("adjUpFile"), status = document.getElementById("adjUpStatus");
      var file = input.files && input.files[0];
      if (!file) { status.textContent = T("rv.up.none"); return; }
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        status.textContent = T("rv.up.tooBig", { mb: (file.size / 1048576).toFixed(1), max: MAX_UPLOAD_MB });
        return;
      }
      var host = document.getElementById("adjSample"), t0 = Date.now();
      status.textContent = T("rv.up.working");
      btn.disabled = true;
      if (host) host.innerHTML = UI.card('<div class="adj-working"><div class="adj-spin"></div><div><b>' + esc(T("rv.up.working")) + "</b></div></div>");
      var marker = document.getElementById("adjUpMarker").value;
      api("/api/adjudicate/analyze?marker=" + encodeURIComponent(marker) + "&name=" + encodeURIComponent(file.name),
          { method: "POST", body: file }).then(function (r) {
        S.result = r; S.id = r.sample_id;
        status.textContent = T("rv.up.done", { s: ((Date.now() - t0) / 1000).toFixed(1) });
        setPlain(plainForSample(r));
        paintSample(r);
        showBanner(r);
      }).catch(function (e) {
        status.textContent = T("rv.up.failed") + " " + e.message;
        if (host) host.innerHTML = UI.state("error", T("rv.up.failed"), e.message);
      }).then(function () { btn.disabled = false; });
    });
  }

  function renderSampleTab() {
    root().innerHTML = picker() + '<div id="adjSample" class="stack"></div>';
    var sel = document.getElementById("adjPick");
    sel.addEventListener("change", function () { selectSample(sel.value); });
    document.getElementById("adjRerun").addEventListener("click", function () {
      if (S.result && S.result.uploaded) { S.id = S.index.samples[0].sample_id; sel.value = S.id; }
      selectSample(S.id, true);
    });
    wireUpload();
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
      if (S.tab === "sample") { setPlain(plainForSample(r)); paintSample(r); }
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

  /* The list this particular sample was judged against (a sample can use the public list or the authors' own). */
  function refLabel(r) {
    var key = "rv.ref." + ((r && r.metadata && r.metadata.profile) || "refseq_12s");
    return T(key, { v: refVersion() });
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
      (r.uploaded ? "" : esc(T("rv.sourceLine", { project: r.metadata.bioproject, run: r.sample_id })) +
        (r.metadata.collection_date ? esc(T("rv.sourceDate", { date: r.metadata.collection_date })) : "")) + "</p>" +
      countingNote(r) +
      '<div class="card-foot">' +
      (r.uploaded ? "" : UI.button(T("rv.print"), { variant: "primary", id: "adjPdf", icon: "download" })) +
      (r.dropped_csv ? '<a class="btn sm" href="/api/adjudicate/dropped/' + encodeURIComponent(r.sample_id) +
        '.csv">' + esc(T("rv.csv")) + "</a>" : "") +
      (r.uploaded ? "" : '<a class="btn sm" target="_blank" rel="noopener" href="' + esc(sourceUrl(r)) + '">' + esc(T("rv.sourceRecord")) + "</a>") +
      "</div>");

    html += r.uploaded ? UI.card('<h2 class="adj-h2">' + esc(T("rv.up.source")) + '</h2><p class="hint">' + esc(T("rv.up.note")) + "</p>") : sourceCard(r);

    var reasons = Object.keys(r.drop_reasons);
    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.dropWhy")) + "</h2></div>" +
      (reasons.length ? reasonBars(r) : '<p class="hint">' + esc(T("rv.nothingDropped")) + "</p>") +
      droppedTable(r));

    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.speciesHead")) + "</h2></div>" +
      speciesChart(r) + (r.metadata.role === "mixed" || r.metadata.role === "mixed_truth" ? expectedBlock(r) : ""));

    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.queue.head")) + "</h2></div>" +
      unknownTable(r));

    if (r.expected_check && r.expected_check.mode === "unknown_identity") {
      html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.ug.head")) + "</h2></div>" + unknownGroups(r));
    }

    html += UI.card('<div class="card-head"><h2 class="adj-h2">' + esc(T("rv.map.head")) + "</h2></div>" +
      (r.metadata.latitude !== null && r.metadata.latitude !== undefined
        ? '<div id="adjMap" class="adj-map"></div>' +
          (r.metadata.coordinate_note ? '<p class="hint">' + esc(T("rv.map.note")) + " " + esc(r.metadata.coordinate_note) + ".</p>" : "")
        : '<p class="hint">' + esc(T("rv.map.noPin")) + "</p>"));

    host.innerHTML = html;
    var pdf = document.getElementById("adjPdf");
    if (pdf) pdf.addEventListener("click", function () {
      window.open("/api/adjudicate/report/" + encodeURIComponent(r.sample_id) + ".pdf", "_blank");
    });
    drawMap(r);
    UI.animateIn && UI.animateIn(host);
  }

  function countingNote(r) {
    var c = r.counting;
    return c && c.note ? '<p class="hint"><b>' + esc(T("rv.count.head")) + ":</b> " + esc(c.note) + "</p>" : "";
  }

  function unknownGroups(r) {
    var e = r.expected_check, g = e.unknown_groups || [];
    if (!g.length) return '<p class="hint">' + esc(T("rv.ug.none")) + "</p>";
    var out = '<p>' + esc(e.verdict) + "</p><p class=\"hint\">" + esc(T("rv.ug.intro")) + "</p>" +
      '<div class="table-wrap"><table class="data"><thead><tr><th>' + esc(T("rv.ug.truth")) + "</th><th>" + esc(T("rv.ug.pieces")) +
      "</th><th>" + esc(T("rv.ug.closest")) + "</th><th>" + esc(T("rv.ug.inMix")) + "</th><th>" + esc(T("rv.ug.share")) + "</th></tr></thead><tbody>" +
      g.slice(0, 12).map(function (x) {
        return "<tr><td><i>" + esc(x.true_species) + "</i></td><td>" + UI.num(x.reads) + "</td><td><i>" + esc(x.closest_public_match || "-") +
          "</i></td><td>" + esc(T(x.in_mock_design ? "rv.ug.yes" : "rv.ug.no")) + "</td><td>" + (x.expected_share ? pct(x.expected_share) : "-") + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    if ((e.wrong_confident_calls || []).length) {
      out += '<div class="adj-note">' + esc(T("rv.ug.wrong", { n: e.wrong_confident_calls.length })) + " " +
        e.wrong_confident_calls.map(function (w) { return "<i>" + esc(w.species) + "</i> (" + UI.num(w.reads) + ")"; }).join(", ") + ".</div>";
    }
    return out + (e.limits ? '<p class="hint">' + esc(e.limits) + "</p>" : "");
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
        row(T("rv.src.marker"), esc(m.marker || (/12S|COI|16S/.exec(m.dataset_title || "") ? m.dataset_title : T("rv.src.markerFallback")))) +
        row(T("rv.src.reference"), esc(refLabel(r))) +
        (m.mock_community
          ? row(T("rv.src.collected"), esc(T("rv.src.lab"))) + row(T("rv.src.place"), esc(T("rv.src.lab")))
          : row(T("rv.src.collected"), esc(m.collection_date || "n/a") + " " + checkBadge(dc)) +
            row(T("rv.src.place"), esc(m.location || "n/a") + (m.latitude !== null && m.latitude !== undefined ? " (" + Number(m.latitude).toFixed(4) + ", " + Number(m.longitude).toFixed(4) + ")" : "") +
              " " + checkBadge(cc))) +
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
    var extra = "";
    if (e.shares_measured) extra += "<p>" + esc(T("rv.exp.tol", { x: e.tolerance_fold, n: e.shares_within_tolerance, m: e.shares_measured })) + "</p>";
    if ((e.unexpected_species || []).length) {
      extra += "<p class=\"hint\">" + esc(T("rv.exp.extra", { n: e.unexpected_species.length, k: e.unexpected_also_in_paper || 0 })) + " " +
        e.unexpected_species.map(function (u) { return "<i>" + esc(u.species) + "</i>"; }).join(", ") + ".</p>";
    }
    return '<h3 class="adj-h3">' + esc(T("rv.exp.comp")) + '</h3><p class="hint">' + esc(e.source) + "</p>" +
      "<p><b>" + esc(e.verdict) + "</b></p>" + extra +
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
      '<div class="adj-note">' + T("rv.queue.ref", { ref: esc(refLabel(r)) }) + " " + esc(T("rv.scoreNote")) + "</div>" +
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
    setTimeout(function () { if (S.map === m) m.invalidateSize(); }, 200);  // the map may be gone after a quick tab switch
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
        S.seasonMap = m; setTimeout(function () { if (S.seasonMap === m) m.invalidateSize(); }, 200);
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
    setTimeout(function () { if (S.alertMap === m) m.invalidateSize(); }, 200);
  }

  /* ── numbers & sources ──────────────────────────────────────────────── */

  function glossaryCard() {
    var P = window.BioRadarPlain;
    return UI.card('<h2 class="adj-h2">' + esc(T("rv.gloss.head")) + "</h2>" + (P ? P.glossaryList() : ""));
  }

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
          '<p class="hint">' + esc(pr.manifest.mates_downloaded) + "</p>") + glossaryCard();
    }).catch(function (e) { root().innerHTML = UI.state("error", T("rv.couldNotLoad"), e.message); });
  }
})();
