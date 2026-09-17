"""Tests for gradient synthesis, theme palettes, and background pattern generators."""

import pytest

from og_canvas_forge.gradients import (
    GradientStop,
    LinearGradient,
    RadialGradient,
    create_linear_gradient,
    generate_theme_defs,
    get_theme,
    list_themes,
)
from og_canvas_forge.models import CardTheme
from og_canvas_forge.patterns import get_pattern_svg, list_patterns


def test_gradient_stop_to_svg():
    """Verify SVG <stop> tag rendering."""
    stop = GradientStop(offset=0.5, color="#1a73e8", opacity=0.8)
    svg = stop.to_svg()
    assert 'offset="50.0%"' in svg
    assert 'stop-color="#1a73e8"' in svg
    assert 'stop-opacity="0.8"' in svg


def test_linear_gradient_coordinates():
    """Verify linear gradient angle trigonometric mapping."""
    grad_90 = LinearGradient(id="grad_90", angle_deg=90.0)
    x1, y1, x2, y2 = grad_90.calculate_coordinates()
    # At 90 degrees (pointing up/down depending on orientation)
    assert "%" in x1 and "%" in y1

    svg = grad_90.to_svg()
    assert '<linearGradient id="grad_90"' in svg


def test_radial_gradient_svg():
    """Verify radial gradient SVG definition."""
    rad = RadialGradient(
        id="glow",
        cx="70%",
        cy="30%",
        r="40%",
        stops=[GradientStop(0.0, "#38bdf8", 0.5), GradientStop(1.0, "#38bdf8", 0.0)],
    )
    svg = rad.to_svg()
    assert '<radialGradient id="glow"' in svg
    assert 'cx="70%"' in svg
    assert 'cy="30%"' in svg


def test_themes_registry_and_defs():
    """Verify built-in themes and SVG definitions generator."""
    themes = list_themes()
    assert len(themes) >= 8

    aurora = get_theme("aurora")
    assert isinstance(aurora, CardTheme)
    assert aurora.id == "aurora"

    defs_svg = generate_theme_defs(aurora)
    assert "<defs>" in defs_svg
    assert "</defs>" in defs_svg
    assert "linearGradient" in defs_svg


def test_patterns_catalog_and_svg_generation():
    """Verify pattern generators for dot matrix, blueprint, hex grid, etc."""
    patterns = list_patterns()
    assert "dot_grid" in patterns or "dots" in patterns or len(patterns) >= 5

    for pat in ["dot_grid", "blueprint", "hex_grid", "hatching", "circuits", "none"]:
        p_def, p_rect = get_pattern_svg(pat, color="#10b981", opacity=0.1, scale=1.0)
        if pat == "none":
            assert p_def == ""
            assert p_rect == ""
        else:
            assert "<pattern" in p_def
            assert "<rect" in p_rect
