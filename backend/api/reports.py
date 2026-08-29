"""POST /api/report, GET /api/report/{report_id} -- PDF report generation."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.report_service import generate_pdf_report
from api.assessment import SITE_STORE
from api.teams import TEAM_STORE
from recommendation.team_allocation import allocate_teams

router = APIRouter()


class ReportRequest(BaseModel):
    case_name: str = "assessment"
    disaster_type: str = "generic"


@router.post("/report")
def create_report(req: ReportRequest):
    sites = list(SITE_STORE.values())
    if not sites:
        raise HTTPException(status_code=400, detail="No assessed sites yet. Call /api/assess first.")

    for s in sites:
        s.setdefault("immediate_action", s.get("explanation", ""))

    assignments = allocate_teams(sites, list(TEAM_STORE.values())) if TEAM_STORE else []

    path = generate_pdf_report({
        "case_name": req.case_name,
        "disaster_type": req.disaster_type,
        "sites": sites,
        "team_assignments": assignments,
    })
    return {"report_path": path, "filename": os.path.basename(path)}


@router.get("/report/{filename}")
def download_report(filename: str):
    import config
    path = os.path.join(config.REPORTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)
