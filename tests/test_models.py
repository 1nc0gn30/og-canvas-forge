"""Tests for og-canvas-forge domain models, dimensions, themes, and configuration."""

from pathlib import Path
import pytest

from og_canvas_forge.models import (
    AuthorSpec,
    BadgeSpec,
    CardDimension,
    CardLayout,
    CardTheme,
    GeneratedCard,
    OGCardConfig,
    TemplatePreset,
)


def test_card_dimension_presets():
    """Verify built-in dimension presets and properties."""
    og = CardDimension.STANDARD_OG
    assert og.width == 1200
    assert og.height == 630
    assert round(og.aspect_ratio, 2) == 1.90 or round(og.aspect_ratio, 2) == 1.91
    assert og.resolution == (1200, 630)
    assert og.to_tuple() == (1200, 630)

    square = CardDimension.SQUARE
    assert square.width == 1080
    assert square.height == 1080
    assert square.aspect_ratio == 1.0


def test_card_dimension_from_value():
    """Verify parsing dimensions from various input formats."""
    # From tuple
    d1 = CardDimension.from_value((800, 400))
    assert d1.width == 800 and d1.height == 400

    # From string preset
    d2 = CardDimension.from_value("square")
    assert d2.width == 1080 and d2.height == 1080

    # From 'WxH' string
    d3 = CardDimension.from_value("1600x900")
    assert d3.width == 1600 and d3.height == 900

    # From dict
    d4 = CardDimension.from_value({"width": 600, "height": 315, "name": "mini"})
    assert d4.width == 600 and d4.height == 315

    # From CardDimension instance
    d5 = CardDimension.from_value(d1)
    assert d5 == d1


def test_card_layout_from_str():
    """Verify CardLayout string conversion and fallbacks."""
    assert CardLayout.from_str("centered") == CardLayout.CENTERED
    assert CardLayout.from_str("DEV_CODE") == CardLayout.DEV_CODE
    assert CardLayout.from_str("dev-code") == CardLayout.DEV_CODE
    assert CardLayout.from_str("unknown-archetype") == CardLayout.DEFAULT


def test_card_theme_to_and_from_dict(sample_theme: CardTheme):
    """Verify theme dictionary roundtrip serialization."""
    d = sample_theme.to_dict()
    assert d["id"] == "test_theme"
    assert d["accent"] == "#00ffcc"
    assert d["is_dark"] is True

    restored = CardTheme.from_dict(d)
    assert restored.id == sample_theme.id
    assert restored.accent == sample_theme.accent
    assert restored.bg_start == sample_theme.bg_start


def test_og_card_config_normalization():
    """Verify OGCardConfig normalizes string author, badge, layout, dimensions in __post_init__."""
    cfg = OGCardConfig(
        title="Normalized Title",
        author="Jane Doe",
        badge="VIP",
        layout="minimal",
        dimensions="1200x630",
    )
    assert isinstance(cfg.author, AuthorSpec)
    assert cfg.author.name == "Jane Doe"
    assert isinstance(cfg.badge, BadgeSpec)
    assert cfg.badge.text == "VIP"
    assert cfg.layout == CardLayout.MINIMAL
    assert isinstance(cfg.dimensions, CardDimension)
    assert cfg.dimensions.width == 1200


def test_generated_card_saving(sample_config: OGCardConfig, temp_workspace: Path):
    """Verify GeneratedCard file export methods."""
    svg_mock = '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"></svg>'
    meta_mock = '<meta property="og:title" content="Test">'
    
    card = GeneratedCard(
        svg=svg_mock,
        html_meta=meta_mock,
        width=1200,
        height=630,
        title="Test Card",
        config=sample_config,
    )

    svg_file = temp_workspace / "card.svg"
    meta_file = temp_workspace / "tags.html"

    card.save_svg(svg_file)
    card.save_meta(meta_file)

    assert svg_file.is_file()
    assert svg_file.read_text(encoding="utf-8") == svg_mock
    assert meta_file.is_file()
    assert meta_file.read_text(encoding="utf-8") == meta_mock


def test_template_preset_model(sample_config: OGCardConfig):
    """Verify TemplatePreset container model."""
    preset = TemplatePreset(
        id="sample_preset",
        name="Sample Template",
        category="general",
        description="A great template for tests.",
        config=sample_config,
    )
    assert preset.id == "sample_preset"
    assert preset.config.title == sample_config.title
