"""End-to-end API tests using FastAPI's TestClient. Needs fastapi+httpx
installed (both already in requirements.txt / requirements-notebooks.txt).
"""
import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_status_endpoint_reports_demo_mode():
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert "demo_mode" in resp.json()


def test_chat_status_endpoint():
    resp = client.get("/api/chat/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["offline_available"] is True
    assert "online_available" in body


def test_chat_endpoint_no_sites_yet_gives_honest_answer():
    resp = client.post("/api/chat", json={"question": "Why is Bridge Z critical?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert body["mode_used"] in ("offline_fallback", "offline_rules")


def test_assess_endpoint_creates_a_site():
    resp = client.post("/api/assess", json={
        "site_id": "API Test Site",
        "asset_type": "major_bridge",
        "damage_severity": 7,
        "accessibility": 6,
        "location": {"lat": 12.91, "lon": 74.79},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["site_id"] == "API Test Site"
    assert "priority_score" in body
    assert "team_size" in body


def test_sites_endpoint_lists_assessed_sites():
    client.post("/api/assess", json={"site_id": "List Test Site", "damage_severity": 5})
    resp = client.get("/api/sites")
    assert resp.status_code == 200
    ids = [s["site_id"] for s in resp.json()]
    assert "List Test Site" in ids


def test_get_single_site_404_for_missing():
    resp = client.get("/api/sites/does-not-exist")
    assert resp.status_code == 404


def test_chat_can_answer_about_an_assessed_site():
    client.post("/api/assess", json={"site_id": "Chat Test Bridge", "damage_severity": 9, "accessibility": 8})
    resp = client.post("/api/chat", json={"question": "Why is Chat Test Bridge critical?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Chat Test Bridge" in body["answer"]


def test_upload_batch_rejects_empty_file_list():
    resp = client.post("/api/upload-batch", data={"case_name": "Empty Test"}, files=[])
    assert resp.status_code in (400, 422)


def test_teams_endpoint_register_and_list():
    resp = client.post("/api/teams", json={
        "team_id": "API Test Team", "specialization": "general", "available": True,
    })
    assert resp.status_code == 200
    resp = client.get("/api/teams")
    ids = [t["team_id"] for t in resp.json()]
    assert "API Test Team" in ids


def test_priority_queue_is_sorted_descending():
    resp = client.get("/api/priority")
    assert resp.status_code == 200
    scores = [s["priority_score"] for s in resp.json()]
    assert scores == sorted(scores, reverse=True)
