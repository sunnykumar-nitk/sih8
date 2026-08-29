"""
POST /api/chat -- AI Q&A / disaster assistant.

Retrieval-then-explain: the chatbot never invents numbers, it only
explains numbers the scoring engine already calculated (see
services/chat_service.py for the full design note).
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.chat_service import answer_question
from api.assessment import SITE_STORE
from api.teams import TEAM_STORE
import config

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    site_id: Optional[str] = None
    mode: Optional[str] = None  # "offline" | "online" | "auto" (default from config.CHAT_MODE_DEFAULT)


@router.post("/chat")
def chat(req: ChatRequest):
    result = answer_question(
        question=req.question,
        sites=SITE_STORE,
        teams=TEAM_STORE,
        site_id=req.site_id,
        mode=req.mode or config.CHAT_MODE_DEFAULT,
    )
    return result


@router.get("/chat/status")
def chat_status():
    """Lets the frontend show whether online mode is actually available,
    without exposing the key itself."""
    return {
        "offline_available": True,
        "online_available": bool(config.GEMINI_API_KEY),
        "default_mode": config.CHAT_MODE_DEFAULT,
        "sites_available": len(SITE_STORE),
    }
