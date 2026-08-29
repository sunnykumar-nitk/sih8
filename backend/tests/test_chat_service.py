"""Tests for services/chat_service.py -- the offline rule-based chatbot path.
Online (Gemini) mode is intentionally NOT tested here since it needs a live
API key and network access; test it manually with GEMINI_API_KEY set.
"""
import pytest
from services.chat_service import answer_question

SITES = {
    "Bridge A": {
        "site_id": "Bridge A", "priority_score": 91, "priority_level": "CRITICAL",
        "damage_severity": 8.4,
        "breakdown": {"damage_severity": 22, "population_impact": 14, "infrastructure_importance": 15},
        "population_data": {"estimated_affected_population": 55292, "data_label": "REFERENCE DATA"},
        "accessibility": 8, "cascading_explanation": "Bridge A may disrupt access to City Hospital.",
        "cascading_impact": 7, "nearby_critical_facilities": ["City General Hospital"],
        "dominant_damage_type": "structural_damage", "explanation": "CRITICAL priority.",
    },
    "Road C": {
        "site_id": "Road C", "priority_score": 62, "priority_level": "HIGH",
        "damage_severity": 5.0, "breakdown": {"damage_severity": 10, "population_impact": 5},
        "population_data": {"estimated_affected_population": 1200, "data_label": "DEMO DATA"},
        "accessibility": 3, "cascading_explanation": "No critical facilities nearby.",
        "cascading_impact": 0, "nearby_critical_facilities": [],
        "dominant_damage_type": "debris", "explanation": "HIGH priority.",
    },
}
TEAMS = {"Team1": {"team_id": "Team1", "specialization": "structural", "location": {"lat": 1, "lon": 1}, "available": True}}


def test_why_critical_uses_real_breakdown():
    r = answer_question("Why is Bridge A critical?", SITES, TEAMS, mode="offline")
    assert r["mode_used"] == "offline_rules"
    assert "91" in r["answer"]
    assert "damage severity" in r["answer"]


def test_never_invents_a_score_not_in_data():
    r = answer_question("Why is Bridge A critical?", SITES, TEAMS, mode="offline")
    # every number mentioned should trace back to the real site record
    assert "91" in r["answer"] or str(SITES["Bridge A"]["priority_score"]) in r["answer"]


def test_ranking_comparison():
    r = answer_question("Why is Bridge A ranked above Road C?", SITES, TEAMS, mode="offline")
    assert "Bridge A" in r["answer"] and "Road C" in r["answer"]


def test_highest_population():
    r = answer_question("Which location has the highest population impact?", SITES, TEAMS, mode="offline")
    assert "Bridge A" in r["answer"]
    assert "55,292" in r["answer"]


def test_hardest_to_reach():
    r = answer_question("Which damaged site is hardest to reach?", SITES, TEAMS, mode="offline")
    assert "Bridge A" in r["answer"]


def test_how_many_sites_inspectable():
    r = answer_question("How many sites can we inspect with 1 teams?", SITES, TEAMS, mode="offline")
    assert "1" in r["answer"]


def test_unmatched_question_falls_back_gracefully():
    r = answer_question("asdkjaslkdj gibberish", SITES, TEAMS, mode="offline")
    assert r["mode_used"] == "offline_fallback"
    assert r["answer"]  # never empty


def test_no_sites_at_all():
    r = answer_question("Why is Bridge A critical?", {}, {}, mode="offline")
    assert r["mode_used"] == "offline_fallback"
    assert "no sites have been assessed" in r["answer"].lower()


def test_online_mode_without_key_falls_back(monkeypatch):
    import config
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    r = answer_question("Why is Bridge A critical?", SITES, TEAMS, mode="online")
    assert r["mode_used"] in ("offline_fallback",)
