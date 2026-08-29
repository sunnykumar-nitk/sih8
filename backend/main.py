"""
Disaster-Resilient Infrastructure Assessment -- FastAPI entrypoint.

Run locally:
    cd backend
    pip install -r ../requirements.txt
    uvicorn main:app --reload --port 8000

Then open http://localhost:8000/docs for interactive API docs, or open
../frontend/index.html in a browser (it calls this API at localhost:8000).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from api import upload, assessment, recommendations, teams, reports, chat

app = FastAPI(
    title="Disaster-Resilient Infrastructure Assessment API",
    description="AI-assisted post-disaster assessment and emergency inspection "
                "prioritization. Decision support only -- does not certify repairs.",
    version="0.1.0",
)

# The frontend is served from this same app/domain (see the StaticFiles
# mount below), so cross-origin requests aren't actually needed for normal
# use. CORS is still left open here only so the API can also be hit
# directly (e.g. from /docs, curl, or a separate dev frontend) -- tighten
# allow_origins to your real domain before a non-demo deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(assessment.router, prefix="/api", tags=["assessment"])
app.include_router(recommendations.router, prefix="/api", tags=["recommendations"])
app.include_router(teams.router, prefix="/api", tags=["teams"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/api/status")
def root():
    return {
        "status": "ok",
        "demo_mode": config.DEMO_MODE,
        "message": "Disaster-Resilient Infrastructure Assessment API. See /docs.",
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Serve the frontend from the same app/domain as the API.
#
# This is deliberate: it means the frontend can always call the API at the
# relative path "/api/..." -- no base URL to configure, no CORS to fight,
# and no separate "static site" deployment for Vercel to misdetect. One
# FastAPI app, one Vercel Function, one deployment.
#
# Must be mounted LAST -- StaticFiles at "/" would otherwise swallow every
# route registered after it, including the /api/* routers above.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.join(os.path.dirname(_BACKEND_DIR), "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
