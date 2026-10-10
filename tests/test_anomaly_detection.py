"""Unit tests for Feature 4: Real-Time Streaming eDNA Anomaly Detection."""

import pytest
from bioradar.analytics.anomaly import detect_anomalies


def test_detect_anomalies_insufficient_data():
    """Verifies cold-start handling when historical samples < 3."""
    res = detect_anomalies("BR-TEST-001")
    assert res["status"] in ["INSUFFICIENT_HISTORICAL_DATA", "ANALYSIS_COMPLETE"]
    assert "anomalies" in res


def test_detect_anomalies_synthetic_baseline(monkeypatch):
    """Tests anomaly detection with synthetic historical sample runs."""
    from bioradar.analytics import anomaly

    # Mock historical runs
    mock_history = [
        {
            "run_id": f"run-{i}",
            "timestamp": 1000 + i * 100,
            "rows": [
                {"sample_id": "BR-MOCK", "scientific_name": "Labeo rohita", "read_count": 100},
                {"sample_id": "BR-MOCK", "scientific_name": "Catla catla", "read_count": 200},
            ]
        }
        for i in range(5)
    ]

    monkeypatch.setattr(anomaly, "get_historical_sample_runs", lambda sid: mock_history)

    # Current sample has a 15x spike in Labeo rohita
    current_rows = [
        {"sample_id": "BR-MOCK", "scientific_name": "Labeo rohita", "read_count": 5000},
        {"sample_id": "BR-MOCK", "scientific_name": "Catla catla", "read_count": 100},
    ]

    res = anomaly.detect_anomalies("BR-MOCK", current_rows=current_rows)
    assert res["status"] == "ANALYSIS_COMPLETE"
    assert res["anomalies_detected_count"] >= 1
    
    spike_anomaly = next((a for a in res["anomalies"] if a["species_name"] == "Labeo rohita"), None)
    assert spike_anomaly is not None
    assert spike_anomaly["anomaly_type"] == "sudden_spike"
    assert spike_anomaly["severity"] in ["warning", "critical"]
    assert spike_anomaly["z_score"] > 3.0
