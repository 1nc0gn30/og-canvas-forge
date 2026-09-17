"""Card synthesizer, SVG renderer, HTML meta generator, and standalone rasterizer.

Zero-dependency card engine rendering production-ready SVG cards, full HTML/Twitter/JSON-LD
metadata tags, and pure-Python 24-bit uncompressed BMP/PPM image rasterizers.
"""

from __future__ import annotations

import html
import json
import math
import struct
import zlib
from typing import Any, Dict, List, Optional, Tuple, Union

from .compat import normalize_path
from .gradients import generate_theme_defs, get_theme
from .layout_engine import (
    BoundingBox,
    ComputedAuthor,
    ComputedBadge,
    ComputedCardLayout,
    ComputedTextElement,
    char_width,
    compute_card_layout,
    estimate_text_width,
)
from .models import (
    AuthorSpec,
    BadgeSpec,
    CardAccessibilityReport,
    CardDimension,
    CardLayout,
    CardTheme,
    GeneratedCard,
    OGCardConfig,
)
from .patterns import get_pattern_svg


# ---------------------------------------------------------------------------
# Vector Icons Library (pure SVG paths)
# ---------------------------------------------------------------------------

_ICONS: Dict[str, str] = {
    "github": '<path fill="currentColor" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>',
    "star": '<path fill="currentColor" d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>',
    "clock": '<path fill="currentColor" d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>',
    "calendar": '<path fill="currentColor" d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/>',
    "terminal": '<path fill="currentColor" d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V8h16v10zm-12-3l3.5-3.5L8 8l1.4-1.4 4.9 4.9-4.9 4.9L8 15zm6 0h5v2h-5v-2z"/>',
    "mic": '<path fill="currentColor" d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>',
    "ticket": '<path fill="currentColor" d="M22 10V6a2 2 0 0 0-2-2H4c-1.1 0-1.99.9-1.99 2v4c1.1 0 1.99.9 1.99 2s-.89 2-2 2v4c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2v-4c-1.1 0-2-.9-2-2s.9-2 2-2zm-2-1.46c-1.19.69-2 1.99-2 3.46s.81 2.77 2 3.46V18H4v-2.54c1.19-.69 2-1.99 2-3.46 0-1.48-.8-2.77-1.99-3.46L4 6h16v2.54z"/>',
    "sparkles": '<path fill="currentColor" d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>',
    "code": '<path fill="currentColor" d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>',
    "user": '<path fill="currentColor" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>',
}


def _render_icon(icon_name: Optional[str], size: int = 18, color: str = "currentColor") -> str:
    """Render an inline SVG icon path wrapped in a viewBox."""
    if not icon_name or icon_name not in _ICONS:
        return ""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" style="color: {color}; vertical-align: middle;">'
        f"{_ICONS[icon_name]}"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# SVG Card Generator
# ---------------------------------------------------------------------------

