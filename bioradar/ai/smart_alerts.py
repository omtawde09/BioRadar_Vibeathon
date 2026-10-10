"""Smart Alerts with Contextual Reasoning for BioRadar.

Enhances raw watchlist detections with legal citations, ecological impact models,
co-occurrence threat analysis, and actionable field response protocols.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from bioradar.ai import knowledge_base


def generate_smart_briefing(alert: Dict[str, Any], all_detections: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Generate a contextual briefing for a single species alert."""
    name = str(alert.get("scientific_name", "")).strip()
    profile = knowledge_base.get_species_profile(name)
    reads = int(alert.get("reads", 0) or 0)
    confidence = float(alert.get("confidence", 0) or 0)
    sites = alert.get("sites", [])

    if not profile:
        # Generic fallback for unprofiled watchlist items
        return {
            "scientific_name": name,
            "headline": f"Detection Alert: {name}",
            "urgency": "MEDIUM",
            "ecological_summary": f"Detected with {reads} reads across {len(sites)} site(s) (classifier confidence {confidence:.2f}).",
            "legal_backing": ["Biological Diversity Act 2002"],
            "co_occurring_threats": [],
            "action_protocol": "Dispatch field team to collect verification samples and record habitat condition.",
        }

    # Detect co-occurring threatened species in the same run/dataset
    threatened_at_risk = []
    if all_detections:
        target_threats = profile.get("target_threatened_species", [])
        for det in all_detections:
            det_name = det.get("name") or det.get("scientific_name", "")
            if det_name in target_threats:
                threatened_at_risk.append(det_name)

    # Determine abundance assessment
    if reads > 1000:
        abundance_desc = "High abundance (suggests established breeding population)"
    elif reads > 100:
        abundance_desc = "Moderate abundance (active population present)"
    else:
        abundance_desc = "Low abundance (early colonization or transport)"

    headline = f"CRITICAL INVASIVE ALERT: {profile['common_name']} ({name})" if alert.get("status") == "invasive" else f"ALERT: {profile['common_name']} ({name})"

    ecological_summary = (
        f"{profile['common_name']} ({name}) detected at {abundance_desc} with {reads:,} reads "
        f"across {len(sites)} site(s). {profile['ecological_impact']}"
    )

    if threatened_at_risk:
        ecological_summary += (
            f" URGENT: Co-located with vulnerable native species ({', '.join(threatened_at_risk)}), "
            "increasing immediate extinction pressure."
        )

    return {
        "scientific_name": name,
        "common_name": profile.get("common_name", ""),
        "headline": headline,
        "urgency": profile.get("urgency_level", "HIGH"),
        "legal_status": profile.get("legal_status", ""),
        "legal_backing": profile.get("legal_sections", []),
        "ecological_summary": ecological_summary,
        "co_occurring_threats": threatened_at_risk,
        "action_protocol": profile.get("action_protocol", ""),
        "native_to": profile.get("native_to", ""),
        "reads": reads,
        "confidence": confidence,
        "sites": sites,
    }


def enhance_alerts(alerts: List[Dict[str, Any]], all_detections: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Attach smart contextual briefings to a list of raw alerts."""
    enhanced = []
    for alert in alerts:
        briefing = generate_smart_briefing(alert, all_detections)
        item = dict(alert)
        item["smart_briefing"] = briefing
        enhanced.append(item)
    return enhanced
