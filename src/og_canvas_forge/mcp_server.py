"""Model Context Protocol (MCP) server for og-canvas-forge over stdio.

Implements full JSON-RPC 2.0 protocol specifications with zero external dependencies.
Exposes tools for card generation, batch processing, template listing, theme discovery,
HTML meta generation, and multi-OS diagnostics, alongside catalog resources and prompt templates.
"""

from __future__ import annotations

import html
import json
import os
import platform
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .compat import get_platform_info, normalize_path
from .models import (
    AuthorSpec,
    BadgeSpec,
    CardDimension,
    CardLayout,
    CardTheme,
    GeneratedCard,
    OGCardConfig,
    TemplatePreset,
)

SERVER_NAME = "og-canvas-forge"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

# ============================================================================
# BUILT-IN THEMES REGISTRY
# ============================================================================

THEMES_CATALOG: Dict[str, CardTheme] = {
    "aurora": CardTheme(
        id="aurora",
        name="Nordic Aurora",
        bg_start="#0b0f19",
        bg_end="#111827",
        accent="#10b981",
        text_primary="#f9fafb",
        text_secondary="#9ca3af",
        badge_bg="rgba(16, 185, 129, 0.18)",
        badge_text="#34d399",
        border_color="rgba(16, 185, 129, 0.25)",
        glow_color="#10b981",
        card_bg="rgba(17, 24, 39, 0.75)",
        is_dark=True,
        gradient_angle=135,
    ),
    "cyberpunk": CardTheme(
        id="cyberpunk",
        name="Cyberpunk Neon",
        bg_start="#090a0f",
        bg_end="#13091f",
        accent="#00f0ff",
        text_primary="#ffffff",
        text_secondary="#e2e8f0",
        badge_bg="rgba(255, 0, 127, 0.22)",
        badge_text="#ff007f",
        border_color="rgba(0, 240, 255, 0.35)",
        glow_color="#ff007f",
        card_bg="rgba(19, 9, 31, 0.8)",
        is_dark=True,
        gradient_angle=145,
    ),
    "dark": CardTheme(
        id="dark",
        name="Modern Slate Dark",
        bg_start="#0f172a",
        bg_end="#1e293b",
        accent="#6366f1",
        text_primary="#f8fafc",
        text_secondary="#94a3b8",
        badge_bg="rgba(99, 102, 241, 0.18)",
        badge_text="#818cf8",
        border_color="rgba(99, 102, 241, 0.25)",
        glow_color="#6366f1",
        card_bg="rgba(30, 41, 59, 0.75)",
        is_dark=True,
        gradient_angle=135,
    ),
    "light": CardTheme(
        id="light",
        name="Clean Minimal Light",
        bg_start="#f8fafc",
        bg_end="#e2e8f0",
        accent="#2563eb",
        text_primary="#0f172a",
        text_secondary="#475569",
        badge_bg="rgba(37, 99, 235, 0.12)",
        badge_text="#2563eb",
        border_color="rgba(37, 99, 235, 0.2)",
        glow_color="#3b82f6",
        card_bg="rgba(255, 255, 255, 0.88)",
        is_dark=False,
        gradient_angle=135,
    ),
    "ocean": CardTheme(
        id="ocean",
        name="Deep Ocean",
        bg_start="#0b192c",
        bg_end="#1e3e62",
        accent="#38bdf8",
        text_primary="#f0fdf4",
        text_secondary="#93c5fd",
        badge_bg="rgba(56, 189, 248, 0.18)",
        badge_text="#38bdf8",
        border_color="rgba(56, 189, 248, 0.25)",
        glow_color="#00d26a",
        card_bg="rgba(30, 62, 98, 0.7)",
        is_dark=True,
        gradient_angle=135,
    ),
    "sunset": CardTheme(
        id="sunset",
        name="Crimson Sunset",
        bg_start="#1e1b4b",
        bg_end="#31103f",
        accent="#f43f5e",
        text_primary="#fff1f2",
        text_secondary="#fda4af",
        badge_bg="rgba(244, 63, 94, 0.2)",
        badge_text="#fb7185",
        border_color="rgba(244, 63, 94, 0.3)",
        glow_color="#f59e0b",
        card_bg="rgba(49, 16, 63, 0.75)",
        is_dark=True,
        gradient_angle=140,
    ),
    "emerald": CardTheme(
        id="emerald",
        name="Forest Emerald",
        bg_start="#022c22",
        bg_end="#064e3b",
        accent="#10b981",
        text_primary="#ecfdf5",
        text_secondary="#a7f3d0",
        badge_bg="rgba(16, 185, 129, 0.2)",
        badge_text="#34d399",
        border_color="rgba(16, 185, 129, 0.3)",
        glow_color="#10b981",
        card_bg="rgba(6, 78, 59, 0.75)",
        is_dark=True,
        gradient_angle=135,
    ),
    "matrix": CardTheme(
        id="matrix",
        name="Terminal Matrix",
        bg_start="#050805",
        bg_end="#0a140a",
        accent="#22c55e",
        text_primary="#4ade80",
        text_secondary="#86efac",
        badge_bg="rgba(34, 197, 94, 0.18)",
        badge_text="#22c55e",
        border_color="rgba(34, 197, 94, 0.35)",
        glow_color="#22c55e",
        card_bg="rgba(10, 20, 10, 0.85)",
        is_dark=True,
        gradient_angle=135,
        font_primary="JetBrains Mono",
        font_secondary="JetBrains Mono",
    ),
    "gold": CardTheme(
        id="gold",
        name="Luxury Gold",
        bg_start="#121212",
        bg_end="#1e1b18",
        accent="#f59e0b",
        text_primary="#fef08a",
        text_secondary="#fde047",
        badge_bg="rgba(245, 158, 11, 0.2)",
        badge_text="#fbbf24",
        border_color="rgba(245, 158, 11, 0.35)",
        glow_color="#f59e0b",
        card_bg="rgba(30, 27, 24, 0.8)",
        is_dark=True,
        gradient_angle=135,
    ),
    "monochrome": CardTheme(
        id="monochrome",
        name="Stark Monochrome",
        bg_start="#000000",
        bg_end="#18181b",
        accent="#ffffff",
        text_primary="#ffffff",
        text_secondary="#a1a1aa",
        badge_bg="rgba(255, 255, 255, 0.12)",
        badge_text="#ffffff",
        border_color="rgba(255, 255, 255, 0.25)",
        glow_color="#ffffff",
        card_bg="rgba(24, 24, 27, 0.85)",
        is_dark=True,
        gradient_angle=135,
    ),
}


def get_theme(name_or_id: Optional[str] = None) -> CardTheme:
    """Retrieve theme by identifier, or fallback to default aurora theme."""
    if not name_or_id:
        return THEMES_CATALOG["aurora"]
    key = name_or_id.strip().lower().replace("-", "_").replace(" ", "_")
    try:
        from .gradients import get_theme as _grad_get_theme
        theme = _grad_get_theme(key)
        if theme:
            return theme
    except Exception:
        pass
    alias_map = {
        "modern_dark": "dark",
        "slate": "dark",
        "clean_light": "light",
        "white": "light",
        "neon": "cyberpunk",
        "neon_nights": "cyberpunk",
        "terminal": "matrix",
        "terminal_green": "matrix",
        "hacker": "matrix",
        "forest": "emerald",
        "luxury": "gold",
        "champagne": "gold",
        "mono": "monochrome",
        "black_and_white": "monochrome",
    }
    target_id = alias_map.get(key, key)
    return THEMES_CATALOG.get(target_id, THEMES_CATALOG["aurora"])


def list_themes(category: Optional[str] = None) -> List[CardTheme]:
    """Return all available themes, optionally filtered by dark/light mode."""
    themes_map = dict(THEMES_CATALOG)
    try:
        from .gradients import list_themes as _grad_list_themes
        for t in _grad_list_themes():
            themes_map[t.id] = t
    except Exception:
        pass
    themes = list(themes_map.values())
    if not category:
        return themes
    cat = category.strip().lower()
    if cat == "dark":
        return [t for t in themes if t.is_dark]
    if cat == "light":
        return [t for t in themes if not t.is_dark]
    return themes


# ============================================================================
# BUILT-IN TEMPLATES REGISTRY
# ============================================================================

