"""
Loads demo disaster case files and determines disaster-specific factor sets.
"""
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def load_demo_case(case_name: str) -> dict:
    """case_name e.g. 'nepal_flood', 'assam_flood', 'ahmedabad_crash'"""
    path = os.path.join(config.DEMO_CASES_DIR, f"{case_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Demo case '{case_name}' not found at {path}")
    with open(path) as f:
        return json.load(f)


def list_demo_cases() -> list:
    if not os.path.exists(config.DEMO_CASES_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(config.DEMO_CASES_DIR) if f.endswith(".json")]


def get_disaster_factors(disaster_type: str) -> list:
    return config.DISASTER_FACTORS.get(disaster_type, config.DISASTER_FACTORS["generic"])