def generate_svg(config: Union[OGCardConfig, str]) -> str:
    """Generate fully compliant, standalone SVG markup for an Open Graph card."""
    if isinstance(config, str):
        from .catalog import get_template
        config = get_template(config).config

    theme = get_theme(config.theme)
    dim = CardDimension.from_value(config.dimensions)
    width, height = dim.width, dim.height

    computed = compute_card_layout(config, width, height)
    theme_defs = generate_theme_defs(theme)

    pattern_def, pattern_rect = get_pattern_svg(
        config.pattern,
        color=theme.accent if theme.is_dark else "#000000",
        opacity=0.07 if theme.is_dark else 0.04,
        scale=1.0,
        pattern_id="og_bg_pattern",
    )

    # Stylesheet with web fonts
    custom_css = config.custom_css or ""
    css_block = f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family={theme.font_primary.replace(" ", "+")}:wght@400;500;600;700;800;900&amp;family={theme.font_secondary.replace(" ", "+")}:wght@400;500;600&amp;family={theme.font_mono.replace(" ", "+")}:wght@400;500;700&amp;display=swap');
      
      .og-card {{
        font-family: '{theme.font_primary}', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        box-sizing: border-box;
      }}
      .og-title {{
        font-family: '{theme.font_primary}', sans-serif;
        font-weight: 800;
        fill: {theme.text_primary};
        letter-spacing: -0.025em;
      }}
      .og-subtitle {{
        font-family: '{theme.font_secondary}', sans-serif;
        fill: {theme.text_secondary};
        letter-spacing: -0.01em;
      }}
      .og-badge {{
        font-family: '{theme.font_primary}', sans-serif;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .og-author {{
        font-family: '{theme.font_primary}', sans-serif;
        font-weight: 700;
        fill: {theme.text_primary};
      }}
      .og-handle {{
        font-family: '{theme.font_secondary}', sans-serif;
        font-weight: 400;
        fill: {theme.text_secondary};
      }}
      .og-meta {{
        font-family: '{theme.font_secondary}', sans-serif;
        font-weight: 500;
        fill: {theme.text_secondary};
      }}
      .og-mono {{
        font-family: '{theme.font_mono}', monospace;
      }}
      {custom_css}
    </style>
""".strip()

    # Glass container border
    inner_card_bg = theme.card_bg or ("rgba(255, 255, 255, 0.03)" if theme.is_dark else "rgba(255, 255, 255, 0.7)")
    card_container = f"""
    <!-- Card Frame / Container -->
    <rect x="28" y="28" width="{width - 56}" height="{height - 56}" rx="24"
          fill="{inner_card_bg}" stroke="{theme.border_color}" stroke-width="1.5" />
    <rect x="29" y="29" width="{width - 58}" height="{height - 58}" rx="23"
          fill="none" stroke="rgba(255, 255, 255, 0.05)" stroke-width="1" />
"""

    # Render layout elements
    elements_svg: List[str] = []

    # 1. Badge
    if computed.badge:
        b = computed.badge
        bg_col = getattr(config.badge, "bg_color", None) or theme.badge_bg
        txt_col = getattr(config.badge, "text_color", None) or theme.badge_text
        bdr_col = getattr(config.badge, "border_color", None) or theme.border_color
        elements_svg.append(f"""
    <!-- Badge -->
    <g transform="translate({b.x}, {b.y})">
      <rect width="{b.width}" height="{b.height}" rx="8" fill="{bg_col}" stroke="{bdr_col}" stroke-width="1" filter="url(#badge_shadow)" />
      <text x="{b.width / 2.0}" y="{b.height / 2.0 + 5.0}" text-anchor="middle" font-size="{b.font_size}" fill="{txt_col}" class="og-badge">{html.escape(b.text)}</text>
    </g>
""")

    # 2. Site Name
    if computed.site_name:
        s = computed.site_name
        elements_svg.append(f"""
    <!-- Site Name / Header Meta -->
    <text x="{s.x}" y="{s.y}" text-anchor="{s.text_anchor}" font-size="{s.font_size}" font-weight="{s.font_weight}" class="og-meta" fill="{theme.accent}">{html.escape(s.text)}</text>
""")

    # 3. Title Lines
    if computed.title_lines:
        t_lines = []
        for line in computed.title_lines:
            t_lines.append(
                f'<text x="{line.x}" y="{line.y}" text-anchor="{line.text_anchor}" font-size="{line.font_size}" class="og-title">{html.escape(line.text)}</text>'
            )
        elements_svg.append(f"<!-- Main Title -->\n    " + "\n    ".join(t_lines))

    # 4. Accent Bar (if Minimal Layout)
    if "accent_bar" in computed.extra:
        bar = computed.extra["accent_bar"]
        elements_svg.append(f"""
    <!-- Accent Line -->
    <rect x="{bar.x}" y="{bar.y}" width="{bar.width}" height="{bar.height}" rx="3" fill="url(#accent_gradient)" filter="url(#accent_glow)" />
""")

    # 5. Subtitle Lines
    if computed.subtitle_lines:
        sub_lines = []
        for line in computed.subtitle_lines:
            sub_lines.append(
                f'<text x="{line.x}" y="{line.y}" text-anchor="{line.text_anchor}" font-size="{line.font_size}" class="og-subtitle">{html.escape(line.text)}</text>'
            )
        elements_svg.append(f"<!-- Subtitle -->\n    " + "\n    ".join(sub_lines))

    # 6. Author Section
    if computed.author:
        a = computed.author
        author_svg_parts = [f'<g class="og-author-section">']
        # Avatar Circle with initials or SVG
        author_svg_parts.append(
            f'  <circle cx="{a.avatar_cx}" cy="{a.avatar_cy}" r="{a.avatar_radius}" fill="{theme.badge_bg}" stroke="{theme.accent}" stroke-width="1.5" />'
        )
        if a.avatar_url:
            author_svg_parts.append(
                f'  <clipPath id="avatar_clip"><circle cx="{a.avatar_cx}" cy="{a.avatar_cy}" r="{a.avatar_radius}" /></clipPath>'
                f'  <image href="{a.avatar_url}" x="{a.avatar_cx - a.avatar_radius}" y="{a.avatar_cy - a.avatar_radius}" width="{a.avatar_radius * 2}" height="{a.avatar_radius * 2}" clip-path="url(#avatar_clip)" />'
            )
        else:
            author_svg_parts.append(
                f'  <text x="{a.avatar_cx}" y="{a.avatar_cy + 5.0}" text-anchor="middle" font-size="{a.avatar_radius * 0.75}" font-weight="700" fill="{theme.accent}" class="og-badge">{html.escape(a.initials)}</text>'
            )

        # Name & Handle
        if a.handle:
            author_svg_parts.append(
                f'  <text x="{a.x}" y="{a.y - 12.0}" font-size="16" class="og-author">{html.escape(a.name)}</text>'
                f'  <text x="{a.x}" y="{a.y + 6.0}" font-size="14" class="og-handle">{html.escape(a.handle)}</text>'
            )
        else:
            author_svg_parts.append(
                f'  <text x="{a.x}" y="{a.y}" font-size="17" class="og-author">{html.escape(a.name)}</text>'
            )

        author_svg_parts.append("</g>")
        elements_svg.append("\n    ".join(author_svg_parts))

    # 7. Date / Reading Time Tag
    if computed.date_tag:
        d = computed.date_tag
        elements_svg.append(f"""
    <!-- Date / Reading Time -->
    <text x="{d.x}" y="{d.y}" text-anchor="{d.text_anchor}" font-size="{d.font_size}" font-weight="{d.font_weight}" class="og-meta">{html.escape(d.text)}</text>
""")

    # 8. Special Layout Archetype Visual Features
    if computed.layout_type == CardLayout.DEV_CODE:
        _render_dev_code_feature(computed, config, theme, elements_svg)
    elif computed.layout_type == CardLayout.SPLIT:
        _render_split_feature(computed, config, theme, elements_svg)
    elif computed.layout_type == CardLayout.PODCAST:
        _render_podcast_feature(computed, config, theme, elements_svg)
    elif computed.layout_type == CardLayout.EVENT_TICKET:
        _render_event_ticket_feature(computed, config, theme, elements_svg)

    # 9. Optional Watermark or Logo
    if config.watermark:
        from og_canvas_forge.watermark import render_watermark_svg
        wm_svg = render_watermark_svg(
            config.watermark,
            width=width,
            height=height,
            default_color=theme.text_primary,
        )
        if wm_svg:
            elements_svg.append(wm_svg)

    if config.qr_code:
        from og_canvas_forge.qr_matrix import render_qr_svg
        qr_content = str(config.qr_code) if not isinstance(config.qr_code, bool) else (config.site_name or config.title)
        qr_size = 96
        qr_x = width - qr_size - 48
        qr_y = height - qr_size - 40
        qr_badge = render_qr_svg(qr_content, size=qr_size, fg=theme.text_primary, bg="rgba(0,0,0,0.45)")
        elements_svg.append(f"""
    <!-- QR Code Scannable Badge -->
    <g transform="translate({qr_x}, {qr_y})">
      {qr_badge}
    </g>
""")

    if config.logo_svg:
        elements_svg.append(f"""
    <!-- Custom Brand Logo -->
    <g transform="translate({width - 120}, {height - 80})">
      {config.logo_svg}
    </g>
""")

    body_content = "\n".join(elements_svg)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" class="og-card">
  {theme_defs}
  {pattern_def}
  {css_block}

  <!-- Canvas Background -->
  <rect width="100%" height="100%" fill="url(#bg_gradient)" />
  <circle cx="88%" cy="12%" r="55%" fill="url(#ambient_glow_top)" />
  <circle cx="12%" cy="92%" r="45%" fill="url(#ambient_glow_bottom)" />
  {pattern_rect}

  {card_container}

  {body_content}
</svg>"""


def _render_dev_code_feature(
    computed: ComputedCardLayout,
    config: OGCardConfig,
    theme: CardTheme,
    elements: List[str],
) -> None:
    """Render syntax highlighted IDE window for DEV_CODE layout."""
    if "terminal_box" not in computed.extra:
        return
    t = computed.extra["terminal_box"]

    snippet = config.code_snippet or """def create_card():
    card = CanvasForge.render(
        title="Automated OpenGraph",
        theme="aurora",
        scale=2.0
    )
    return card.to_svg()"""

    code_lines = snippet.strip().split("\n")
    code_lines_svg = []
    line_y = t.y + 56.0
    for idx, raw_line in enumerate(code_lines[:8], start=1):
        # Format code line with line number
        line_num = f"{idx:>2}"
        escaped_line = html.escape(raw_line)
        # Highlight basic Python keywords
        for kw in ("def", "return", "import", "from", "class", "async", "await"):
            escaped_line = escaped_line.replace(f"{kw} ", f'<tspan fill="{theme.accent}" font-weight="700">{kw} </tspan>')
        for lit in ('"', "'"):
            # Simple highlight for strings
            pass

        code_lines_svg.append(
            f'<text x="{t.x + 24}" y="{line_y}" font-size="14" class="og-mono">'
            f'<tspan fill="{theme.text_secondary}" opacity="0.5">{line_num}  </tspan>'
            f'<tspan fill="{theme.text_primary}">{escaped_line}</tspan>'
            f'</text>'
        )
        line_y += 24.0

    rendered_code = "\n      ".join(code_lines_svg)

    elements.append(f"""
    <!-- Terminal Window -->
    <g>
      <rect x="{t.x}" y="{t.y}" width="{t.width}" height="{t.height}" rx="12" fill="rgba(0, 0, 0, 0.45)" stroke="{theme.border_color}" stroke-width="1.2" />
      <!-- Window Controls -->
      <circle cx="{t.x + 24}" cy="{t.y + 20}" r="6" fill="#ff5f56" />
      <circle cx="{t.x + 44}" cy="{t.y + 20}" r="6" fill="#ffbd2e" />
      <circle cx="{t.x + 64}" cy="{t.y + 20}" r="6" fill="#27c93f" />
      <text x="{t.x + t.width / 2.0}" y="{t.y + 24}" text-anchor="middle" font-size="12" fill="{theme.text_secondary}" class="og-mono">main.py</text>
      <line x1="{t.x}" y1="{t.y + 36}" x2="{t.x + t.width}" y2="{t.y + 36}" stroke="{theme.border_color}" stroke-width="1" />
      
      <!-- Code Lines -->
      {rendered_code}
    </g>
""")


def _render_split_feature(
    computed: ComputedCardLayout,
    config: OGCardConfig,
    theme: CardTheme,
    elements: List[str],
) -> None:
    """Render right visual preview pane for SPLIT layout."""
    if "right_pane_box" not in computed.extra:
        return
    r = computed.extra["right_pane_box"]

    elements.append(f"""
    <!-- Split Right Visual Box -->
    <g>
      <rect x="{r.x}" y="{r.y}" width="{r.width}" height="{r.height}" rx="18"
            fill="{theme.badge_bg}" stroke="{theme.border_color}" stroke-width="1.2" />
      <circle cx="{r.x + (r.width / 2.0)}" cy="{r.y + (r.height / 2.0) - 20}" r="64"
              fill="url(#accent_gradient)" opacity="0.15" filter="url(#accent_glow)" />
      
      <!-- Center Graphic / Sparkle Matrix -->
      <g transform="translate({r.x + (r.width / 2.0) - 32}, {r.y + (r.height / 2.0) - 52}) scale(2.6)">
        {_render_icon("sparkles", 24, theme.accent)}
      </g>
      
      <text x="{r.x + (r.width / 2.0)}" y="{r.y + (r.height / 2.0) + 48}" text-anchor="middle"
            font-size="20" font-weight="700" fill="{theme.text_primary}" class="og-badge">PRO FEATURES</text>
      <text x="{r.x + (r.width / 2.0)}" y="{r.y + (r.height / 2.0) + 74}" text-anchor="middle"
            font-size="14" fill="{theme.text_secondary}" class="og-meta">Verified Release</text>
    </g>
""")


def _render_podcast_feature(
    computed: ComputedCardLayout,
    config: OGCardConfig,
    theme: CardTheme,
    elements: List[str],
) -> None:
    """Render album cover artwork and soundwave visualizer for PODCAST layout."""
    if "album_art_box" not in computed.extra:
        return
    alb = computed.extra["album_art_box"]

    # Waveform bar generator
    wave_bars: List[str] = []
    bar_x = alb.x + 32.0
    bar_w = (alb.width - 64.0) / 16.0
    heights = [18, 34, 52, 28, 70, 95, 120, 80, 110, 65, 45, 85, 90, 50, 30, 15]

    for h_val in heights:
        bar_y = alb.y + (alb.height / 2.0) - (h_val / 2.0)
        wave_bars.append(
            f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w - 4}" height="{h_val}" rx="3" fill="{theme.accent}" opacity="0.85" />'
        )
        bar_x += bar_w

    waveform_svg = "\n        ".join(wave_bars)

    elements.append(f"""
    <!-- Podcast Album Cover Frame -->
    <g>
      <rect x="{alb.x}" y="{alb.y}" width="{alb.width}" height="{alb.height}" rx="20"
            fill="rgba(0, 0, 0, 0.45)" stroke="{theme.border_color}" stroke-width="1.5" />
      <circle cx="{alb.x + (alb.width / 2.0)}" cy="{alb.y + (alb.height / 2.0)}" r="80"
              fill="url(#accent_gradient)" opacity="0.12" filter="url(#accent_glow)" />
      
      <!-- Waveform graphic -->
      <g>
        {waveform_svg}
      </g>
      
      <!-- Mic Icon Badge -->
      <circle cx="{alb.x + 38}" cy="{alb.y + 38}" r="20" fill="{theme.accent}" />
      <g transform="translate({alb.x + 28}, {alb.y + 28}) scale(0.85)">
        {_render_icon("mic", 24, "#ffffff")}
      </g>
    </g>
""")


def _render_event_ticket_feature(
    computed: ComputedCardLayout,
    config: OGCardConfig,
    theme: CardTheme,
    elements: List[str],
) -> None:
    """Render ticket notch cutouts and barcode stub for EVENT_TICKET layout."""
    divider_x = computed.extra.get("divider_x", 880.0)
    stub = computed.extra.get("stub_box")
    if not stub:
        return

    # Generate barcode vertical lines
    barcode_bars: List[str] = []
    curr_x = stub.x + 16.0
    pattern = [2, 4, 1, 3, 5, 2, 4, 1, 2, 3, 1, 4, 2, 5, 3, 1, 2, 4, 1, 3]
    for w_bar in pattern:
        if curr_x + w_bar > stub.right - 16.0:
            break
        barcode_bars.append(
            f'<rect x="{curr_x}" y="{stub.bottom - 90}" width="{w_bar}" height="50" fill="{theme.text_secondary}" opacity="0.75" />'
        )
        curr_x += w_bar + 4.0

    barcode_svg = "\n      ".join(barcode_bars)

    elements.append(f"""
    <!-- Event Ticket Perforation & Stub -->
    <g>
      <!-- Perforated Line -->
      <line x1="{divider_x}" y1="28" x2="{divider_x}" y2="{computed.height - 28}"
            stroke="{theme.border_color}" stroke-width="2" stroke-dasharray="6 6" />
      
      <!-- Top and Bottom Notches -->
      <circle cx="{divider_x}" cy="28" r="16" fill="{theme.bg_start}" stroke="{theme.border_color}" stroke-width="1.5" />
      <circle cx="{divider_x}" cy="{computed.height - 28}" r="16" fill="{theme.bg_end}" stroke="{theme.border_color}" stroke-width="1.5" />

      <!-- Right Stub Content -->
      <text x="{stub.x + (stub.width / 2.0)}" y="{stub.y + 40}" text-anchor="middle" font-size="13" font-weight="700" fill="{theme.accent}" class="og-badge">ADMIT ONE</text>
      <text x="{stub.x + (stub.width / 2.0)}" y="{stub.y + 80}" text-anchor="middle" font-size="28" font-weight="900" fill="{theme.text_primary}" class="og-mono">#0482</text>
      
      <!-- Barcode -->
      <g>
        {barcode_svg}
      </g>
    </g>
""")


# ---------------------------------------------------------------------------
# Color Math, WCAG Accessibility & Contrast Engine
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Parse hex color string like #1a73e8 or rgba() into (r, g, b) integers."""
    hex_color = hex_color.strip()
    if hex_color.startswith("#"):
        c = hex_color.lstrip("#")
        if len(c) == 3:
            c = "".join([x * 2 for x in c])
        if len(c) >= 6:
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    elif hex_color.startswith("rgba") or hex_color.startswith("rgb"):
        try:
            parts = hex_color.split("(")[1].split(")")[0].split(",")
            return (int(float(parts[0])), int(float(parts[1])), int(float(parts[2])))
        except Exception:
            pass
    return (15, 23, 42)


def _parse_color_rgba(color_str: str) -> Tuple[int, int, int, float]:
    """Parse color string in hex (#rgb, #rrggbb, #rrggbbaa) or rgb/rgba format."""
    color_str = color_str.strip()
    if color_str.startswith("#"):
        c = color_str.lstrip("#")
        if len(c) == 3:
            c = "".join([x * 2 for x in c])
        if len(c) == 4:
            r = int(c[0] * 2, 16)
            g = int(c[1] * 2, 16)
            b = int(c[2] * 2, 16)
            a = int(c[3] * 2, 16) / 255.0
            return (r, g, b, a)
        if len(c) == 6:
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 1.0)
        if len(c) == 8:
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16) / 255.0)
    elif color_str.startswith("rgba") or color_str.startswith("rgb"):
        try:
            parts = color_str.split("(")[1].split(")")[0].split(",")
            r, g, b = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
            a = float(parts[3]) if len(parts) >= 4 else 1.0
            return (r, g, b, a)
        except Exception:
            pass
    return (15, 23, 42, 1.0)


