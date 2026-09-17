"""Tests for typography metrics, text wrapping, and layout coordinate calculations."""

import pytest

from og_canvas_forge.layout_engine import (
    BoundingBox,
    char_width,
    compute_card_layout,
    estimate_text_height,
    estimate_text_width,
    fit_text_to_box,
    truncate_with_ellipsis,
    wrap_text,
)
from og_canvas_forge.models import CardDimension, CardLayout, OGCardConfig


def test_char_width_metrics():
    """Verify relative character width heuristics."""
    w_narrow = char_width("i", font_size=20, font_family="Inter")
    w_wide = char_width("W", font_size=20, font_family="Inter")
    w_cjk = char_width("中", font_size=20, font_family="Inter")
    w_emoji = char_width("🚀", font_size=20, font_family="Inter")

    assert w_narrow < w_wide
    assert w_cjk >= 20.0  # Full width
    assert w_emoji >= 20.0


def test_estimate_text_width_and_height():
    """Verify total text width and bounding box height estimates."""
    width = estimate_text_width("Hello World", font_size=24)
    assert width > 0
    assert estimate_text_width("", font_size=24) == 0.0

    height = estimate_text_height(lines_count=3, font_size=32, line_height_ratio=1.25)
    assert height == 3 * 32 * 1.25
    assert estimate_text_height(lines_count=0, font_size=32) == 0.0


def test_truncate_with_ellipsis():
    """Verify text truncation when exceeding max width."""
    long_text = "This is an extremely long title that must be truncated with ellipsis"
    truncated = truncate_with_ellipsis(long_text, max_width=150, font_size=20)
    assert truncated.endswith("...")
    assert len(truncated) < len(long_text)

    short_text = "Short"
    not_truncated = truncate_with_ellipsis(short_text, max_width=500, font_size=20)
    assert not_truncated == short_text


def test_wrap_text():
    """Verify word-wrapping algorithm honors maximum width."""
    long_paragraph = "OpenGraph social card forge generates production ready vector cards in pure Python."
    lines = wrap_text(long_paragraph, max_width=250, font_size=24)
    
    assert len(lines) >= 2
    # All words should be accounted for
    assert any("OpenGraph" in l for l in lines)


def test_fit_text_to_box():
    """Verify text auto-scaling to fit within bounding box."""
    lines, font_size, total_h = fit_text_to_box(
        text="A Moderately Long Title For Fitting",
        max_width=400,
        max_height=200,
        initial_font_size=64,
        min_font_size=24,
        max_lines=3,
    )
    assert len(lines) >= 1
    assert 24 <= font_size <= 64
    assert total_h > 0


def test_compute_card_layout_archetypes():
    """Verify layout solver produces valid coordinate bounding boxes across archetypes."""
    layouts = [
        CardLayout.DEFAULT,
        CardLayout.CENTERED,
        CardLayout.SPLIT,
        CardLayout.MINIMAL,
        CardLayout.DEV_CODE,
        CardLayout.PODCAST,
        CardLayout.EVENT_TICKET,
    ]

    for lay in layouts:
        cfg = OGCardConfig(
            title="Next Generation Autonomous Framework",
            subtitle="Deep architectural analysis and benchmark results.",
            category="Frameworks",
            tags=["AI", "Python"],
            layout=lay,
            dimensions=CardDimension.STANDARD_OG,
        )

        computed = compute_card_layout(cfg, width=1200, height=630)
        assert computed is not None
        assert len(computed.title_lines) >= 1
        assert computed.title_lines[0].font_size > 0
        assert computed.title_lines[0].x >= 0
        assert computed.title_lines[0].y >= 0
