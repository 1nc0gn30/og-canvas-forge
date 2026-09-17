"""Gradient synthesizer and built-in theme color system for og-canvas-forge.

Generates mathematical linear and radial SVG gradients, cinematic glow meshes,
and manages 14+ designer themes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from .models import CardTheme


@dataclass
class GradientStop:
    """A color stop in a linear or radial SVG gradient."""

    offset: float  # 0.0 to 1.0
    color: str
    opacity: float = 1.0

    def to_svg(self) -> str:
        """Render stop element."""
        off_pct = f"{round(self.offset * 100, 2)}%"
        op_attr = f' stop-opacity="{self.opacity}"' if self.opacity < 1.0 else ""
        return f'<stop offset="{off_pct}" stop-color="{self.color}"{op_attr} />'


@dataclass
class LinearGradient:
    """Linear SVG gradient with geometric angle calculation."""

    id: str
    angle_deg: float = 135.0
    stops: List[GradientStop] = field(default_factory=list)
    spread_method: str = "pad"

    def calculate_coordinates(self) -> Tuple[str, str, str, str]:
        """Convert degree angle into normalized SVG x1, y1, x2, y2 percentages."""
        rad = math.radians(self.angle_deg % 360)
        # Angle vector centered at (50%, 50%)
        cos_val = math.cos(rad)
        sin_val = math.sin(rad)

        x1 = round(50 - 50 * cos_val, 2)
        y1 = round(50 - 50 * sin_val, 2)
        x2 = round(50 + 50 * cos_val, 2)
        y2 = round(50 + 50 * sin_val, 2)

        return (f"{x1}%", f"{y1}%", f"{x2}%", f"{y2}%")

    def to_svg(self) -> str:
        """Render complete <linearGradient> SVG tag."""
        x1, y1, x2, y2 = self.calculate_coordinates()
        stops_svg = "\n    ".join(stop.to_svg() for stop in self.stops)
        return (
            f'<linearGradient id="{self.id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'spreadMethod="{self.spread_method}">\n'
            f"    {stops_svg}\n"
            f"</linearGradient>"
        )


@dataclass
class RadialGradient:
    """Radial SVG gradient for ambient glows and spotlights."""

    id: str
    cx: str = "50%"
    cy: str = "50%"
    r: str = "50%"
    fx: Optional[str] = None
    fy: Optional[str] = None
    stops: List[GradientStop] = field(default_factory=list)

    def to_svg(self) -> str:
        """Render complete <radialGradient> SVG tag."""
        f_attrs = ""
        if self.fx:
            f_attrs += f' fx="{self.fx}"'
        if self.fy:
            f_attrs += f' fy="{self.fy}"'
        stops_svg = "\n    ".join(stop.to_svg() for stop in self.stops)
        return (
            f'<radialGradient id="{self.id}" cx="{self.cx}" cy="{self.cy}" r="{self.r}"{f_attrs}>\n'
            f"    {stops_svg}\n"
            f"</radialGradient>"
        )


def create_linear_gradient(
    id: str,
    start_color: str,
    end_color: str,
    angle: float = 135.0,
    opacity_start: float = 1.0,
    opacity_end: float = 1.0,
) -> LinearGradient:
    """Create standard 2-stop linear gradient."""
    return LinearGradient(
        id=id,
        angle_deg=angle,
        stops=[
            GradientStop(0.0, start_color, opacity_start),
            GradientStop(1.0, end_color, opacity_end),
        ],
    )


def create_radial_glow(
    id: str,
    color: str,
    opacity: float = 0.35,
    cx: str = "85%",
    cy: str = "15%",
    r: str = "60%",
) -> RadialGradient:
    """Create ambient glow radial gradient that fades to transparent."""
    return RadialGradient(
        id=id,
        cx=cx,
        cy=cy,
        r=r,
        stops=[
            GradientStop(0.0, color, opacity),
            GradientStop(0.5, color, opacity * 0.4),
            GradientStop(1.0, color, 0.0),
        ],
    )


# ---------------------------------------------------------------------------
# Built-in 14+ Color Themes
# ---------------------------------------------------------------------------

_THEMES: Dict[str, CardTheme] = {
    "google_aurora": CardTheme(
        id="google_aurora",
        name="Google Aurora Blue",
        bg_start="#0b132b",
        bg_end="#1c2541",
        accent="#4285f4",
        text_primary="#ffffff",
        text_secondary="#93c5fd",
        badge_bg="rgba(66, 133, 244, 0.18)",
        badge_text="#60a5fa",
        border_color="rgba(66, 133, 244, 0.25)",
        glow_color="#4285f4",
        is_dark=True,
        gradient_angle=135,
        card_bg="rgba(15, 23, 42, 0.65)",
    ),
    "aurora": CardTheme(
        id="aurora",
        name="Aurora Slate",
        bg_start="#0f172a",
        bg_end="#1e293b",
        accent="#38bdf8",
        text_primary="#f8fafc",
        text_secondary="#94a3b8",
        badge_bg="rgba(56, 189, 248, 0.16)",
        badge_text="#38bdf8",
        border_color="rgba(255, 255, 255, 0.12)",
        glow_color="#38bdf8",
        is_dark=True,
        gradient_angle=135,
    ),
    "cyber_neon": CardTheme(
        id="cyber_neon",
        name="Cyber Neon",
        bg_start="#070913",
        bg_end="#120e2e",
        accent="#00f2fe",
        text_primary="#ffffff",
        text_secondary="#a5b4fc",
        badge_bg="rgba(0, 242, 254, 0.15)",
        badge_text="#00f2fe",
        border_color="rgba(0, 242, 254, 0.3)",
        glow_color="#00f2fe",
        is_dark=True,
        gradient_angle=140,
    ),
    "sunset_velvet": CardTheme(
        id="sunset_velvet",
        name="Sunset Velvet",
        bg_start="#1a0b2e",
        bg_end="#380036",
        accent="#ff7a00",
        text_primary="#ffffff",
        text_secondary="#fbcfe8",
        badge_bg="rgba(255, 122, 0, 0.18)",
        badge_text="#ff9e40",
        border_color="rgba(255, 122, 0, 0.25)",
        glow_color="#ff5e62",
        is_dark=True,
        gradient_angle=125,
    ),
    "emerald_matrix": CardTheme(
        id="emerald_matrix",
        name="Emerald Matrix",
        bg_start="#021b14",
        bg_end="#064e3b",
        accent="#10b981",
        text_primary="#f0fdf4",
        text_secondary="#6ee7b7",
        badge_bg="rgba(16, 185, 129, 0.18)",
        badge_text="#34d399",
        border_color="rgba(16, 185, 129, 0.25)",
        glow_color="#10b981",
        is_dark=True,
        gradient_angle=130,
    ),
    "deep_obsidian": CardTheme(
        id="deep_obsidian",
        name="Deep Obsidian",
        bg_start="#090d16",
        bg_end="#161b26",
        accent="#58a6ff",
        text_primary="#f0f6fc",
        text_secondary="#8b949e",
        badge_bg="rgba(88, 166, 255, 0.15)",
        badge_text="#58a6ff",
        border_color="rgba(240, 246, 252, 0.1)",
        glow_color="#58a6ff",
        is_dark=True,
        gradient_angle=135,
    ),
    "royal_gold": CardTheme(
        id="royal_gold",
        name="Royal Gold",
        bg_start="#120f08",
        bg_end="#261f0d",
        accent="#f59e0b",
        text_primary="#fffbeb",
        text_secondary="#fcd34d",
        badge_bg="rgba(245, 158, 11, 0.18)",
        badge_text="#fbbf24",
        border_color="rgba(245, 158, 11, 0.3)",
        glow_color="#f59e0b",
        is_dark=True,
        gradient_angle=135,
    ),
    "minimalist_white": CardTheme(
        id="minimalist_white",
        name="Minimalist White",
        bg_start="#ffffff",
        bg_end="#f1f5f9",
        accent="#2563eb",
        text_primary="#0f172a",
        text_secondary="#475569",
        badge_bg="rgba(37, 99, 235, 0.10)",
        badge_text="#2563eb",
        border_color="rgba(15, 23, 42, 0.10)",
        glow_color="#2563eb",
        is_dark=False,
        gradient_angle=135,
    ),
    "synthwave_purple": CardTheme(
        id="synthwave_purple",
        name="Synthwave Purple",
        bg_start="#190326",
        bg_end="#3c096c",
        accent="#f72585",
        text_primary="#ffffff",
        text_secondary="#e0aaff",
        badge_bg="rgba(247, 37, 133, 0.20)",
        badge_text="#f72585",
        border_color="rgba(247, 37, 133, 0.3)",
        glow_color="#7209b7",
        is_dark=True,
        gradient_angle=135,
    ),
    "nordic_frost": CardTheme(
        id="nordic_frost",
        name="Nordic Frost",
        bg_start="#0c1929",
        bg_end="#1e3a5f",
        accent="#0284c7",
        text_primary="#f8fafc",
        text_secondary="#bae6fd",
        badge_bg="rgba(2, 132, 199, 0.18)",
        badge_text="#38bdf8",
        border_color="rgba(255, 255, 255, 0.15)",
        glow_color="#0284c7",
        is_dark=True,
        gradient_angle=135,
    ),
    "crimson_ember": CardTheme(
        id="crimson_ember",
        name="Crimson Ember",
        bg_start="#1c0a0a",
        bg_end="#3b1212",
        accent="#ef4444",
        text_primary="#fef2f2",
        text_secondary="#fca5a5",
        badge_bg="rgba(239, 68, 68, 0.20)",
        badge_text="#f87171",
        border_color="rgba(239, 68, 68, 0.3)",
        glow_color="#ef4444",
        is_dark=True,
        gradient_angle=135,
    ),
    "tokyo_night": CardTheme(
        id="tokyo_night",
        name="Tokyo Night",
        bg_start="#16161e",
        bg_end="#24283b",
        accent="#bb9af7",
        text_primary="#c0caf5",
        text_secondary="#7aa2f7",
        badge_bg="rgba(187, 154, 247, 0.16)",
        badge_text="#bb9af7",
        border_color="rgba(187, 154, 247, 0.25)",
        glow_color="#7aa2f7",
        is_dark=True,
        gradient_angle=135,
    ),
    "solar_flare": CardTheme(
        id="solar_flare",
        name="Solar Flare",
        bg_start="#1a0c00",
        bg_end="#381b05",
        accent="#f97316",
        text_primary="#fffaf0",
        text_secondary="#fdba74",
        badge_bg="rgba(249, 115, 22, 0.18)",
        badge_text="#fb923c",
        border_color="rgba(249, 115, 22, 0.3)",
        glow_color="#f97316",
        is_dark=True,
        gradient_angle=135,
    ),
    "monochrome_slate": CardTheme(
        id="monochrome_slate",
        name="Monochrome Slate",
        bg_start="#18181b",
        bg_end="#27272a",
        accent="#e4e4e7",
        text_primary="#fafafa",
        text_secondary="#a1a1aa",
        badge_bg="rgba(255, 255, 255, 0.12)",
        badge_text="#f4f4f5",
        border_color="rgba(255, 255, 255, 0.15)",
        glow_color="#ffffff",
        is_dark=True,
        gradient_angle=135,
    ),
    "dracula": CardTheme(
        id="dracula",
        name="Dracula Noir",
        bg_start="#1e1f29",
        bg_end="#282a36",
        accent="#ff79c6",
        text_primary="#f8f8f2",
        text_secondary="#bd93f9",
        badge_bg="rgba(255, 121, 198, 0.18)",
        badge_text="#ff79c6",
        border_color="rgba(98, 114, 164, 0.3)",
        glow_color="#bd93f9",
        is_dark=True,
        gradient_angle=135,
    ),
    "midnight_ocean": CardTheme(
        id="midnight_ocean",
        name="Midnight Ocean",
        bg_start="#031926",
        bg_end="#0d3b66",
        accent="#00a8e8",
        text_primary="#ffffff",
        text_secondary="#90e0ef",
        badge_bg="rgba(0, 168, 232, 0.18)",
        badge_text="#00a8e8",
        border_color="rgba(0, 168, 232, 0.25)",
        glow_color="#00a8e8",
        is_dark=True,
        gradient_angle=140,
    ),
}


def get_theme(theme_id_or_name: Union[str, CardTheme]) -> CardTheme:
    """Retrieve theme by id or name, falling back to Aurora."""
    if isinstance(theme_id_or_name, CardTheme):
        return theme_id_or_name

    key = str(theme_id_or_name).strip().lower().replace("-", "_").replace(" ", "_")
    if key in _THEMES:
        return _THEMES[key]

    for t in _THEMES.values():
        if t.name.lower() == key:
            return t

    return _THEMES["aurora"]


def list_themes() -> List[CardTheme]:
    """List all registered themes."""
    return list(_THEMES.values())


def register_theme(theme: CardTheme) -> None:
    """Register or override a custom theme."""
    _THEMES[theme.id.lower().replace("-", "_")] = theme


def generate_theme_defs(theme: CardTheme) -> str:
    """Generate SVG <defs> containing background gradients, glows, and filter effects."""
    bg_grad = create_linear_gradient(
        id="bg_gradient",
        start_color=theme.bg_start,
        end_color=theme.bg_end,
        angle=theme.gradient_angle,
    )

    accent_grad = create_linear_gradient(
        id="accent_gradient",
        start_color=theme.accent,
        end_color=theme.glow_color,
        angle=90.0,
    )

    radial_glow_1 = create_radial_glow(
        id="ambient_glow_top",
        color=theme.glow_color,
        opacity=0.35 if theme.is_dark else 0.15,
        cx="88%",
        cy="12%",
        r="55%",
    )

    radial_glow_2 = create_radial_glow(
        id="ambient_glow_bottom",
        color=theme.accent,
        opacity=0.20 if theme.is_dark else 0.08,
        cx="12%",
        cy="92%",
        r="45%",
    )

    return f"""
  <defs>
    {bg_grad.to_svg()}
    {accent_grad.to_svg()}
    {radial_glow_1.to_svg()}
    {radial_glow_2.to_svg()}

    <!-- Glow & Shadow Filters -->
    <filter id="accent_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="12" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>

    <filter id="card_shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="24" flood-color="#000000" flood-opacity="0.45" />
    </filter>

    <filter id="badge_shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000000" flood-opacity="0.25" />
    </filter>
  </defs>
""".strip()