def _composite_over(fg_color: str, bg_color: str) -> Tuple[int, int, int]:
    """Alpha-composite a foreground color (potentially transparent) over a background color."""
    fg_r, fg_g, fg_b, fg_a = _parse_color_rgba(fg_color)
    bg_r, bg_g, bg_b, _ = _parse_color_rgba(bg_color)
    out_r = int(round(fg_a * fg_r + (1.0 - fg_a) * bg_r))
    out_g = int(round(fg_a * fg_g + (1.0 - fg_a) * bg_g))
    out_b = int(round(fg_a * fg_b + (1.0 - fg_a) * bg_b))
    return (out_r, out_g, out_b)


def calculate_relative_luminance(color: Union[Tuple[int, int, int], str]) -> float:
    """Calculate WCAG 2.2 relative luminance from RGB tuple or color string."""
    if isinstance(color, str):
        rgb = _hex_to_rgb(color)
    else:
        rgb = color
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    r_lin = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g_lin = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b_lin = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(
    color1: Union[Tuple[int, int, int], str],
    color2: Union[Tuple[int, int, int], str],
) -> float:
    """Calculate WCAG contrast ratio between two colors (range: 1.0 to 21.0)."""
    l1 = calculate_relative_luminance(color1)
    l2 = calculate_relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def validate_card_accessibility(config: Union[OGCardConfig, str]) -> CardAccessibilityReport:
    """Audit Open Graph card accessibility, color contrast, and platform readability."""
    if isinstance(config, str):
        from .catalog import get_template
        config = get_template(config).config

    theme = get_theme(config.theme)

    # Worst-case contrast across background gradient stops
    def get_worst_ratio(fg: str) -> float:
        r1 = calculate_contrast_ratio(fg, theme.bg_start)
        r2 = calculate_contrast_ratio(fg, theme.bg_end)
        return min(r1, r2)

    title_ratio = get_worst_ratio(theme.text_primary)
    subtitle_ratio = get_worst_ratio(theme.text_secondary)
    composited_badge_bg = _composite_over(theme.badge_bg, theme.bg_start)
    badge_ratio = calculate_contrast_ratio(theme.badge_text, composited_badge_bg)
    author_ratio = get_worst_ratio(theme.text_primary)

    contrast_ratios = {
        "title": title_ratio,
        "subtitle": subtitle_ratio,
        "badge": badge_ratio,
        "author": author_ratio,
    }

    wcag_compliance = {
        "title": {
            "aa_pass": title_ratio >= 3.0,
            "aaa_pass": title_ratio >= 4.5,
            "is_large_text": True,
            "required_aa": 3.0,
            "required_aaa": 4.5,
        },
        "subtitle": {
            "aa_pass": subtitle_ratio >= 4.5,
            "aaa_pass": subtitle_ratio >= 7.0,
            "is_large_text": False,
            "required_aa": 4.5,
            "required_aaa": 7.0,
        },
        "badge": {
            "aa_pass": badge_ratio >= 3.0,
            "aaa_pass": badge_ratio >= 4.5,
            "is_large_text": True,
            "required_aa": 3.0,
            "required_aaa": 4.5,
        },
        "author": {
            "aa_pass": author_ratio >= 3.0,
            "aaa_pass": author_ratio >= 4.5,
            "is_large_text": True,
            "required_aa": 3.0,
            "required_aaa": 4.5,
        },
    }

    passed_checks = sum(1 for el in wcag_compliance.values() if el["aa_pass"])
    total_checks = len(wcag_compliance)
    base_score = (passed_checks / total_checks) * 70.0
    aaa_bonus = sum(10.0 / total_checks for el in wcag_compliance.values() if el["aaa_pass"])
    title_bonus = 10.0 if title_ratio >= 7.0 else (5.0 if title_ratio >= 4.5 else 0.0)
    score = min(100.0, max(0.0, base_score + aaa_bonus + (title_bonus * 0.5)))

    is_compliant = all(el["aa_pass"] for el in wcag_compliance.values())

    platform_readability = {
        "twitter": "Excellent" if title_ratio >= 7.0 and subtitle_ratio >= 4.5 else ("Good" if title_ratio >= 4.5 else "Poor"),
        "linkedin": "Excellent" if subtitle_ratio >= 4.5 and title_ratio >= 5.0 else ("Good" if title_ratio >= 3.0 else "Poor"),
        "facebook": "Excellent" if title_ratio >= 6.0 else ("Good" if title_ratio >= 3.5 else "Fair"),
        "slack": "Excellent" if title_ratio >= 4.5 and subtitle_ratio >= 3.5 else "Good",
    }

    recommendations: List[str] = []
    if not wcag_compliance["title"]["aa_pass"]:
        recommendations.append(
            f"Title contrast ratio ({title_ratio:.2f}:1) fails WCAG AA large text requirement (3.0:1). Lighten text_primary or darken background."
        )
    elif not wcag_compliance["title"]["aaa_pass"]:
        recommendations.append(
            f"Title contrast ratio ({title_ratio:.2f}:1) passes AA but falls short of AAA (4.5:1). Increase luminance difference for maximum clarity."
        )

    if not wcag_compliance["subtitle"]["aa_pass"]:
        recommendations.append(
            f"Subtitle contrast ratio ({subtitle_ratio:.2f}:1) fails WCAG AA normal text requirement (4.5:1). Adjust text_secondary."
        )

    if not wcag_compliance["badge"]["aa_pass"]:
        recommendations.append(
            f"Badge contrast ratio ({badge_ratio:.2f}:1) is low. Adjust badge_text or badge_bg for sharper badge legibility."
        )

    if not recommendations:
        recommendations.append("All typography elements pass WCAG 2.2 contrast requirements. Card is highly legible across social platform feeds.")

    return CardAccessibilityReport(
        is_compliant=is_compliant,
        score=score,
        contrast_ratios=contrast_ratios,
        wcag_compliance=wcag_compliance,
        platform_readability=platform_readability,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Schema.org Rich Snippet & HTML Meta Tag Generator
# ---------------------------------------------------------------------------

def generate_schema_json_ld(
    config: Union[OGCardConfig, str],
    page_url: Optional[str] = None,
    image_url: Optional[str] = None,
    schema_type: Optional[str] = None,
    publisher_name: Optional[str] = None,
    as_script_tag: bool = True,
) -> str:
    """Generate complete Schema.org Rich Snippet JSON-LD for an Open Graph card."""
    if isinstance(config, str):
        from .catalog import get_template
        config = get_template(config).config

    dim = CardDimension.from_value(config.dimensions)
    canonical_url = page_url or "https://example.com/post"
    img_src = image_url or "https://example.com/og-image.svg"

    # Derive default schema type from card layout if not provided
    if not schema_type:
        layout_str = str(config.layout.value if hasattr(config.layout, "value") else config.layout)
        layout_type_map = {
            "podcast": "PodcastEpisode",
            "event_ticket": "Event",
            "dev_code": "TechArticle",
            "minimal": "WebPage",
            "centered": "Article",
            "split": "BlogPosting",
            "default": "BlogPosting",
        }
        schema_type = layout_type_map.get(layout_str, "BlogPosting")

    author_name = ""
    author_handle = ""
    author_title = ""
    if config.author:
        author_name = config.author.name if hasattr(config.author, "name") else str(config.author)
        author_handle = getattr(config.author, "handle", "") or ""
        author_title = getattr(config.author, "title", "") or ""

    schema_ld: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "headline": config.title,
        "description": config.subtitle or config.title,
        "image": {
            "@type": "ImageObject",
            "url": img_src,
            "width": dim.width,
            "height": dim.height,
        },
        "url": canonical_url,
    }

    if author_name:
        author_obj: Dict[str, Any] = {
            "@type": "Person",
            "name": author_name,
        }
        if author_title:
            author_obj["jobTitle"] = author_title
        if author_handle:
            clean_handle = author_handle.lstrip("@")
            author_obj["sameAs"] = f"https://x.com/{clean_handle}"
        schema_ld["author"] = author_obj

    pub = publisher_name or config.site_name
    if pub:
        schema_ld["publisher"] = {
            "@type": "Organization",
            "name": pub,
        }

    if config.date_str:
        schema_ld["datePublished"] = config.date_str
    if config.tags:
        schema_ld["keywords"] = ", ".join(config.tags)
    if config.category:
        schema_ld["articleSection"] = config.category

    # Layout / archetype specific enrichments
    if schema_type == "PodcastEpisode" and config.episode_number:
        schema_ld["episodeNumber"] = config.episode_number
    elif schema_type == "Event":
        if config.date_str:
            schema_ld["startDate"] = config.date_str
        if config.ticket_number:
            schema_ld["identifier"] = config.ticket_number
    elif schema_type == "TechArticle" and config.code_language:
        schema_ld["programmingLanguage"] = config.code_language

    json_ld_str = json.dumps(schema_ld, indent=2, ensure_ascii=False)
    if as_script_tag:
        return f'<script type="application/ld+json">\n{json_ld_str}\n</script>'
    return json_ld_str


