"""Computer Vision Field Verification Helper (TFLite).

On-device / local image-based species identification helper for field officers
photographing specimens to verify eDNA detections.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from bioradar import verification


def predict_species_from_photo(
    photo_path: str,
    target_species: Optional[str] = None
) -> Dict[str, Any]:
    """Simulate on-device TFLite MobileNetV3 species classification on a field photograph."""
    # Stub / offline TFLite classifier proxy
    if target_species:
        clean_target = target_species.strip()
    else:
        clean_target = "Clarias gariepinus"

    candidates = [
        {"species": clean_target, "confidence": 0.94, "match": True},
        {"species": "Clarias magur", "confidence": 0.04, "match": False},
        {"species": "Heteropneustes fossilis", "confidence": 0.02, "match": False},
    ]

    top_match = candidates[0]
    is_confirmed = top_match["confidence"] >= 0.85

    return {
        "photo": photo_path,
        "top_species": top_match["species"],
        "confidence": top_match["confidence"],
        "is_confirmed": is_confirmed,
        "candidates": candidates,
        "verification_verdict": verification.CONFIRMED if is_confirmed else verification.UNCERTAIN,
    }
