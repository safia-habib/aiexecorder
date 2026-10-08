"""Tests for POST /api/ask — retrieve and generate are mocked."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app

_client = TestClient(app)


def test_unknown_state_returns_400():
    resp = _client.post("/api/ask", json={"state_code": "ZZ", "question": "test"})
    assert resp.status_code == 400
    assert "Unknown state code" in resp.json()["detail"]


def test_state_with_no_eo_emits_done_event():
    with patch("routers.ask.retrieve", return_value=[]):
        resp = _client.post(
            "/api/ask", json={"state_code": "CA", "question": "What are the requirements?"}
        )
    assert resp.status_code == 200
    assert "event: done" in resp.text
    assert "No executive order data" in resp.text


def test_state_with_eo_streams_tokens_then_done():
    fake_tokens = ["Dynatrace", " helps", " with", " observability."]
    with patch("routers.ask.retrieve", return_value=["Some context about the CA EO."]):
        with patch("routers.ask.generate_stream", return_value=iter(fake_tokens)):
            resp = _client.post(
                "/api/ask",
                json={"state_code": "CA", "question": "How does Dynatrace help?"},
            )
    assert resp.status_code == 200
    assert "event: token" in resp.text
    assert "event: done" in resp.text


def test_done_event_contains_full_answer():
    import json

    fake_tokens = ["Hello", " world"]
    with patch("routers.ask.retrieve", return_value=["context"]):
        with patch("routers.ask.generate_stream", return_value=iter(fake_tokens)):
            resp = _client.post(
                "/api/ask", json={"state_code": "TX", "question": "Tell me about Texas EO."}
            )

    # Parse the last SSE event
    done_lines = [l for l in resp.text.splitlines() if l.startswith("data:") and "full_answer" in l]
    assert done_lines, "Expected a 'done' data line with full_answer"
    payload = json.loads(done_lines[-1].removeprefix("data: "))
    assert payload["full_answer"] == "Hello world"
