"""
AI Q&A / disaster assistant chatbot -- retrieval-then-explain, never
invent-a-number.

This was PROJECT_REQUIREMENTS_STATUS.md's single biggest missing feature
("no /api/chat endpoint exists"). Two modes, matching what you asked for
("build offline and online both bot i will decide later"):

  OFFLINE (default, $0, no key): pattern-matches the question against the
  example questions from the SIH spec ("why is X critical", "which team
  for Y", etc.) and answers using template text built ONLY from real
  numbers already sitting in SITE_STORE / TEAM_STORE. Always available.

  ONLINE (optional): if GEMINI_API_KEY is set, free-form questions that
  don't match a rule are sent to Gemini with the SAME structured site data
  locked into the prompt and an explicit instruction to never invent a
  number that isn't in that data. Uses Python's stdlib urllib -- no extra
  dependency (`requests`/`google-generativeai`) needed.

Both paths return the same shape:
    {"answer": str, "supporting_factors": [...], "data_sources": [...],
     "confidence_note": str, "mode_used": "offline_rules"|"online_llm"|"offline_fallback"}
"""
from __future__ import annotations

import json
import re
import sys
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from recommendation.team_allocation import allocate_teams


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------

def _fmt_pop(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "an unknown number of"


def _site_summary_line(site: Dict[str, Any]) -> str:
    return (
        f"{site.get('site_id')}: priority {site.get('priority_score')}/100 "
        f"({site.get('priority_level')}), severity {site.get('damage_severity')}/10"
    )


def _find_site(sites: Dict[str, Dict[str, Any]], name_fragment: str) -> Optional[Dict[str, Any]]:
    """Case-insensitive, substring match -- questions rarely use the exact site_id casing."""
    name_fragment = name_fragment.strip().lower()
    if not name_fragment:
        return None
    # exact match first
    for site_id, site in sites.items():
        if site_id.lower() == name_fragment:
            return site
    # substring match
    for site_id, site in sites.items():
        if name_fragment in site_id.lower() or site_id.lower() in name_fragment:
            return site
    return None


# ---------------------------------------------------------------------------
# Rule-based (offline) question handlers
# ---------------------------------------------------------------------------
# Each handler: (compiled_regex, function(match, sites, teams) -> answer_dict | None)
# Return None if the pattern matched syntactically but there's no data to
# answer with -- the caller falls through to the next rule / online / fallback.

def _rule_why_critical(m, sites, teams):
    site = _find_site(sites, m.group(1))
    if not site:
        return None
    breakdown = site.get("breakdown", {})
    top = sorted(breakdown.items(), key=lambda kv: -kv[1])[:3]
    top_text = ", ".join(f"{k.replace('_', ' ')} ({v} pts)" for k, v in top)
    answer = (
        f"{site.get('site_id')} is {site.get('priority_level')} priority "
        f"({site.get('priority_score')}/100). The largest contributors are: {top_text}. "
    )
    if site.get("cascading_explanation"):
        answer += site["cascading_explanation"]
    return {
        "answer": answer,
        "supporting_factors": [k for k, v in top],
        "data_sources": [f"priority breakdown for {site.get('site_id')}"],
    }


def _rule_compare_ranking(m, sites, teams):
    site_a = _find_site(sites, m.group(1))
    site_b = _find_site(sites, m.group(2))
    if not site_a or not site_b:
        return None
    diff = round((site_a.get("priority_score", 0) - site_b.get("priority_score", 0)), 2)
    winner, loser = (site_a, site_b) if diff >= 0 else (site_b, site_a)
    winner_top = sorted(winner.get("breakdown", {}).items(), key=lambda kv: -kv[1])[:2]
    winner_top_text = ", ".join(k.replace("_", " ") for k, v in winner_top)
    answer = (
        f"{winner.get('site_id')} ({winner.get('priority_score')}/100) ranks above "
        f"{loser.get('site_id')} ({loser.get('priority_score')}/100) mainly because of "
        f"{winner_top_text}."
    )
    return {
        "answer": answer,
        "supporting_factors": [k for k, v in winner_top],
        "data_sources": [f"priority breakdown for {site_a.get('site_id')} and {site_b.get('site_id')}"],
    }


def _rule_highest_population(m, sites, teams):
    if not sites:
        return None
    ranked = sorted(
        sites.values(),
        key=lambda s: s.get("population_data", {}).get("estimated_affected_population", 0),
        reverse=True,
    )
    top = ranked[0]
    pop = top.get("population_data", {}).get("estimated_affected_population", 0)
    label = top.get("population_data", {}).get("data_label", "")
    answer = (
        f"{top.get('site_id')} has the highest estimated population impact: "
        f"~{_fmt_pop(pop)} people ({label})."
    )
    return {
        "answer": answer,
        "supporting_factors": ["population_impact"],
        "data_sources": [f"population_data for {top.get('site_id')}"],
    }


def _rule_hardest_to_reach(m, sites, teams):
    if not sites:
        return None
    # accessibility convention in this codebase: HIGHER = HARDER to reach
    ranked = sorted(sites.values(), key=lambda s: s.get("accessibility", 0), reverse=True)
    top = ranked[0]
    answer = (
        f"{top.get('site_id')} is the hardest to reach (accessibility difficulty "
        f"{top.get('accessibility')}/10, where higher = harder)."
    )
    return {
        "answer": answer,
        "supporting_factors": ["accessibility"],
        "data_sources": [f"accessibility score for {top.get('site_id')}"],
    }


def _rule_which_team_first(m, sites, teams):
    team_frag = m.group(1).strip()
    if not sites or not teams:
        return None
    assignments = allocate_teams(list(sites.values()), list(teams.values()))
    for a in assignments:
        if team_frag.lower() in str(a.get("team_id", "")).lower():
            return {
                "answer": (
                    f"Team {a.get('team_id')} should go to {a.get('site_id')} first "
                    f"(priority {a.get('priority_score', 'N/A')})."
                ),
                "supporting_factors": ["priority_score", "team capability", "distance"],
                "data_sources": ["team allocation result"],
            }
    return None


def _rule_structural_team_site(m, sites, teams):
    if not sites:
        return None
    candidates = [
        s for s in sites.values()
        if s.get("dominant_damage_type") in ("structural_damage", "collapse", "crack")
    ]
    if not candidates:
        return None
    top = max(candidates, key=lambda s: s.get("priority_score", 0))
    answer = (
        f"{top.get('site_id')} should receive the structural team -- dominant damage is "
        f"{top.get('dominant_damage_type')}, priority {top.get('priority_score')}/100."
    )
    return {
        "answer": answer,
        "supporting_factors": ["dominant_damage_type", "priority_score"],
        "data_sources": [f"detections for {top.get('site_id')}"],
    }


def _rule_how_many_inspectable(m, sites, teams):
    n = int(m.group(1))
    if not sites:
        return None
    ranked = sorted(sites.values(), key=lambda s: -s.get("priority_score", 0))
    top_n = ranked[:n]
    names = ", ".join(s.get("site_id", "?") for s in top_n)
    answer = (
        f"With {n} team(s), you can cover the top {len(top_n)} priority site(s): {names}. "
        f"{max(0, len(ranked) - n)} lower-priority site(s) would wait."
    )
    return {
        "answer": answer,
        "supporting_factors": ["priority_score"],
        "data_sources": ["priority queue"],
    }


def _rule_affects_hospital(m, sites, teams):
    if not sites:
        return None
    candidates = [
        s for s in sites.values()
        if any("hospital" in n.lower() for n in s.get("nearby_critical_facilities", []))
    ]
    if not candidates:
        return {
            "answer": "No currently assessed site lists a hospital among its nearby critical facilities.",
            "supporting_factors": [],
            "data_sources": ["nearby_critical_facilities for all sites"],
        }
    names = ", ".join(s.get("site_id", "?") for s in candidates)
    return {
        "answer": f"These sites are near a hospital and could affect its access: {names}.",
        "supporting_factors": ["nearby_critical_facilities", "cascading_impact"],
        "data_sources": ["nearby_critical_facilities for all sites"],
    }


def _rule_what_if_blocked(m, sites, teams):
    site = _find_site(sites, m.group(1))
    if not site:
        return None
    explanation = site.get("cascading_explanation", "No cascading dependency data available.")
    return {
        "answer": (
            f"If {site.get('site_id')} is closed/blocked: {explanation} "
            f"(cascading_impact score: {site.get('cascading_impact')}/10). "
            f"Use POST /api/route with blocked=true for an actual travel-time delta."
        ),
        "supporting_factors": ["cascading_impact"],
        "data_sources": [f"cascading_explanation for {site.get('site_id')}"],
    }


_RULES = [
    # More specific "ranked above" comparison must be checked BEFORE the
    # generic "why is X critical" pattern, since both start with "why is".
    (re.compile(r"why is\s+(.+?)\s+ranked above\s+(.+?)\??$", re.I), _rule_compare_ranking),
    (re.compile(r"why is[' ]s?\s*(.+?)\s+(?:critical|priority|the highest)", re.I), _rule_why_critical),
    (re.compile(r"(?:highest|largest|most)\s+population", re.I), _rule_highest_population),
    (re.compile(r"hardest to reach", re.I), _rule_hardest_to_reach),
    (re.compile(r"which site should team\s+(\S+)", re.I), _rule_which_team_first),
    (re.compile(r"structural team", re.I), _rule_structural_team_site),
    (re.compile(r"how many sites.*?(\d+)\s+teams?", re.I), _rule_how_many_inspectable),
    (re.compile(r"infrastructure affects? a hospital|affects? .*hospital", re.I), _rule_affects_hospital),
    (re.compile(r"what happens if\s+(.+?)\s+(?:is\s+)?(?:closed|blocked)", re.I), _rule_what_if_blocked),
]


def answer_offline(question: str, sites: Dict[str, Any], teams: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Try every rule in order; return the first non-None answer."""
    for pattern, handler in _RULES:
        m = pattern.search(question)
        if m:
            result = handler(m, sites, teams)
            if result:
                result["mode_used"] = "offline_rules"
                result.setdefault(
                    "confidence_note",
                    "Answered by a deterministic rule template using only the calculated site data -- no LLM involved.",
                )
                return result
    return None


def _offline_fallback(question: str, sites: Dict[str, Any], site_id: Optional[str]) -> Dict[str, Any]:
    """Last resort when no rule matches and no online key is configured (or online failed):
    give a useful, honest, data-grounded summary instead of a hard failure."""
    if site_id and site_id in sites:
        site = sites[site_id]
        answer = (
            f"I couldn't match that to a specific question pattern, but here's what's on record for "
            f"{site_id}: {_site_summary_line(site)}. {site.get('explanation', '')}"
        )
        sources = [f"site record for {site_id}"]
    elif sites:
        ranked = sorted(sites.values(), key=lambda s: -s.get("priority_score", 0))[:3]
        lines = "; ".join(_site_summary_line(s) for s in ranked)
        answer = (
            "I couldn't match that to a specific question pattern. Here are the current top "
            f"priority sites: {lines}. Try asking e.g. \"why is <site> critical\" or "
            "\"which site has the highest population impact\"."
        )
        sources = ["priority queue"]
    else:
        answer = (
            "No sites have been assessed yet, so there's no data to answer from. "
            "Run an assessment via /api/upload-batch or /api/assess first."
        )
        sources = []
    return {
        "answer": answer,
        "supporting_factors": [],
        "data_sources": sources,
        "confidence_note": "No matching question pattern and no online mode used -- this is a generic data summary, not a targeted answer.",
        "mode_used": "offline_fallback",
    }


# ---------------------------------------------------------------------------
# Online (Gemini) path -- optional, only used if GEMINI_API_KEY is set
# ---------------------------------------------------------------------------

_GEMINI_SYSTEM_INSTRUCTION = (
    "You are a disaster-response assessment assistant. You will be given a JSON object "
    "called DATA containing the ONLY facts you may use. Answer the user's question using "
    "just these numbers and facts. NEVER invent, estimate, or guess a number that is not "
    "present in DATA. If DATA does not contain what's needed to answer, say so plainly "
    "instead of guessing. Keep answers concise (2-5 sentences). This is decision support "
    "only, not an engineering certification."
)


def _build_context(sites: Dict[str, Any], teams: Dict[str, Any], site_id: Optional[str]) -> Dict[str, Any]:
    """Only send the fields actually needed to answer -- keeps the prompt small
    and avoids leaking internal-only fields (file paths, etc.)."""
    def _slim_site(s: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "site_id": s.get("site_id"),
            "priority_score": s.get("priority_score"),
            "priority_level": s.get("priority_level"),
            "severity_score": s.get("damage_severity"),
            "breakdown": s.get("breakdown"),
            "population_data": s.get("population_data"),
            "team_size": s.get("team_size"),
            "accessibility": s.get("accessibility"),
            "cascading_explanation": s.get("cascading_explanation"),
            "nearby_critical_facilities": s.get("nearby_critical_facilities"),
            "dominant_damage_type": s.get("dominant_damage_type"),
            "disaster_type": s.get("disaster_type"),
        }

    if site_id and site_id in sites:
        relevant_sites = {site_id: _slim_site(sites[site_id])}
    else:
        relevant_sites = {k: _slim_site(v) for k, v in sites.items()}

    return {
        "sites": relevant_sites,
        "teams": {k: {"team_id": v.get("team_id"), "specialization": v.get("specialization")} for k, v in teams.items()},
    }


def answer_online(question: str, sites: Dict[str, Any], teams: Dict[str, Any], site_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Calls Gemini's generateContent REST endpoint directly via urllib (no SDK dependency).
    Returns None on any failure (missing key, network error, bad response) so the caller can
    fall back to the offline path -- online mode is a nice-to-have, never a hard requirement."""
    if not config.GEMINI_API_KEY:
        return None

    data_context = _build_context(sites, teams, site_id)
    prompt = (
        f"{_GEMINI_SYSTEM_INSTRUCTION}\n\nDATA = {json.dumps(data_context, default=str)}\n\n"
        f"Question: {question}"
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return {
            "answer": text.strip(),
            "supporting_factors": list(data_context["sites"].keys()),
            "data_sources": ["Gemini (online), grounded in the same structured site data as offline mode"],
            "confidence_note": "Generated by an LLM constrained to the structured data provided; verify against the raw breakdown for critical decisions.",
            "mode_used": "online_llm",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, TimeoutError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def answer_question(
    question: str,
    sites: Dict[str, Any],
    teams: Dict[str, Any],
    site_id: Optional[str] = None,
    mode: str = "auto",
) -> Dict[str, Any]:
    """
    mode: "offline" (rules only), "online" (Gemini only, if key configured),
          "auto" (default -- rules first, online fallback if a rule doesn't
          match and a key is configured, else the offline summary fallback).
    """
    mode = (mode or config.CHAT_MODE_DEFAULT or "auto").lower()

    if mode == "offline":
        result = answer_offline(question, sites, teams)
        return result or _offline_fallback(question, sites, site_id)

    if mode == "online":
        result = answer_online(question, sites, teams, site_id)
        return result or _offline_fallback(question, sites, site_id)

    # auto
    result = answer_offline(question, sites, teams)
    if result:
        return result
    result = answer_online(question, sites, teams, site_id)
    if result:
        return result
    return _offline_fallback(question, sites, site_id)
