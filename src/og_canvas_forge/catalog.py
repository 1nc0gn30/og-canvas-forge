"""Template catalog, preset library, and high-level card generation factory.

Provides 16+ preconfigured templates across tech blogging, open source, AI research,
podcasts, events, newsletters, e-commerce, and developer tools.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .card_generator import generate_card as _generate_card_impl
from .gradients import get_theme, list_themes
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

# ---------------------------------------------------------------------------
# 16+ Built-in Template Presets
# ---------------------------------------------------------------------------

_TEMPLATES: Dict[str, TemplatePreset] = {
    "tech_blog": TemplatePreset(
        id="tech_blog",
        name="Modern Tech Blog Post",
        category="blog",
        description="Clean editorial layout with category badge, reading time, author, and date.",
        config=OGCardConfig(
            title="Building High-Throughput Distributed Pipelines in Python",
            subtitle="Architectural patterns, memory management, and zero-copy data streaming.",
            author=AuthorSpec(name="Alex Rivera", handle="@arivera", title="Staff Engineer"),
            category="Engineering",
            tags=["python", "distributed-systems", "performance"],
            site_name="Engineering Insights",
            theme="aurora",
            layout=CardLayout.DEFAULT,
            dimensions=CardDimension.STANDARD_OG,
            pattern="dot_grid",
            reading_time_min=6,
            date_str="September 2026",
        ),
    ),
    "github_repo": TemplatePreset(
        id="github_repo",
        name="Open Source GitHub Repository",
        category="developer",
        description="Terminal IDE layout with live code preview and repository stats.",
        config=OGCardConfig(
            title="facebook/react",
            subtitle="★ 225k stars  •  ⑂ 45k forks  •  MIT License",
            author=AuthorSpec(name="React Core Team", handle="@reactjs"),
            category="Open Source",
            site_name="github.com/facebook/react",
            theme="deep_obsidian",
            layout=CardLayout.DEV_CODE,
            dimensions=CardDimension.STANDARD_OG,
            pattern="circuits",
            code_snippet="""import { useState, useEffect } from 'react';

function LiveCounter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}""",
            code_language="TypeScript",
        ),
    ),
    "saas_launch": TemplatePreset(
        id="saas_launch",
        name="SaaS Feature Launch",
        category="marketing",
        description="Split-pane showcase with glowing badge and feature highlights.",
        config=OGCardConfig(
            title="Introducing Canvas Engine 3.0: Real-time Vector Graphics",
            subtitle="Sub-millisecond SVG rendering with built-in GPU acceleration and web-ready meta generation.",
            site_name="CanvasForge Cloud",
            badge=BadgeSpec(text="NEW RELEASE", icon_svg="sparkles"),
            theme="cyber_neon",
            layout=CardLayout.SPLIT,
            dimensions=CardDimension.STANDARD_OG,
            pattern="hex_grid",
        ),
    ),
    "ai_research": TemplatePreset(
        id="ai_research",
        name="AI Research Paper / arXiv",
        category="research",
        description="Minimalist high-contrast layout for academic preprints and research papers.",
        config=OGCardConfig(
            title="Attention Calibration in Latent Diffusion Architectures",
            subtitle="Demystifying spatial self-attention dynamics across high-resolution image synthesis pipelines.",
            author=AuthorSpec(name="Dr. Elena Vance et al.", title="Deep Generative Lab"),
            category="arXiv:2609.08192 [cs.CV]",
            site_name="arXiv Preprint",
            theme="nordic_frost",
            layout=CardLayout.MINIMAL,
            dimensions=CardDimension.STANDARD_OG,
            pattern="blueprint",
            date_str="Published Sep 2026",
        ),
    ),
    "podcast_episode": TemplatePreset(
        id="podcast_episode",
        name="Podcast Episode Cover",
        category="audio",
        description="Album cover frame with soundwave visualizer and host attribution.",
        config=OGCardConfig(
            title="The Future of Autonomous AI Agents in Production",
            subtitle="With guest Dr. Sarah Chen, VP of AI Systems at Neural Labs",
            site_name="The Silicon Latent Podcast",
            episode_number="EP. 142",
            theme="sunset_velvet",
            layout=CardLayout.PODCAST,
            dimensions=CardDimension.STANDARD_OG,
            pattern="rings",
            reading_time_min=48,
        ),
    ),
    "youtube_thumbnail": TemplatePreset(
        id="youtube_thumbnail",
        name="YouTube Video Thumbnail",
        category="video",
        description="High-impact centered typography designed for maximum click-through clarity.",
        config=OGCardConfig(
            title="I Built an Operating System in 24 Hours",
            subtitle="From Bootloader to GUI Desktop in Rust",
            author=AuthorSpec(name="Tech Lead Studio"),
            badge=BadgeSpec(text="MUST WATCH"),
            site_name="Tech Lead Studio",
            theme="solar_flare",
            layout=CardLayout.CENTERED,
            dimensions=CardDimension.YOUTUBE_THUMBNAIL,
            pattern="hatching",
        ),
    ),
    "event_ticket": TemplatePreset(
        id="event_ticket",
        name="Developer Conference Ticket",
        category="events",
        description="Perforated ticket stub with barcode, event details, and admit-one badge.",
        config=OGCardConfig(
            title="Global Developer Summit 2026",
            subtitle="Moscone Center, San Francisco • Hall A & B",
            category="VIP ALL ACCESS",
            ticket_number="PASS #0894",
            site_name="GDS 2026",
            theme="emerald_matrix",
            layout=CardLayout.EVENT_TICKET,
            dimensions=CardDimension.STANDARD_OG,
            pattern="crosses",
            date_str="OCT 18-20, 2026",
        ),
    ),
    "cyber_announcement": TemplatePreset(
        id="cyber_announcement",
        name="Security & Cyber Advisory",
        category="security",
        description="Terminal alert layout for vulnerability advisories and security releases.",
        config=OGCardConfig(
            title="CRITICAL: Memory Safety Patch for Linux Kernel 6.12",
            subtitle="Immediate update recommended for all edge production nodes.",
            category="CVE-2026-8941",
            badge=BadgeSpec(text="SECURITY ADVISORY", bg_color="rgba(239, 68, 68, 0.2)", text_color="#ef4444"),
            site_name="Security Response Center",
            theme="crimson_ember",
            layout=CardLayout.DEV_CODE,
            dimensions=CardDimension.STANDARD_OG,
            pattern="circuits",
            code_snippet="""# Verification & Hotfix Patch
