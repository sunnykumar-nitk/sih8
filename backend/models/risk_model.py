"""
Thin wrapper module kept separate from recommendation/scoring.py so the
"models" layer (AI-facing) and "recommendation" layer (decision-facing)
stay architecturally distinct, per the project's design principle:
AI detects evidence -> scoring engine calculates priority -> LLM only explains.

This module re-exports the priority engine for convenience so API routes
can import from backend.models if that reads more naturally in context.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommendation.scoring import calculate_priority  # noqa: F401