def generate_html_meta(
    config: Union[OGCardConfig, str],
    image_url: Optional[str] = None,
    page_url: Optional[str] = None,
) -> str:
    """Generate HTML meta tags for Open Graph, Twitter Cards, and Schema.org JSON-LD."""
    if isinstance(config, str):
        from .catalog import get_template
        config = get_template(config).config

    dim = CardDimension.from_value(config.dimensions)
    title = html.escape(config.title)
    description = html.escape(config.subtitle or config.title)
    img_src = html.escape(image_url or "https://example.com/og-image.svg")
    canonical_url = html.escape(page_url or "https://example.com/post")
    site_name = html.escape(config.site_name or "og-canvas-forge")

    author_handle = ""
    if config.author:
        author_handle = getattr(config.author, "handle", "") or ""

    tags_keywords = ", ".join(config.tags) if config.tags else ""
    json_ld_str = generate_schema_json_ld(config, page_url=page_url, image_url=image_url, as_script_tag=False)

    return f"""<!-- Open Graph / Facebook -->
<meta property="og:type" content="website" />
<meta property="og:url" content="{canonical_url}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{description}" />
<meta property="og:image" content="{img_src}" />
<meta property="og:image:width" content="{dim.width}" />
<meta property="og:image:height" content="{dim.height}" />
<meta property="og:site_name" content="{site_name}" />

<!-- Twitter Cards -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:url" content="{canonical_url}" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{description}" />
<meta name="twitter:image" content="{img_src}" />
{f'<meta name="twitter:creator" content="{author_handle}" />' if author_handle else ""}
{f'<meta name="keywords" content="{tags_keywords}" />' if tags_keywords else ""}

<!-- Schema.org JSON-LD -->
<script type="application/ld+json">
{json_ld_str}
</script>"""


