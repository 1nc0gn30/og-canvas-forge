"""Pytest configuration and shared test fixtures for og-canvas-forge."""

import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Generator, Tuple

import pytest

# Ensure src/ is on sys.path for direct pytest invocation without pip install
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from og_canvas_forge.models import (
    AuthorSpec,
    BadgeSpec,
    CardDimension,
    CardLayout,
    CardTheme,
    OGCardConfig,
)
from og_canvas_forge.ui_server import StudioServer, create_server


def get_free_port() -> int:
    """Find a free ephemeral TCP port for local server testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


@pytest.fixture
def sample_author() -> AuthorSpec:
    """Fixture providing a standard test author."""
    return AuthorSpec(
        name="Antigravity Team",
        title="Lead AI Architect",
        handle="@antigravity",
    )


@pytest.fixture
def sample_badge() -> BadgeSpec:
    """Fixture providing a test badge specification."""
    return BadgeSpec(
        text="OPEN SOURCE",
        bg_color="rgba(56, 189, 248, 0.2)",
        text_color="#38bdf8",
    )


@pytest.fixture
def sample_theme() -> CardTheme:
    """Fixture providing a custom dark theme."""
    return CardTheme(
        id="test_theme",
        name="Test Obsidian",
        bg_start="#0a0a0a",
        bg_end="#1a1a1a",
        accent="#00ffcc",
        text_primary="#ffffff",
        text_secondary="#888888",
        badge_bg="rgba(0, 255, 204, 0.15)",
        badge_text="#00ffcc",
        border_color="rgba(255, 255, 255, 0.1)",
        glow_color="#00ffcc",
        is_dark=True,
    )


@pytest.fixture
def sample_config(sample_author: AuthorSpec, sample_badge: BadgeSpec) -> OGCardConfig:
    """Fixture providing a full card configuration."""
    return OGCardConfig(
        title="Building Next-Gen AI Applications in Pure Python",
        subtitle="Zero external runtime dependencies with high-performance vector graphics.",
        author=sample_author,
        badge=sample_badge,
        category="Python & AI",
        tags=["Python", "SVG", "OpenGraph", "Studio"],
        site_name="github.com/og-canvas-forge",
        theme="aurora",
        layout=CardLayout.DEFAULT,
        dimensions=CardDimension.STANDARD_OG,
        pattern="dot_grid",
        reading_time_min=5,
        date_str="September 2026",
    )


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Provide a clean temporary directory for filesystem operations."""
    with tempfile.TemporaryDirectory(prefix="og_test_") as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def live_server() -> Generator[Tuple[StudioServer, str], None, None]:
    """Start an ephemeral background StudioServer for HTTP API testing."""
    port = get_free_port()
    server = create_server(host="127.0.0.1", port=port)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"

    # Wait for socket to be ready
    ready = False
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                ready = True
                break
        except OSError:
            time.sleep(0.05)

    if not ready:
        server.shutdown()
        server.server_close()
        raise RuntimeError(f"Server failed to bind on port {port}")

    yield server, base_url

    server.shutdown()
    server.server_close()
