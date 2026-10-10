"""Unit tests for Feature 6: Satellite Change Detection Alerts."""

import pytest
from bioradar.satellite.change_detection import check_site_changes, compute_ndvi


def test_compute_ndvi():
    """Tests NDVI mathematical formula computation."""
    ndvi = compute_ndvi(nir_b8=0.8, red_b4=0.2)
    assert abs(ndvi - 0.6) < 1e-4


def test_check_site_changes_deforestation():
    """Tests detection of deforestation event (NDVI drop > 0.3)."""
    res = check_site_changes("BR-GOA-001", mock_ndvi_before=0.70, mock_ndvi_after=0.30)
    assert res["change_detected"] is True
    assert res["change_type"] == "deforestation"
    assert res["alert"] is not None
    assert res["alert"]["severity"] == "critical"
    assert res["alert"]["ndvi_change"] == -0.40
