"""Watermark and Branding Overlay Engine for OG Social Cards.

Supports subtle corner watermarks, large diagonal security/preview marks,
confidential stamps, and repeated grid watermarks.
Pure Python, zero-dependency.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class WatermarkSpec:
    """Specification for card watermark branding overlay."""

    text: str
    style: str = "subtle"  # "subtle", "diagonal", "stamp", "badge", "repeat_grid", "confidential"
    opacity: float = 0.08
    font_size: int = 48
    color: Optional[str] = None
    position: str = "bottom_right"  # "bottom_right", "top_right", "center", "diagonal"
    rotation_deg: float = -25.0

    @classmethod
    def from_input(cls, val: Union[WatermarkSpec, str, None]) -> Optional[WatermarkSpec]:
        """Resolve string or spec to WatermarkSpec instance."""
        if val is None:
            return None
        if isinstance(val, WatermarkSpec):
            return val
        text = str(val).strip()
        if not text:
            return None
        # Check for style prefix, e.g. "CONFIDENTIAL:draft" or "DIAGONAL:preview"
        if ":" in text:
            prefix, rest = text.split(":", 1)
            prefix_lower = prefix.strip().lower()
            if prefix_lower in ("subtle", "diagonal", "stamp", "badge", "repeat_grid", "confidential"):
                return cls(text=rest.strip(), style=prefix_lower)
        return cls(text=text)


def render_watermark_svg(
    spec: Union[WatermarkSpec, str],
    width: int = 1200,
    height: int = 630,
    default_color: str = "#ffffff",
) -> str:
    """Render watermark SVG overlay layer."""
    parsed = WatermarkSpec.from_input(spec)
    if not parsed:
        return ""

    color = parsed.color or default_color
    safe_text = html.escape(parsed.text)
    style = parsed.style.lower()

    if style in ("diagonal", "confidential"):
        # Large diagonal watermark across center of canvas
        opacity = max(0.04, min(0.25, parsed.opacity if parsed.opacity != 0.08 else 0.08))
        font_size = max(50, parsed.font_size if parsed.font_size != 48 else int(width * 0.07))
        cx = width / 2
        cy = height / 2

        border_box = ""
        if style == "confidential":
            box_w = len(parsed.text) * font_size * 0.65 + 60
            box_h = font_size + 40
            border_box = f"""
    <rect x="{-box_w / 2}" y="{-box_h / 2}" width="{box_w}" height="{box_h}" rx="12" fill="none" stroke="{color}" stroke-width="4" stroke-dasharray="16,8" opacity="{opacity * 1.5:.2f}" />"""

        return f"""
  <!-- Watermark: {style.upper()} -->
  <g class="watermark-{style}" transform="translate({cx}, {cy}) rotate({parsed.rotation_deg})" pointer-events="none">
    {border_box}
    <text x="0" y="{font_size * 0.35}" fill="{color}" font-size="{font_size}" font-family="Inter, sans-serif" font-weight="900" text-anchor="middle" letter-spacing="8" text-transform="uppercase" opacity="{opacity:.2f}">{safe_text}</text>
  </g>"""

    elif style == "stamp":
        # Vintage / rubber-stamp style badge in top-right or bottom-right
        opacity = max(0.1, min(0.4, parsed.opacity if parsed.opacity != 0.08 else 0.18))
        font_size = 20
        box_w = len(parsed.text) * 14 + 32
        box_h = 36
        x = width - box_w - 48
        y = 52

        return f"""
  <!-- Watermark: STAMP -->
  <g class="watermark-stamp" transform="translate({x}, {y}) rotate(-4)" pointer-events="none">
    <rect width="{box_w}" height="{box_h}" rx="6" fill="none" stroke="{color}" stroke-width="2.5" opacity="{opacity:.2f}" />
    <text x="{box_w / 2}" y="{box_h / 2 + 5}" fill="{color}" font-size="{font_size}" font-family="JetBrains Mono, monospace" font-weight="800" text-anchor="middle" letter-spacing="3" text-transform="uppercase" opacity="{opacity:.2f}">{safe_text}</text>
  </g>"""

    elif style == "repeat_grid":
        # Repeated subtle diagonal stamps across entire canvas
        opacity = 0.04
        font_size = 28
        stamps: list[str] = []
        step_x = 320
        step_y = 180
        for gx in range(40, width + 100, step_x):
            for gy in range(40, height + 100, step_y):
                stamps.append(
                    f'<text x="{gx}" y="{gy}" fill="{color}" font-size="{font_size}" font-family="Inter, sans-serif" font-weight="700" letter-spacing="4" text-anchor="middle" transform="rotate(-20, {gx}, {gy})" opacity="{opacity}">{safe_text}</text>'
                )
        stamps_svg = "\n    ".join(stamps)
        return f"""
  <!-- Watermark: REPEAT GRID -->
  <g class="watermark-grid" pointer-events="none">
    {stamps_svg}
  </g>"""

    else:
        # Default "subtle" corner watermark
        opacity = max(0.1, min(0.3, parsed.opacity if parsed.opacity != 0.08 else 0.15))
        font_size = 14
        x = width - 48
        y = height - 32
        if parsed.position == "top_right":
            y = 48
        elif parsed.position == "center":
            x = width / 2
            y = height / 2

        anchor = "middle" if parsed.position == "center" else "end"
        return f"""
  <!-- Watermark: SUBTLE -->
  <g class="watermark-subtle" pointer-events="none">
    <text x="{x}" y="{y}" fill="{color}" font-size="{font_size}" font-family="Inter, sans-serif" font-weight="600" letter-spacing="1.5" text-anchor="{anchor}" opacity="{opacity:.2f}">{safe_text}</text>
  </g>"""
