"""Tests for multi-OS command line interface (CLI)."""

from pathlib import Path
import pytest

from og_canvas_forge.cli import main


def test_cli_version(capsys):
    """Verify --version returns version information."""
    ret = main(["--version"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "og-canvas-forge" in captured.out or "0.1.0" in captured.out


def test_cli_templates_list(capsys):
    """Verify `templates` subcommand lists templates."""
    ret = main(["templates", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "tech_blog" in captured.out or "templates" in captured.out


def test_cli_themes_list(capsys):
    """Verify `themes` subcommand lists themes."""
    ret = main(["themes", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "aurora" in captured.out or "themes" in captured.out


def test_cli_generate_card(temp_workspace: Path, capsys):
    """Verify `generate` subcommand creates an SVG file on disk."""
    out_svg = temp_workspace / "cli_card.svg"
    ret = main([
        "generate",
        "--title", "CLI Generated Card",
        "--subtitle", "Automated Testing of Command Line",
        "--author", "CLI Test Runner",
        "--theme", "aurora",
        "--output", str(out_svg),
    ])
    assert ret == 0
    assert out_svg.is_file()
    content = out_svg.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "CLI Generated Card" in content


def test_cli_meta_generation(capsys):
    """Verify `meta` subcommand prints HTML meta tags."""
    ret = main([
        "meta",
        "--title", "Meta CLI Test",
        "--description", "Testing HTML tags generation from terminal",
        "--image", "https://example.com/test.svg",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert 'property="og:title"' in captured.out
    assert "Meta CLI Test" in captured.out


def test_cli_diagnostics(capsys):
    """Verify `diagnostics` subcommand runs and outputs system report."""
    ret = main(["diagnostics", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "platform" in captured.out or "python" in captured.out.lower()
