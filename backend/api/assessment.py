"""
GET/POST /api/assess, /api/sites -- full pipeline: detections -> priority score.
In-memory store for the prototype (swap for SQLAlchemy models later --
see recommended project structure in the README).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommendation.scoring import calculate_priority
from recommendation.triage import build_explanation, build_cascading_explanation
from services.gis_service import get_importance_score, find_nearby_critical_facilities
from services.population_service import get_population_impact
from recommendation.team_sizing import estimate_team_size
from services import db_service

router = APIRouter()

# In-memory store, mirrored to SQLite (services/db_service.py) on every
# write so data survives a process restart -- see PROJECT_REQUIREMENTS_STATUS.md
# item 11. Loaded back from the DB at import time (server startup).
db_service.init_db()
SITE_STORE: Dict[str, Dict[str, Any]] = db_service.load_all_sites()


class AssessRequest(BaseModel):
    site_id: str
    asset_type: str = "other"
    damage_severity: float = 5
    accessibility: float = 5
    disaster_conditions: float = 5
    time_sensitivity: float = 5
    alternative_route_risk: float = 5
    cascading_impact: float = 0
    data_confidence: float = 0.8
    location: Optional[Dict[str, float]] = None


@router.post("/assess")
def assess_site(req: AssessRequest):
    location = req.location or {}
    pop = get_population_impact(location.get("lat", 0), location.get("lon", 0)) if location else {
        "estimated_affected_population": 0, "population_density": 0
    }
    importance = get_importance_score(req.asset_type)
    nearby_critical = find_nearby_critical_facilities(location.get("lat", 0), location.get("lon", 0)) if location else []

    site = req.dict()
    site["infrastructure_importance"] = importance
    site["population_impact"] = min(10, pop["estimated_affected_population"] / 5000)
    site["critical_facility_impact"] = min(10, len(nearby_critical) * 3)
    site["human_impact"] = site["population_impact"]
    # Previously computed but never saved onto the site record -- meant
    # chat_service.py's "does any site affect a hospital?" and "what
    # happens if X is blocked?" handlers always looked at an empty list /
    # missing key, regardless of what find_nearby_critical_facilities()
    # actually found. Save the real facility names + the explanation
    # sentence so both offline rules and the online Gemini context have
    # real data instead of silently-empty fields.
    site["nearby_critical_facilities"] = [f["name"] for f in nearby_critical]

    priority_result = calculate_priority(site)
    site.update(priority_result)
    # Same 0-100 normalization as the upload-batch flow -- keep the two
    # entry points consistent (see chat_service._severity_100 / doc request
    # to "calculate severity score also in 100").
    site["severity_score_100"] = round(min(10.0, max(0.0, req.damage_severity)) * 10, 1)
    site["explanation"] = build_explanation(site, priority_result)
    site["cascading_explanation"] = build_cascading_explanation(site, site["nearby_critical_facilities"])
    site["population_data"] = pop
    site["team_size"] = estimate_team_size(
        damage_type=req.asset_type,
        severity_score=req.damage_severity,
        priority_level=priority_result["priority_level"],
        estimated_affected_population=pop.get("estimated_affected_population", 0),
        accessibility=req.accessibility,
    )

    SITE_STORE[req.site_id] = site
    db_service.save_site(req.site_id, site)
    return site


@router.get("/sites")
def list_sites():
    return list(SITE_STORE.values())


@router.get("/sites/{site_id}")
def get_site(site_id: str):
    site = SITE_STORE.get(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.get("/priority")
def priority_queue():
    return sorted(SITE_STORE.values(), key=lambda s: -s.get("priority_score", 0))