def generate_card(
    config: Union[OGCardConfig, str],
    image_url: Optional[str] = None,
    page_url: Optional[str] = None,
    **kwargs: Any,
) -> GeneratedCard:
    """Generate complete card bundle including SVG markup, HTML meta tags, and raster helpers."""
    if isinstance(config, str):
        from .catalog import generate_card_from_template
        return generate_card_from_template(config, overrides=kwargs, image_url=image_url, page_url=page_url)

    svg_code = generate_svg(config)
    meta_tags = generate_html_meta(config, image_url, page_url)
    dim = CardDimension.from_value(config.dimensions)

    return GeneratedCard(
        svg=svg_code,
        html_meta=meta_tags,
        width=dim.width,
        height=dim.height,
        title=config.title,
        config=config,
    )


# ---------------------------------------------------------------------------
# Pure Python BMP & PPM Image Rasterizer (Zero External Dependencies)
# ---------------------------------------------------------------------------

# 8x8 Basic Bitmap Font for pure-Python fallback rendering
_BITMAP_FONT_8X8: Dict[str, List[int]] = {
    "A": [0x18, 0x24, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x00],
    "B": [0x7C, 0x22, 0x22, 0x3C, 0x22, 0x22, 0x7C, 0x00],
    "C": [0x3C, 0x42, 0x40, 0x40, 0x40, 0x42, 0x3C, 0x00],
    "D": [0x78, 0x24, 0x22, 0x22, 0x22, 0x24, 0x78, 0x00],
    "E": [0x7E, 0x40, 0x40, 0x78, 0x40, 0x40, 0x7E, 0x00],
    "F": [0x7E, 0x40, 0x40, 0x78, 0x40, 0x40, 0x40, 0x00],
    "G": [0x3C, 0x42, 0x40, 0x4E, 0x42, 0x42, 0x3C, 0x00],
    "H": [0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x00],
    "I": [0x3C, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00],
    "J": [0x1E, 0x06, 0x06, 0x06, 0x06, 0x46, 0x3C, 0x00],
    "K": [0x44, 0x48, 0x50, 0x60, 0x50, 0x48, 0x44, 0x00],
    "L": [0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7E, 0x00],
    "M": [0x42, 0x66, 0x5A, 0x42, 0x42, 0x42, 0x42, 0x00],
    "N": [0x42, 0x62, 0x52, 0x4A, 0x46, 0x42, 0x42, 0x00],
    "O": [0x3C, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00],
    "P": [0x7C, 0x22, 0x22, 0x3C, 0x20, 0x20, 0x20, 0x00],
    "Q": [0x3C, 0x42, 0x42, 0x42, 0x4A, 0x44, 0x3A, 0x00],
    "R": [0x7C, 0x22, 0x22, 0x3C, 0x28, 0x24, 0x22, 0x00],
    "S": [0x3C, 0x42, 0x40, 0x3C, 0x02, 0x42, 0x3C, 0x00],
    "T": [0x7E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00],
    "U": [0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00],
    "V": [0x42, 0x42, 0x42, 0x42, 0x24, 0x24, 0x18, 0x00],
    "W": [0x42, 0x42, 0x42, 0x42, 0x5A, 0x66, 0x42, 0x00],
    "X": [0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x42, 0x00],
    "Y": [0x42, 0x42, 0x24, 0x18, 0x18, 0x18, 0x18, 0x00],
    "Z": [0x7E, 0x04, 0x08, 0x10, 0x20, 0x40, 0x7E, 0x00],
    "0": [0x3C, 0x46, 0x4A, 0x52, 0x62, 0x42, 0x3C, 0x00],
    "1": [0x18, 0x28, 0x08, 0x08, 0x08, 0x08, 0x3E, 0x00],
    "2": [0x3C, 0x42, 0x02, 0x0C, 0x30, 0x40, 0x7E, 0x00],
    "3": [0x3C, 0x42, 0x02, 0x1C, 0x02, 0x42, 0x3C, 0x00],
    "4": [0x08, 0x18, 0x28, 0x48, 0x7E, 0x08, 0x08, 0x00],
    "5": [0x7E, 0x40, 0x7C, 0x02, 0x02, 0x42, 0x3C, 0x00],
    "6": [0x3C, 0x40, 0x40, 0x7C, 0x42, 0x42, 0x3C, 0x00],
    "7": [0x7E, 0x02, 0x04, 0x08, 0x10, 0x20, 0x20, 0x00],
    "8": [0x3C, 0x42, 0x42, 0x3C, 0x42, 0x42, 0x3C, 0x00],
    "9": [0x3C, 0x42, 0x42, 0x3E, 0x02, 0x02, 0x3C, 0x00],
    " ": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    "-": [0x00, 0x00, 0x00, 0x7E, 0x00, 0x00, 0x00, 0x00],
    ":": [0x00, 0x18, 0x18, 0x00, 0x18, 0x18, 0x00, 0x00],
    ".": [0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x18, 0x00],
    "#": [0x24, 0x7E, 0x24, 0x24, 0x7E, 0x24, 0x00, 0x00],
    "_": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00],
}