TEMPLATES_CATALOG: Dict[str, TemplatePreset] = {
    "modern-blog": TemplatePreset(
        id="modern-blog",
        name="Modern Editorial Blog",
        category="blog",
        description="Clean and modern social card for blog posts, articles, and essays with prominent title, subtitle, reading time, and author badge.",
        config=OGCardConfig(
            title="Mastering Distributed Systems Architecture in 2026",
            subtitle="A comprehensive deep dive into consensus protocols, raft algorithms, and event sourcing.",
            author=AuthorSpec(name="Alex Rivera", title="Staff Engineer"),
            category="Architecture",
            tags=["DistributedSystems", "Raft", "Cloud"],
            theme="aurora",
            layout=CardLayout.DEFAULT,
            reading_time_min=7,
            date_str="Sep 16, 2026",
            site_name="devnotes.io",
        ),
        sample_data={
            "title": "Mastering Distributed Systems Architecture in 2026",
            "subtitle": "A comprehensive deep dive into consensus protocols, raft algorithms, and event sourcing.",
            "author": "Alex Rivera",
            "category": "Architecture",
            "tags": ["DistributedSystems", "Raft", "Cloud"],
            "reading_time_min": 7,
            "date_str": "Sep 16, 2026",
            "site_name": "devnotes.io",
        },
    ),
    "tech-launch": TemplatePreset(
        id="tech-launch",
        name="Product & Tech Launch",
        category="marketing",
        description="High-energy tech announcement banner with project headline, version chip, feature tags, and repository branding.",
        config=OGCardConfig(
            title="Announcing Canvas Forge v1.0",
            subtitle="The ultimate pure Python social preview engine and MCP protocol server.",
            author=AuthorSpec(name="OG Canvas Forge Team"),
            category="Major Release",
            tags=["OpenSource", "Python", "MCP", "AI"],
            theme="cyberpunk",
            layout=CardLayout.CENTERED,
            site_name="github.com/og-canvas-forge",
            badge="v1.0.0 Stable",
        ),
        sample_data={
            "title": "Announcing Canvas Forge v1.0",
            "subtitle": "The ultimate pure Python social preview engine and MCP protocol server.",
            "author": "OG Canvas Forge Team",
            "category": "Major Release",
            "tags": ["OpenSource", "Python", "MCP", "AI"],
            "site_name": "github.com/og-canvas-forge",
            "badge": "v1.0.0 Stable",
        },
    ),
    "podcast-episode": TemplatePreset(
        id="podcast-episode",
        name="Podcast Episode",
        category="audio",
        description="Engaging podcast episode preview with episode badge, waveform visualization, host name, and guest headline.",
        config=OGCardConfig(
            title="The Future of Agentic AI & Autonomous Coding",
            subtitle="Interview with leading AI research engineers on next-gen tool use and multi-agent coordination.",
            author=AuthorSpec(name="Hosted by Sarah Chen"),
            category="AI Frontiers Podcast",
            episode_number="EP #108",
            tags=["ArtificialIntelligence", "Podcasts", "Tech"],
            theme="sunset",
            layout=CardLayout.PODCAST,
            site_name="aifrontiers.fm",
        ),
        sample_data={
            "title": "The Future of Agentic AI & Autonomous Coding",
            "subtitle": "Interview with leading AI research engineers on next-gen tool use and multi-agent coordination.",
            "author": "Hosted by Sarah Chen",
            "category": "AI Frontiers Podcast",
            "episode_number": "EP #108",
            "tags": ["ArtificialIntelligence", "Podcasts", "Tech"],
            "site_name": "aifrontiers.fm",
        },
    ),
    "dev-tutorial": TemplatePreset(
        id="dev-tutorial",
        name="Developer Code Tutorial",
        category="developer",
        description="Developer-focused guide template featuring code syntax accent, language tags, and author badge.",
        config=OGCardConfig(
            title="Building a Zero-Dependency MCP Server in Python",
            subtitle="Step-by-step tutorial implementing JSON-RPC 2.0 stdio protocols from scratch.",
            author=AuthorSpec(name="Marcus Vance"),
            category="Hands-On Guide",
            code_snippet="@mcp.tool()\ndef generate_card(title: str) -> str:\n    return forge.render(title)",
            code_language="python",
            tags=["Python3", "Tutorial", "MCP"],
            theme="matrix",
            layout=CardLayout.DEV_CODE,
            reading_time_min=10,
            site_name="codecraft.dev",
        ),
        sample_data={
            "title": "Building a Zero-Dependency MCP Server in Python",
            "subtitle": "Step-by-step tutorial implementing JSON-RPC 2.0 stdio protocols from scratch.",
            "author": "Marcus Vance",
            "category": "Hands-On Guide",
            "code_snippet": "@mcp.tool()\ndef generate_card(title: str) -> str:\n    return forge.render(title)",
            "code_language": "python",
            "tags": ["Python3", "Tutorial", "MCP"],
            "reading_time_min": 10,
            "site_name": "codecraft.dev",
        },
    ),
    "newsletter": TemplatePreset(
        id="newsletter",
        name="Curated Weekly Newsletter",
        category="editorial",
        description="Editorial newsletter banner with issue number, curation hook, highlighted quote, and author attribution.",
        config=OGCardConfig(
            title="The Weekly Dispatch: Issue #84",
            subtitle="This week: breakthroughs in context caching, reasoning models, and agent architectures.",
            author=AuthorSpec(name="Curated by Elena Rostova"),
            category="Weekly Newsletter",
            episode_number="Issue #84",
            tags=["Newsletter", "TechNews", "Trends"],
            theme="ocean",
            layout=CardLayout.DEFAULT,
            date_str="Sep 16, 2026",
            site_name="weeklydispatch.substack.com",
        ),
        sample_data={
            "title": "The Weekly Dispatch: Issue #84",
            "subtitle": "This week: breakthroughs in context caching, reasoning models, and agent architectures.",
            "author": "Curated by Elena Rostova",
            "category": "Weekly Newsletter",
            "episode_number": "Issue #84",
            "tags": ["Newsletter", "TechNews", "Trends"],
            "date_str": "Sep 16, 2026",
            "site_name": "weeklydispatch.substack.com",
        },
    ),
    "minimalist": TemplatePreset(
        id="minimalist",
        name="Minimalist Editorial",
        category="minimal",
        description="Sophisticated typography-led design with generous whitespace, subtle frame, and refined editorial elegance.",
        config=OGCardConfig(
            title="Less is More: The Principles of Restrained Software Design",
            subtitle="Why removing features is often the highest-leverage engineering decision.",
            author=AuthorSpec(name="Dieter Rams"),
            category="Design Philosophy",
            tags=["Design", "Simplicity", "Engineering"],
            theme="monochrome",
            layout=CardLayout.MINIMAL,
            site_name="minimalist.design",
        ),
        sample_data={
            "title": "Less is More: The Principles of Restrained Software Design",
            "subtitle": "Why removing features is often the highest-leverage engineering decision.",
            "author": "Dieter Rams",
            "category": "Design Philosophy",
            "tags": ["Design", "Simplicity", "Engineering"],
            "site_name": "minimalist.design",
        },
    ),
    "quote-card": TemplatePreset(
        id="quote-card",
        name="Thought Leader Quote",
        category="social",
        description="Impactful quote showcase featuring decorative quotation marks, emphasized wisdom text, and speaker citation.",
        config=OGCardConfig(
            title="“Simplicity is prerequisite for reliability.”",
            subtitle="Reflections on software complexity, reliability, and human cognition.",
            author=AuthorSpec(name="Edsger W. Dijkstra"),
            category="Computing Wisdom",
            tags=["Quotes", "ComputerScience", "Software"],
            theme="gold",
            layout=CardLayout.CENTERED,
            site_name="turingquotes.com",
        ),
        sample_data={
            "title": "“Simplicity is prerequisite for reliability.”",
            "subtitle": "Reflections on software complexity, reliability, and human cognition.",
            "author": "Edsger W. Dijkstra",
            "category": "Computing Wisdom",
            "tags": ["Quotes", "ComputerScience", "Software"],
            "site_name": "turingquotes.com",
        },
    ),
    "event-summit": TemplatePreset(
        id="event-summit",
        name="Conference & Event Ticket",
        category="events",
        description="Conference and webinar announcement with date/time pill, speaker badge, location, and ticket stub styling.",
        config=OGCardConfig(
            title="Global AI Protocol Summit 2026",
            subtitle="The premier gathering for agent protocol developers, researchers, and tool builders.",
            author=AuthorSpec(name="Keynote: Dr. Aris Thorne"),
            category="Virtual Conference",
            ticket_number="TICKET #0429",
            date_str="October 24-26, 2026",
            tags=["AIConf", "Keynote", "Protocols"],
            theme="emerald",
            layout=CardLayout.EVENT_TICKET,
            site_name="aisummit.org",
        ),
        sample_data={
            "title": "Global AI Protocol Summit 2026",
            "subtitle": "The premier gathering for agent protocol developers, researchers, and tool builders.",
            "author": "Keynote: Dr. Aris Thorne",
            "category": "Virtual Conference",
            "ticket_number": "TICKET #0429",
            "date_str": "October 24-26, 2026",
            "tags": ["AIConf", "Keynote", "Protocols"],
            "site_name": "aisummit.org",
        },
    ),
    "ecommerce-drop": TemplatePreset(
        id="ecommerce-drop",
        name="Product & Merchandise Drop",
        category="ecommerce",
        description="Vibrant product drop card with price badge, product category, feature chips, and store branding.",
        config=OGCardConfig(
            title="Mechanical Keycap Set: Cyberpunk Edition",
            subtitle="Custom PBT double-shot keycaps with glow-in-the-dark legends and artisan esc key.",
            author=AuthorSpec(name="Limited Batch of 500 Units"),
            category="New Arrival",
            badge=BadgeSpec(text="$129 USD"),
            tags=["Hardware", "Keyboards", "Mechanical"],
            theme="sunset",
            layout=CardLayout.SPLIT,
            site_name="mechforge.shop",
        ),
        sample_data={
            "title": "Mechanical Keycap Set: Cyberpunk Edition",
            "subtitle": "Custom PBT double-shot keycaps with glow-in-the-dark legends and artisan esc key.",
            "author": "Limited Batch of 500 Units",
            "category": "New Arrival",
            "badge": "$129 USD",
            "tags": ["Hardware", "Keyboards", "Mechanical"],
            "site_name": "mechforge.shop",
        },
    ),
    "changelog-release": TemplatePreset(
        id="changelog-release",
        name="Release Notes & Changelog",
        category="developer",
        description="Product release changelog card featuring version pill, highlight bullets, and release timestamp.",
        config=OGCardConfig(
            title="v2.4.0 Release: Realtime Stdio Streaming & Zero-Copy Rasterization",
            subtitle="Featuring 10x faster card generation, 12 new themes, and full MCP JSON-RPC 2.0 conformance.",
            author=AuthorSpec(name="Release Engineering Team"),
            category="Changelog",
            badge=BadgeSpec(text="v2.4.0"),
            tags=["Changelog", "Updates", "Performance"],
            theme="dark",
            layout=CardLayout.DEFAULT,
            date_str="Sep 16, 2026",
            site_name="canvasforge.dev/changelog",
        ),
        sample_data={
            "title": "v2.4.0 Release: Realtime Stdio Streaming & Zero-Copy Rasterization",
            "subtitle": "Featuring 10x faster card generation, 12 new themes, and full MCP JSON-RPC 2.0 conformance.",
            "author": "Release Engineering Team",
            "category": "Changelog",
            "badge": "v2.4.0",
            "tags": ["Changelog", "Updates", "Performance"],
            "date_str": "Sep 16, 2026",
            "site_name": "canvasforge.dev/changelog",
        },
    ),
    "documentation": TemplatePreset(
        id="documentation",
        name="API Documentation Reference",
        category="developer",
        description="API and technical documentation card with route breadcrumb, method badge, and endpoint summary.",
        config=OGCardConfig(
            title="POST /v1/cards/generate",
            subtitle="Generate a custom Open Graph SVG card programmatically with high-performance rasterization.",
            author=AuthorSpec(name="API Reference Docs"),
            category="REST API Endpoint",
            code_snippet='POST /v1/cards/generate HTTP/1.1\nContent-Type: application/json\n\n{"title": "My Card", "theme": "aurora"}',
            code_language="http",
            tags=["API", "REST", "Documentation"],
            theme="ocean",
            layout=CardLayout.DEV_CODE,
            site_name="docs.canvasforge.dev",
        ),
        sample_data={
            "title": "POST /v1/cards/generate",
            "subtitle": "Generate a custom Open Graph SVG card programmatically with high-performance rasterization.",
            "author": "API Reference Docs",
            "category": "REST API Endpoint",
            "code_snippet": 'POST /v1/cards/generate HTTP/1.1\nContent-Type: application/json\n\n{"title": "My Card", "theme": "aurora"}',
            "code_language": "http",
            "tags": ["API", "REST", "Documentation"],
            "site_name": "docs.canvasforge.dev",
        },
    ),
    "split-showcase": TemplatePreset(
        id="split-showcase",
        name="Split Visual Showcase",
        category="marketing",
        description="Dynamic split-screen layout with visual gradient showcase on the right and structured content on the left.",
        config=OGCardConfig(
            title="Next-Gen Visual Asset Generation for Modern Web Apps",
            subtitle="Automate your social preview pipeline with pure Python vector synthesis.",
            author=AuthorSpec(name="Design Systems Lab"),
            category="Design System",
            tags=["DesignSystems", "SVG", "WebDesign"],
            theme="aurora",
            layout=CardLayout.SPLIT,
            site_name="designlab.internal",
        ),
        sample_data={
            "title": "Next-Gen Visual Asset Generation for Modern Web Apps",
            "subtitle": "Automate your social preview pipeline with pure Python vector synthesis.",
            "author": "Design Systems Lab",
            "category": "Design System",
            "tags": ["DesignSystems", "SVG", "WebDesign"],
            "site_name": "designlab.internal",
        },
    ),
}


