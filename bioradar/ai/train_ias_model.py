"""Invasive Species Establishment Risk Model Trainer.

Trains a Random Forest Ecological Niche Classifier (SDM) using site environmental
features (BOD, waterbody type, protected status), species eco-traits (trophic level,
max body size, habitat specificity), and eDNA read intensity.

Serializes model artifact to bioradar/ai/models/ias_classifier.joblib.
"""

from pathlib import Path
import csv
import random
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import joblib

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "ias_classifier.joblib"

WATERBODY_TYPES = ["estuary", "lagoon", "freshwater_lake", "river", "marine", "creek", "coral_lagoon"]
HABITAT_SPECIFICITY_MAP = {"low": 1.0, "medium": 2.0, "high": 3.0}
PROTECTED_STATUS_MAP = {"unprotected": 1.0, "ramsar": 2.0, "sanctuary": 2.5, "biosphere_reserve": 3.0, "national_park": 3.0}

FEATURE_NAMES = [
    "water_bod",
    "trophic_level",
    "max_size_cm",
    "read_share_pct",
    "habitat_specificity",
    "protected_status",
    "is_estuary",
    "is_lagoon",
    "is_freshwater_lake",
    "is_river",
    "is_marine",
]


def load_reference_traits():
    data_dir = Path(__file__).parents[2] / "data"
    traits_file = data_dir / "species_traits.csv"
    traits = {}
    if traits_file.exists():
        with open(traits_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                traits[row["scientific_name"]] = {
                    "max_size_cm": float(row.get("max_size_cm", 30.0)),
                    "trophic_level": float(row.get("trophic_level", 2.5)),
                    "water_bod": float(row.get("water_bod", 2.5)),
                    "habitat_specificity": HABITAT_SPECIFICITY_MAP.get(row.get("habitat_specificity", "medium").lower(), 2.0),
                }
    return traits


def generate_synthetic_dataset(n_samples=600, random_seed=42):
    random.seed(random_seed)
    np.random.seed(random_seed)

    X = []
    y = []

    for _ in range(n_samples):
        water_bod = float(np.random.uniform(0.8, 6.0))
        trophic_level = float(np.random.uniform(2.0, 4.2))
        max_size_cm = float(np.random.uniform(2.0, 250.0))
        read_share_pct = float(np.random.uniform(0.1, 45.0))
        habitat_specificity = random.choice([1.0, 2.0, 3.0])
        protected_status = random.choice([1.0, 2.0, 2.5, 3.0])
        wb_type = random.choice(WATERBODY_TYPES)

        is_estuary = 1.0 if wb_type == "estuary" else 0.0
        is_lagoon = 1.0 if wb_type == "lagoon" else 0.0
        is_freshwater = 1.0 if wb_type in ["freshwater_lake", "river"] else 0.0
        is_river = 1.0 if wb_type == "river" else 0.0
        is_marine = 1.0 if wb_type in ["marine", "coral_lagoon"] else 0.0

        # Ecological risk scoring heuristic to generate realistic targets
        # High BOD + High Read Share + Low Habitat Specificity + High Trophic Level = High Invasion Risk
        risk_score = (
            (water_bod / 5.0) * 0.30 +
            (read_share_pct / 30.0) * 0.35 +
            (trophic_level / 4.0) * 0.20 +
            (1.0 / habitat_specificity) * 0.15 +
            (1.0 / protected_status) * 0.10 +
            np.random.normal(0, 0.08)
        )

        if risk_score >= 0.65:
            label = 2  # CRITICAL INVASION TAKEOVER
        elif risk_score >= 0.40:
            label = 1  # MODERATE ESTABLISHMENT RISK
        else:
            label = 0  # LOW TRANSIENT DRIFT

        features = [
            water_bod,
            trophic_level,
            max_size_cm,
            read_share_pct,
            habitat_specificity,
            protected_status,
            is_estuary,
            is_lagoon,
            is_freshwater,
            is_river,
            is_marine,
        ]

        X.append(features)
        y.append(label)

    return np.array(X), np.array(y)


def train_and_save_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    X, y = generate_synthetic_dataset()

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_split=4,
        random_state=42
    )

    scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
    cv_mean = float(np.mean(scores))

    clf.fit(X, y)

    payload = {
        "model": clf,
        "feature_names": FEATURE_NAMES,
        "cv_accuracy": cv_mean,
        "classes": ["LOW_TRANSIENT_DRIFT", "MODERATE_ESTABLISHMENT_RISK", "CRITICAL_INVASION_TAKEOVER"]
    }

    joblib.dump(payload, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH} (CV Accuracy: {cv_mean * 100:.2f}%)")
    return payload


if __name__ == "__main__":
    train_and_save_model()