curl -fsSL https://security.kernel.org/patch-6.12.9.sh | sudo bash
sudo sysctl -w kernel.kptr_restrict=2""",
            code_language="Bash",
        ),
    ),
    "newsletter_edition": TemplatePreset(
        id="newsletter_edition",
        name="Weekly Engineering Newsletter",
        category="newsletter",
        description="Centered editorial card for weekly email newsletters and substacks.",
        config=OGCardConfig(
            title="The Pragmatic Architect #84: Zero-Downtime Database Migrations",
            subtitle="Schema evolutions, lock-free tables, and dual-write replication patterns.",
            author=AuthorSpec(name="Marcus Sterling", handle="@msterling"),
            badge=BadgeSpec(text="ISSUE #84"),
            site_name="The Pragmatic Architect",
            theme="dracula",
            layout=CardLayout.CENTERED,
            dimensions=CardDimension.STANDARD_OG,
            pattern="dot_grid",
            reading_time_min=8,
            date_str="September 16, 2026",
        ),
    ),
    "changelog_update": TemplatePreset(
        id="changelog_update",
        name="Product Changelog / Release Notes",
        category="product",
        description="Split view highlighting product features, speed improvements, and version numbers.",
        config=OGCardConfig(
            title="Changelog v4.2: Lightning Fast Cold Starts & Global Edge CDN",
            subtitle="50% reduction in p99 latency and automatic Brotli compression on all endpoints.",
            badge=BadgeSpec(text="VERSION 4.2"),
            site_name="Changelog",
            theme="tokyo_night",
            layout=CardLayout.SPLIT,
            dimensions=CardDimension.STANDARD_OG,
            pattern="blueprint",
        ),
    ),
    "e_commerce_product": TemplatePreset(
        id="e_commerce_product",
        name="Digital Product & SaaS Tier",
        category="commerce",
        description="Minimalist luxury gold layout for premium products, courses, and SaaS subscriptions.",
        config=OGCardConfig(
            title="Forge Studio Pro: The Complete Developer Toolkit",
            subtitle="Unlock unlimited cloud builds, collaborative canvases, and priority support.",
            badge=BadgeSpec(text="$49 / LIFETIME"),
            site_name="Forge Studio",
            theme="royal_gold",
            layout=CardLayout.MINIMAL,
            dimensions=CardDimension.STANDARD_OG,
            pattern="dot_grid",
        ),
    ),
    "course_masterclass": TemplatePreset(
        id="course_masterclass",
        name="Online Course / Masterclass",
        category="education",
        description="Synthwave centered card for programming tutorials and masterclasses.",
        config=OGCardConfig(
            title="Mastering Modern Asynchronous Systems in Rust",
            subtitle="12 Modules • 48 Hands-on Labs • Real-world Actor Framework Projects",
            author=AuthorSpec(name="Sophia Lin", title="Principal Rust Instructor"),
            badge=BadgeSpec(text="COMPLETE MASTERCLASS"),
            site_name="Academy of Code",
            theme="synthwave_purple",
            layout=CardLayout.CENTERED,
            dimensions=CardDimension.STANDARD_OG,
            pattern="hex_grid",
        ),
    ),
    "api_docs": TemplatePreset(
        id="api_docs",
        name="API Documentation & Endpoint Reference",
        category="developer",
        description="Developer code layout showcasing REST/GraphQL endpoint signatures.",
        config=OGCardConfig(
            title="POST /v1/cards/synthesize",
            subtitle="Generate deterministic SVG & raster assets via JSON payload.",
            category="REST API Reference",
            site_name="CanvasForge API Docs",
            theme="deep_obsidian",
            layout=CardLayout.DEV_CODE,
            dimensions=CardDimension.STANDARD_OG,
            pattern="circuits",
            code_snippet="""curl -X POST https://api.canvasforge.io/v1/cards/synthesize \\
  -H "Authorization: Bearer $FORGE_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"template": "tech_blog", "title": "Production AI"}'""",
            code_language="cURL",
        ),
    ),
    "job_opening": TemplatePreset(
        id="job_opening",
        name="Tech Career & Job Opening",
        category="hiring",
        description="Clean light-mode split card for hiring announcements and careers.",
        config=OGCardConfig(
            title="Senior Staff Systems Engineer",
            subtitle="San Francisco, CA / Remote • Competitive Equity & Full Benefits",
            badge=BadgeSpec(text="WE ARE HIRING"),
            site_name="Acme Infrastructure Inc.",
            theme="minimalist_white",
            layout=CardLayout.SPLIT,
            dimensions=CardDimension.STANDARD_OG,
            pattern="dot_grid",
        ),
    ),
    "design_system": TemplatePreset(
        id="design_system",
        name="Design System & UI Library",
        category="design",
        description="Google Aurora showcase for modern component libraries and UI design tokens.",
        config=OGCardConfig(
            title="Aurora UI: Next-Gen React Component System",
            subtitle="Accessible, themeable, and lightning fast components for web apps.",
            badge=BadgeSpec(text="DESIGN SYSTEM v2.0"),
            site_name="Aurora UI Kit",
            theme="google_aurora",
            layout=CardLayout.SPLIT,
            dimensions=CardDimension.STANDARD_OG,
            pattern="blueprint",
        ),
    ),
    "founder_story": TemplatePreset(
        id="founder_story",
        name="Founder Story & Case Study",
        category="story",
        description="Editorial centered storytelling layout with publication branding.",
        config=OGCardConfig(
            title="How We Scaled from 0 to 1,000,000 Users with Zero Marketing Budget",
            subtitle="The definitive guide to engineering-led growth and product mechanics.",
            author=AuthorSpec(name="David Miller", title="Founder & CEO", handle="@dmiller"),
            badge=BadgeSpec(text="FOUNDER ESSAYS"),
            site_name="Bootstrapped Founder Journal",
            theme="sunset_velvet",
            layout=CardLayout.CENTERED,
            dimensions=CardDimension.STANDARD_OG,
            pattern="dot_grid",
            reading_time_min=12,
        ),
    ),
    "mobile_story": TemplatePreset(
        id="mobile_story",
        name="Mobile Reel & Story Card",
        category="social",
        description="Vertical 9:16 aspect ratio (1080x1920) formatted for mobile stories.",
        config=OGCardConfig(
            title="Top 5 Python Performance Tips You Need in 2026",
            subtitle="Swipe up to read the full benchmark breakdown.",
            author=AuthorSpec(name="CodeCraft"),
            badge=BadgeSpec(text="QUICK TIP"),
            site_name="@codecraft_daily",
            theme="cyber_neon",
            layout=CardLayout.CENTERED,
            dimensions=CardDimension.STORY,
            pattern="dot_grid",
        ),
    ),
    "square_social": TemplatePreset(
        id="square_social",
        name="Square Instagram & Social Feed",
        category="social",
        description="Square 1:1 aspect ratio (1080x1080) for Instagram feed posts.",
        config=OGCardConfig(
            title="Clean Architecture vs. Microservices: The Honest Tradeoffs",
            subtitle="When to split monoliths and when to keep it simple.",
            author=AuthorSpec(name="Tech Architecture Daily"),
            badge=BadgeSpec(text="SWIPE FOR DETAILS"),
            site_name="techarchitecture.io",
            theme="dracula",
            layout=CardLayout.CENTERED,
            dimensions=CardDimension.SQUARE,
            pattern="hex_grid",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Catalog Access Functions
# ---------------------------------------------------------------------------

def get_template(template_id: str) -> TemplatePreset:
    """Retrieve template preset by ID, falling back to 'tech_blog'."""
    key = template_id.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _TEMPLATES:
        return _TEMPLATES[key]
    for t in _TEMPLATES.values():
        if t.name.lower() == key:
            return t
    return _TEMPLATES["tech_blog"]


def list_templates(category: Optional[str] = None) -> List[TemplatePreset]:
    """List all available template presets, optionally filtered by category."""
    if not category:
        return list(_TEMPLATES.values())
    cat_lower = category.strip().lower()
    return [t for t in _TEMPLATES.values() if t.category.lower() == cat_lower]


def get_all_templates() -> List[TemplatePreset]:
    """Return list of all built-in template presets."""
    return list(_TEMPLATES.values())


def generate_from_template(
    template_id: str,
    overrides: Optional[Dict[str, Any]] = None,
    image_url: Optional[str] = None,
    page_url: Optional[str] = None,
    **kwargs: Any,
) -> GeneratedCard:
    """Generate a card starting from a preconfigured template and applying overrides."""
    tpl = get_template(template_id)
    cfg = tpl.config

    combined_overrides: Dict[str, Any] = {}
    if overrides:
        combined_overrides.update(overrides)
    if kwargs:
        combined_overrides.update(kwargs)

    if combined_overrides:
        author_val = combined_overrides.get("author", cfg.author)
        if isinstance(author_val, str):
            author_val = AuthorSpec(name=author_val)
        badge_val = combined_overrides.get("badge", cfg.badge)
        layout_val = combined_overrides.get("layout", cfg.layout)
        dim_val = combined_overrides.get("dimensions", cfg.dimensions)

        cfg = OGCardConfig(
            title=combined_overrides.get("title", cfg.title),
            subtitle=combined_overrides.get("subtitle", cfg.subtitle),
            author=author_val,
            category=combined_overrides.get("category", cfg.category),
            tags=combined_overrides.get("tags", cfg.tags),
            site_name=combined_overrides.get("site_name", cfg.site_name),
            theme=combined_overrides.get("theme", cfg.theme),
            layout=layout_val,
            dimensions=dim_val,
            pattern=combined_overrides.get("pattern", cfg.pattern),
            logo_svg=combined_overrides.get("logo_svg", cfg.logo_svg),
            icon_svg=combined_overrides.get("icon_svg", cfg.icon_svg),
            reading_time_min=combined_overrides.get("reading_time_min", cfg.reading_time_min),
            date_str=combined_overrides.get("date_str", cfg.date_str),
            code_snippet=combined_overrides.get("code_snippet", cfg.code_snippet),
            code_language=combined_overrides.get("code_language", cfg.code_language),
            episode_number=combined_overrides.get("episode_number", cfg.episode_number),
            ticket_number=combined_overrides.get("ticket_number", cfg.ticket_number),
            badge=badge_val,
            watermark=combined_overrides.get("watermark", cfg.watermark),
            custom_css=combined_overrides.get("custom_css", cfg.custom_css),
        )

    return _generate_card_impl(cfg, image_url=image_url, page_url=page_url)


def generate_card_from_template(
    template_id: str,
    overrides: Optional[Dict[str, Any]] = None,
    image_url: Optional[str] = None,
    page_url: Optional[str] = None,
    **kwargs: Any,
) -> GeneratedCard:
    """Generate a card from template."""
    return generate_from_template(template_id, overrides=overrides, image_url=image_url, page_url=page_url, **kwargs)


def generate_card(
    config_or_template: Union[OGCardConfig, TemplatePreset, str],
    **kwargs: Any,
) -> GeneratedCard:
    """Unified entrypoint for generating cards from config, preset, or template name.

    Examples:
        >>> card = generate_card("tech_blog", title="My New Post")
        >>> card = generate_card(OGCardConfig(title="Custom Title", theme="cyber_neon"))
    """
    image_url = kwargs.pop("image_url", None)
    page_url = kwargs.pop("page_url", None)

    if isinstance(config_or_template, OGCardConfig):
        return _generate_card_impl(config_or_template, image_url=image_url, page_url=page_url)
    elif isinstance(config_or_template, TemplatePreset):
        return generate_from_template(config_or_template.id, overrides=kwargs, image_url=image_url, page_url=page_url)
    elif isinstance(config_or_template, str):
        return generate_from_template(config_or_template, overrides=kwargs, image_url=image_url, page_url=page_url)

    raise ValueError(f"Unsupported card configuration type: {type(config_or_template)}")

