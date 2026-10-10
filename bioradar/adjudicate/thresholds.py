"""Load the single thresholds file. Nothing else in the package hard-codes a number."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

THRESHOLDS_FILE = Path(__file__).with_name("thresholds.json")


class Thresholds:
    """Attribute access to values; `.rationale()` returns the 'why' for the UI."""

    def __init__(self, raw: Dict[str, Dict[str, Any]]) -> None:
        self._raw = raw

    def __getattr__(self, name: str) -> Any:
        try:
            return self._raw[name]["value"]
        except KeyError:
            raise AttributeError(name)

    def for_marker(self, marker: str) -> "Thresholds":
        """The same thresholds with the species-identity cutoff set for this marker."""
        raw = {k: dict(v) for k, v in self._raw.items()}
        per_marker = raw.get("species_identity_by_marker", {}).get("value", {})
        key = next((m for m in per_marker if m.lower() in (marker or "").lower()), None)
        if key:
            raw["identity_species"]["value"] = per_marker[key]
        return Thresholds(raw)

    def rationale(self) -> Dict[str, Dict[str, Any]]:
        return {k: {"value": v["value"], "unit": v.get("unit", ""), "why": v["why"]}
                for k, v in self._raw.items()}


def load(path: Path = THRESHOLDS_FILE) -> Thresholds:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Thresholds(data["thresholds"])
