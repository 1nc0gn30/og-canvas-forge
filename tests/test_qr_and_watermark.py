"""Tests for QR Code Matrix Synthesizer, Barcode, and Watermark Engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from og_canvas_forge.card_generator import generate_card
from og_canvas_forge.cli import main as cli_main
from og_canvas_forge.mcp_server import execute_tool
from og_canvas_forge.models import CardDimension, CardLayout, OGCardConfig
from og_canvas_forge.qr_matrix import (
    generate_qr_matrix,
    render_barcode_svg,
    render_qr_svg,
)
from og_canvas_forge.ui_server import StudioHTTPRequestHandler, StudioServer
from og_canvas_forge.watermark import WatermarkSpec, render_watermark_svg


class TestQRMatrix:
    """Test suite for pure-Python QR Code matrix generation."""

    def test_qr_matrix_version1_dimensions(self) -> None:
        matrix = generate_qr_matrix("https://py.org")
        assert len(matrix) == 21
        assert len(matrix[0]) == 21
        # Check that values are binary 0 or 1
        for row in matrix:
            for val in row:
                assert val in (0, 1)

    def test_qr_matrix_version2_dimensions(self) -> None:
        # Longer string triggering Version 2 (25x25)
        long_text = "https://github.com/1nc0gn30/og-canvas-forge"
        matrix = generate_qr_matrix(long_text)
        assert len(matrix) == 25
        assert len(matrix[0]) == 25

    def test_qr_finder_patterns(self) -> None:
        matrix = generate_qr_matrix("test")
        # Top-left finder: (0,0) is black (1)
        assert matrix[0][0] == 1
        assert matrix[0][6] == 1
        assert matrix[6][0] == 1
        assert matrix[6][6] == 1
        # Center of top-left finder is black (3,3)
        assert matrix[3][3] == 1

    def test_render_qr_svg(self) -> None:
        svg = render_qr_svg("https://example.com", size=150, label="SCAN ME")
        assert "<g class=\"qr-code-badge\">" in svg
        assert "width=\"150\"" in svg
        assert "SCAN ME" in svg
        assert "<rect" in svg

    def test_render_barcode_svg(self) -> None:
        svg = render_barcode_svg("TICKET-99482", width=220, height=45)
        assert "<g class=\"linear-barcode\">" in svg
        assert "TICKET-99482" in svg


class TestWatermarkEngine:
    """Test suite for watermark overlay engine."""

    def test_watermark_spec_parsing(self) -> None:
        spec1 = WatermarkSpec.from_input("DRAFT")
        assert spec1 is not None
        assert spec1.text == "DRAFT"
        assert spec1.style == "subtle"

        spec2 = WatermarkSpec.from_input("CONFIDENTIAL:Project Secret")
        assert spec2 is not None
        assert spec2.text == "Project Secret"
        assert spec2.style == "confidential"

        spec3 = WatermarkSpec.from_input("STAMP:APPROVED")
        assert spec3 is not None
        assert spec3.text == "APPROVED"
        assert spec3.style == "stamp"

        assert WatermarkSpec.from_input(None) is None

    def test_render_watermark_styles(self) -> None:
        styles = ["subtle", "diagonal", "stamp", "confidential", "repeat_grid"]
        for st in styles:
            svg = render_watermark_svg(f"{st}:TestStamp", width=1200, height=630)
            assert f"watermark-" in svg
            assert "TestStamp" in svg


class TestCardWithQRAndWatermark:
    """Test card generation with watermark and QR code integration."""

    def test_generate_card_with_watermark_and_qr(self) -> None:
        cfg = OGCardConfig(
            title="Next Gen Vector Database Release",
            subtitle="Autonomous AI Knowledge Engine",
            watermark="CONFIDENTIAL:INTERNAL ONLY",
            qr_code="https://github.com/example/repo",
            layout=CardLayout.DEV_CODE,
            theme="cyberpunk",
        )
        card = generate_card(cfg)
        assert "<svg" in card.svg
        assert "watermark-confidential" in card.svg
        assert "INTERNAL ONLY" in card.svg
        assert "qr-code-badge" in card.svg


class TestMCPQRAndWatermarkTools:
    """Test MCP tool execution for QR and Watermark tools."""

    def test_mcp_og_render_qr_code(self) -> None:
        res = execute_tool("og_render_qr_code", {"text": "https://mcp.io", "size": 100})
        assert not res.get("isError")
        svg = res["content"][0]["text"]
        assert "<g class=\"qr-code-badge\">" in svg

    def test_mcp_og_render_watermark(self) -> None:
        res = execute_tool("og_render_watermark", {"text": "PREVIEW ONLY", "style": "diagonal"})
        assert not res.get("isError")
        svg = res["content"][0]["text"]
        assert "watermark-diagonal" in svg
        assert "PREVIEW ONLY" in svg


class TestCLIQRCommand:
    """Test CLI subcommand for QR code and card generation."""

    def test_cli_qr_command(self, tmp_path: Path) -> None:
        out_file = tmp_path / "test_qr.svg"
        ret = cli_main(["qr", "https://example.com", "-o", str(out_file), "-s", "100"])
        assert ret == 0
        assert out_file.exists()
        assert "<g class=\"qr-code-badge\">" in out_file.read_text(encoding="utf-8")

    def test_cli_generate_with_watermark_and_qr(self, tmp_path: Path) -> None:
        out_file = tmp_path / "card_with_wm.svg"
        ret = cli_main([
            "generate",
            "-t", "Release 2.0 Live",
            "--watermark", "STAMP:VERIFIED",
            "--qr", "https://myapp.com",
            "-o", str(out_file),
            "--quiet",
        ])
        assert ret == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "watermark-stamp" in content
        assert "qr-code-badge" in content