def get_template(template_id: Optional[str] = None) -> Optional[TemplatePreset]:
    """Retrieve template preset by identifier."""
    if not template_id:
        return None
    key = template_id.strip().lower()
    try:
        from .catalog import get_template as _cat_get_template
        t = _cat_get_template(key)
        if t:
            return t
    except Exception:
        pass
    return TEMPLATES_CATALOG.get(key) or TEMPLATES_CATALOG.get(key.replace("_", "-"))


def list_templates(category: Optional[str] = None) -> List[TemplatePreset]:
    """Return all available templates, optionally filtered by category."""
    tmpl_map = dict(TEMPLATES_CATALOG)
    try:
        from .catalog import list_templates as _cat_list_templates
        for t in _cat_list_templates():
            tmpl_map[t.id] = t
    except Exception:
        pass
    templates = list(tmpl_map.values())
    if not category:
        return templates
    cat = category.strip().lower()
    return [t for t in templates if t.category.lower() == cat]


# ============================================================================
# HTML META TAG GENERATOR
# ============================================================================


def render_html_meta(
    title: str,
    image_url: str,
    description: Optional[str] = None,
    url: Optional[str] = None,
    site_name: Optional[str] = None,
    twitter_handle: Optional[str] = None,
    twitter_card: str = "summary_large_image",
    card_type: str = "article",
    published_time: Optional[str] = None,
    author: Optional[str] = None,
    section: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """Generate HTML <meta> tags for Open Graph and Twitter Card compliance."""
    safe_title = html.escape(title or "")
    safe_image = html.escape(image_url or "")
    safe_desc = html.escape(description or "")

    lines: List[str] = [
        "<!-- Open Graph Meta Tags Generated by og-canvas-forge -->",
        f'<meta property="og:title" content="{safe_title}">',
    ]

    if safe_desc:
        lines.append(f'<meta property="og:description" content="{safe_desc}">')

    lines.extend([
        f'<meta property="og:image" content="{safe_image}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:type" content="{html.escape(card_type)}">',
    ])

    if url:
        lines.append(f'<meta property="og:url" content="{html.escape(url)}">')
    if site_name:
        lines.append(f'<meta property="og:site_name" content="{html.escape(site_name)}">')
    if published_time:
        lines.append(f'<meta property="article:published_time" content="{html.escape(published_time)}">')
    if author:
        lines.append(f'<meta property="article:author" content="{html.escape(author)}">')
    if section:
        lines.append(f'<meta property="article:section" content="{html.escape(section)}">')
    if tags:
        for tag in tags:
            lines.append(f'<meta property="article:tag" content="{html.escape(tag)}">')

    lines.extend([
        "",
        "<!-- Twitter Card Meta Tags -->",
        f'<meta name="twitter:card" content="{html.escape(twitter_card)}">',
        f'<meta name="twitter:title" content="{safe_title}">',
    ])

    if safe_desc:
        lines.append(f'<meta name="twitter:description" content="{safe_desc}">')

    lines.append(f'<meta name="twitter:image" content="{safe_image}">')

    if twitter_handle:
        handle = twitter_handle if twitter_handle.startswith("@") else f"@{twitter_handle}"
        lines.append(f'<meta name="twitter:creator" content="{html.escape(handle)}">')
        lines.append(f'<meta name="twitter:site" content="{html.escape(handle)}">')

    return "\n".join(lines)


# ============================================================================
# SVG RENDERING ENGINE (Pure Python, Zero External Dependencies)
# ============================================================================


def _wrap_text(text: str, max_chars_per_line: int, max_lines: int = 3) -> List[str]:
    """Wrap text intelligently into multiple lines respecting word boundaries."""
    if not text:
        return []
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current_line: List[str] = []
    current_length = 0

    for word in words:
        word_length = len(word)
        if current_line and (current_length + 1 + word_length) > max_chars_per_line:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_length
            if len(lines) >= max_lines:
                break
        else:
            current_line.append(word)
            current_length += (word_length + 1) if current_line else word_length

    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))

    # Add ellipsis if truncated
    if len(lines) == max_lines and len(words) > len(" ".join(lines).split()):
        if lines[-1].endswith("."):
            lines[-1] = lines[-1][:-1] + "..."
        else:
            lines[-1] = lines[-1] + "..."

    return lines


