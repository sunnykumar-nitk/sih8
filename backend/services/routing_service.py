"""
Routing/accessibility provider. DEMO/MOCK by default -- swap `get_route_estimate`
internals for a real routing API (OSRM, Google Directions, etc.) later.
"""
from typing import Dict, Any
import math


def _distance_km(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b or "lat" not in a or "lat" not in b:
        return 10.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a["lat"], a["lon"], b["lat"], b["lon"]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(x))


def get_route_estimate(origin: Dict[str, float], destination: Dict[str, float], blocked: bool = False) -> Dict[str, Any]:
    """DEMO DATA: assumes 30 km/h average speed, doubles time + flags detour if blocked."""
    dist = round(_distance_km(origin, destination), 2)
    base_minutes = round((dist / 30.0) * 60, 1)  # 30 km/h assumption

    if blocked:
        return {
            "distance_km": dist,
            "travel_time_minutes": round(base_minutes * 1.8, 1),
            "route_status": "BLOCKED",
            "alternative_available": True,
        }
    return {
        "distance_km": dist,
        "travel_time_minutes": base_minutes,
        "route_status": "CLEAR",
        "alternative_available": True,
    }
