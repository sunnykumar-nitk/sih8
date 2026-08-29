"""Tests for recommendation/scoring.py -- the deterministic priority engine."""
from recommendation.scoring import calculate_priority


def test_priority_score_in_range(sample_site):
    result = calculate_priority(sample_site)
    assert 0 <= result["priority_score"] <= 100


def test_priority_level_matches_thresholds(sample_site):
    result = calculate_priority(sample_site)
    assert result["priority_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_high_severity_high_population_is_critical_or_high():
    site = {
        "damage_severity": 10, "population_impact": 10, "infrastructure_importance": 10,
        "accessibility": 10, "disaster_conditions": 10, "critical_facility_impact": 10,
        "cascading_impact": 10, "human_impact": 10, "time_sensitivity": 10,
        "alternative_route_risk": 10, "data_confidence": 1.0,
    }
    result = calculate_priority(site)
    assert result["priority_level"] == "CRITICAL"
    assert result["priority_score"] > 90


def test_all_zero_factors_is_low():
    site = {k: 0 for k in [
        "damage_severity", "population_impact", "infrastructure_importance", "accessibility",
        "disaster_conditions", "critical_facility_impact", "cascading_impact", "human_impact",
        "time_sensitivity", "alternative_route_risk",
    ]}
    site["data_confidence"] = 0
    result = calculate_priority(site)
    assert result["priority_level"] == "LOW"
    assert result["priority_score"] == 0


def test_breakdown_sums_to_total(sample_site):
    result = calculate_priority(sample_site)
    assert abs(sum(result["breakdown"].values()) - result["priority_score"]) < 0.5


def test_severity_moderate_but_huge_population_can_still_be_high():
    """Priority != severity -- a moderately-damaged but critical, hard-to-reach,
    high-population site should still score HIGH/CRITICAL even with only
    moderate damage_severity."""
    site = {
        "damage_severity": 4, "population_impact": 10, "infrastructure_importance": 10,
        "accessibility": 9, "disaster_conditions": 8, "critical_facility_impact": 10,
        "cascading_impact": 10, "human_impact": 10, "time_sensitivity": 9,
        "alternative_route_risk": 9, "data_confidence": 0.9,
    }
    result = calculate_priority(site)
    assert result["priority_level"] in ("HIGH", "CRITICAL")
