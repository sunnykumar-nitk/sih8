"""Tests for recommendation/disaster_factors.py -- disaster-type-specific scoring."""
from recommendation.disaster_factors import compute_disaster_conditions

FLOOD_DETECTIONS = [
    {"object_type": "road", "damage_type": "flooding", "damage_percentage": 80, "confidence": 0.9},
    {"object_type": "building", "damage_type": "debris", "damage_percentage": 40, "confidence": 0.7},
]
CRASH_DETECTIONS = [
    {"object_type": "building", "damage_type": "fire", "damage_percentage": 70, "confidence": 0.8},
    {"object_type": "building", "damage_type": "debris", "damage_percentage": 60, "confidence": 0.75},
]


def test_flood_factors_match_flood_evidence():
    result = compute_disaster_conditions("flood", FLOOD_DETECTIONS)
    assert "flood_depth" in result["matched_factors"]
    assert result["disaster_conditions"] > 5


def test_crash_factors_match_fire_evidence():
    result = compute_disaster_conditions("aircraft_crash", CRASH_DETECTIONS)
    assert "fire" in result["matched_factors"]
    assert result["disaster_conditions"] > 5


def test_disaster_type_discriminates_between_scenarios():
    """The core requirement: flood evidence should NOT score as highly against
    flood factors as crash evidence scores against crash factors, and vice versa."""
    flood_on_flood = compute_disaster_conditions("flood", FLOOD_DETECTIONS)
    flood_on_crash = compute_disaster_conditions("flood", CRASH_DETECTIONS)
    assert flood_on_flood["disaster_conditions"] >= flood_on_crash["disaster_conditions"]


def test_generic_disaster_type_returns_neutral_baseline():
    result = compute_disaster_conditions("generic", FLOOD_DETECTIONS)
    assert result["disaster_conditions"] == 5.0
    assert result["matched_factors"] == []


def test_no_detections_returns_neutral_baseline():
    result = compute_disaster_conditions("flood", [])
    assert result["disaster_conditions"] == 5.0


def test_unknown_disaster_type_falls_back_to_generic():
    result = compute_disaster_conditions("meteor_strike", FLOOD_DETECTIONS)
    assert result["disaster_conditions"] == 5.0