def _render_svg_card(config: OGCardConfig, theme: CardTheme) -> str:
    """Generate a clean, high-DPI SVG Open Graph social card."""
    width = config.dimensions.width
    height = config.dimensions.height

    # Escaped fields
    raw_title = config.title or "Untitled Social Card"
    title_escaped = html.escape(raw_title)
    subtitle_raw = config.subtitle or ""
    subtitle_escaped = html.escape(subtitle_raw)

    author_name = ""
    if isinstance(config.author, AuthorSpec):
        author_name = config.author.name
    elif isinstance(config.author, str):
        author_name = config.author

    badge_text = ""
    if isinstance(config.badge, BadgeSpec):
        badge_text = config.badge.text
    elif isinstance(config.badge, str):
        badge_text = config.badge
    elif config.category:
        badge_text = config.category

    site_name = config.site_name or ""
    date_str = config.date_str or ""
    reading_time = f"{config.reading_time_min} min read" if config.reading_time_min else ""

    # Dimensions & coordinates
    padding_x = 72
    padding_y = 64
    content_width = width - (padding_x * 2)

    # Layout archetype
    layout_type = config.layout
    if isinstance(layout_type, str):
        layout_type = CardLayout.from_str(layout_type)

    # Font sizing & line wrapping based on layout
    is_centered = (layout_type == CardLayout.CENTERED)
    is_split = (layout_type == CardLayout.SPLIT)
    is_minimal = (layout_type == CardLayout.MINIMAL)
    is_dev = (layout_type == CardLayout.DEV_CODE)
    is_podcast = (layout_type == CardLayout.PODCAST)
    is_event = (layout_type == CardLayout.EVENT_TICKET)

    title_chars = 34 if not is_split else 26
    if len(raw_title) > 60:
        title_font_size = 48
        title_line_height = 58
    elif len(raw_title) > 35:
        title_font_size = 54
        title_line_height = 64
    else:
        title_font_size = 60
        title_line_height = 72

    title_lines = _wrap_text(raw_title, title_chars, max_lines=3)
    subtitle_lines = _wrap_text(subtitle_raw, 56 if not is_split else 38, max_lines=2)

    # SVG Defs: Gradients, Filters, Patterns
    defs_svg = f"""
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{theme.bg_start}"/>
      <stop offset="100%" stop-color="{theme.bg_end}"/>
    </linearGradient>

    <!-- Accent Gradient -->
    <linearGradient id="accentGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{theme.accent}"/>
      <stop offset="100%" stop-color="{theme.glow_color}"/>
    </linearGradient>

    <!-- Ambient Glow Filter -->
    <filter id="ambientGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="60" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>

    <!-- Drop Shadow Filter -->
    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="24" flood-color="#000000" flood-opacity="0.45"/>
    </filter>

    <!-- Subtle Dot Pattern -->
    <pattern id="dotPattern" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.5" fill="{theme.accent}" fill-opacity="0.08"/>
    </pattern>
  </defs>"""

    # Background Base
    bg_svg = f"""
  <!-- Background Rect -->
  <rect width="{width}" height="{height}" fill="url(#bgGradient)"/>
  <rect width="{width}" height="{height}" fill="url(#dotPattern)"/>

  <!-- Ambient Light Orbs -->
  <circle cx="{width - 120}" cy="100" r="240" fill="{theme.glow_color}" fill-opacity="0.12" filter="url(#ambientGlow)"/>
  <circle cx="100" cy="{height - 80}" r="200" fill="{theme.accent}" fill-opacity="0.09" filter="url(#ambientGlow)"/>"""

    # Layout-specific content generation
    inner_content = []

    if is_centered:
        # Centered Layout
        current_y = 130
        if badge_text:
            badge_esc = html.escape(badge_text.upper())
            inner_content.append(f"""
    <!-- Centered Badge -->
    <g transform="translate({width // 2}, {current_y})">
      <rect x="-110" y="-20" width="220" height="40" rx="20" fill="{theme.badge_bg}" stroke="{theme.border_color}" stroke-width="1.5"/>
      <text x="0" y="6" text-anchor="middle" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="14" font-weight="700" fill="{theme.badge_text}" letter-spacing="1.5">{badge_esc}</text>
    </g>""")
            current_y += 70

        # Centered Title
        inner_content.append(f"""
    <!-- Centered Title -->
    <g transform="translate({width // 2}, {current_y + 40})">""")
        for idx, line in enumerate(title_lines):
            y_offset = idx * title_line_height
            inner_content.append(
                f'      <text x="0" y="{y_offset}" text-anchor="middle" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="{title_font_size}" font-weight="800" fill="{theme.text_primary}" letter-spacing="-0.5">{html.escape(line)}</text>'
            )
        inner_content.append("    </g>")
        current_y += len(title_lines) * title_line_height + 40

        # Centered Subtitle
        if subtitle_lines:
            inner_content.append(f"""
    <!-- Centered Subtitle -->
    <g transform="translate({width // 2}, {current_y + 10})">""")
            for idx, line in enumerate(subtitle_lines):
                y_offset = idx * 34
                inner_content.append(
                    f'      <text x="0" y="{y_offset}" text-anchor="middle" font-family="{theme.font_secondary}, system-ui, sans-serif" font-size="22" font-weight="400" fill="{theme.text_secondary}">{html.escape(line)}</text>'
                )
            inner_content.append("    </g>")

        # Centered Footer / Author
        footer_y = height - padding_y - 20
        if author_name or site_name:
            footer_text = f"{author_name} • {site_name}" if (author_name and site_name) else (author_name or site_name)
            inner_content.append(f"""
    <!-- Centered Footer -->
    <g transform="translate({width // 2}, {footer_y})">
      <text x="0" y="0" text-anchor="middle" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="18" font-weight="600" fill="{theme.accent}">{html.escape(footer_text)}</text>
    </g>""")

    elif is_split:
        # Split Layout: 60% Content Left, 40% Visual Hero Right
        split_x = int(width * 0.58)
        inner_content.append(f"""
    <!-- Split Divider & Right Panel -->
    <rect x="{split_x}" y="32" width="{width - split_x - 32}" height="{height - 64}" rx="24" fill="{theme.card_bg or 'rgba(255,255,255,0.04)'}" stroke="{theme.border_color}" stroke-width="1.5" />
    <circle cx="{split_x + (width - split_x - 32) // 2}" cy="{height // 2}" r="110" fill="url(#accentGradient)" fill-opacity="0.2" filter="url(#ambientGlow)"/>
    <rect x="{split_x + 40}" y="{height // 2 - 60}" width="{width - split_x - 112}" height="120" rx="16" fill="{theme.badge_bg}" stroke="{theme.accent}" stroke-width="2" />
    <text x="{split_x + (width - split_x - 32) // 2}" y="{height // 2 - 10}" text-anchor="middle" font-family="{theme.font_mono}, monospace" font-size="15" font-weight="700" fill="{theme.accent}">OG PREVIEW</text>
    <text x="{split_x + (width - split_x - 32) // 2}" y="{height // 2 + 25}" text-anchor="middle" font-family="{theme.font_primary}, sans-serif" font-size="28" font-weight="800" fill="{theme.text_primary}">{html.escape(badge_text or 'CANVAS FORGE')}</text>""")

        # Left Column
        current_y = padding_y + 40
        if badge_text:
            inner_content.append(f"""
    <!-- Category Badge -->
    <g transform="translate({padding_x}, {current_y})">
      <rect x="0" y="-18" width="{len(badge_text) * 11 + 36}" height="36" rx="18" fill="{theme.badge_bg}" stroke="{theme.border_color}" stroke-width="1.5"/>
      <text x="{18 + (len(badge_text) * 11) // 2}" y="5" text-anchor="middle" font-family="{theme.font_primary}, sans-serif" font-size="13" font-weight="700" fill="{theme.badge_text}" letter-spacing="1">{html.escape(badge_text.upper())}</text>
    </g>""")
            current_y += 64

        # Title
        inner_content.append(f"""
    <!-- Left Column Title -->
    <g transform="translate({padding_x}, {current_y + 36})">""")
        for idx, line in enumerate(title_lines):
            y_offset = idx * title_line_height
            inner_content.append(
                f'      <text x="0" y="{y_offset}" font-family="{theme.font_primary}, sans-serif" font-size="{title_font_size}" font-weight="800" fill="{theme.text_primary}" letter-spacing="-0.5">{html.escape(line)}</text>'
            )
        inner_content.append("    </g>")
        current_y += len(title_lines) * title_line_height + 30

        # Subtitle
        if subtitle_lines:
            inner_content.append(f"""
    <!-- Left Column Subtitle -->
    <g transform="translate({padding_x}, {current_y + 10})">""")
            for idx, line in enumerate(subtitle_lines):
                y_offset = idx * 32
                inner_content.append(
                    f'      <text x="0" y="{y_offset}" font-family="{theme.font_secondary}, sans-serif" font-size="20" font-weight="400" fill="{theme.text_secondary}">{html.escape(line)}</text>'
                )
            inner_content.append("    </g>")

        # Author Footer
        if author_name:
            footer_y = height - padding_y - 15
            inner_content.append(f"""
    <!-- Author Footer -->
    <g transform="translate({padding_x}, {footer_y})">
      <circle cx="16" cy="-6" r="16" fill="{theme.accent}" fill-opacity="0.25"/>
      <text x="16" y="0" text-anchor="middle" font-family="{theme.font_primary}, sans-serif" font-size="14" font-weight="700" fill="{theme.accent}">{html.escape(author_name[:1])}</text>
      <text x="44" y="0" font-family="{theme.font_primary}, sans-serif" font-size="17" font-weight="600" fill="{theme.text_primary}">{html.escape(author_name)}</text>
    </g>""")

    elif is_dev:
        # Developer / Code Snippet Layout
        current_y = padding_y + 30
        if badge_text:
            inner_content.append(f"""
    <!-- Dev Category Badge -->
    <g transform="translate({padding_x}, {current_y})">
      <rect x="0" y="-16" width="{len(badge_text) * 11 + 32}" height="32" rx="6" fill="{theme.badge_bg}" stroke="{theme.accent}" stroke-width="1.5"/>
      <text x="{16 + (len(badge_text) * 11) // 2}" y="5" text-anchor="middle" font-family="{theme.font_mono}, monospace" font-size="13" font-weight="700" fill="{theme.accent}">{html.escape(badge_text)}</text>
    </g>""")
            current_y += 56

        # Title
        inner_content.append(f"""
    <!-- Dev Title -->
    <g transform="translate({padding_x}, {current_y + 30})">""")
        for idx, line in enumerate(title_lines[:2]):
            y_offset = idx * 56
            inner_content.append(
                f'      <text x="0" y="{y_offset}" font-family="{theme.font_mono}, monospace" font-size="46" font-weight="800" fill="{theme.text_primary}">{html.escape(line)}</text>'
            )
        inner_content.append("    </g>")
        current_y += min(2, len(title_lines)) * 56 + 24

        # Code Box Preview
        code_box_y = current_y + 10
        code_box_height = 160
        code_text = config.code_snippet or "def run_mcp_forge():\n    return CanvasForge.synthesize()"
        code_lines = code_text.split("\n")[:4]

        inner_content.append(f"""
    <!-- Code Box Window -->
    <g transform="translate({padding_x}, {code_box_y})">
      <rect x="0" y="0" width="{content_width}" height="{code_box_height}" rx="12" fill="rgba(0,0,0,0.6)" stroke="{theme.border_color}" stroke-width="1.5"/>
      <circle cx="20" cy="18" r="6" fill="#EF4444"/>
      <circle cx="38" cy="18" r="6" fill="#F59E0B"/>
      <circle cx="56" cy="18" r="6" fill="#10B981"/>
      <text x="{content_width - 24}" y="22" text-anchor="end" font-family="{theme.font_mono}, monospace" font-size="12" fill="{theme.text_secondary}">{html.escape(config.code_language or 'python')}</text>
      <line x1="0" y1="36" x2="{content_width}" y2="36" stroke="{theme.border_color}" stroke-width="1"/>
      <g transform="translate(24, 66)">""")
        for c_idx, c_line in enumerate(code_lines):
            c_y = c_idx * 26
            inner_content.append(
                f'        <text x="0" y="{c_y}" font-family="{theme.font_mono}, monospace" font-size="16" fill="{theme.text_primary}">{html.escape(c_line)}</text>'
            )
        inner_content.append("""      </g>
    </g>""")

    elif is_podcast:
        # Podcast Layout with Waveform
        current_y = padding_y + 40
        ep_text = config.episode_number or "EPISODE"
        inner_content.append(f"""
    <!-- Podcast Pill & Episode -->
    <g transform="translate({padding_x}, {current_y})">
      <rect x="0" y="-18" width="{len(ep_text) * 11 + 36}" height="36" rx="18" fill="{theme.accent}" fill-opacity="0.2" stroke="{theme.accent}" stroke-width="1.5"/>
      <text x="{18 + (len(ep_text) * 11) // 2}" y="5" text-anchor="middle" font-family="{theme.font_primary}, sans-serif" font-size="14" font-weight="800" fill="{theme.accent}">{html.escape(ep_text)}</text>
    </g>""")
        current_y += 64

        # Title
        inner_content.append(f"""
    <!-- Podcast Title -->
    <g transform="translate({padding_x}, {current_y + 36})">""")
        for idx, line in enumerate(title_lines):
            y_offset = idx * title_line_height
            inner_content.append(
                f'      <text x="0" y="{y_offset}" font-family="{theme.font_primary}, sans-serif" font-size="{title_font_size}" font-weight="800" fill="{theme.text_primary}">{html.escape(line)}</text>'
            )
        inner_content.append("    </g>")
        current_y += len(title_lines) * title_line_height + 30

        # Simulated Audio Waveform Bars
        wave_y = height - padding_y - 70
        bar_heights = [24, 48, 72, 36, 80, 56, 92, 40, 68, 88, 32, 60, 84, 44, 76, 52, 96, 64, 40, 28]
        inner_content.append(f"""
    <!-- Audio Waveform Visualization -->
    <g transform="translate({padding_x}, {wave_y})">""")
        for b_idx, b_height in enumerate(bar_heights):
            b_x = b_idx * 16
            b_y = -b_height // 2
            inner_content.append(
                f'      <rect x="{b_x}" y="{b_y}" width="8" height="{b_height}" rx="4" fill="{theme.accent}" fill-opacity="0.85"/>'
            )
        inner_content.append("    </g>")

        if author_name:
            inner_content.append(f"""
    <!-- Host Citation -->
    <g transform="translate({width - padding_x}, {wave_y})">
      <text x="0" y="8" text-anchor="end" font-family="{theme.font_primary}, sans-serif" font-size="20" font-weight="700" fill="{theme.text_primary}">{html.escape(author_name)}</text>
    </g>""")

    elif is_event:
        # Event Ticket Layout
        ticket_x = padding_x
        ticket_y = padding_y
        ticket_w = content_width
        ticket_h = height - (padding_y * 2)
        stub_x = ticket_w - 220

        inner_content.append(f"""
    <!-- Ticket Container -->
    <g transform="translate({ticket_x}, {ticket_y})">
      <rect x="0" y="0" width="{ticket_w}" height="{ticket_h}" rx="20" fill="{theme.card_bg or 'rgba(255,255,255,0.05)'}" stroke="{theme.border_color}" stroke-width="2"/>
      <!-- Perforated Line -->
      <line x1="{stub_x}" y1="0" x2="{stub_x}" y2="{ticket_h}" stroke="{theme.border_color}" stroke-width="2" stroke-dasharray="8 8"/>
      <!-- Stub Notches -->
      <circle cx="{stub_x}" cy="0" r="16" fill="{theme.bg_start}"/>
      <circle cx="{stub_x}" cy="{ticket_h}" r="16" fill="{theme.bg_end}"/>
      
      <!-- Ticket Main Body -->
      <text x="40" y="60" font-family="{theme.font_primary}, sans-serif" font-size="14" font-weight="800" fill="{theme.accent}" letter-spacing="2">{html.escape((badge_text or 'EVENT PASS').upper())}</text>
      <text x="40" y="130" font-family="{theme.font_primary}, sans-serif" font-size="46" font-weight="800" fill="{theme.text_primary}">{html.escape(raw_title[:45])}</text>
      <text x="40" y="190" font-family="{theme.font_secondary}, sans-serif" font-size="20" fill="{theme.text_secondary}">{html.escape(subtitle_raw[:65])}</text>
      <text x="40" y="{ticket_h - 40}" font-family="{theme.font_primary}, sans-serif" font-size="18" font-weight="600" fill="{theme.text_primary}">{html.escape(author_name or date_str or 'Live Event')}</text>

      <!-- Ticket Stub -->
      <g transform="translate({stub_x + 110}, {ticket_h // 2}) rotate(90)">
        <text x="0" y="0" text-anchor="middle" font-family="{theme.font_mono}, monospace" font-size="18" font-weight="700" fill="{theme.accent}">{html.escape(config.ticket_number or 'ADMIT ONE')}</text>
      </g>
    </g>""")

    else:
        # Default / Standard Layout (Card container with category, title, subtitle, author, tags, site watermark)
        current_y = padding_y + 36

        # Category Pill
        if badge_text:
            badge_width = max(110, len(badge_text) * 11 + 36)
            inner_content.append(f"""
    <!-- Category Badge -->
    <g transform="translate({padding_x}, {current_y})">
      <rect x="0" y="-18" width="{badge_width}" height="36" rx="18" fill="{theme.badge_bg}" stroke="{theme.border_color}" stroke-width="1.5"/>
      <text x="{badge_width // 2}" y="5" text-anchor="middle" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="13" font-weight="700" fill="{theme.badge_text}" letter-spacing="1.2">{html.escape(badge_text.upper())}</text>
    </g>""")
            current_y += 64

        # Main Title
        inner_content.append(f"""
    <!-- Main Title -->
    <g transform="translate({padding_x}, {current_y + 36})">""")
        for idx, line in enumerate(title_lines):
            y_offset = idx * title_line_height
            inner_content.append(
                f'      <text x="0" y="{y_offset}" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="{title_font_size}" font-weight="800" fill="{theme.text_primary}" letter-spacing="-0.5">{html.escape(line)}</text>'
            )
        inner_content.append("    </g>")
        current_y += len(title_lines) * title_line_height + 24

        # Subtitle
        if subtitle_lines:
            inner_content.append(f"""
    <!-- Subtitle -->
    <g transform="translate({padding_x}, {current_y + 12})">""")
            for idx, line in enumerate(subtitle_lines):
                y_offset = idx * 34
                inner_content.append(
                    f'      <text x="0" y="{y_offset}" font-family="{theme.font_secondary}, system-ui, sans-serif" font-size="22" font-weight="400" fill="{theme.text_secondary}">{html.escape(line)}</text>'
                )
            inner_content.append("    </g>")

        # Bottom Bar: Author Attribution, Tags, and Brand Watermark
        bottom_y = height - padding_y - 12
        author_x = padding_x

        if author_name:
            initial = html.escape(author_name[:1].upper())
            inner_content.append(f"""
    <!-- Author Pill -->
    <g transform="translate({author_x}, {bottom_y})">
      <circle cx="18" cy="-6" r="18" fill="{theme.accent}" fill-opacity="0.2" stroke="{theme.accent}" stroke-width="1.5"/>
      <text x="18" y="0" text-anchor="middle" font-family="{theme.font_primary}, sans-serif" font-size="15" font-weight="800" fill="{theme.accent}">{initial}</text>
      <text x="48" y="0" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="18" font-weight="600" fill="{theme.text_primary}">{html.escape(author_name)}</text>
    </g>""")
            author_x += len(author_name) * 11 + 80

        # Tags
        if config.tags:
            tag_x = author_x + 20
            inner_content.append(f"""
    <!-- Tags Group -->
    <g transform="translate({tag_x}, {bottom_y})">""")
            current_tag_x = 0
            for tag in config.tags[:3]:
                tag_str = f"#{tag}" if not tag.startswith("#") else tag
                tag_w = len(tag_str) * 9 + 20
                if current_tag_x + tag_w < (content_width - 200):
                    inner_content.append(f"""
        <rect x="{current_tag_x}" y="-22" width="{tag_w}" height="28" rx="14" fill="{theme.badge_bg}" stroke="{theme.border_color}" stroke-width="1"/>
        <text x="{current_tag_x + tag_w // 2}" y="-3" text-anchor="middle" font-family="{theme.font_mono}, monospace" font-size="12" font-weight="600" fill="{theme.text_secondary}">{html.escape(tag_str)}</text>""")
                    current_tag_x += tag_w + 12
            inner_content.append("    </g>")

        # Watermark / Site Name in bottom right corner
        if site_name:
            inner_content.append(f"""
    <!-- Site Watermark -->
    <g transform="translate({width - padding_x}, {bottom_y})">
      <text x="0" y="0" text-anchor="end" font-family="{theme.font_primary}, system-ui, sans-serif" font-size="16" font-weight="700" fill="{theme.accent}">{html.escape(site_name)}</text>
    </g>""")

    # Combine SVG
    svg_body = "\n".join(inner_content)
    svg_document = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
{defs_svg}
{bg_svg}
{svg_body}
</svg>"""
    return svg_document


def generate_card(
    config: Optional[Union[OGCardConfig, Dict[str, Any], str]] = None,
    **kwargs: Any,
) -> GeneratedCard:
    """Core card generation factory. Accepts OGCardConfig or keyword arguments."""
    # Resolve config object
    if config is None:
        cfg = OGCardConfig(title=str(kwargs.get("title", "Untitled Card")))
    elif isinstance(config, OGCardConfig):
        cfg = config
    elif isinstance(config, dict):
        # Merge dict with kwargs
        merged = {**config, **kwargs}
        title = merged.pop("title", "Untitled Card")
        cfg = OGCardConfig(title=str(title), **merged)
    elif isinstance(config, str):
        cfg = OGCardConfig(title=config, **kwargs)
    else:
        cfg = OGCardConfig(title=str(config), **kwargs)

    # Apply extra kwargs if passed to override config
    for k, v in kwargs.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)

    # Handle template overlay if specified
    template_preset = None
    if isinstance(getattr(cfg, "template", None), str):
        template_preset = get_template(getattr(cfg, "template"))
    elif "template" in kwargs:
        template_preset = get_template(kwargs["template"])

    if template_preset:
        base_cfg = template_preset.config
        # Overlay user-provided values over preset
        if not cfg.subtitle and base_cfg.subtitle:
            cfg.subtitle = base_cfg.subtitle
        if not cfg.author and base_cfg.author:
            cfg.author = base_cfg.author
        if not cfg.category and base_cfg.category:
            cfg.category = base_cfg.category
        if not cfg.tags and base_cfg.tags:
            cfg.tags = base_cfg.tags
        if cfg.theme == "aurora" and base_cfg.theme:
            cfg.theme = base_cfg.theme
        if cfg.layout == CardLayout.DEFAULT and base_cfg.layout != CardLayout.DEFAULT:
            cfg.layout = base_cfg.layout

    # Resolve theme
    theme_obj = cfg.theme if isinstance(cfg.theme, CardTheme) else get_theme(str(cfg.theme))

    # Generate SVG
    svg_content = _render_svg_card(cfg, theme_obj)

    # Generate HTML meta tags
    html_meta = render_html_meta(
        title=cfg.title,
        image_url=f"/og-images/{cfg.title.lower().replace(' ', '-')}.svg",
        description=cfg.subtitle,
        site_name=cfg.site_name,
        author=cfg.author.name if isinstance(cfg.author, AuthorSpec) else (cfg.author or None),
        section=cfg.category,
        tags=cfg.tags,
    )

    return GeneratedCard(
        svg=svg_content,
        html_meta=html_meta,
        width=cfg.dimensions.width,
        height=cfg.dimensions.height,
        title=cfg.title,
        config=cfg,
    )


def export_svg(config: Union[OGCardConfig, Dict[str, Any], str], **kwargs: Any) -> str:
    """Generate and return raw SVG XML string directly."""
    return generate_card(config, **kwargs).svg


# ============================================================================
# PROTOCOL DEFINITIONS: TOOLS, RESOURCES, PROMPTS CATALOGS
# ============================================================================

MCP_TOOLS = [
    {
        "name": "og_generate_card",
        "description": "Generate an Open Graph social card SVG from parameters (title, subtitle, author, category, tags, theme, layout, dimensions).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Main title / headline of the card (required)",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Subtitle, tagline, or short description text",
                },
                "author": {
                    "type": "string",
                    "description": "Author name or creator handle (e.g. 'Jane Doe')",
                },
                "category": {
                    "type": "string",
                    "description": "Category or topic pill badge (e.g. 'Engineering', 'Release')",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of keyword tags (e.g. ['Python', 'AI', 'OpenGraph'])",
                },
                "theme": {
                    "type": "string",
                    "description": "Theme palette ID (aurora, cyberpunk, dark, light, ocean, sunset, emerald, matrix, gold, monochrome)",
                },
                "layout": {
                    "type": "string",
                    "description": "Layout style (default, centered, split, minimal, dev_code, podcast, event_ticket)",
                },
                "template": {
                    "type": "string",
                    "description": "Preset template ID (modern-blog, tech-launch, podcast-episode, dev-tutorial, newsletter, minimalist, quote-card, event-summit, ecommerce-drop, changelog-release, documentation, split-showcase)",
                },
                "width": {
                    "type": "integer",
                    "description": "Width in pixels (default 1200)",
                },
                "height": {
                    "type": "integer",
                    "description": "Height in pixels (default 630)",
                },
                "site_name": {
                    "type": "string",
                    "description": "Site name or brand watermark displayed in the corner",
                },
                "reading_time_min": {
                    "type": "integer",
                    "description": "Estimated reading time in minutes",
                },
                "date_str": {
                    "type": "string",
                    "description": "Publication date string (e.g. 'Sep 16, 2026')",
                },
                "code_snippet": {
                    "type": "string",
                    "description": "Code snippet for dev_code layout or dev-tutorial template",
                },
                "code_language": {
                    "type": "string",
                    "description": "Programming language for code snippet",
                },
                "episode_number": {
                    "type": "string",
                    "description": "Episode or issue number (e.g. 'EP #42')",
                },
                "badge": {
                    "type": "string",
                    "description": "Custom badge pill text",
                },
                "format": {
                    "type": "string",
                    "enum": ["svg", "html", "json", "bmp"],
                    "description": "Output format: 'svg' (default), 'html' (preview wrapper), 'json' (structured card object), 'bmp' (BMP info)",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "og_batch_generate",
        "description": "Generate multiple cards from an array of post titles/metadata in a single batch operation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "subtitle": {"type": "string"},
                            "author": {"type": "string"},
                            "category": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "theme": {"type": "string"},
                            "layout": {"type": "string"},
                            "template": {"type": "string"},
                            "site_name": {"type": "string"},
                        },
                        "required": ["title"],
                    },
                    "description": "Array of card metadata objects to generate",
                },
                "default_theme": {
                    "type": "string",
                    "description": "Default theme for cards without explicit theme",
                },
                "default_layout": {
                    "type": "string",
                    "description": "Default layout for cards without explicit layout",
                },
                "format": {
                    "type": "string",
                    "enum": ["svg", "json", "html"],
                    "description": "Output format per card (default: svg)",
                },
            },
            "required": ["cards"],
        },
    },
    {
        "name": "og_list_templates",
        "description": "List available built-in card templates with categories, layout bindings, and descriptions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by template category (blog, marketing, developer, audio, editorial, minimal, events, ecommerce)",
                }
            },
        },
    },
    {
        "name": "og_list_themes",
        "description": "List available color palettes, gradients, and theme definitions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by theme mode ('dark' or 'light')",
                }
            },
        },
    },
    {
        "name": "og_render_html_meta",
        "description": "Generate HTML <meta property=\"og:...\"> and Twitter card tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Page and social card title (required)",
                },
                "image_url": {
                    "type": "string",
                    "description": "Absolute URL to the generated Open Graph image (required)",
                },
                "description": {
                    "type": "string",
                    "description": "Page and social card description",
                },
                "url": {
                    "type": "string",
                    "description": "Canonical URL of the target page",
                },
                "site_name": {
                    "type": "string",
                    "description": "Website or brand publication name",
                },
                "twitter_handle": {
                    "type": "string",
                    "description": "Twitter @handle for creator/site attribution",
                },
                "twitter_card": {
                    "type": "string",
                    "enum": ["summary_large_image", "summary"],
                    "description": "Twitter card type (default: summary_large_image)",
                },
                "card_type": {
                    "type": "string",
                    "description": "Open Graph type (e.g. 'article', 'website', 'product')",
                },
                "published_time": {
                    "type": "string",
                    "description": "ISO 8601 published date/time",
                },
                "author": {
                    "type": "string",
                    "description": "Author name",
                },
                "section": {
                    "type": "string",
                    "description": "Article category / section",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Article keyword tags",
                },
            },
            "required": ["title", "image_url"],
        },
    },
    {
        "name": "og_diagnostics",
        "description": "Multi-OS diagnostics check: verifies environment, platform capabilities, encoding, and template readiness.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "detailed": {
                    "type": "boolean",
                    "description": "Include verbose system and runtime environment metrics",
                }
            },
        },
    },
    {
        "name": "og_audit_accessibility",
        "description": "Audit Open Graph card accessibility against WCAG 2.2 AA/AAA contrast criteria and calculate social platform readability scores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "description": "Theme palette ID to audit (aurora, cyberpunk, dark, light, ocean, sunset, emerald, matrix, gold, monochrome)",
                },
                "template": {
                    "type": "string",
                    "description": "Preset template ID to audit",
                },
                "title": {
                    "type": "string",
                    "description": "Card title (optional, defaults to sample title)",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Card subtitle (optional)",
                },
            },
        },
    },
    {
        "name": "og_generate_schema_ld",
        "description": "Generate complete Schema.org Rich Snippet JSON-LD for an Open Graph social card (Article, BlogPosting, Event, PodcastEpisode, TechArticle).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Main title / headline (required)",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Description / subtitle text",
                },
                "page_url": {
                    "type": "string",
                    "description": "Canonical page URL",
                },
                "image_url": {
                    "type": "string",
                    "description": "URL of the social card image",
                },
                "author": {
                    "type": "string",
                    "description": "Author name",
                },
                "schema_type": {
                    "type": "string",
                    "description": "Schema.org type (BlogPosting, Article, Event, PodcastEpisode, TechArticle, WebPage)",
                },
                "publisher_name": {
                    "type": "string",
                    "description": "Publisher / organization name",
                },
            },
            "required": ["title"],
        },
    },
]

MCP_RESOURCES = [
    {
        "uri": "og://templates",
        "name": "OG Canvas Templates Catalog",
        "description": "Comprehensive JSON catalog of built-in Open Graph social card templates with layout and theme bindings.",
        "mimeType": "application/json",
    },
    {
        "uri": "og://themes",
        "name": "OG Canvas Themes and Palettes",
        "description": "JSON catalog of color themes, gradient stops, accent colors, and background definitions.",
        "mimeType": "application/json",
    },
    {
        "uri": "og://specs/social-card-guide",
        "name": "Social Media Card Dimensions and Best Practices Guide",
        "description": "Complete reference guide for social platform OG image specs, aspect ratios, safe zones, and typography guidelines.",
        "mimeType": "text/markdown",
    },
]

MCP_PROMPTS = [
    {
        "name": "og_card_builder_prompt",
        "description": "Interactive assistant prompt for crafting click-worthy social card designs tailored to content type and target audience.",
        "arguments": [
            {
                "name": "title",
                "description": "The article or project title",
                "required": True,
            },
            {
                "name": "content_type",
                "description": "Type of content (blog, release, tutorial, podcast, newsletter, portfolio)",
                "required": False,
            },
            {
                "name": "target_audience",
                "description": "Target audience (e.g. software engineers, designers, executives)",
                "required": False,
            },
            {
                "name": "tone",
                "description": "Visual tone (modern, playful, minimal, technical, bold, vibrant)",
                "required": False,
            },
        ],
    },
    {
        "name": "og_social_campaign_prompt",
        "description": "Assistant prompt for generating consistent social banners across a multi-article series or marketing launch.",
        "arguments": [
            {
                "name": "campaign_name",
                "description": "Name of the campaign or series",
                "required": True,
            },
            {
                "name": "article_count",
                "description": "Number of articles/posts in the series (default: 3)",
                "required": False,
            },
            {
                "name": "primary_theme",
                "description": "Consistent base theme (e.g. aurora, cyberpunk, dark)",
                "required": False,
            },
            {
                "name": "brand_name",
                "description": "Brand or publication name",
                "required": False,
            },
        ],
    },
]

SOCIAL_CARD_SPECS_GUIDE = """# Open Graph Social Card Specifications & Best Practices Guide

