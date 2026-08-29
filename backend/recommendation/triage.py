"""
Triage classification + cascading dependency logic.

Cascading impact: if a damaged asset is a dependency for another important
asset (e.g. "Bridge A" is the only route to "Hospital B"), its effective
priority should reflect that downstream risk, not just its own damage.
"""
from typing import Dict, Any, List
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def classify(priority_score: float) -> str:
    for name, threshold in sorted(config.PRIORITY_THRESHOLDS.items(), key=lambda kv: -kv[1]):
        if priority_score >= threshold:
            return name
    return "LOW"


def calculate_cascading_impact(site: Dict[str, Any], dependency_graph: Dict[str, List[str]] = None) -> float:
    """
    dependency_graph: {"site_id": ["dependent_site_id_1", "dependent_site_id_2"]}
    e.g. {"bridge_a": ["hospital_b"]} means hospital_b's access depends on bridge_a.

    Returns a 0-10 cascading impact score based on:
      - how many sites depend on this one
      - how important those dependents are
    """
    if not dependency_graph:
        return site.get("cascading_impact", 0)

    dependents = dependency_graph.get(site.get("site_id"), [])
    if not dependents:
        return 0.0

    # Simple heuristic: more dependents + higher importance = higher cascading score.
    # In a full system, look up each dependent's actual importance from infrastructure.csv.
    base = min(len(dependents) * 3, 10)
    return float(base)


def build_cascading_explanation(site: Dict[str, Any], nearby_critical_names: List[str]) -> str:
    """
    The auto-generated 'Bridge A -> Road -> Hospital B' style sentence that
    PROJECT_REQUIREMENTS_STATUS.md item 6 flagged as missing -- previously
    only a `cascading_impact` NUMBER existed, with no explanation of WHICH
    facilities that number was actually about.

    This is intentionally honest about being a proximity-based estimate:
    it names the real nearby critical facilities (from infrastructure.csv
    via gis_service.find_nearby_critical_facilities), not a fabricated
    dependency graph -- "may disrupt access to" rather than a certainty.
    """
    site_name = site.get("site_id", "This site")
    asset_type = (site.get("asset_type") or "infrastructure").replace("_", " ")

    if not nearby_critical_names:
        return (
            f"No critical facilities (hospitals, schools, fire/police stations) were found "
            f"within the search radius of {site_name}, so no cascading dependency is asserted."
        )

    cascading_score = site.get("cascading_impact", 0)
    names = nearby_critical_names[:4]
    names_text = ", ".join(names[:-1]) + (" and " + names[-1] if len(names) > 1 else names[0])

    if cascading_score >= 5:
        severity_phrase = "is likely to disrupt emergency access to"
    elif cascading_score >= 2:
        severity_phrase = "may reduce accessibility to"
    else:
        severity_phrase = "is near, but unlikely to significantly affect access to,"

    return (
        f"{site_name} ({asset_type}) {severity_phrase} nearby critical facilit"
        f"{'ies' if len(names) > 1 else 'y'}: {names_text}. This proximity-based estimate "
        f"drives the cascading_impact score of {cascading_score}/10 -- verify the actual "
        f"road/access dependency on site."
    )


def build_explanation(site: Dict[str, Any], priority_result: Dict[str, Any]) -> str:
    """Generates the 'WHY CRITICAL?' style explanation shown in the demo screen."""
    level = priority_result["priority_level"]
    top_factors = sorted(priority_result["breakdown"].items(), key=lambda kv: -kv[1])[:3]
    factor_text = ", ".join(f"{k.replace('_', ' ')}" for k, v in top_factors)
    reasons = f"{level} priority driven mainly by: {factor_text}."
    if site.get("cascading_impact", 0) >= 5:
        reasons += " This site is a critical dependency for other infrastructure."
    return reasons
