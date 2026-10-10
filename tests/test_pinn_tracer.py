from bioradar.ai.pinn_tracer import (
    predict_upstream_origin,
    inverse_advection_dispersion_solver,
    predict_all_upstream_origins_for_run,
)


def test_inverse_advection_dispersion_solver():
    res = inverse_advection_dispersion_solver(read_count=1200, total_reads=4694, flow_velocity_ms=0.45, temp_c=28.0)
    assert "travel_time_hrs" in res
    assert "upstream_distance_km" in res
    assert "map_uncertainty_km" in res
    assert res["upstream_distance_km"] > 0.0
    assert res["map_uncertainty_km"] > 0.0


def test_predict_upstream_origin_normal():
    res = predict_upstream_origin(
        site_id="GOA-MANDOVI",
        site_lat=15.4989,
        site_lon=73.8278,
        species_name="Clarias gariepinus",
        read_count=1500,
        total_reads=4694
    )
    assert res["site_id"] == "GOA-MANDOVI"
    assert "predicted_origin" in res
    origin = res["predicted_origin"]
    assert origin["latitude"] != 15.4989 or origin["longitude"] != 73.8278
    assert "map_spatial_uncertainty_km" in origin
    assert len(res["geojson"]["features"]) == 3


def test_predict_upstream_origin_extreme_latitude_and_zero_reads():
    """Verify polar boundary math and zero reads do not crash or produce NaN/Infinity."""
    res_polar = predict_upstream_origin(
        site_id="ARCTIC-SITE",
        site_lat=89.9,
        site_lon=0.0,
        read_count=0,
        total_reads=0
    )
    assert "predicted_origin" in res_polar
    origin = res_polar["predicted_origin"]
    assert isinstance(origin["latitude"], float)
    assert isinstance(origin["longitude"], float)
    assert not (origin["latitude"] != origin["latitude"])  # NaN check


def test_predict_all_upstream_origins_for_run_edge_cases():
    """Verify multi-site PINN origin calculation handles empty and malformed points list."""
    res_empty = predict_all_upstream_origins_for_run([])
    assert len(res_empty["traces"]) == 0


    malformed_points = [
        {"site_id": "SITE-A", "latitude": None, "longitude": "invalid", "total_reads": "0"},
        {"site_id": "SITE-B", "latitude": 15.4, "longitude": 73.9, "total_reads": 1000}
    ]
    res_malformed = predict_all_upstream_origins_for_run(malformed_points)
    assert len(res_malformed["traces"]) == 2
    assert res_malformed["geojson"]["type"] == "FeatureCollection"
