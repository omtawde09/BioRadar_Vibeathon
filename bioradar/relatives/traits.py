"""Species traits for the relative finder: observed evidence versus inferred profile.

Traits are used in exactly two ways, and the two are never mixed:

1. EVIDENCE - only for factors actually OBSERVED for this sample or specimen. From an eDNA
   water sample that means what the sample metadata states (country from `geo_loc_name`,
   habitat only when the dataset title / design note / isolation source says so in words).
   Diet, karyotype, genome size and hormones are NOT in a DNA fragment from water; they become
   evidence only when a user supplies a measurement from a physical specimen. Each observed
   factor is compared with each candidate species' documented trait: 'consistent',
   'inconsistent' or 'no_data'.

2. INFERRED PROFILE - for factors that were not observed, what the specimen's nearest
   relatives are documented to have (weighted by relative weight), with sources. This is
   "what to expect if the hypothesis is right", never a measurement of the sample.

Trait rows live in CSV files under data/real_challenge/reference/traits/*.csv with columns
species,factor,value,unit,source,source_url,retrieved. A row without a source is rejected.

The factor weights in RULES are documented priors chosen by hand, not calibrated
probabilities.

Standard library only; Python 3.8 compatible.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAITS_DIR = REPO_ROOT / "data" / "real_challenge" / "reference" / "traits"

COLUMNS = ["species", "factor", "value", "unit", "source", "source_url", "retrieved"]

FACTORS: List[str] = [
    "habitat",
    "country_native",
    "diet",
    "trophic_level",
    "karyotype_2n",
    "genome_size_pg",
    "max_length_cm",
    "hormone",
]

# Factors that can be read off sample metadata for an eDNA sample. Everything else needs a
# physical specimen and a user-supplied observation before it can be evidence.
OBSERVABLE_FROM_EDNA = {"habitat", "country"}

NUMERIC_FACTORS = {"trophic_level", "karyotype_2n", "genome_size_pg", "max_length_cm"}
CATEGORICAL_FACTORS = {"habitat", "country_native", "diet"}  # values may be ';'-joined
TEXT_FACTORS = {"hormone"}  # free text, never split

# Observation keys that are not factor names but map onto one.
OBSERVATION_ALIASES = {"country": "country_native"}

NO_DATA_STATUS = "no data in trait tables"
INFERRED_NOTE = ("Expected if the hypothesis is right: documented values of the nearest "
                 "relatives, weighted by relative weight. Not measured on this sample.")

DEFAULT_INCONSISTENT_WEIGHT = 0.5

RULES: Dict[str, Dict[str, Any]] = {
    "habitat": {
        "rule": "consistent if the observed habitat is in the documented set; 'brackish' is also "
                "consistent when both 'freshwater' and 'marine' are documented",
        "used_as_evidence": True,
        "inconsistent_weight": 0.25,
        "why": "Salinity tolerance is a strong, well-documented constraint on where a fish lives. "
               "A species documented in both freshwater and marine water is euryhaline and can "
               "use estuaries. The penalty is not exclusion because eDNA drifts with water from "
               "adjacent habitats and species habitat lists are incomplete.",
    },
    "country_native": {
        "rule": "consistent if the observed country is in the documented native-country list",
        "used_as_evidence": True,
        "inconsistent_weight": 0.5,
        "why": "The native range narrows which relatives are plausible, but 'inconsistent' only "
               "means 'not documented as native there': introduced and invasive populations "
               "exist, which is exactly what an invasive-species alert looks for.",
    },
    "diet": {
        "rule": "consistent if the observed diet category exactly matches a documented category",
        "used_as_evidence": True,
        "inconsistent_weight": 0.5,
        "why": "Only observable from a specimen (gut content, feeding observation). Diet "
               "categories are coarse and many fish shift diet with age and season, so a "
               "mismatch is a moderate penalty.",
    },
    "trophic_level": {
        "rule": "consistent if |observed - documented| <= 0.5",
        "used_as_evidence": True,
        "tolerance": 0.5,
        "inconsistent_weight": 0.5,
        "why": "Trophic level estimates (e.g. from stable isotopes or diet composition) carry "
               "roughly half a level of uncertainty between studies.",
    },
    "karyotype_2n": {
        "rule": "consistent if |observed - documented| <= 2",
        "used_as_evidence": True,
        "tolerance": 2,
        "inconsistent_weight": 0.2,
        "why": "Diploid chromosome number is a stable species character; small differences arise "
               "from counting error and Robertsonian polymorphism, larger ones point to a "
               "different species. Only observable from a specimen's cells.",
    },
    "genome_size_pg": {
        "rule": "consistent if observed is within 20% of a documented value",
        "used_as_evidence": True,
        "relative_tolerance": 0.2,
        "inconsistent_weight": 0.5,
        "why": "C-values differ between methods (flow cytometry, Feulgen densitometry) by "
               "10-20% for the same species, so only larger differences count.",
    },
    "max_length_cm": {
        "rule": "never used as evidence",
        "used_as_evidence": False,
        "inconsistent_weight": 1.0,
        "why": "A maximum recorded size says nothing decisive about one specimen, which can be "
               "any size below it (juveniles, larvae, eggs in eDNA). Shown only in the inferred "
               "profile.",
    },
    "hormone": {
        "rule": "free text: consistent if the observed text matches a documented value "
                "(case-insensitive); a mismatch is reported as no_data, never as inconsistent",
        "used_as_evidence": True,
        "inconsistent_weight": 1.0,
        "why": "There is no structured species-level hormone source, so the channel is empty "
               "unless a user supplies rows. Free text cannot be reliably contradicted.",
    },
}

_COUNTRY_ALIASES = {
    "usa": "united states",
    "us": "united states",
    "united states of america": "united states",
    "uk": "united kingdom",
    "great britain": "united kingdom",
    "britain": "united kingdom",
    "viet nam": "vietnam",
    "people's republic of china": "china",
    "prc": "china",
}

# INSDC "missing value" vocabulary: geo_loc_name set to one of these is not a country.
_MISSING_VALUES = {
    "", "missing", "not applicable", "not collected", "not provided", "restricted access",
    "na", "n/a", "unknown", "none",
}

# Explicit words only. Checked as word starts, so 'seasons' or 'research' never mean 'sea'.
_HABITAT_WORDS: List[Tuple[str, str, str]] = [
    (r"\bfresh[\s-]?water", "freshwater", "freshwater"),
    (r"\brivers?\b", "freshwater", "river"),
    (r"\birrigation", "freshwater", "irrigation"),
    (r"\bestuar", "brackish", "estuar"),
    (r"\bmarine\b", "marine", "marine"),
    (r"\bsea(?:water|s)?\b", "marine", "sea"),
    (r"\bocean", "marine", "ocean"),
]


# --------------------------------------------------------------------------- helpers

def _norm_species(name: Any) -> str:
    return " ".join(str(name or "").replace("_", " ").split()).lower()


def _norm_factor(name: Any) -> str:
    key = str(name or "").strip().lower()
    return OBSERVATION_ALIASES.get(key, key)


def _norm_text(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _norm_country(value: Any) -> str:
    key = _norm_text(value)
    return _COUNTRY_ALIASES.get(key, key)


def _split(factor: str, value: Any) -> List[str]:
    """Display values of one cell: ';'-split for categorical factors, whole otherwise."""
    text = " ".join(str(value or "").split())
    if factor in CATEGORICAL_FACTORS:
        return [part.strip() for part in text.split(";") if part.strip()]
    return [text] if text else []


def _cat_key(factor: str, value: str) -> str:
    return _norm_country(value) if factor == "country_native" else _norm_text(value)


def _to_float(value: Any) -> Optional[float]:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _sources(rows: List[dict]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for row in rows:
        key = (row.get("source", ""), row.get("source_url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append({"source": row.get("source", ""), "source_url": row.get("source_url", ""),
                    "retrieved": row.get("retrieved", "")})
    return out


def _fmt(number: float) -> str:
    return "{:g}".format(number)


# --------------------------------------------------------------------------- table

class TraitTable:
    """species -> factor -> list of trait rows (each row a dict with the CSV columns)."""

    def __init__(self) -> None:
        self._rows: Dict[str, Dict[str, List[dict]]] = {}
        self._names: Dict[str, str] = {}  # normalised -> name as first written
        self.files: List[str] = []
        self.skipped: List[Dict[str, Any]] = []  # rejected rows, with the reason

    def add(self, row: Dict[str, Any], origin: str = "") -> bool:
        """Validate and store one row. Returns False (and records why) when rejected."""
        clean = {col: " ".join(str(row.get(col) or "").split()) for col in COLUMNS}
        clean["factor"] = _norm_factor(clean["factor"])
        reason = ""
        if not clean["species"]:
            reason = "empty species"
        elif clean["factor"] not in FACTORS:
            reason = "unknown factor '{}'".format(clean["factor"])
        elif not clean["value"]:
            reason = "empty value"
        elif not clean["source"]:
            reason = "no source: every trait row must say where it comes from"
        elif clean["factor"] in NUMERIC_FACTORS and _to_float(clean["value"]) is None:
            reason = "value '{}' is not a number".format(clean["value"])
        if reason:
            self.skipped.append({"origin": origin, "row": clean, "reason": reason})
            return False
        clean["origin"] = origin
        key = _norm_species(clean["species"])
        self._names.setdefault(key, clean["species"])
        self._rows.setdefault(key, {}).setdefault(clean["factor"], []).append(clean)
        return True

    def get(self, species: str, factor: str) -> List[dict]:
        factor_rows = self._rows.get(_norm_species(species), {})
        return list(factor_rows.get(_norm_factor(factor), []))

    def species_with(self, factor: str) -> Set[str]:
        factor = _norm_factor(factor)
        return {self._names[key] for key, rows in self._rows.items() if rows.get(factor)}

    def coverage(self) -> Dict[str, int]:
        """Number of species with at least one row, per factor (every factor listed)."""
        return {factor: len(self.species_with(factor)) for factor in FACTORS}

    def species(self) -> List[str]:
        return sorted(self._names.values())

    def __len__(self) -> int:
        return sum(len(rows) for factors in self._rows.values() for rows in factors.values())


def load_traits(folder: Optional[Path] = None) -> TraitTable:
    """Read every *.csv in `folder` (default data/real_challenge/reference/traits).
    A missing folder gives an empty table; rejected rows are kept in `table.skipped`."""
    table = TraitTable()
    folder = Path(folder) if folder is not None else TRAITS_DIR
    if not folder.is_dir():
        return table
    for path in sorted(folder.glob("*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [col for col in ("species", "factor", "value", "source")
                       if col not in (reader.fieldnames or [])]
            if missing:
                table.skipped.append({"origin": path.name, "row": {},
                                      "reason": "file lacks columns: " + ", ".join(missing)})
                continue
            table.files.append(path.name)
            for line_no, row in enumerate(reader, start=2):
                table.add(row, origin="{}:{}".format(path.name, line_no))
    return table


# --------------------------------------------------------------------------- sample context

def sample_context(metadata: Dict) -> Dict[str, Any]:
    """What the sample metadata itself states: country and (only from explicit words) habitat.

    country: metadata['biosample_attributes']['geo_loc_name'] before the first ':'.
    habitat: words in dataset_title / design_note / isolation_source ('freshwater', 'river',
    'irrigation' -> freshwater; 'estuar' -> brackish; 'marine', 'sea', 'ocean' -> marine).
    An estuary mention wins over river/sea words (an estuary is where they meet); freshwater
    and marine words without an estuary are a conflict and give None.
    """
    metadata = metadata or {}
    attrs = metadata.get("biosample_attributes") or {}
    basis: Dict[str, Optional[str]] = {"country": None, "habitat": None}

    country = None
    geo = " ".join(str(attrs.get("geo_loc_name") or "").split())
    if geo:
        head = geo.split(":")[0].strip()
        if head.lower() not in _MISSING_VALUES:
            country = head
            basis["country"] = "biosample_attributes.geo_loc_name = '{}'".format(geo)

    fields = [
        ("dataset_title", metadata.get("dataset_title")),
        ("design_note", metadata.get("design_note")),
        ("biosample_attributes.isolation_source", attrs.get("isolation_source")),
        ("isolation_source", metadata.get("isolation_source")),
    ]
    hits: Dict[str, List[str]] = {}
    for field, text in fields:
        text = str(text or "")
        for pattern, habitat, word in _HABITAT_WORDS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.setdefault(habitat, []).append("{} contains '{}'".format(field, word))

    habitat = None
    if "brackish" in hits:
        habitat = "brackish"
    elif len(hits) == 1:
        habitat = next(iter(hits))
    if habitat:
        basis["habitat"] = "; ".join(hits[habitat])
    elif hits:
        basis["habitat"] = "conflicting habitat words, none used: " + "; ".join(
            "{} ({})".format(h, ", ".join(why)) for h, why in sorted(hits.items()))
    return {"country": country, "habitat": habitat, "basis": basis}


# --------------------------------------------------------------------------- evidence

def _result(factor: str, observed: Any, documented: List[Any], verdict: str, note: str,
            rows: List[dict]) -> Dict[str, Any]:
    rule = RULES.get(factor, {})
    if verdict == "consistent":
        weight = 1.0
    elif verdict == "inconsistent":
        weight = float(rule.get("inconsistent_weight", DEFAULT_INCONSISTENT_WEIGHT))
    else:
        weight = 1.0
    return {"factor": factor, "observed": observed, "documented": documented,
            "verdict": verdict, "factor_weight": weight, "note": note,
            "sources": _sources(rows)}


def compare(factor: str, observed: Any, rows: List[dict]) -> Dict:
    """Compare one observed value with a species' documented rows for that factor (RULES)."""
    factor = _norm_factor(factor)
    rows = list(rows or [])
    unit = next((r.get("unit") for r in rows if r.get("unit")), "")
    unit_txt = " " + unit if unit else ""

    if factor in NUMERIC_FACTORS:
        documented: List[Any] = []
        for row in rows:
            number = _to_float(row.get("value"))
            if number is not None and number not in documented:
                documented.append(number)
    else:
        documented = []
        seen = set()
        for row in rows:
            for value in _split(factor, row.get("value")):
                key = _cat_key(factor, value)
                if key not in seen:
                    seen.add(key)
                    documented.append(value)

    if _is_empty(observed):
        return _result(factor, observed, documented, "no_data",
                       "Nothing was observed for this factor, so it is not evidence.", rows)
    if not documented:
        return _result(factor, observed, documented, "no_data",
                       "No documented value for this species in the trait tables; this factor "
                       "neither supports nor weakens the hypothesis.", rows)
    if factor == "max_length_cm":
        return _result(factor, observed, documented, "no_data",
                       "Maximum recorded length is never used as evidence: one specimen can be "
                       "any size below it.", rows)

    if factor in NUMERIC_FACTORS:
        obs = _to_float(observed)
        if obs is None:
            return _result(factor, observed, documented, "no_data",
                           "Observed value '{}' is not a number, so it was not compared.".format(
                               observed), rows)
        if factor == "genome_size_pg":
            tol = RULES[factor]["relative_tolerance"]
            best = min(documented, key=lambda d: abs(obs - d) / d if d else float("inf"))
            ok = best > 0 and abs(obs - best) <= tol * best
            rel = abs(obs - best) / best if best else float("inf")
            note = "observed {}{} vs documented {}{}: {:.0%} apart (limit {:.0%})".format(
                _fmt(obs), unit_txt, _fmt(best), unit_txt, rel, tol)
        else:
            tol = RULES[factor]["tolerance"]
            best = min(documented, key=lambda d: abs(obs - d))
            diff = abs(obs - best)
            ok = diff <= tol + 1e-9
            note = "observed {}{} vs documented {}{}: difference {} (limit {})".format(
                _fmt(obs), unit_txt, _fmt(best), unit_txt, _fmt(round(diff, 6)), _fmt(tol))
        return _result(factor, obs, documented, "consistent" if ok else "inconsistent", note,
                       rows)

    if factor == "hormone":
        obs_key = _norm_text(observed)
        if obs_key in {_norm_text(v) for v in documented}:
            return _result(factor, observed, documented, "consistent",
                           "Observed hormone note matches a documented value.", rows)
        return _result(factor, observed, documented, "no_data",
                       "Free-text hormone notes differ; free text is not treated as a "
                       "contradiction.", rows)

    # categorical: habitat, country_native, diet (and anything else categorical)
    observed_values = observed if isinstance(observed, (list, tuple, set)) else \
        _split("habitat", observed)  # ';'-split like any categorical cell
    obs_keys = {_cat_key(factor, str(v)) for v in observed_values if str(v).strip()}
    doc_keys = {_cat_key(factor, v) for v in documented}
    display_obs = observed if not isinstance(observed, (list, tuple, set)) else \
        "; ".join(str(v) for v in observed)

    if factor == "habitat":
        if obs_keys & doc_keys:
            return _result(factor, display_obs, documented, "consistent",
                           "Observed habitat is documented for this species.", rows)
        if "brackish" in obs_keys and {"freshwater", "marine"} <= doc_keys:
            return _result(factor, display_obs, documented, "consistent",
                           "Brackish water observed; the species is documented in both "
                           "freshwater and marine water (euryhaline).", rows)
        return _result(factor, display_obs, documented, "inconsistent",
                       "Observed habitat is not documented for this species. eDNA can drift "
                       "from adjacent water, so this weakens but does not exclude it.", rows)

    if factor == "country_native":
        if obs_keys & doc_keys:
            return _result(factor, display_obs, documented, "consistent",
                           "Documented as native in the sampled country.", rows)
        return _result(factor, display_obs, documented, "inconsistent",
                       "Not documented as native in {}. This means 'not native there', not "
                       "'cannot be there': introduced and invasive populations exist.".format(
                           display_obs), rows)

    if obs_keys & doc_keys:
        return _result(factor, display_obs, documented, "consistent",
                       "Observed category matches a documented category.", rows)
    return _result(factor, display_obs, documented, "inconsistent",
                   "Observed category does not match any documented category.", rows)


