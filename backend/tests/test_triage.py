"""Tests for recommendation/triage.py -- classification + cascading explanations."""
from recommendation.triage import classify, build_cascading_explanation, build_explanation


def test_classify_critical():
    assert classify(90) == "CRITICAL"


def test_classify_low():
    assert classify(5) == "LOW"


def test_cascading_explanation_names_real_facilities():
    site = {"site_id": "Bridge A", "asset_type": "major_bridge", "cascading_impact": 7}
    text = build_cascading_explanation(site, ["City General Hospital", "Government School"])
    assert "City General Hospital" in text
    assert "Bridge A" in text


def test_cascading_explanation_no_facilities():
    site = {"site_id": "Minor Road", "asset_type": "minor_road", "cascading_impact": 0}
    text = build_cascading_explanation(site, [])
    assert "No critical facilities" in text


def test_cascading_explanation_severity_language_scales_with_score():
    high = {"site_id": "X", "asset_type": "bridge", "cascading_impact": 8}
    low = {"site_id": "X", "asset_type": "bridge", "cascading_impact": 1}
    high_text = build_cascading_explanation(high, ["Hospital A"])
    low_text = build_cascading_explanation(low, ["Hospital A"])
    assert "disrupt" in high_text
    assert "unlikely" in low_text


def test_build_explanation_mentions_priority_level():
    priority_result = {
        "priority_level": "CRITICAL",
        "breakdown": {"damage_severity": 22, "population_impact": 14, "infrastructure_importance": 15},
    }
    site = {"cascading_impact": 6}
    text = build_explanation(site, priority_result)
    assert "CRITICAL" in text
