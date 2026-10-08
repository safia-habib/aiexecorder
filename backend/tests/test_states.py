"""Tests for /api/states endpoints — Qdrant is mocked, no running cluster needed."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_mock_qdrant(records=None):
    m = MagicMock()
    m.scroll.return_value = (records or [], None)
    return m


@pytest.fixture
def api(monkeypatch):
    mock_qdrant = _make_mock_qdrant()
    with patch("routers.states.get_client", return_value=mock_qdrant):
        from main import app
        yield TestClient(app), mock_qdrant


def test_list_states_always_returns_50(api):
    client, _ = api
    resp = client.get("/api/states")
    assert resp.status_code == 200
    assert len(resp.json()["states"]) == 50


def test_states_have_required_fields(api):
    client, _ = api
    for s in client.get("/api/states").json()["states"]:
        assert {"state", "state_code", "has_eo"}.issubset(s.keys())


def test_empty_qdrant_all_greyed(api):
    client, _ = api
    states = client.get("/api/states").json()["states"]
    assert all(not s["has_eo"] for s in states)
    assert all(s["eo_name"] is None for s in states)


def test_unknown_state_code_returns_404(api):
    client, _ = api
    resp = client.get("/api/states/ZZ/eo")
    assert resp.status_code == 404


def test_known_state_with_no_eo_returns_200_not_404(api):
    client, _ = api
    resp = client.get("/api/states/CA/eo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_eo"] is False
    assert "message" in data


def test_known_state_with_eo_returns_all_fields():
    fake_payload = {
        "state_code": "CA",
        "chunk_type": "full_record",
        "eo_name": "EO N-12-23",
        "date_issued": "2023-09-06",
        "governor": "Gavin Newsom",
        "main_topics": "AI governance",
        "top_items": "Model explainability",
        "dynatrace_features": "APM",
        "bindplane_features": "Log routing",
        "arize_features": "Drift detection",
    }
    fake_record = MagicMock()
    fake_record.payload = fake_payload
    mock_qdrant = _make_mock_qdrant(records=[fake_record])

    with patch("routers.states.get_client", return_value=mock_qdrant):
        from main import app
        client = TestClient(app)
        resp = client.get("/api/states/CA/eo")

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_eo"] is True
    assert data["eo_name"] == "EO N-12-23"
    assert "dynatrace_features" in data
    assert "bindplane_features" in data
    assert "arize_features" in data
