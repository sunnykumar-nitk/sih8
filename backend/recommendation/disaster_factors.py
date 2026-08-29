"""
Disaster-specific factor wiring.

Previously (see PROJECT_REQUIREMENTS_STATUS.md item 4) `config.DISASTER_FACTORS`
listed the right signals per disaster type but every disaster type ran
through the exact same weighted-sum, so a flood and an aircraft crash with
similar raw damage percentages scored identically. This module is what
actually changes the `disaster_conditions` factor (0-10, one of the 11
inputs to scoring.calculate_priority) based on which disaster-specific
signals are actually present in the pooled detections for a site -- so a
flood with heavy water coverage AND blocked roads scores its
disaster_conditions higher than a flood with only light water coverage.

Deterministic and rule-based, same spirit as scoring.py: no LLM involved.
"""
from typing import Any, Dict, List

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Which damage_type values (from damage_detector.py) count as evidence for
# which named disaster-specific factor (from config.DISASTER_FACTORS).
_FACTOR_EVIDENCE = {
    # flood
    "flood_depth": ["flooding"],
    "road_blockage": ["flooding", "debris"],
    "bridge_access": ["flooding", "structural_damage"],
    "rainfall_intensity": ["flooding"],
    # earthquake
    "structural_tilt": ["structural_damage", "collapse"],
    "aftershock_risk": ["collapse", "crack"],
    "building_occupancy": ["structural_damage", "collapse"],
    "trapped_person_possibility": ["collapse"],
    # aircraft_crash
    "fire": ["fire"],
    "smoke": ["fire", "debris"],
    "debris_field": ["debris"],
    "secondary_explosion_risk": ["fire"],
}


def compute_disaster_conditions(disaster_type: str, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns:
        {
          "disaster_conditions": 0-10,
          "disaster_type": str,
          "matched_factors": [str, ...],   # which DISASTER_FACTORS actually
                                            # had supporting evidence in the
                                            # detections for THIS disaster type
          "explanation": str
        }

    Sites with no matching evidence still get a baseline of 5 (neutral --
    same default as scoring.calculate_priority's other factors) rather than
    being penalized for a disaster type the detector wasn't told about.
    """
    factor_names = config.DISASTER_FACTORS.get(disaster_type, config.DISASTER_FACTORS["generic"])
    if not factor_names or not detections:
        return {
            "disaster_conditions": 5.0,
            "disaster_type": disaster_type,
            "matched_factors": [],
            "explanation": f"No disaster-specific factors configured for '{disaster_type}'; using neutral baseline."
            if not factor_names else "No detections to evaluate disaster-specific factors against.",
        }

    detected_damage_types = {d.get("damage_type") for d in detections if d.get("damage_type")}
    # Average damage_percentage per damage_type, used to weight how strongly
    # a factor is "matched" rather than treating it as a binary yes/no.
    pct_by_type: Dict[str, List[float]] = {}
    for d in detections:
        dt = d.get("damage_type")
        if dt:
            pct_by_type.setdefault(dt, []).append(d.get("damage_percentage") or 0)
    avg_pct_by_type = {k: sum(v) / len(v) for k, v in pct_by_type.items()}

    matched = []
    factor_scores = []
    for factor in factor_names:
        evidence_types = _FACTOR_EVIDENCE.get(factor, [])
        overlap = detected_damage_types.intersection(evidence_types)
        if overlap:
            matched.append(factor)
            # Strength of this factor = strongest supporting damage_type's avg %.
            strength_pct = max(avg_pct_by_type.get(t, 0) for t in overlap)
            factor_scores.append(strength_pct / 100.0 * 10)  # scale to 0-10

    if not factor_scores:
        score = 4.0  # slightly below neutral: disaster-specific signals were checked for and NOT found
        explanation = (
            f"None of the {disaster_type}-specific factors "
            f"({', '.join(factor_names)}) had supporting evidence in the detected damage types."
        )
    else:
        score = round(sum(factor_scores) / len(factor_scores), 2)
        readable = ", ".join(f.replace("_", " ") for f in matched)
        explanation = (
            f"{disaster_type.replace('_', ' ').title()}-specific factors detected: {readable}."
        )

    return {
        "disaster_conditions": min(10.0, max(0.0, score)),
        "disaster_type": disaster_type,
        "matched_factors": matched,
        "explanation": explanation,
    }
