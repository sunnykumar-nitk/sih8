"""
Route/accessibility recommendation. In demo mode, uses simple mock/heuristic
estimates. Swap `estimate_route()` internals for a real routing_service call
(OSRM/Google Directions/etc.) once available -- interface stays the same.
"""
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.routing_service import get_route_estimate


def estimate_route(origin: Dict[str, float], destination: Dict[str, float], blocked: bool = False) -> Dict[str, Any]:
    """
    Returns: {
        "distance_km": float,
        "travel_time_minutes": float,
        "route_status": "CLEAR" | "BLOCKED" | "PARTIALLY_BLOCKED",
        "alternative_available": bool
    }
    """
    return get_route_estimate(origin, destination, blocked)


def recommend_route_action(route: Dict[str, Any]) -> str:
    if route["route_status"] == "BLOCKED" and not route["alternative_available"]:
        return "No viable route currently -- coordinate with local authorities for access."
    if route["route_status"] == "BLOCKED" and route["alternative_available"]:
        return f"Primary route blocked -- use alternate route (~{route['travel_time_minutes']} min)."
    if route["route_status"] == "PARTIALLY_BLOCKED":
        return f"Route passable with caution (~{route['travel_time_minutes']} min) -- expect delays."
    return f"Route clear -- estimated travel time ~{route['travel_time_minutes']} min."