## 1. Platform Resolution & Aspect Ratio Standards

| Platform | Recommended Resolution | Aspect Ratio | Safe Margin | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Standard Open Graph (FB/OG)** | 1200 × 630 px | 1.91 : 1 | 40 px | Universally supported standard |
| **Twitter / X Large Summary** | 1200 × 675 px / 1200 × 630 px | 16 : 9 / 1.91 : 1 | 50 px | Use `twitter:card` `summary_large_image` |
| **LinkedIn Feed Post** | 1200 × 627 px | 1.91 : 1 | 40 px | Auto-crops top/bottom on mobile |
| **Discord Embedded Link** | 1200 × 630 px | 1.91 : 1 | 30 px | Dark theme embed container |
| **Slack Unfurl Link** | 1200 × 630 px | 1.91 : 1 | 40 px | Displayed in chat threads |
| **Square (Instagram / Feed)** | 1080 × 1080 px | 1 : 1 | 60 px | Best for multi-channel posts |
| **Vertical Story / Reels** | 1080 × 1920 px | 9 : 16 | 120 px | Keep title in middle vertical 60% |
| **Header Banner** | 1500 × 500 px | 3 : 1 | 60 px | Twitter / GitHub profile banners |

---

## 2. Typography & Visual Safe Zones
- **Title**: Font size 48px - 64px, bold (800 weight), max 3 lines (40 - 70 characters optimal).
- **Subtitle**: Font size 20px - 26px, regular (400 weight), max 2 lines (80 - 120 characters optimal).
- **Category Badge**: Font size 12px - 14px uppercase with tracking/letter-spacing.
- **Safe Zone**: Always maintain at least 48px padding from all four outer boundaries to prevent platform UI clipping.

