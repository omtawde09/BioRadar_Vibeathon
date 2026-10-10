"""Unit tests for Feature 1: AI Biodiversity Weather Forecast."""

import pytest
from bioradar.analytics.forecast import generate_forecast


def test_generate_forecast_insufficient_data():
    """Verifies baseline generation when historical samples < 3."""
    res = generate_forecast("BR-TEST-COLD")
    assert res["status"] == "SUCCESS"
    assert "model_version" in res
    assert "last_updated" in res


def test_generate_forecast_synthetic_baseline(monkeypatch):
    """Tests 7-day weather forecast generation with synthetic historical sampling rounds."""
    from bioradar.analytics import anomaly

    mock_history = [
        {
            "run_id": f"run-{i}",
            "timestamp": 1000 + i * 86400,
            "rows": [
                {"sample_id": "BR-FORECAST", "scientific_name": "Tor putitora", "read_count": 500},
                {"sample_id": "BR-FORECAST", "scientific_name": "Clarias gariepinus", "read_count": 200},
            ]
        }
        for i in range(5)
    ]

    monkeypatch.setattr(anomaly, "get_historical_sample_runs", lambda sid: mock_history)

    res = generate_forecast("BR-FORECAST", days=7)
    assert res["status"] == "SUCCESS"
    assert res["forecast_days"] == 7
    assert len(res["daily_forecasts"]) == 7
    assert res["overall_trend"] in ["improving", "declining", "stable"]

    day1 = res["daily_forecasts"][0]
    assert "date" in day1
    assert "species_forecasts" in day1
    assert len(day1["species_forecasts"]) >= 1

    sp1 = day1["species_forecasts"][0]
    assert "species_name" in sp1
    assert 0.0 <= sp1["detection_probability"] <= 1.0
    assert "detection_probability_pct" in sp1
    assert "confidence_interval_95" in sp1
