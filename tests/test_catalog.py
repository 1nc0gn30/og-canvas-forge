"""Tests for preconfigured templates catalog and template card generation."""

import pytest

from og_canvas_forge.catalog import (
    generate_card,
    generate_from_template,
    get_all_templates,
    get_template,
    list_templates,
)
from og_canvas_forge.models import GeneratedCard, TemplatePreset


def test_list_and_get_templates():
    """Verify catalog lists all templates and retrieval by ID."""
    templates = list_templates()
    assert len(templates) >= 8

    # Get specific template
    tmpl_id = templates[0].id if hasattr(templates[0], "id") else str(templates[0])
    tmpl = get_template(tmpl_id)
    assert isinstance(tmpl, TemplatePreset)
    assert tmpl.id == tmpl_id
    assert tmpl.config is not None


def test_all_catalog_presets_render_svg():
    """Ensure every built-in template preset renders valid SVG without errors."""
    all_templates = list_templates()
    assert len(all_templates) >= 8

    for tmpl in all_templates:
        card = generate_from_template(tmpl.id)
        assert isinstance(card, GeneratedCard)
        assert card.width > 0
        assert card.height > 0
        assert "<svg" in card.svg
        assert "</svg>" in card.svg


def test_generate_from_template_with_overrides():
    """Verify generating a card from a template with custom title and author overrides."""
    card = generate_from_template(
        "tech_blog",
        overrides={
            "title": "Custom Overridden Title for Testing",
            "author": "Override Author",
        },
    )
    assert "Custom Overridden Title for Testing" in card.svg
    assert "Override Author" in card.svg

    # Also test generate_card shortcut
    card2 = generate_card(
        "tech_blog",
        title="Shortcut Overridden Title",
    )
    assert "Shortcut Overridden Title" in card2.svg