---

## 3. Accessibility & Contrast
- Minimum WCAG AA contrast ratio of 4.5:1 between text and background.
- Test both light and dark backgrounds.
- Avoid low-contrast pastels for critical headline text.

---

## 4. Required HTML Meta Tags
```html
<meta property="og:title" content="Your Article Headline">
<meta property="og:description" content="Your concise description.">
<meta property="og:image" content="https://yourdomain.com/og-card.svg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Your Article Headline">
<meta name="twitter:image" content="https://yourdomain.com/og-card.svg">
```
"""

# ============================================================================
# DIAGNOSTICS HANDLER
# ============================================================================


def run_diagnostics(detailed: bool = False) -> Dict[str, Any]:
    """Perform multi-OS diagnostics check."""
    p_info = get_platform_info()
    res: Dict[str, Any] = {
        "status": "OK",
        "service": SERVER_NAME,
        "version": SERVER_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "platform": {
            "os_name": p_info.os_name,
            "system": p_info.system,
            "release": p_info.release,
            "is_windows": p_info.is_windows,
            "is_linux": p_info.is_linux,
            "is_macos": p_info.is_macos,
            "is_termux": p_info.is_termux,
            "is_wsl": p_info.is_wsl,
            "python_version": p_info.python_version,
        },
        "catalogs": {
            "templates_count": len(TEMPLATES_CATALOG),
            "themes_count": len(THEMES_CATALOG),
            "tools_count": len(MCP_TOOLS),
            "resources_count": len(MCP_RESOURCES),
            "prompts_count": len(MCP_PROMPTS),
        },
        "terminal": {
            "isatty": sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False,
            "stdout_encoding": getattr(sys.stdout, "encoding", "utf-8"),
            "no_color_env": bool(os.environ.get("NO_COLOR")),
        },
    }

    if detailed:
        res["detailed_environment"] = {
            "sys_executable": sys.executable,
            "sys_path": sys.path[:5],
            "cwd": str(Path.cwd()),
            "templates_available": list(TEMPLATES_CATALOG.keys()),
            "themes_available": list(THEMES_CATALOG.keys()),
        }

    return res


# ============================================================================
# TOOL EXECUTION HANDLER
# ============================================================================


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an MCP tool by name and return content response or error."""
    tool_key = name.strip().lower()
    if tool_key in ("og_generate_card", "generate_og_card", "generate_card"):
        title = arguments.get("title")
        if not title:
            return {
                "content": [{"type": "text", "text": "Error: 'title' is required"}],
                "isError": True,
            }

        fmt = arguments.get("format", "svg").lower()
        width = int(arguments.get("width", 1200))
        height = int(arguments.get("height", 630))

        config = OGCardConfig(
            title=title,
            subtitle=arguments.get("subtitle"),
            author=AuthorSpec(name=arguments["author"]) if arguments.get("author") else None,
            category=arguments.get("category"),
            tags=arguments.get("tags", []),
            theme=arguments.get("theme", "aurora"),
            layout=CardLayout.from_str(arguments.get("layout", "default")),
            dimensions=CardDimension(width, height, f"{width}x{height}"),
            site_name=arguments.get("site_name"),
            reading_time_min=arguments.get("reading_time_min"),
            date_str=arguments.get("date_str"),
            code_snippet=arguments.get("code_snippet"),
            code_language=arguments.get("code_language"),
            episode_number=arguments.get("episode_number"),
            badge=BadgeSpec(text=arguments["badge"]) if arguments.get("badge") else None,
        )

        card = generate_card(config, template=arguments.get("template"))

        if fmt == "html":
            html_preview = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(card.title)} - Preview</title>
  {card.html_meta}
  <style>
    body {{ margin: 0; background: #0b0f19; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: system-ui; }}
    .card-container {{ max-width: 90vw; max-height: 90vh; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7); border-radius: 16px; overflow: hidden; }}
    svg {{ display: block; width: 100%; height: auto; }}
  </style>
</head>
<body>
  <div class="card-container">
    {card.svg}
  </div>
</body>
</html>"""
            return {"content": [{"type": "text", "text": html_preview}], "isError": False}

        elif fmt == "json":
            data = {
                "title": card.title,
                "width": card.width,
                "height": card.height,
                "theme": card.config.theme if isinstance(card.config.theme, str) else card.config.theme.id,
                "layout": card.config.layout.value if isinstance(card.config.layout, CardLayout) else str(card.config.layout),
                "svg": card.svg,
                "html_meta": card.html_meta,
            }
            return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "isError": False}

        elif fmt == "bmp":
            bmp_bytes = card.to_bmp()
            return {
                "content": [{
                    "type": "text",
                    "text": f"Successfully rasterized 24-bit BMP image ({card.width}x{card.height}, {len(bmp_bytes)} bytes).",
                }],
                "isError": False,
            }

        # Default: SVG output
        return {"content": [{"type": "text", "text": card.svg}], "isError": False}

    elif tool_key in ("og_batch_generate", "batch_generate", "batch_generate_cards"):
        cards_input = arguments.get("cards", [])
        if not isinstance(cards_input, list) or not cards_input:
            return {
                "content": [{"type": "text", "text": "Error: 'cards' array is required and must not be empty"}],
                "isError": True,
            }

        def_theme = arguments.get("default_theme", "aurora")
        def_layout = arguments.get("default_layout", "default")
        fmt = arguments.get("format", "svg").lower()

        results: List[Dict[str, Any]] = []
        for idx, item in enumerate(cards_input):
            if not isinstance(item, dict) or "title" not in item:
                continue
            card_cfg = OGCardConfig(
                title=item["title"],
                subtitle=item.get("subtitle"),
                author=AuthorSpec(name=item["author"]) if item.get("author") else None,
                category=item.get("category"),
                tags=item.get("tags", []),
                theme=item.get("theme", def_theme),
                layout=CardLayout.from_str(item.get("layout", def_layout)),
                site_name=item.get("site_name"),
            )
            generated = generate_card(card_cfg, template=item.get("template"))
            results.append({
                "index": idx,
                "title": generated.title,
                "dimensions": {"width": generated.width, "height": generated.height},
                "svg": generated.svg if fmt == "svg" else None,
                "html_meta": generated.html_meta if fmt == "html" else None,
            })

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"count": len(results), "cards": results}, indent=2),
            }],
            "isError": False,
        }

    elif tool_key in ("og_list_templates", "list_templates", "get_templates"):
        category = arguments.get("category")
        templates = list_templates(category)
        data = [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "default_layout": t.config.layout.value if isinstance(t.config.layout, CardLayout) else str(t.config.layout),
                "default_theme": t.config.theme if isinstance(t.config.theme, str) else t.config.theme.id,
                "sample_data": t.sample_data,
            }
            for t in templates
        ]
        return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "isError": False}

    elif tool_key in ("og_list_themes", "list_themes", "get_themes"):
        category = arguments.get("category")
        themes = list_themes(category)
        data = [t.to_dict() for t in themes]
        return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "isError": False}

    elif tool_key in ("og_render_html_meta", "render_html_meta", "render_meta", "og_meta"):
        title = arguments.get("title")
        image_url = arguments.get("image_url")
        if not title or not image_url:
            return {
                "content": [{"type": "text", "text": "Error: 'title' and 'image_url' are required"}],
                "isError": True,
            }
        meta_html = render_html_meta(
            title=title,
            image_url=image_url,
            description=arguments.get("description"),
            url=arguments.get("url"),
            site_name=arguments.get("site_name"),
            twitter_handle=arguments.get("twitter_handle"),
            twitter_card=arguments.get("twitter_card", "summary_large_image"),
            card_type=arguments.get("card_type", "article"),
            published_time=arguments.get("published_time"),
            author=arguments.get("author"),
            section=arguments.get("section"),
            tags=arguments.get("tags"),
        )
        return {"content": [{"type": "text", "text": meta_html}], "isError": False}

    elif tool_key in ("og_diagnostics", "diagnostics", "doctor", "platform"):
        detailed = bool(arguments.get("detailed", False))
        diag = run_diagnostics(detailed=detailed)
        return {"content": [{"type": "text", "text": json.dumps(diag, indent=2)}], "isError": False}

    elif tool_key in ("og_audit_accessibility", "audit_accessibility", "audit_card_accessibility"):
        theme_id = arguments.get("theme", "aurora")
        template_id = arguments.get("template")
        title = arguments.get("title", "Sample Card Headline")
        subtitle = arguments.get("subtitle", "Sample Card Subtitle")
        from .card_generator import validate_card_accessibility
        if template_id:
            report = validate_card_accessibility(template_id)
        else:
            cfg = OGCardConfig(title=title, subtitle=subtitle, theme=theme_id)
            report = validate_card_accessibility(cfg)
        return {
            "content": [{"type": "text", "text": json.dumps(report.to_dict(), indent=2)}],
            "isError": False,
        }

    elif tool_key in ("og_generate_schema_ld", "generate_schema_ld", "schema_json_ld"):
        title = arguments.get("title")
        if not title:
            return {"content": [{"type": "text", "text": "Error: 'title' is required"}], "isError": True}
        from .card_generator import generate_schema_json_ld
        cfg = OGCardConfig(
            title=title,
            subtitle=arguments.get("subtitle"),
            author=AuthorSpec(name=arguments["author"]) if arguments.get("author") else None,
            site_name=arguments.get("publisher_name"),
            layout=arguments.get("layout", "default"),
        )
        schema_code = generate_schema_json_ld(
            cfg,
            page_url=arguments.get("page_url"),
            image_url=arguments.get("image_url"),
            schema_type=arguments.get("schema_type"),
            publisher_name=arguments.get("publisher_name"),
        )
        return {"content": [{"type": "text", "text": schema_code}], "isError": False}

    else:
        return {
            "content": [{"type": "text", "text": f"Error: Tool '{name}' not found"}],
            "isError": True,
        }


# ============================================================================
# RESOURCE HANDLER
# ============================================================================


def read_resource(uri: str) -> Optional[Dict[str, Any]]:
    """Read resource by URI."""
    if uri == "og://templates":
        data = [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "default_layout": t.config.layout.value if isinstance(t.config.layout, CardLayout) else str(t.config.layout),
                "default_theme": t.config.theme if isinstance(t.config.theme, str) else t.config.theme.id,
                "sample_data": t.sample_data,
            }
            for t in TEMPLATES_CATALOG.values()
        ]
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(data, indent=2),
            }]
        }

    elif uri == "og://themes":
        data = [t.to_dict() for t in THEMES_CATALOG.values()]
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(data, indent=2),
            }]
        }

    elif uri == "og://specs/social-card-guide":
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "text/markdown",
                "text": SOCIAL_CARD_SPECS_GUIDE,
            }]
        }

    return None


# ============================================================================
# PROMPT HANDLER
# ============================================================================


def get_prompt(name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate prompt messages for interactive assistant workflows."""
    if name == "og_card_builder_prompt":
        title = arguments.get("title", "My New Post")
        content_type = arguments.get("content_type", "blog")
        audience = arguments.get("target_audience", "developers and creators")
        tone = arguments.get("tone", "modern")

        system_instruction = f"""You are the OG Canvas Forge Design Assistant.
Your goal is to help craft high-impact social preview cards for '{title}'.
Content type: {content_type} | Target audience: {audience} | Desired tone: {tone}.

Recommended Workflow:
1. Select the best matching template (e.g. 'modern-blog', 'tech-launch', 'dev-tutorial', 'newsletter', 'podcast-episode').
2. Choose a harmonious color theme (e.g. 'aurora' for engineering, 'cyberpunk' for releases/AI, 'sunset' for podcasts, 'ocean' for editorial).
3. Craft a punchy subtitle (under 90 chars) that creates curiosity.
4. Call `og_generate_card` with the configured parameters.
5. Provide the user with the SVG vector preview and HTML meta tags."""

        return {
            "description": f"OG Card Builder for '{title}'",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please design an Open Graph social card for '{title}' ({content_type}, targeting {audience}, tone: {tone}).",
                    },
                },
                {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": system_instruction,
                    },
                },
            ],
        }

    elif name == "og_social_campaign_prompt":
        campaign = arguments.get("campaign_name", "Product Launch")
        count = arguments.get("article_count", "3")
        theme = arguments.get("primary_theme", "aurora")
        brand = arguments.get("brand_name", "Our Publication")

        campaign_instruction = f"""You are coordinating a cohesive social media visual campaign for '{campaign}'.
Total pieces in series: {count} | Consistent Theme: {theme} | Brand: {brand}.

Strategy:
- Maintain consistent palette ({theme}) and typography across all cards for instant brand recognition.
- Vary the badge/category and layout archetype per post (e.g. Post 1: 'Overview' in centered layout, Post 2: 'Deep Dive' in split layout, Post 3: 'Changelog' in dev_code layout).
- Batch generate the complete card set using `og_batch_generate`."""

        return {
            "description": f"Social Campaign Planner for '{campaign}'",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Generate a consistent {count}-card social preview campaign for '{campaign}' under brand '{brand}' using theme '{theme}'.",
                    },
                },
                {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": campaign_instruction,
                    },
                },
            ],
        }

    return None


