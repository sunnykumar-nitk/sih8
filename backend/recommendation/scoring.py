"""
Deterministic priority scoring engine. Combines many 0-10 (or 0-1) factors
into a single 0-100 priority score using configurable weights from config.py.

IMPORTANT: this is a transparent weighted-sum formula, not a black-box model.
Every factor and its contribution can be shown to judges (see explain_score()).
"""
from typing import Dict, Any
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def _normalize(value: float, max_value: float = 10.0) -> float:
    """Clamp and scale a 0-max_value input to 0-1."""
    value = max(0.0, min(value, max_value))
    return value / max_value


def calculate_priority(site: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected `site` fields (all 0-10 unless noted, all optional -> default 5):
      damage_severity, population_impact, infrastructure_importance,
      accessibility (higher = HARDER to reach), disaster_conditions,
      critical_facility_impact, cascading_impact, human_impact,
      time_sensitivity, alternative_route_risk, data_confidence (0-1)

    Returns: {
        "priority_score": 0-100,
        "priority_level": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW",
        "breakdown": {factor: contribution_points, ...}
    }
    """
    factors = {
        "damage_severity": site.get("damage_severity", 5),
        "population_impact": site.get("population_impact", 5),
        "infrastructure_importance": site.get("infrastructure_importance", 5),
        "accessibility": site.get("accessibility", 5),
        "disaster_conditions": site.get("disaster_conditions", 5),
        "critical_facility_impact": site.get("critical_facility_impact", 5),
        "cascading_impact": site.get("cascading_impact", 0),
        "human_impact": site.get("human_impact", 5),
        "time_sensitivity": site.get("time_sensitivity", 5),
        "alternative_route_risk": site.get("alternative_route_risk", 5),
    }
    # data_confidence is 0-1 already (AI confidence * data confidence)
    data_confidence = site.get("data_confidence", 0.8)

    breakdown = {}
    breakdown_max = {}
    total = 0.0
    for key, raw_value in factors.items():
        weight = config.PRIORITY_WEIGHTS.get(key, 0)
        contribution = _normalize(raw_value) * weight * 100
        breakdown[key] = round(contribution, 2)
        breakdown_max[key] = round(weight * 100, 2)
        total += contribution

    confidence_weight = config.PRIORITY_WEIGHTS.get("data_confidence", 0)
    confidence_contribution = data_confidence * confidence_weight * 100
    breakdown["data_confidence"] = round(confidence_contribution, 2)
    breakdown_max["data_confidence"] = round(confidence_weight * 100, 2)
    total += confidence_contribution

    total = round(min(total, 100.0), 2)

    level = "LOW"
    for name, threshold in sorted(config.PRIORITY_THRESHOLDS.items(), key=lambda kv: -kv[1]):
        if total >= threshold:
            level = name
            break

    return {
        "priority_score": total,
        "priority_level": level,
        "breakdown": breakdown,
        "breakdown_max": breakdown_max,
    }


def explain_score(priority_result: Dict[str, Any]) -> str:
    """Human-readable explanation string for the AI Q&A / report layer."""
    lines = [f"Priority Score = {priority_result['priority_score']}/100 ({priority_result['priority_level']})", ""]
    for factor, points in priority_result["breakdown"].items():
        lines.append(f"  {factor.replace('_', ' ').title():<28} {points:>6.2f} pts")
    return "\n".join(lines)
