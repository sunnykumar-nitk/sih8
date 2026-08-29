"""
GIS / infrastructure-importance lookups. Reads backend/data/infrastructure.csv.
Falls back to config.INFRASTRUCTURE_IMPORTANCE defaults if a type isn't listed.
Clearly a DEMO/OPEN-DATA provider -- swap internals for OSM/Overpass later
without changing the function signatures below.
"""
import csv
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_cache = None


def _load_infrastructure():
    global _cache
    if _cache is not None:
        return _cache
    _cache = []
    if os.path.exists(config.INFRASTRUCTURE_CSV):
        with open(config.INFRASTRUCTURE_CSV, newline="") as f:
            _cache = list(csv.DictReader(f))
    return _cache


def get_importance_score(infra_type: str) -> float:
    """Returns 0-10 importance for a given infrastructure type."""
    return float(config.INFRASTRUCTURE_IMPORTANCE.get(infra_type, config.INFRASTRUCTURE_IMPORTANCE["other"]))


def find_nearby_critical_facilities(lat: float, lon: float, radius_km: float = 5.0):
    """DEMO DATA: returns infrastructure.csv rows within a crude bounding box.
    Replace with a real geospatial query (PostGIS/Overpass) for production."""
    rows = _load_infrastructure()
    nearby = []
    for row in rows:
        try:
            r_lat, r_lon = float(row["lat"]), float(row["lon"])
        except (KeyError, ValueError):
            continue
        if abs(r_lat - lat) < (radius_km / 111.0) and abs(r_lon - lon) < (radius_km / 111.0):
            nearby.append(row)
    return nearby
