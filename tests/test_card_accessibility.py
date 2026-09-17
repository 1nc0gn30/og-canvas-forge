"""Unit test suite for Social Card Accessibility & Schema.org Rich Snippet Generator.

Tests WCAG 2.2 contrast validation, relative luminance math, platform readability,
Schema.org JSON-LD generation, CLI integration, MCP tools, and UI server endpoints.
Zero third-party runtime dependencies.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from og_canvas_forge.card_generator import (
    calculate_contrast_ratio,
    calculate_relative_luminance,
    generate_card,
    generate_schema_json_ld,
    validate_card_accessibility,
)
from og_canvas_forge.mcp_server import handle_jsonrpc_request
from og_canvas_forge.models import (
    AuthorSpec,
    CardAccessibilityReport,
    CardDimension,
    CardLayout,
    OGCardConfig,
)


# ============================================================================
# COLOR MATH & LUMINANCE TESTS
# ============================================================================


def test_relative_luminance_extremes() -> None:
    """Test luminance on black and white boundaries."""
    lum_black = calculate_relative_luminance("#000000")
    lum_white = calculate_relative_luminance("#ffffff")
    assert pytest.approx(lum_black, abs=1e-4) == 0.0
    assert pytest.approx(lum_white, abs=1e-4) == 1.0


def test_contrast_ratio_extremes() -> None:
    """Test contrast ratios for pure black/white and identical pairs."""
    max_contrast = calculate_contrast_ratio("#000000", "#ffffff")
    assert pytest.approx(max_contrast, abs=0.01) == 21.0

    identity_contrast = calculate_contrast_ratio("#1a73e8", "#1a73e8")
    assert pytest.approx(identity_contrast, abs=0.01) == 1.0


def test_contrast_ratio_rgb_and_hex_equivalence() -> None:
    """Test contrast ratio handles both tuples and hex strings."""
    ratio_hex = calculate_contrast_ratio("#ffffff", "#000000")
    ratio_rgb = calculate_contrast_ratio((255, 255, 255), (0, 0, 0))
    assert pytest.approx(ratio_hex, abs=1e-3) == ratio_rgb


# ============================================================================
# ACCESSIBILITY AUDIT TESTS
# ============================================================================


def test_validate_card_accessibility_default() -> None:
    """Test auditing default aurora card configuration."""
    cfg = OGCardConfig(
        title="Modern Web Architectures",
        subtitle="Designing scalable micro-frontends with Python and TypeScript",
        author=AuthorSpec(name="Alex Rivera", handle="@arivera"),
        theme="aurora",
    )
    report = validate_card_accessibility(cfg)

    assert isinstance(report, CardAccessibilityReport)
    assert report.score > 0.0
    assert "title" in report.contrast_ratios
    assert "subtitle" in report.contrast_ratios
    assert "badge" in report.contrast_ratios
    assert "author" in report.contrast_ratios

    # Verify WCAG compliance breakdown
    assert "title" in report.wcag_compliance
    title_comp = report.wcag_compliance["title"]
    assert "aa_pass" in title_comp
    assert "aaa_pass" in title_comp

    # Verify platform readability
    assert "twitter" in report.platform_readability
    assert "linkedin" in report.platform_readability
    assert "facebook" in report.platform_readability
    assert "slack" in report.platform_readability

    # Verify serialization
    data = report.to_dict()
    assert "is_compliant" in data
    assert "score" in data
    assert "contrast_ratios" in data
    assert "recommendations" in data


def test_validate_card_accessibility_template_id() -> None:
    """Test auditing directly from built-in template ID."""
    report = validate_card_accessibility("modern-blog")
    assert isinstance(report, CardAccessibilityReport)
    assert report.score >= 50.0
    assert len(report.recommendations) >= 1


def test_generated_card_audit_method() -> None:
    """Test calling audit_accessibility directly on GeneratedCard artifact."""
    card = generate_card(
        OGCardConfig(
            title="Design influenced by Material 3 tokens",
            subtitle="Honest token design and accessibility guidelines",
            theme="dark",
        )
    )
    report = card.audit_accessibility()
    assert isinstance(report, CardAccessibilityReport)
    assert report.is_compliant is True


# ============================================================================
# SCHEMA.ORG RICH SNIPPET GENERATOR TESTS
# ============================================================================


def test_generate_schema_json_ld_article() -> None:
    """Test JSON-LD rich snippet synthesis for articles."""
    cfg = OGCardConfig(
        title="Building Autonomous Agents with Python",
        subtitle="Step-by-step deep dive into agent architectures",
        author=AuthorSpec(name="Dr. Jane Ellis", title="AI Researcher", handle="@jellis"),
        site_name="AI Architecture Journal",
        date_str="2026-09-17",
        tags=["AI", "Python", "Agents"],
        dimensions=CardDimension(1200, 630),
    )
    script_tag = generate_schema_json_ld(
        cfg,
        page_url="https://example.com/blog/autonomous-agents",
        image_url="https://example.com/og/agents.svg",
        as_script_tag=True,
    )
    assert script_tag.startswith('<script type="application/ld+json">')
    assert script_tag.strip().endswith("</script>")

    raw_json = generate_schema_json_ld(
        cfg,
        page_url="https://example.com/blog/autonomous-agents",
        image_url="https://example.com/og/agents.svg",
        as_script_tag=False,
    )
    data = json.loads(raw_json)
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "BlogPosting"
    assert data["headline"] == "Building Autonomous Agents with Python"
    assert data["url"] == "https://example.com/blog/autonomous-agents"
    assert data["image"]["url"] == "https://example.com/og/agents.svg"
    assert data["image"]["width"] == 1200
    assert data["image"]["height"] == 630
    assert data["author"]["name"] == "Dr. Jane Ellis"
    assert data["author"]["jobTitle"] == "AI Researcher"
    assert data["author"]["sameAs"] == "https://x.com/jellis"
    assert data["publisher"]["name"] == "AI Architecture Journal"
    assert data["datePublished"] == "2026-09-17"
    assert "AI, Python, Agents" in data["keywords"]


def test_generate_schema_json_ld_layout_types() -> None:
    """Test schema type auto-detection from card layout."""
    # Podcast
    podcast_cfg = OGCardConfig(
        title="Tech Talks #42",
        layout=CardLayout.PODCAST,
        episode_number="42",
    )
    podcast_data = json.loads(generate_schema_json_ld(podcast_cfg, as_script_tag=False))
    assert podcast_data["@type"] == "PodcastEpisode"
    assert podcast_data["episodeNumber"] == "42"

    # Event
    event_cfg = OGCardConfig(
        title="Global Dev Summit 2026",
        layout=CardLayout.EVENT_TICKET,
        ticket_number="VIP-90210",
        date_str="2026-10-15",
    )
    event_data = json.loads(generate_schema_json_ld(event_cfg, as_script_tag=False))
    assert event_data["@type"] == "Event"
    assert event_data["identifier"] == "VIP-90210"
    assert event_data["startDate"] == "2026-10-15"

    # Dev Code
    code_cfg = OGCardConfig(
        title="Quick Sort in Rust",
        layout=CardLayout.DEV_CODE,
        code_language="rust",
    )
    code_data = json.loads(generate_schema_json_ld(code_cfg, as_script_tag=False))
    assert code_data["@type"] == "TechArticle"
    assert code_data["programmingLanguage"] == "rust"


# ============================================================================
# MCP TOOLS INTEGRATION TESTS
# ============================================================================


def test_mcp_tool_og_audit_accessibility() -> None:
    """Test MCP tool call for og_audit_accessibility."""
    req = {
        "jsonrpc": "2.0",
        "id": "audit-1",
        "method": "tools/call",
        "params": {
            "name": "og_audit_accessibility",
            "arguments": {
                "theme": "cyberpunk",
                "title": "Cyberpunk Card Headline",
            },
        },
    }
    resp = handle_jsonrpc_request(req)
    assert resp["id"] == "audit-1"
    assert "result" in resp
    assert resp["result"]["isError"] is False
    content_text = resp["result"]["content"][0]["text"]
    report_dict = json.loads(content_text)
    assert "is_compliant" in report_dict
    assert "score" in report_dict


def test_mcp_tool_og_generate_schema_ld() -> None:
    """Test MCP tool call for og_generate_schema_ld."""
    req = {
        "jsonrpc": "2.0",
        "id": "schema-1",
        "method": "tools/call",
        "params": {
            "name": "og_generate_schema_ld",
            "arguments": {
                "title": "State of AI 2026",
                "subtitle": "Annual Review",
                "author": "Tech Team",
                "publisher_name": "Tech Corp",
            },
        },
    }
    resp = handle_jsonrpc_request(req)
    assert resp["id"] == "schema-1"
    assert resp["result"]["isError"] is False
    assert "<script type=\"application/ld+json\">" in resp["result"]["content"][0]["text"]


# ============================================================================
# CLI AUDIT & SCHEMA SUBCOMMAND TESTS
# ============================================================================


def test_cli_audit_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI audit command executes cleanly and outputs report."""
    from og_canvas_forge.cli import main

    exit_code = main(["audit", "--theme", "dark", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert "is_compliant" in report
    assert "score" in report


def test_cli_schema_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI schema command outputs valid JSON-LD script."""
    from og_canvas_forge.cli import main

    exit_code = main(["schema", "--title", "CLI Schema Test", "--author", "Tester"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '<script type="application/ld+json">' in captured.out
    assert "CLI Schema Test" in captured.out


def test_cli_generate_with_audit_flag(tmp_path: Any, capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI generate command with --audit flag."""
    from og_canvas_forge.cli import main

    out_file = tmp_path / "card.svg"
    exit_code = main(["generate", "--title", "Audited Card", "--output", str(out_file), "--audit"])
    assert exit_code == 0
    assert out_file.is_file()
    captured = capsys.readouterr()
    assert "WCAG 2.2 Accessibility Report" in captured.err
