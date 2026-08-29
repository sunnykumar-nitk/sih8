"""GET /api/recommendations/{site_id} -- full recommendation bundle for one site."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommendation.mitigation import (
    get_immediate_safety, get_temporary_mitigation, fix_vs_reroute, get_inspection_recommendation
)
from recommendation.route_planner import estimate_route, recommend_route_action
from services.population_service import get_population_impact
from api.assessment import SITE_STORE

router = APIRouter()


class FixVsRerouteRequest(BaseModel):
    repair_time_minutes: Optional[float] = None
    detour_time_minutes: Optional[float] = None


class RouteRequest(BaseModel):
    origin: Dict[str, float]        # {"lat": .., "lon": ..}
    destination: Dict[str, float]   # {"lat": .., "lon": ..}
    blocked: bool = False           # simulate the road/bridge being blocked


@router.get("/recommendations/{site_id}")
def get_recommendations(site_id: str):
    site = SITE_STORE.get(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found. Call /api/assess first.")

    damage_type = site.get("dominant_damage_type") or "structural_damage"
    severity = site.get("damage_severity", 5)

    return {
        "site_id": site_id,
        "immediate_safety": get_immediate_safety(damage_type, severity),
        "temporary_mitigation": get_temporary_mitigation(damage_type),
        "inspection_recommendation": get_inspection_recommendation(damage_type, severity),
        "priority_level": site.get("priority_level"),
        "explanation": site.get("explanation"),
    }


@router.post("/recommendations/fix-vs-reroute")
def fix_vs_reroute_endpoint(req: FixVsRerouteRequest):
    return fix_vs_reroute(req.repair_time_minutes, req.detour_time_minutes)


@router.post("/route")
def route_endpoint(req: RouteRequest):
    """
    Road-block simulation: estimate travel time/distance between two points,
    optionally as if the direct route were blocked (bridge out, flooded
    road, etc.). Call twice (blocked=false then blocked=true) to compare
    before/after and see the extra delay a blockage would cause.
    """
    route = estimate_route(req.origin, req.destination, req.blocked)
    route["recommended_action"] = recommend_route_action(route)
    return route


@router.get("/population")
def population_endpoint(lat: float, lon: float, radius_km: float = 2.0):
    """Look up population context for a point on the map -- used by the
    map/assessment UI to preview population density before running a full
    assessment. See population_service for the REFERENCE vs DEMO data rules."""
    return get_population_impact(lat, lon, radius_km)
