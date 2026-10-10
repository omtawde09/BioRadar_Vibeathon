"""Hydro-Corridor Fluid Dispersal & Site-Anchored Water Flow Engine.

Models invasive species dispersal starting DIRECTLY AT THE OCCURRENCE SITE pin marker
and flowing downstream along the natural blue water body channel.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Arrival time front color tokens for fluid flow channel visualization
CORRIDOR_COLORS = {
    "1-3_months": "#dc2626",   # Dark Crimson (Immediate Front)
    "3-6_months": "#ef4444",   # Vivid Red
    "6-12_months": "#f97316",  # Amber/Orange
    "12+_months": "#eab308",   # Light Gold
}

# Regional Water Channel Flow Trajectories (Relative offsets from site origin along blue water body)
WATER_CORRIDOR_OFFSETS: Dict[str, Dict[str, Any]] = {
    "VEMBANAD": {
        "name": "Vembanad Lake Estuary Channel",
        "flow_direction": "South-Southwest Lake Corridor",
        # Offsets (d_lat, d_lon, channel_width_km) following blue lake water down to Alappuzha
        "offsets": [
            (0.0000, 0.0000, 1.8),   # Origin at Site Pin Marker
            (-0.0250, -0.0120, 2.4),  # Mid Lake Channel
            (-0.0550, -0.0280, 2.6),  # Lower Vembanad Lake
            (-0.0880, -0.0450, 2.1),  # Komalapuram / Aryad Lake Channel
            (-0.1250, -0.0580, 1.4),  # Alappuzha / Punnamada Lagoon Exit
        ],
    },
    "MANDOVI": {
        "name": "Mandovi River Estuary Channel",
        "flow_direction": "Westward Tidal Estuary",
        "offsets": [
            (0.0000, 0.0000, 1.0),
            (-0.0080, 0.0180, 1.5),
            (-0.0180, 0.0420, 1.8),
            (-0.0280, 0.0700, 1.4),
            (-0.0400, 0.0950, 1.0),
        ],
    },
    "KOLLERU": {
        "name": "Kolleru Lake Central Basin",
        "flow_direction": "Southeast Wetland Basin",
        "offsets": [
            (0.0000, 0.0000, 1.5),
            (-0.0200, 0.0350, 2.8),
            (-0.0450, 0.0750, 3.2),
            (-0.0750, 0.1150, 2.2),
        ],
    },
    "KAVARATTI": {
        "name": "Kavaratti Lagoon Waters",
        "flow_direction": "Southwest Lagoon Channel",
        "offsets": [
            (0.0000, 0.0000, 0.8),
            (-0.0120, -0.0080, 1.2),
            (-0.0250, -0.0150, 1.4),
        ],
    },
}


def calculate_habitat_suitability(
    temperature_c: float = 26.5,
    water_bod: float = 2.5,
    flow_velocity_m_s: float = 0.5,
    salinity_ppt: float = 5.0,
) -> float:
    """MaxEnt suitability score (0.0 to 1.0) based on environmental parameters."""
    temp_score = math.exp(-((temperature_c - 27.0) ** 2) / 18.0)
    bod_score = min(1.0, water_bod / 4.0)
    flow_score = min(1.0, max(0.2, flow_velocity_m_s * 1.5))
    salinity_penalty = max(0.0, 1.0 - (salinity_ppt / 35.0) * 0.4)

    suitability = ((temp_score * 0.4) + (bod_score * 0.3) + (flow_score * 0.3)) * salinity_penalty
    return round(max(0.0, min(1.0, suitability)), 3)


def _get_water_corridor_data(site_id: str, lat: float, lon: float) -> Tuple[str, List[Tuple[float, float, float]], Dict[str, Any]]:
    """Match site to regional water corridor flow offsets."""
    key_upper = site_id.upper()
    for key, data in WATER_CORRIDOR_OFFSETS.items():
        if key in key_upper:
            return data["name"], data["offsets"], data

    # Geographic coordinate bounding box matching
    if 9.3 <= lat <= 9.9 and 76.2 <= lon <= 76.6:
        data = WATER_CORRIDOR_OFFSETS["VEMBANAD"]
        return data["name"], data["offsets"], data
    elif 15.3 <= lat <= 15.6 and 73.7 <= lon <= 74.0:
        data = WATER_CORRIDOR_OFFSETS["MANDOVI"]
        return data["name"], data["offsets"], data
    elif 16.4 <= lat <= 16.8 and 81.1 <= lon <= 81.5:
        data = WATER_CORRIDOR_OFFSETS["KOLLERU"]
        return data["name"], data["offsets"], data

    # Generic downstream water corridor offsets
    generic_offsets = [
        (0.0000, 0.0000, 1.2),
        (-0.0180, 0.0150, 1.6),
        (-0.0380, 0.0320, 2.0),
        (-0.0600, 0.0550, 1.5),
    ]
    return f"{site_id} Waterway", generic_offsets, {"flow_direction": "River Channel"}


def forecast_invasive_spread(
    species_name: str,
    occurrence_sites: List[Dict[str, Any]],
    months_ahead: int = 6,
) -> Dict[str, Any]:
    """Run Site-Anchored Water Dispersal Simulation originating AT the occurrence site marker."""
    corridor_networks = []
    all_predictions = []

    for site in occurrence_sites:
        site_id = site.get("site_id") or site.get("name") or "SITE"
        try:
            lat = float(site.get("latitude") or 0.0)
            lon = float(site.get("longitude") or 0.0)
        except ValueError:
            continue

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            continue

        suitability = calculate_habitat_suitability()
        w_name, offsets, w_meta = _get_water_corridor_data(site_id, lat, lon)

        # Build smooth site-anchored flow tube waypoints
        tube_waypoints = []
        cum_dist = 0.0

        for idx, (d_lat, d_lon, channel_width) in enumerate(offsets):
            pt_lat = round(lat + d_lat, 5)
            pt_lon = round(lon + d_lon, 5)

            if idx > 0:
                prev_lat = tube_waypoints[-1]["lat"]
                prev_lon = tube_waypoints[-1]["lon"]
                # Great-circle approximation in km
                dist_lat = (pt_lat - prev_lat) * 111.0
                dist_lon = (pt_lon - prev_lon) * 111.0 * math.cos(math.radians(pt_lat))
                segment_km = math.sqrt(dist_lat * dist_lat + dist_lon * dist_lon)
                cum_dist += segment_km

            arrival_months = round(cum_dist / 1.5, 1)
            if arrival_months > (months_ahead + 2.0):
                continue

            if arrival_months <= 3:
                time_bracket = "1-3_months"
            elif arrival_months <= 6:
                time_bracket = "3-6_months"
            elif arrival_months <= 12:
                time_bracket = "6-12_months"
            else:
                time_bracket = "12+_months"

            tube_waypoints.append({
                "lat": pt_lat,
                "lon": pt_lon,
                "channel_width_km": channel_width,
                "distance_from_origin_km": round(cum_dist, 1),
                "arrival_months": arrival_months,
                "time_bracket": time_bracket,
                "color": CORRIDOR_COLORS[time_bracket],
                "colonisation_risk": "HIGH" if arrival_months <= 3 else ("MEDIUM" if arrival_months <= 6 else "LOW"),
            })

        if tube_waypoints:
            max_dist = max(p["distance_from_origin_km"] for p in tube_waypoints)
            max_prob = min(0.98, round(0.55 + (suitability * 0.4), 2))

            corridor_networks.append({
                "origin_site_id": site_id,
                "origin_coords": [lat, lon],
                "waterway_name": w_name,
                "flow_direction": w_meta.get("flow_direction", "Downstream Channel"),
                "max_spread_km": max_dist,
                "habitat_suitability": suitability,
                "waypoints": tube_waypoints,
                "water_boundary_polygon": [[p["lat"], p["lon"]] for p in tube_waypoints],
            })

            all_predictions.append({
                "origin_site_id": site_id,
                "origin_lat": lat,
                "origin_lon": lon,
                "predicted_lat": tube_waypoints[-1]["lat"],
                "predicted_lon": tube_waypoints[-1]["lon"],
                "spread_distance_km": max_dist,
                "months_ahead": months_ahead,
                "habitat_suitability": suitability,
                "invasion_probability": max_prob,
                "estimated_read_growth": f"{round(1.8 ** (months_ahead / 6.0), 2)}x",
                "risk_level": "HIGH" if max_prob >= 0.75 else "MEDIUM",
            })

    max_overall_km = max([p["spread_distance_km"] for p in all_predictions], default=0.0)

    summary_text = (
        f"Site-anchored fluid hydro dispersal simulation for {species_name} over {months_ahead} months projects "
        f"channel propagation originating from detection sites up to {max_overall_km} km along blue water corridors."
    )

    return {
        "species": species_name,
        "months_ahead": months_ahead,
        "simulation_summary": summary_text,
        "predictions": all_predictions,
        "hydro_corridors": corridor_networks,
        "legend": {
            "1-3_months": {"label": "1–3 Months (Immediate Water Front)", "color": "#dc2626"},
            "3-6_months": {"label": "3–6 Months (Intermediate Front)", "color": "#ef4444"},
            "6-12_months": {"label": "6–12 Months (Expanding Front)", "color": "#f97316"},
            "12+_months": {"label": "12+ Months (Distal Corridor)", "color": "#eab308"},
        },
    }
