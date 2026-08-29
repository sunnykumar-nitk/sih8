"""Shared pytest fixtures. Run from the `backend/` directory:
    cd backend && pip install -r ../requirements.txt pytest httpx && pytest -v
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use a throwaway SQLite file for tests so they never touch dev/prod data.
_TMP_DB = os.path.join(tempfile.gettempdir(), "disaster_ai_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["DEMO_MODE"] = "true"

import pytest


@pytest.fixture
def sample_site():
    return {
        "site_id": "Test Bridge",
        "asset_type": "major_bridge",
        "damage_severity": 7.5,
        "population_impact": 8,
        "infrastructure_importance": 9,
        "accessibility": 7,
        "disaster_conditions": 6,
        "critical_facility_impact": 6,
        "cascading_impact": 6,
        "human_impact": 8,
        "time_sensitivity": 7,
        "alternative_route_risk": 6,
        "data_confidence": 0.85,
    }


@pytest.fixture
def sample_detections():
    return [
        {"object_type": "road", "damage_type": "flooding", "damage_percentage": 80, "confidence": 0.9},
        {"object_type": "building", "damage_type": "debris", "damage_percentage": 40, "confidence": 0.7},
    ]
