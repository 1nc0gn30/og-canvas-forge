"""Tests for pure-Python PNG binary generation in og-canvas-forge."""

import struct
import zlib
from og_canvas_forge.card_generator import generate_card_image, export_png
from og_canvas_forge.models import OGCardConfig


def test_png_export_signature_and_chunks():
    config = OGCardConfig(
        title="Test Social Card",
        subtitle="Pure Python PNG Engine",
        theme="aurora",
        dimensions="1200x630",
    )

    png_bytes = generate_card_image(config, format="png")
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 100

    # Verify PNG 8-byte magic signature
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    # Verify IHDR chunk
    assert png_bytes[12:16] == b"IHDR"
    width, height, bit_depth, color_type = struct.unpack(">IIBB", png_bytes[16:26])
    assert width == 1200
    assert height == 630
    assert bit_depth == 8
    assert color_type == 2  # RGB

    # Verify IDAT chunk exists
    assert b"IDAT" in png_bytes

    # Verify IEND chunk exists at end
    assert png_bytes[-12:-8] == b"\x00\x00\x00\x00"
    assert png_bytes[-8:-4] == b"IEND"


def test_export_png_alias():
    config = OGCardConfig(
        title="Minimal Card",
        theme="matrix",
        dimensions="1080x1080",
    )
    png_data = export_png(config)
    assert png_data[:8] == b"\x89PNG\r\n\x1a\n"
