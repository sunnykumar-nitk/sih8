"""
Temporary mitigation + fix-vs-reroute recommendation logic.
Never certifies repairs -- always frames output as temporary/decision-support,
consistent with the project's core safety principle.
"""
from typing import Dict, Any, Optional

# Damage-type -> immediate safety action
IMMEDIATE_SAFETY = {
    "collapse": "Do not enter. Restrict all access and establish a wide exclusion perimeter.",
    "fire": "Evacuate the area. Alert fire services. Restrict public access.",
    "flooding": "Avoid route. Do not attempt to cross. Warn public via signage.",
    "structural_damage": "Cordon off area. Restrict entry pending inspection.",
    "debris": "Restrict access to blocked area. Warning signage recommended.",
    "crack": "Monitor. Restrict heavy load if severity is high.",
}

# Damage-type -> temporary mitigation suggestion
TEMPORARY_MITIGATION = {
    "collapse": ["Full closure", "Signpost detour", "24/7 monitoring for further collapse risk"],
    "fire": ["Establish safety perimeter", "Coordinate with fire services", "Assess secondary fire risk"],
    "flooding": ["Close road/route", "Signpost alternate route", "Temporary drainage if feasible"],
    "structural_damage": ["Install warning barriers", "Restrict heavy vehicle access", "Temporary support if trained personnel available"],
    "debris": ["Debris clearance", "Traffic diversion", "Temporary controlled passage"],
    "crack": ["Monitor for progression", "Restrict load if on a bridge/structure"],
}


def get_immediate_safety(damage_type: str, severity_score: float) -> str:
    action = IMMEDIATE_SAFETY.get(damage_type, "Restrict access pending inspection.")
    if severity_score >= 9:
        action = "URGENT: " + action
    return action


def get_temporary_mitigation(damage_type: str) -> list:
    return TEMPORARY_MITIGATION.get(damage_type, ["Standard caution signage recommended pending inspection."])


def fix_vs_reroute(repair_time_minutes: Optional[float], detour_time_minutes: Optional[float]) -> Dict[str, Any]:
    """
    Compares quick-fix repair time vs. detour time and recommends whichever
    restores access faster. Mirrors the "2 ft bridge crack, 2 min fix vs
    10 min detour" example from the project discussion.
    """
    if repair_time_minutes is None:
        return {
            "recommendation": "REROUTE",
            "reason": f"No quick fix available -- recommend detour (~{detour_time_minutes or 'unknown'} min) until full repair.",
        }
    if detour_time_minutes is None:
        return {
            "recommendation": "QUICK_FIX",
            "reason": f"Quick fix available in ~{repair_time_minutes} min; no detour time on record.",
        }
    if repair_time_minutes < detour_time_minutes:
        saved = round(detour_time_minutes - repair_time_minutes, 1)
        return {
            "recommendation": "QUICK_FIX",
            "reason": f"Quick fix (~{repair_time_minutes} min) is faster than detour (~{detour_time_minutes} min) -- saves ~{saved} min per crossing.",
        }
    return {
        "recommendation": "REROUTE",
        "reason": f"Detour (~{detour_time_minutes} min) is currently faster than repair (~{repair_time_minutes} min).",
    }


def get_team_and_equipment(damage_type: str, severity_score: float, priority_level: str) -> Dict[str, Any]:
    """Recommended response team + equipment for the result card."""
    if priority_level in ("CRITICAL", "HIGH") or damage_type in ("collapse", "fire", "structural_damage"):
        return {
            "team": "Structural / Disaster Assessment Team",
            "equipment": ["Drone", "GPS", "PPE", "Camera"],
        }
    if damage_type == "flooding":
        return {
            "team": "Road / Flood Assessment Team",
            "equipment": ["Drone", "GPS", "Waders/PPE"],
        }
    return {
        "team": "General Assessment Team",
        "equipment": ["Camera", "GPS"],
    }


def build_reason(breakdown: Dict[str, float], breakdown_max: Dict[str, float]) -> str:
    """Short 'Reason:' line for the result card, built from the top-contributing factors.
    Excludes data_confidence -- that reflects data quality, not urgency, so it
    shouldn't be cited as a reason a site is prioritized."""
    excluded = {"data_confidence"}
    ratios = {
        k: (breakdown.get(k, 0) / breakdown_max[k]) if breakdown_max.get(k) else 0
        for k in breakdown_max if k not in excluded
    }
    top = sorted(ratios.items(), key=lambda kv: -kv[1])[:3]
    phrases = {
        "damage_severity": "high damage",
        "population_impact": "high population impact",
        "infrastructure_importance": "critical infrastructure",
        "accessibility": "difficult accessibility",
        "disaster_conditions": "severe disaster conditions",
        "critical_facility_impact": "proximity to critical facilities",
        "cascading_impact": "critical route dependency",
        "human_impact": "significant human impact",
        "time_sensitivity": "time-sensitive response need",
        "alternative_route_risk": "limited alternative routes",
        "data_confidence": "high-confidence data",
    }
    parts = [phrases.get(k, k.replace("_", " ")) for k, _ in top if ratios[k] > 0.4]
    if not parts:
        return "Moderate readings across assessed factors."
    return ("Driven by " + " + ".join(parts) + ".").capitalize()


def get_inspection_recommendation(damage_type: str, severity_score: float) -> str:
    if damage_type in ("collapse", "structural_damage") and severity_score >= 6:
        return "Structural engineer required"
    if damage_type == "flooding":
        return "Flood/road engineer assessment required"
    if damage_type == "fire":
        return "Fire safety inspection required"
    if damage_type == "debris":
        return "Ground verification / debris assessment"
    return "General assessor / drone re-survey"
