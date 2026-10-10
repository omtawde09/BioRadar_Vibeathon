"""Invasive Alien Species (IAS) Establishment Risk Inference Engine.

Loads the trained Random Forest Ecological Niche Classifier and predicts establishment risk,
survival probability, feature importances (XAI), and conservation control actions.
"""

from pathlib import Path
import csv
import joblib
import numpy as np

MODEL_PATH = Path(__file__).parent / "models" / "ias_classifier.joblib"
_MODEL_CACHE = None

HABITAT_SPECIFICITY_MAP = {"low": 1.0, "medium": 2.0, "high": 3.0}
PROTECTED_STATUS_MAP = {"unprotected": 1.0, "ramsar": 2.0, "sanctuary": 2.5, "biosphere_reserve": 3.0, "national_park": 3.0}

INVASIVE_SPECIES = [
    "Oreochromis mossambicus",
    "Clarias gariepinus",
    "Pterygoplichthys pardalis",
    "Gambusia holbrooki",
    "Cyprinus carpio"
]


def load_model():
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    if not MODEL_PATH.exists():
        from bioradar.ai.train_ias_model import train_and_save_model
        _MODEL_CACHE = train_and_save_model()
    else:
        try:
            _MODEL_CACHE = joblib.load(MODEL_PATH)
        except Exception:
            from bioradar.ai.train_ias_model import train_and_save_model
            _MODEL_CACHE = train_and_save_model()

    return _MODEL_CACHE


def load_reference_traits():
    data_dir = Path(__file__).parents[2] / "data"
    traits_file = data_dir / "species_traits.csv"
    traits = {}
    if traits_file.exists():
        with open(traits_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                traits[row["scientific_name"]] = {
                    "common_name": row.get("common_name", ""),
                    "max_size_cm": float(row.get("max_size_cm", 30.0)),
                    "trophic_level": float(row.get("trophic_level", 2.5)),
                    "water_bod": float(row.get("water_bod", 2.5)),
                    "habitat_specificity": row.get("habitat_specificity", "medium").lower(),
                    "iucn_category": row.get("iucn_category", "Least Concern")
                }
    return traits


def predict_establishment_risk(species_name, site_name="Mandovi Estuary", waterbody_type="estuary",
                               read_count=1200, total_reads=4694, water_bod=3.8,
                               protected_status="unprotected"):
    model_data = load_model()
    clf = model_data["model"]
    feature_names = model_data["feature_names"]

    traits_map = load_reference_traits()
    species_info = traits_map.get(species_name, {
        "common_name": species_name,
        "max_size_cm": 40.0,
        "trophic_level": 3.0,
        "water_bod": water_bod,
        "habitat_specificity": "medium",
        "iucn_category": "Least Concern"
    })

    try:
        rc = float(read_count or 0)
        tr = float(total_reads or 4694)
    except (ValueError, TypeError):
        rc, tr = 1200.0, 4694.0

    read_share_pct = (rc / (tr or 1.0)) * 100.0
    hab_spec_num = HABITAT_SPECIFICITY_MAP.get(species_info.get("habitat_specificity", "medium"), 2.0)
    prot_stat_num = PROTECTED_STATUS_MAP.get((protected_status or "unprotected").lower(), 1.0)
    spec_bod_val = species_info.get("water_bod")
    spec_bod = float(spec_bod_val if spec_bod_val is not None else (water_bod if water_bod is not None else 2.5))



    wb_type = (waterbody_type or "estuary").lower()
    is_estuary = 1.0 if "estuary" in wb_type else 0.0
    is_lagoon = 1.0 if "lagoon" in wb_type else 0.0
    is_freshwater = 1.0 if ("freshwater" in wb_type or "lake" in wb_type or "river" in wb_type) else 0.0
    is_river = 1.0 if "river" in wb_type else 0.0
    is_marine = 1.0 if "marine" in wb_type else 0.0

    X_vec = np.array([[
        spec_bod,
        species_info["trophic_level"],
        species_info["max_size_cm"],
        read_share_pct,
        hab_spec_num,
        prot_stat_num,
        is_estuary,
        is_lagoon,
        is_freshwater,
        is_river,
        is_marine
    ]])

    probs = clf.predict_proba(X_vec)[0]  # [p_low, p_mod, p_crit]
    establishment_prob = float(probs[2] * 1.0 + probs[1] * 0.5)

    if establishment_prob >= 0.65:
        risk_level = "CRITICAL_INVASION_TAKEOVER"
        badge = "CRITICAL INVASION TAKEOVER"
        color = "#ef4444"
        action = f"Deploy physical barriers & targeted electrofishing at {site_name} immediately."
    elif establishment_prob >= 0.35:
        risk_level = "MODERATE_ESTABLISHMENT_RISK"
        badge = "MODERATE ESTABLISHMENT RISK"
        color = "#f97316"
        action = f"Increase eDNA sampling frequency to bi-weekly at {site_name}."
    else:
        risk_level = "LOW_TRANSIENT_DRIFT"
        badge = "LOW TRANSIENT DRIFT"
        color = "#10b981"
        action = f"Maintain standard monthly baseline monitoring at {site_name}."

    importances = clf.feature_importances_
    xai_features = [
        {"feature": "Water BOD Level", "importance": float(importances[0])},
        {"feature": "eDNA Read Share", "importance": float(importances[3])},
        {"feature": "Species Trophic Level", "importance": float(importances[1])},
        {"feature": "Habitat Specificity", "importance": float(importances[4])},
    ]

    return {
        "species_name": species_name,
        "common_name": species_info.get("common_name", species_name),
        "site_name": site_name,
        "establishment_probability": round(establishment_prob * 100, 1),
        "risk_level": risk_level,
        "risk_badge": badge,
        "severity_color": color,
        "recommended_action": action,
        "threat_drivers": xai_features,
        "model_metadata": {
            "model_type": "RandomForestClassifier",
            "cv_accuracy": model_data.get("cv_accuracy", 0.84)
        }
    }


def predict_all_invasives_for_run(report_data):
    if not report_data:
        return []

    top_taxa = report_data.get("top_species", []) or report_data.get("species", [])
    total_reads = report_data.get("total_reads", 4694)
    results = []

    for t in top_taxa:
        name = t.get("name") or t.get("scientific_name") or t.get("species")
        if name in INVASIVE_SPECIES or t.get("is_invasive"):
            read_cnt = t.get("reads", 1200)
            res = predict_establishment_risk(
                species_name=name,
                site_name="Mandovi Estuary (Panaji)",
                waterbody_type="estuary",
                read_count=read_cnt,
                total_reads=total_reads
            )
            results.append(res)

    return results
