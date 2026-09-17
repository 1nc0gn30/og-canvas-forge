"""Tests for Google OG Canvas Studio UI server and REST API endpoints."""

import json
import urllib.request
import urllib.error
from pathlib import Path
import pytest

from og_canvas_forge.ui_server import create_server


def test_server_initialization(temp_workspace: Path):
    """Verify create_server instantiates StudioServer with correct attributes."""
    server = create_server(host="127.0.0.1", port=0, public_dir=temp_workspace)
    assert server.public_dir == temp_workspace.resolve()
    assert server.cards_generated == 0
    assert server.start_time > 0
    server.server_close()


def test_http_get_index(live_server):
    """Verify GET / returns Google OG Canvas Studio HTML page."""
    server, base_url = live_server
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8")
        assert "Google OG Canvas Studio" in body or "OpenGraph" in body


def test_http_get_templates_api(live_server):
    """Verify GET /api/templates returns valid JSON list of templates."""
    server, base_url = live_server
    req = urllib.request.Request(f"{base_url}/api/templates")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "templates" in data
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) >= 1


def test_http_get_themes_api(live_server):
    """Verify GET /api/themes returns valid JSON list of themes."""
    server, base_url = live_server
    req = urllib.request.Request(f"{base_url}/api/themes")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "themes" in data
        assert isinstance(data["themes"], list)
        assert len(data["themes"]) >= 1


def test_http_get_stats_and_diagnostics_api(live_server):
    """Verify GET /api/stats and GET /api/diagnostics endpoints."""
    server, base_url = live_server

    # Stats
    with urllib.request.urlopen(f"{base_url}/api/stats") as resp:
        assert resp.status == 200
        stats = json.loads(resp.read().decode("utf-8"))
        assert stats["status"] == "healthy"
        assert "uptime_seconds" in stats

    # Diagnostics
    with urllib.request.urlopen(f"{base_url}/api/diagnostics") as resp:
        assert resp.status == 200
        diag = json.loads(resp.read().decode("utf-8"))
        assert "platform" in diag
        assert "version" in diag


def test_http_post_generate_api(live_server):
    """Verify POST /api/generate accepts card config and returns SVG payload."""
    server, base_url = live_server
    payload = {
        "title": "REST API Test Card",
        "subtitle": "Generated via HTTP POST endpoint",
        "author": {"name": "Test Runner", "handle": "@test"},
        "theme": "aurora",
        "tags": ["API", "Test"],
    }
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "svg" in data
        assert "<svg" in data["svg"]
        assert "REST API Test Card" in data["svg"]
        assert server.cards_generated >= 1


def test_http_post_meta_api(live_server):
    """Verify POST /api/meta generates HTML meta tags snippet."""
    server, base_url = live_server
    payload = {
        "title": "Meta Tags Endpoint",
        "description": "Generating OpenGraph snippets",
        "site_name": "example.com",
    }
    req = urllib.request.Request(
        f"{base_url}/api/meta",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "html" in data
        assert 'property="og:title"' in data["html"]
        assert "Meta Tags Endpoint" in data["html"]


def test_http_post_batch_api(live_server):
    """Verify POST /api/batch renders multiple cards."""
    server, base_url = live_server
    payload = {
        "cards": [
            {"title": "Batch Card 1", "theme": "aurora"},
            {"title": "Batch Card 2", "theme": "emerald_matrix"},
        ]
    }
    req = urllib.request.Request(
        f"{base_url}/api/batch",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["count"] == 2
        assert len(data["cards"]) == 2
        assert "<svg" in data["cards"][0]["svg"]


def test_http_cors_preflight(live_server):
    """Verify OPTIONS pre-flight requests receive standard CORS headers."""
    server, base_url = live_server
    req = urllib.request.Request(f"{base_url}/api/generate", method="OPTIONS")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 204 or resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_http_error_handling(live_server):
    """Verify 404 for unknown endpoints and 400 for bad JSON."""
    server, base_url = live_server

    # 404
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{base_url}/api/unknown_route")
    assert exc_info.value.code == 404

    # 400 for invalid JSON
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=b"{ invalid json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
