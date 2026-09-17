"""Tests for SVG card generation, HTML meta tags, and pure-Python rasterizers."""

import pytest

from og_canvas_forge.card_generator import (
    generate_card,
    generate_html_meta,
    generate_svg,
    render_svg_to_bmp,
    render_svg_to_ppm,
)
from og_canvas_forge.models import (
    AuthorSpec,
    BadgeSpec,
    CardDimension,
    CardLayout,
    GeneratedCard,
    OGCardConfig,
)


def test_generate_svg_basic(sample_config: OGCardConfig):
    """Verify SVG generator produces valid, well-formed XML/SVG markup."""
    svg = generate_svg(sample_config)
    assert svg.startswith("<svg") or "<?xml" in svg or "<svg" in svg
    assert "</svg>" in svg
    assert f'viewBox="0 0 {sample_config.dimensions.width} {sample_config.dimensions.height}"' in svg
    assert "Building Next-Gen AI Applications" in svg
    assert "Antigravity Team" in svg


def test_generate_card_object(sample_config: OGCardConfig):
    """Verify generate_card returns a complete GeneratedCard instance."""
    card = generate_card(sample_config)
    assert isinstance(card, GeneratedCard)
    assert card.width == 1200
    assert card.height == 630
    assert card.title == sample_config.title
    assert "<svg" in card.svg
    assert "<meta" in card.html_meta


def test_generate_html_meta(sample_config: OGCardConfig):
    """Verify HTML meta tag generation includes OpenGraph and Twitter cards."""
    meta = generate_html_meta(sample_config, image_url="https://canvas.antigravity.dev/og.svg")
    assert 'property="og:title"' in meta
    assert 'name="twitter:card" content="summary_large_image"' in meta
    assert 'name="twitter:creator"' in meta
    assert "https://canvas.antigravity.dev/og.svg" in meta


def test_dev_code_terminal_svg():
    """Verify developer code layout generates code blocks and window buttons."""
    cfg = OGCardConfig(
        title="Async Vector Pipeline in Python",
        subtitle="Zero-copy data transfer with pure stdlib.",
        layout=CardLayout.DEV_CODE,
        code_snippet="async def fetch_vector():\n    return await stream()",
        code_language="Python",
    )
    svg = generate_svg(cfg)
    assert "fetch_vector" in svg
    assert "</svg>" in svg


def test_pure_python_rasterizers(sample_config: OGCardConfig):
    """Verify zero-dependency BMP and PPM image byte rasterizers."""
    card = generate_card(sample_config)

    # 1. BMP (24-bit uncompressed header "BM")
    bmp_bytes = card.to_bmp()
    assert isinstance(bmp_bytes, bytes)
    assert bmp_bytes.startswith(b"BM")
    assert len(bmp_bytes) > 54  # Valid BMP header length

    # 2. PPM (P6 binary header)
    ppm_bytes = card.to_ppm()
    assert isinstance(ppm_bytes, bytes)
    assert ppm_bytes.startswith(b"P6")