# ============================================================================
# JSON-RPC 2.0 PROTOCOL ENGINE & REQUEST DISPATCHER
# ============================================================================


def handle_jsonrpc_request(request: Union[Dict[str, Any], str]) -> Optional[Dict[str, Any]]:
    """Process a JSON-RPC 2.0 request dictionary or string and return the response."""
    if isinstance(request, str):
        try:
            req_obj = json.loads(request)
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON payload",
                    "data": str(e),
                },
            }
    else:
        req_obj = request

    if not isinstance(req_obj, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid Request: Expected JSON object"},
        }

    # Protocol fields
    req_id = req_obj.get("id")
    method = req_obj.get("method")
    params = req_obj.get("params", {})

    # Check if notification (no id)
    is_notification = (req_id is None)

    # 1. Initialize Handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                    "logging": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "instructions": "og-canvas-forge: High-performance pure-Python Open Graph social card synthesis and MCP server. Generates vector SVGs and HTML meta tags.",
            },
        }

    # 2. Initialized Notification
    elif method == "notifications/initialized":
        return None

    # 3. Ping
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 4. Tools List
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    # 5. Tools Call
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Invalid params: 'name' is required"},
            }
        result = execute_tool(tool_name, args)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    # 6. Resources List
    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": MCP_RESOURCES},
        }

    # 7. Resources Read
    elif method == "resources/read":
        uri = params.get("uri")
        if not uri:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Invalid params: 'uri' is required"},
            }
        res_data = read_resource(uri)
        if res_data is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32002, "message": f"Resource not found: '{uri}'"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": res_data}

    # 8. Prompts List
    elif method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"prompts": MCP_PROMPTS},
        }

    # 9. Prompts Get
    elif method == "prompts/get":
        prompt_name = params.get("name")
        prompt_args = params.get("arguments", {})
        if not prompt_name:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Invalid params: 'name' is required"},
            }
        prompt_data = get_prompt(prompt_name, prompt_args)
        if prompt_data is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32001, "message": f"Prompt not found: '{prompt_name}'"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": prompt_data}

    # Method not found
    else:
        if is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: '{method}'"},
        }


