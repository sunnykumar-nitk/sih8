"""POST/GET /api/teams, POST /api/allocate -- team registry + allocation."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommendation.team_allocation import allocate_teams
from api.assessment import SITE_STORE
from services import db_service

router = APIRouter()

TEAM_STORE: Dict[str, Dict[str, Any]] = db_service.load_all_teams()


class Team(BaseModel):
    team_id: str
    specialization: str = "general"  # structural | road | fire | general
    equipment: List[str] = []
    location: Optional[Dict[str, float]] = None
    available: bool = True


@router.post("/teams")
def register_team(team: Team):
    TEAM_STORE[team.team_id] = team.dict()
    db_service.save_team(team.team_id, TEAM_STORE[team.team_id])
    return TEAM_STORE[team.team_id]


@router.get("/teams")
def list_teams():
    return list(TEAM_STORE.values())


@router.post("/allocate")
def allocate():
    sites = list(SITE_STORE.values())
    teams = list(TEAM_STORE.values())
    return allocate_teams(sites, teams)
