"""
Central configuration for the Disaster-Resilient AI backend.
Everything tunable (weights, thresholds, importance values) lives here,
NOT hard-coded inside logic files, so judges/teammates can adjust it
without touching the scoring code itself.
"""
import os

# Load a local .env file (if present) into the process environment so
# `os.getenv(...)` below can see it. Deployment platforms (Vercel/Render)
# inject real env vars directly and don't need this, so a missing .env file
# or a missing python-dotenv install is not an error -- just a no-op.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Demo / mock mode
# ---------------------------------------------------------------------------
# When True, the app runs fully offline using mock detection + mock GIS/population
# data. Flip to False once a real trained model + real data sources exist.
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Priority score weights (must sum to ~1.0). NOT official engineering standards
# -- these are configurable starting points for a hackathon prototype.
# ---------------------------------------------------------------------------
PRIORITY_WEIGHTS = {
    "damage_severity": 0.25,
    "population_impact": 0.15,
    "infrastructure_importance": 0.15,
    "accessibility": 0.10,
    "disaster_conditions": 0.08,
    "critical_facility_impact": 0.08,
    "cascading_impact": 0.07,
    "human_impact": 0.05,
    "time_sensitivity": 0.03,
    "alternative_route_risk": 0.02,
    "data_confidence": 0.02,
}

# ---------------------------------------------------------------------------
# Priority classification thresholds (0-100 scale)
# ---------------------------------------------------------------------------
PRIORITY_THRESHOLDS = {
    "CRITICAL": 76,
    "HIGH": 51,
    "MEDIUM": 26,
    "LOW": 0,
}

# ---------------------------------------------------------------------------
# Severity classification thresholds (0-10 scale)
# ---------------------------------------------------------------------------
SEVERITY_THRESHOLDS = {
    "Critical": 8,
    "Severe": 6,
    "Moderate": 4,
    "Low": 2,
    "Minor": 0,
}

# ---------------------------------------------------------------------------
# Infrastructure importance defaults (0-10). Configurable, not universal truth.
# ---------------------------------------------------------------------------
INFRASTRUCTURE_IMPORTANCE = {
    "hospital": 10,
    "emergency_center": 10,
    "major_bridge": 9,
    "main_highway": 9,
    "fire_station": 9,
    "police_station": 8,
    "school": 6,
    "residential_building": 6,
    "minor_road": 4,
    "other": 5,
}

# ---------------------------------------------------------------------------
# Disaster-specific factor sets (which extra signals matter per event type)
# ---------------------------------------------------------------------------
DISASTER_FACTORS = {
    "flood": ["flood_depth", "road_blockage", "bridge_access", "rainfall_intensity"],
    "earthquake": ["structural_tilt", "aftershock_risk", "building_occupancy", "trapped_person_possibility"],
    "aircraft_crash": ["fire", "smoke", "debris_field", "secondary_explosion_risk"],
    "generic": [],
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Vercel (and most serverless platforms) mount the deployed code read-only;
# only /tmp is writable, and it's ephemeral (wiped between cold starts).
# Detect that environment and redirect writable paths there automatically,
# while reads of bundled reference data (infrastructure.csv etc.) still
# come from the read-only DATA_DIR shipped with the code.
IS_SERVERLESS = bool(os.getenv("VERCEL"))
_WRITABLE_ROOT = "/tmp/disaster_resilient_ai" if IS_SERVERLESS else os.path.dirname(BASE_DIR)

UPLOAD_DIR = os.path.join(_WRITABLE_ROOT, "uploads") if IS_SERVERLESS else os.path.join(DATA_DIR, "uploads")
DEMO_CASES_DIR = os.path.join(DATA_DIR, "demo_cases")
REPORTS_DIR = os.path.join(_WRITABLE_ROOT, "generated_reports") if IS_SERVERLESS else os.path.join(os.path.dirname(BASE_DIR), "generated_reports")
INFRASTRUCTURE_CSV = os.path.join(DATA_DIR, "infrastructure.csv")
TEAMS_CSV = os.path.join(DATA_DIR, "teams.csv")

# ---------------------------------------------------------------------------
# Trained model weights (only used when DEMO_MODE=False and file exists)
# ---------------------------------------------------------------------------
YOLO_WEIGHTS_PATH = os.getenv("YOLO_WEIGHTS_PATH", os.path.join(BASE_DIR, "models", "weights", "best.pt"))

# ---------------------------------------------------------------------------
# AI Q&A chatbot
# ---------------------------------------------------------------------------
# Offline mode (default) is rule-based, free, and needs no key -- it pattern
# matches the question and answers strictly from SITE_STORE/TEAM_STORE data.
# Online mode calls Google's Gemini API (free tier) with the SAME structured
# data locked into the prompt, for free-form phrasing the rules don't catch.
# Set GEMINI_API_KEY (env var, never hard-coded) to enable online mode.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
# "offline" | "online" | "auto" (try offline rules first, fall back to
# online only if a key is configured and the question matches no rule)
CHAT_MODE_DEFAULT = os.getenv("CHAT_MODE_DEFAULT", "auto")

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
# SQLite by default -- swap DATABASE_URL for a real Postgres URL in prod.
# On Vercel/serverless, the deployed code directory is read-only and only
# /tmp is writable, and /tmp is wiped on every cold start -- so persistence
# there is "survives while the function instance is warm", not permanent.
# For real persistence in production, point DATABASE_URL at a hosted DB
# (Neon/Supabase Postgres, Turso, etc.) instead of the default SQLite file.
_DB_DIR = _WRITABLE_ROOT if IS_SERVERLESS else BASE_DIR
_DEFAULT_DB_PATH = os.path.join(_DB_DIR, "disaster_ai.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")