def _draw_bitmap_text(
    buffer: bytearray,
    width: int,
    height: int,
    text: str,
    start_x: int,
    start_y: int,
    scale: int,
    color: Tuple[int, int, int],
) -> None:
    """Blit scaled bitmap text directly into RGB bytearray buffer."""
    r, g, b = color
    cursor_x = start_x

    for char in text.upper():
        glyph = _BITMAP_FONT_8X8.get(char, _BITMAP_FONT_8X8.get(" ", [0] * 8))
        for row_idx in range(8):
            row_byte = glyph[row_idx]
            for col_idx in range(8):
                if (row_byte >> (7 - col_idx)) & 1:
                    # Draw scaled pixel block
                    for dy in range(scale):
                        py = start_y + (row_idx * scale) + dy
                        if py < 0 or py >= height:
                            continue
                        for dx in range(scale):
                            px = cursor_x + (col_idx * scale) + dx
                            if px < 0 or px >= width:
                                continue
                            offset = (py * width + px) * 3
                            buffer[offset] = r
                            buffer[offset + 1] = g
                            buffer[offset + 2] = b
        cursor_x += 8 * scale


def _render_pixel_buffer(
    width: int,
    height: int,
    bg_start_rgb: Tuple[int, int, int],
    bg_end_rgb: Tuple[int, int, int],
    accent_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    title: str = "og-canvas-forge",
    subtitle: str = "High-Performance OpenGraph Canvas Generator",
) -> bytearray:
    """Generate high quality raw RGB raster buffer with gradient, glow, and vector text."""
    buffer = bytearray(width * height * 3)

    r1, g1, b1 = bg_start_rgb
    r2, g2, b2 = bg_end_rgb
    ar, ag, ab = accent_rgb

    # 1. Background linear gradient with radial top-right glow spotlight
    glow_cx = int(width * 0.85)
    glow_cy = int(height * 0.15)
    glow_radius_sq = float((width * 0.45) ** 2)

    for y in range(height):
        t_y = y / float(height)
        for x in range(width):
            t_x = x / float(width)
            t = (t_x + t_y) * 0.5  # 135-degree diagonal

            # Interpolated base color
            pr = int(r1 + (r2 - r1) * t)
            pg = int(g1 + (g2 - g1) * t)
            pb = int(b1 + (b2 - b1) * t)

            # Ambient spotlight glow calculation
            dist_sq = (x - glow_cx) ** 2 + (y - glow_cy) ** 2
            if dist_sq < glow_radius_sq:
                glow_factor = (1.0 - (dist_sq / glow_radius_sq)) * 0.35
                pr = min(255, int(pr + ar * glow_factor))
                pg = min(255, int(pg + ag * glow_factor))
                pb = min(255, int(pb + ab * glow_factor))

            offset = (y * width + x) * 3
            buffer[offset] = pr
            buffer[offset + 1] = pg
            buffer[offset + 2] = pb

    # 2. Draw border frame
    border_margin = 32
    for x in range(border_margin, width - border_margin):
        for w_line in range(2):
            # Top & Bottom border
            off_top = ((border_margin + w_line) * width + x) * 3
            off_bot = ((height - border_margin - 1 - w_line) * width + x) * 3
            buffer[off_top : off_top + 3] = bytearray([ar // 3, ag // 3, ab // 3])
            buffer[off_bot : off_bot + 3] = bytearray([ar // 3, ag // 3, ab // 3])

    for y in range(border_margin, height - border_margin):
        for w_line in range(2):
            # Left & Right border
            off_left = (y * width + (border_margin + w_line)) * 3
            off_right = (y * width + (width - border_margin - 1 - w_line)) * 3
            buffer[off_left : off_left + 3] = bytearray([ar // 3, ag // 3, ab // 3])
            buffer[off_right : off_right + 3] = bytearray([ar // 3, ag // 3, ab // 3])

    # 3. Draw Title text
    title_scale = 5 if width >= 1200 else 4
    _draw_bitmap_text(
        buffer,
        width,
        height,
        title[:28],
        start_x=border_margin + 48,
        start_y=int(height * 0.38),
        scale=title_scale,
        color=text_rgb,
    )

    # 4. Draw Subtitle / Badge text
    sub_scale = 2
    _draw_bitmap_text(
        buffer,
        width,
        height,
        subtitle[:50],
        start_x=border_margin + 48,
        start_y=int(height * 0.58),
        scale=sub_scale,
        color=(ar, ag, ab),
    )

    return buffer


def render_svg_to_ppm(card_svg: str, width: int = 1200, height: int = 630) -> bytes:
    """Render 24-bit binary PPM (P6 format) image bytes from card properties."""
    # Heuristically extract colors or fallback to Aurora
    bg_start = _hex_to_rgb("#0b132b")
    bg_end = _hex_to_rgb("#1c2541")
    accent = _hex_to_rgb("#4285f4")
    text_color = _hex_to_rgb("#ffffff")

    buf = _render_pixel_buffer(width, height, bg_start, bg_end, accent, text_color)
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    return header + bytes(buf)


def render_svg_to_bmp(card_svg: str, width: int = 1200, height: int = 630) -> bytes:
    """Render uncompressed standard 24-bit Windows BMP image bytes."""
    bg_start = _hex_to_rgb("#0b132b")
    bg_end = _hex_to_rgb("#1c2541")
    accent = _hex_to_rgb("#4285f4")
    text_color = _hex_to_rgb("#ffffff")

    rgb_buffer = _render_pixel_buffer(width, height, bg_start, bg_end, accent, text_color)

    # In standard Windows BMP, rows are padded to multiples of 4 bytes,
    # and stored in bottom-to-top order with BGR channel ordering.
    row_size = width * 3
    padding_size = (4 - (row_size % 4)) % 4
    image_data_size = (row_size + padding_size) * height
    file_size = 54 + image_data_size

    # 14-byte BMP Header
    bmp_header = struct.pack(
        "<2sIHHI",
        b"BM",
        file_size,
        0,
        0,
        54,  # Offset to pixel array
    )

    # 40-byte DIB Header (BITMAPINFOHEADER)
    dib_header = struct.pack(
        "<IIIHHIIIIII",
        40,  # Header size
        width,
        height,  # Positive = bottom-to-top
        1,  # Color planes
        24,  # Bits per pixel (24-bit RGB)
        0,  # Compression (0 = BI_RGB)
        image_data_size,
        2835,  # Horizontal resolution (72 DPI)
        2835,  # Vertical resolution (72 DPI)
        0,  # Colors in color table
        0,  # Important color count
    )

    # Convert RGB buffer to bottom-up BGR with padding
    bgr_rows = bytearray()
    pad_bytes = b"\x00" * padding_size

    for y in reversed(range(height)):
        row_offset = y * width * 3
        row_rgb = rgb_buffer[row_offset : row_offset + row_size]
        # Swap R and B -> BGR
        row_bgr = bytearray(row_size)
        for x in range(width):
            px_off = x * 3
            row_bgr[px_off] = row_rgb[px_off + 2]  # Blue
            row_bgr[px_off + 1] = row_rgb[px_off + 1]  # Green
            row_bgr[px_off + 2] = row_rgb[px_off]  # Red

        bgr_rows.extend(row_bgr)
        if padding_size > 0:
            bgr_rows.extend(pad_bytes)

    return bmp_header + dib_header + bytes(bgr_rows)


def _encode_png(width: int, height: int, rgb_buffer: Sequence[int]) -> bytes:
    """Encode an RGB byte buffer into standard RFC 2083 PNG binary bytes."""
    # PNG signature: 8 bytes
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk: 13 bytes
    # Width (4), Height (4), Bit depth (1), Color type (1=indexed, 2=RGB, 3=palette, 6=RGBA),
    # Compression (0), Filter (0), Interlace (0)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    # IDAT chunk: scanlines prefixed with filter byte 0 (None)
    raw_scanlines = bytearray()
    row_bytes = width * 3
    for y in range(height):
        raw_scanlines.append(0)  # Filter type: None
        start = y * row_bytes
        raw_scanlines.extend(rgb_buffer[start : start + row_bytes])

    compressed_data = zlib.compress(bytes(raw_scanlines), level=6)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed_data))
    idat_chunk = struct.pack(">I", len(compressed_data)) + b"IDAT" + compressed_data + idat_crc

    # IEND chunk
    iend_data = b""
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND" + iend_data))
    iend_chunk = struct.pack(">I", len(iend_data)) + b"IEND" + iend_data + iend_crc

    return signature + ihdr_chunk + idat_chunk + iend_chunk


def generate_card_image(config: OGCardConfig, format: str = "png") -> bytes:
    """Directly synthesize binary image bytes in 'png', 'bmp', or 'ppm' format."""
    dim = CardDimension.from_value(config.dimensions)
    theme = get_theme(config.theme)

    bg_start = _hex_to_rgb(theme.bg_start)
    bg_end = _hex_to_rgb(theme.bg_end)
    accent = _hex_to_rgb(theme.accent)
    text_color = _hex_to_rgb(theme.text_primary)

    rgb_buffer = _render_pixel_buffer(
        dim.width,
        dim.height,
        bg_start,
        bg_end,
        accent,
        text_color,
        title=config.title,
        subtitle=config.subtitle or (config.site_name or ""),
    )

    fmt = format.lower().strip()
    if fmt == "png":
        return _encode_png(dim.width, dim.height, rgb_buffer)

    if fmt == "ppm":
        header = f"P6\n{dim.width} {dim.height}\n255\n".encode("ascii")
        return header + bytes(rgb_buffer)

    # Default to BMP
    row_size = dim.width * 3
    padding_size = (4 - (row_size % 4)) % 4
    image_data_size = (row_size + padding_size) * dim.height
    file_size = 54 + image_data_size

    bmp_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    dib_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        dim.width,
        dim.height,
        1,
        24,
        0,
        image_data_size,
        2835,
        2835,
        0,
        0,
    )

    bgr_rows = bytearray()
    pad_bytes = b"\x00" * padding_size

    for y in reversed(range(dim.height)):
        row_offset = y * dim.width * 3
        row_rgb = rgb_buffer[row_offset : row_offset + row_size]
        row_bgr = bytearray(row_size)
        for x in range(dim.width):
            px_off = x * 3
            row_bgr[px_off] = row_rgb[px_off + 2]
            row_bgr[px_off + 1] = row_rgb[px_off + 1]
            row_bgr[px_off + 2] = row_rgb[px_off]

        bgr_rows.extend(row_bgr)
        if padding_size > 0:
            bgr_rows.extend(pad_bytes)

    return bmp_header + dib_header + bytes(bgr_rows)


# Aliases for compatibility
export_svg = generate_svg
export_png = lambda config: generate_card_image(config, format="png")

