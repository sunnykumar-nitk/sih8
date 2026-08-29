"""Tests for recommendation/team_sizing.py."""
from recommendation.team_sizing import estimate_team_size


def test_severe_damage_adds_structural_engineer():
    result = estimate_team_size(
        damage_type="structural_damage", severity_score=8.5, priority_level="CRITICAL",
        estimated_affected_population=100, accessibility=3,
    )
    assert result["roles"].get("structural_engineers", 0) >= 1


def test_large_population_increases_team_size():
    small = estimate_team_size(
        damage_type="debris", severity_score=3, priority_level="LOW",
        estimated_affected_population=100, accessibility=2,
    )
    large = estimate_team_size(
        damage_type="debris", severity_score=3, priority_level="LOW",
        estimated_affected_population=60000, accessibility=2,
    )
    assert large["total_personnel"] > small["total_personnel"]


def test_hard_to_reach_adds_support_crew():
    easy = estimate_team_size(
        damage_type="debris", severity_score=5, priority_level="MEDIUM",
        estimated_affected_population=1000, accessibility=1,
    )
    hard = estimate_team_size(
        damage_type="debris", severity_score=5, priority_level="MEDIUM",
        estimated_affected_population=1000, accessibility=9,
    )
    assert hard["total_personnel"] > easy["total_personnel"]


def test_total_personnel_equals_sum_of_roles():
    result = estimate_team_size(
        damage_type="fire", severity_score=7, priority_level="HIGH",
        estimated_affected_population=15000, accessibility=6,
    )
    assert result["total_personnel"] == sum(result["roles"].values())
