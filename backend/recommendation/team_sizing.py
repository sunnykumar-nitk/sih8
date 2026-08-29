"""
Estimates HOW MANY responders a site needs, and of what role -- not just
WHICH team (that's team_allocation.py). Deterministic, rule-based, and
fully explainable: driven by severity, estimated affected population, and
how hard the site is to reach.

This is a sizing heuristic for a hackathon decision-support prototype, not
an official emergency-staffing standard -- thresholds live in one place
below so they're easy to defend/adjust in front of judges.
"""
from typing import Dict, Any


# Population brackets -> extra "general responder" headcount.
# (upper_bound_people, extra_people)
_POPULATION_BRACKETS = [
    (500, 0),
    (2000, 1),
    (10000, 2),
    (50000, 4),
    (float("inf"), 6),
]


def _population_headcount(estimated_affected_population: float) -> int:
    for upper, extra in _POPULATION_BRACKETS:
        if estimated_affected_population <= upper:
            return extra
    return 6


def estimate_team_size(
    damage_type: str,
    severity_score: float,
    priority_level: str,
    estimated_affected_population: float,
    accessibility: float,
) -> Dict[str, Any]:
    """
    Returns a role-by-role headcount recommendation plus the total, and a
    one-line explanation of what drove the number up or down.

    accessibility: 0-10, HIGHER = HARDER to reach (matches the rest of the
    codebase's convention -- see scoring.py).
    """
    roles: Dict[str, int] = {}

    # --- Base structural/technical staffing from damage type + severity ---
    if damage_type in ("collapse", "structural_damage") and severity_score >= 6:
        roles["structural_engineers"] = 2 if severity_score >= 8.5 else 1
    elif damage_type == "crack":
        roles["structural_engineers"] = 1
    elif damage_type == "flooding":
        roles["road_flood_engineers"] = 1
    elif damage_type == "fire":
        roles["fire_safety_officers"] = 1

    # --- Medical personnel when population exposure is meaningful ---
    if estimated_affected_population >= 2000 or priority_level in ("CRITICAL", "HIGH"):
        roles["medical_personnel"] = 2 if estimated_affected_population >= 10000 else 1

    # --- Drone operator whenever a visual re-survey is warranted ---
    if severity_score >= 5 or priority_level in ("CRITICAL", "HIGH"):
        roles["drone_operator"] = 1

    # --- General responders/support, scaled by population exposure ---
    general = 1 + _population_headcount(estimated_affected_population)

    # --- Accessibility penalty: hard-to-reach sites need extra support crew
    #     (to carry equipment, manage a longer/rougher trip, etc.) ---
    if accessibility >= 8:
        general += 2
    elif accessibility >= 5:
        general += 1

    roles["general_responders"] = general

    total = sum(roles.values())

    reasons = []
    if severity_score >= 8:
        reasons.append("critical damage severity")
    elif severity_score >= 6:
        reasons.append("severe damage")
    if estimated_affected_population >= 10000:
        reasons.append(f"large affected population (~{int(estimated_affected_population):,})")
    elif estimated_affected_population >= 2000:
        reasons.append(f"moderate affected population (~{int(estimated_affected_population):,})")
    if accessibility >= 8:
        reasons.append("very difficult access")
    elif accessibility >= 5:
        reasons.append("limited access")

    reason = ("Sized for " + ", ".join(reasons) + ".") if reasons else \
        "Standard sizing -- no severity, population, or access factors pushed this above baseline."

    return {
        "roles": roles,
        "total_personnel": total,
        "reason": reason,
    }