def evidence(candidate_species: str, observations: Dict[str, Any],
             table: TraitTable) -> List[Dict]:
    """One compare() per OBSERVED factor for one candidate species.

    `observations` keys are factor names plus 'country' (-> country_native) and 'habitat';
    empty values and keys that are not factors (e.g. 'basis' from sample_context) are ignored.
    Unobserved factors are never evidence, whatever the trait tables hold.
    """
    observed: Dict[str, Any] = {}
    for key, value in (observations or {}).items():
        factor = _norm_factor(key)
        if factor not in FACTORS or _is_empty(value):
            continue
        observed.setdefault(factor, value)
    return [compare(factor, observed[factor], table.get(candidate_species, factor))
            for factor in FACTORS if factor in observed]


# --------------------------------------------------------------------------- inferred profile

def inferred_profile(weighted_species: List[Tuple[str, float]], table: TraitTable,
                     exclude: Iterable[str] = ()) -> Dict[str, Dict]:
    """What the relatives are documented to have, per factor not in `exclude`.

    numeric factors: weighted_mean, min, max, n_species, sources, coverage.
    categorical / text factors: shares = for each value, the fraction of the weight (of
    relatives with data) documented with that value; a relative documented with several
    values counts for each, so shares can sum to more than 1.
    coverage = fraction of the total relative weight that has any data for the factor.
    A factor with no data at all -> {'status': 'no data in trait tables'}.
    """
    skip = {_norm_factor(f) for f in exclude}
    merged: Dict[str, float] = {}
    display: Dict[str, str] = {}
    for name, weight in weighted_species or []:
        number = _to_float(weight)
        if not name or number is None or number <= 0:
            continue
        key = _norm_species(name)
        merged[key] = merged.get(key, 0.0) + number
        display.setdefault(key, str(name).strip())
    total = sum(merged.values())

    profile: Dict[str, Dict] = {}
    for factor in FACTORS:
        if factor in skip:
            continue
        with_data = []  # (display name, weight, rows)
        for key, weight in merged.items():
            rows = table.get(display[key], factor)
            if rows:
                with_data.append((display[key], weight, rows))
        if not with_data or total <= 0:
            profile[factor] = {"status": NO_DATA_STATUS}
            continue
        data_weight = sum(w for _, w, _ in with_data)
        all_rows = [row for _, _, rows in with_data for row in rows]
        entry: Dict[str, Any] = {
            "status": "inferred from relatives",
            "note": INFERRED_NOTE,
            "n_species": len(with_data),
            "coverage": round(data_weight / total, 4),
            "sources": _sources(all_rows),
        }
        unit = next((r.get("unit") for r in all_rows if r.get("unit")), "")
        if unit:
            entry["unit"] = unit
        if factor in NUMERIC_FACTORS:
            per_species = []
            for name, weight, rows in with_data:
                values = [v for v in (_to_float(r.get("value")) for r in rows) if v is not None]
                per_species.append((name, weight, sum(values) / len(values)))
            entry["kind"] = "numeric"
            entry["weighted_mean"] = round(
                sum(w * v for _, w, v in per_species) / data_weight, 4)
            entry["min"] = min(v for _, _, v in per_species)
            entry["max"] = max(v for _, _, v in per_species)
            entry["per_species"] = [{"species": n, "weight": round(w, 4), "value": v}
                                    for n, w, v in per_species]
        else:
            shares: Dict[str, float] = {}
            labels: Dict[str, str] = {}
            per_species = []
            for name, weight, rows in with_data:
                keys: Dict[str, str] = {}
                for row in rows:
                    for value in _split(factor, row.get("value")):
                        keys.setdefault(_cat_key(factor, value), value)
                for key, label in keys.items():
                    labels.setdefault(key, label)
                    shares[key] = shares.get(key, 0.0) + weight
                per_species.append({"species": name, "weight": round(weight, 4),
                                    "values": list(keys.values())})
            entry["kind"] = "text" if factor in TEXT_FACTORS else "categorical"
            entry["shares"] = {labels[k]: round(v / data_weight, 4)
                               for k, v in sorted(shares.items(), key=lambda kv: (-kv[1], kv[0]))}
            entry["per_species"] = per_species
        profile[factor] = entry
    return profile


__all__ = [
    "FACTORS", "OBSERVABLE_FROM_EDNA", "RULES", "TRAITS_DIR", "NO_DATA_STATUS",
    "TraitTable", "load_traits", "sample_context", "compare", "evidence", "inferred_profile",
]
