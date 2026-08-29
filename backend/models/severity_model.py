"""
Converts raw detections into a single 0-10 severity score per site.
This is a deterministic scoring function, NOT an ML model that "predicts"
severity end-to-end -- keeping detection and decision-making separate
(see architecture note in the project README).
"""
from typing import List, Dict, Any
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Relative weight of each damage type toward severity, per unit of
# damage_percentage. Tune freely.
DAMAGE_TYPE_WEIGHT = {
    "collapse": 1.0,
    "fire": 0.95,
    "flooding": 0.85,
    "structural_damage": 0.8,
    "debris": 0.5,
    "crack": 0.4,
}


def calculate_severity(detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Input: list of detection dicts (see damage_detector.py for shape).
    Output: {
        "severity_score": 0-10,
        "severity_label": "Minor"|"Low"|"Moderate"|"Severe"|"Critical",
        "ai_confidence": 0-1,
        "dominant_damage_type": str
    }
    """
    if not detections:
        return {
            "severity_score": 0.0,
            "severity_label": "Minor",
            "ai_confidence": 0.0,
            "dominant_damage_type": None,
        }

    weighted_scores = []
    confidences = []
    for d in detections:
        pct = d.get("damage_percentage") or 0
        weight = DAMAGE_TYPE_WEIGHT.get(d.get("damage_type"), 0.5)
        weighted_scores.append((pct / 100.0) * weight * 10)  # scale to 0-10
        confidences.append(d.get("confidence", 0.5))

    severity_score = round(max(weighted_scores), 2)  # worst detected damage drives severity
    ai_confidence = round(sum(confidences) / len(confidences), 2)

    dominant = max(detections, key=lambda d: d.get("damage_percentage") or 0)

    label = "Minor"
    for name, threshold in sorted(config.SEVERITY_THRESHOLDS.items(), key=lambda kv: -kv[1]):
        if severity_score >= threshold:
            label = name
            break

    return {
        "severity_score": severity_score,
        "severity_label": label,
        "ai_confidence": ai_confidence,
        "dominant_damage_type": dominant.get("damage_type"),
    }