def process_request(raw_input: str) -> Optional[str]:
    """Process raw input string from client and return serialized response string."""
    clean = raw_input.strip()
    if not clean:
        return None
    res = handle_jsonrpc_request(clean)
    if res is None:
        return None
    return json.dumps(res)


# ============================================================================
# STDIO SERVER RUNNER (Framing Support for Line-Delimited & Content-Length)
# ============================================================================


def run_stdio_server() -> None:
    """Run interactive MCP JSON-RPC 2.0 stdio server loop."""
    # Ensure stdout/stdin work smoothly with UTF-8
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    content_length_header = re.compile(r"^Content-Length:\s*(\d+)", re.IGNORECASE)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            line_strip = line.strip()
            if not line_strip:
                continue

            payload: Optional[str] = None

            # Check for LSP/MCP Content-Length header framing
            m = content_length_header.match(line_strip)
            if m:
                length = int(m.group(1))
                # Skip empty lines until body
                while True:
                    header_line = sys.stdin.readline()
                    if not header_line or header_line.strip() == "":
                        break
                # Read exact content length
                payload = sys.stdin.read(length)
            elif line_strip.startswith("{"):
                # Line-delimited JSON
                payload = line_strip

            if payload:
                response = process_request(payload)
                if response:
                    # Write response as line-delimited JSON
                    sys.stdout.write(response + "\n")
                    sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal server error: {e}"},
            }
            try:
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
            except Exception:
                pass


def main() -> None:
    """Entry point for running MCP server directly."""
    run_stdio_server()


if __name__ == "__main__":
    main()
