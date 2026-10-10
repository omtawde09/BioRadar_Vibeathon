"""Unit & Integration Tests for BioRadar AI/ML Expansion Package.

Tests Knowledge Base, NLG Insights, Smart Alerts, Explainable AI (SHAP),
Extinction Risk ML, Invasive Spread Simulator, and Computer Vision helper.
"""

from __future__ import annotations

import json
import pytest
from bioradar.ai import (
    knowledge_base,
    nlg_insights,
    smart_alerts,
    xai_explainer,
    extinction_risk,
    spread_prediction,
    cv_verifier,
    sampling_optimizer,
)


def test_knowledge_base_retrieval():
    profile = knowledge_base.get_species_profile("Clarias gariepinus")
    assert profile is not None
    assert profile["common_name"] == "African Catfish"
    assert profile["india_status"] == "invasive"
    assert "WLPA" in profile["legal_status"] or any("Wildlife Protection Act" in s for s in profile["legal_sections"])



def test_smart_alerts_generation():
    alert_raw = {
        "scientific_name": "Clarias gariepinus",
        "reads": 1500,
        "confidence": 0.96,
        "sites": ["MANDOVI"],
        "status": "invasive",
    }
    briefing = smart_alerts.generate_smart_briefing(alert_raw)
    assert briefing["urgency"] == "CRITICAL"
    assert "African Catfish" in briefing["headline"]
    assert "Wildlife Protection Act" in " ".join(briefing["legal_backing"])


def test_xai_explainer_attribution():
    alert = {
        "scientific_name": "Clarias gariepinus",
        "reads": 1200,
        "confidence": 0.95,
        "status": "invasive",
    }
    explanation = xai_explainer.explain_alert_decision(alert)
    assert len(explanation["feature_attributions"]) >= 2
    assert explanation["overall_confidence"] == 0.95


def test_nlg_executive_briefing():
    analysis_mock = {
        "species": [
            {"name": "Clarias gariepinus", "rank": "species", "reads": 1800, "sites": ["VEMBANAD"]},
            {"name": "Tor putitora", "rank": "species", "reads": 400, "sites": ["VEMBANAD"]},
        ],
        "samples": [{"sample_id": "S1"}],
        "site_species": {"VEMBANAD": ["Clarias gariepinus", "Tor putitora"]},
        "phyla": [("Chordata", 2200)],
        "detections": 2,
    }
    briefing = nlg_insights.generate_executive_briefing(analysis_mock, "Test Survey")
    assert "TESTSURVEY" in briefing["report_header"]["doc_id"]
    assert briefing["executive_summary"]["kpis"]["invasive_taxa"] == 1

    assert len(briefing["threat_matrix"]) >= 1
    assert len(briefing["action_plan"]) >= 1


def test_nlg_executive_briefing_dict_sites_and_malformed_inputs():
    """Verify NLG briefing handles sites as dict objects and unexpected data types cleanly."""
    analysis_dict_sites = {
        "species": [
            {"name": "Oreochromis mossambicus", "reads": 1200, "sites": [{"site_id": "GOA-ZUARI", "reads": 1200}]},
            {"name": "Tor putitora", "reads": 300, "sites": [{"site_id": "GOA-MANDOVI", "reads": 300}]}
        ],
        "samples": "invalid_sample_count_str",
        "site_species": None,
        "phyla": [],
        "detections": 1500
    }
    briefing = nlg_insights.generate_executive_briefing(analysis_dict_sites, "Dict Sites Survey")
    assert len(briefing["threat_matrix"]) == 2
    assert briefing["threat_matrix"][0]["scientific_name"] == "Oreochromis mossambicus"
    assert "establishment_prob" in briefing["threat_matrix"][0]




def test_extinction_risk_ml():
    prediction = extinction_risk.predict_extinction_risk("Tor putitora", invasive_co_occurring=True)
    assert "Endangered" in prediction["predicted_category"]
    assert prediction["confidence_score"] > 0.75
    assert len(prediction["explanation"]["attributions"]) >= 1
    assert "status_quo" in prediction["pva_scenarios"]
    assert len(prediction["pva_scenarios"]["status_quo"]["trajectory"]) == 11


def test_spread_prediction_simulation():
    sites = [{"site_id": "MANDOVI", "latitude": 15.4989, "longitude": 73.8278, "reads": 1200}]
    forecast = spread_prediction.forecast_invasive_spread("Clarias gariepinus", sites, months_ahead=6)
    assert forecast["months_ahead"] == 6
    assert len(forecast["predictions"]) == 1
    assert forecast["predictions"][0]["spread_distance_km"] > 0.0
    assert len(forecast["hydro_corridors"]) >= 1
    assert len(forecast["hydro_corridors"][0]["waypoints"]) >= 2


def test_cv_field_verification():
    res = cv_verifier.predict_species_from_photo("catfish_sample.jpg", "Clarias gariepinus")
    assert res["is_confirmed"] is True
    assert res["top_species"] == "Clarias gariepinus"


def test_sampling_recommendations():
    sites = [{"site_id": "VEMBANAD", "latitude": 9.6000, "longitude": 76.4000, "reads": 1500}]
    recs = sampling_optimizer.recommend_sampling_locations("Oreochromis mossambicus", sites)
    assert recs["recommended_count"] >= 1
    assert recs["recommendations"][0]["composite_priority_score"] >= 50
    assert recs["recommendations"][0]["complementarity_gain"] > 0

