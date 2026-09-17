"""Domain models and data structures for og-canvas-forge.

Defines cards, themes, dimensions, layouts, authors, badges, generated cards,
and preset template specifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .compat import atomic_write_bytes, atomic_write_text


@dataclass(frozen=True)
class CardDimension:
    """Card dimensions in pixels with metadata."""

    width: int
    height: int
    name: str = "custom"

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width / height)."""
        return self.width / max(1, self.height)

    @property
    def resolution(self) -> Tuple[int, int]:
        """Return (width, height) tuple."""
        return (self.width, self.height)

    def to_tuple(self) -> Tuple[int, int]:
        """Return (width, height) tuple."""
        return (self.width, self.height)

    # Standard Presets
    STANDARD_OG: CardDimension = None  # type: ignore[assignment]
    SQUARE: CardDimension = None  # type: ignore[assignment]
    TWITTER_LARGE: CardDimension = None  # type: ignore[assignment]
    TWITTER_SUMMARY: CardDimension = None  # type: ignore[assignment]
    STORY: CardDimension = None  # type: ignore[assignment]
    MOBILE: CardDimension = None  # type: ignore[assignment]
    BANNER: CardDimension = None  # type: ignore[assignment]
    YOUTUBE_THUMBNAIL: CardDimension = None  # type: ignore[assignment]

    @classmethod
    def from_value(
        cls,
        value: Union[CardDimension, Tuple[int, int], str, Dict[str, Any]],
    ) -> CardDimension:
        """Resolve a dimension preset from various input formats."""
        if isinstance(value, CardDimension):
            return value
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            return cls(width=int(value[0]), height=int(value[1]), name=f"{value[0]}x{value[1]}")
        if isinstance(value, dict):
            return cls(
                width=int(value.get("width", 1200)),
                height=int(value.get("height", 630)),
                name=value.get("name", "custom"),
            )
        if isinstance(value, str):
            key = value.strip().lower().replace("-", "_").replace(" ", "_")
            presets: Dict[str, CardDimension] = {
                "standard_og": CardDimension(1200, 630, "Standard Open Graph"),
                "og": CardDimension(1200, 630, "Standard Open Graph"),
                "standard": CardDimension(1200, 630, "Standard Open Graph"),
                "default": CardDimension(1200, 630, "Standard Open Graph"),
                "square": CardDimension(1080, 1080, "Instagram / Square"),
                "instagram": CardDimension(1080, 1080, "Instagram / Square"),
                "twitter_large": CardDimension(1200, 675, "Twitter Large Summary"),
                "twitter": CardDimension(1200, 675, "Twitter Large Summary"),
                "twitter_summary": CardDimension(1200, 675, "Twitter Large Summary"),
                "story": CardDimension(1080, 1920, "Mobile Story / Reels"),
                "mobile": CardDimension(1080, 1920, "Mobile Story / Reels"),
                "reels": CardDimension(1080, 1920, "Mobile Story / Reels"),
                "banner": CardDimension(1500, 500, "Header Banner"),
                "youtube": CardDimension(1280, 720, "YouTube Thumbnail"),
                "youtube_thumbnail": CardDimension(1280, 720, "YouTube Thumbnail"),
            }
            if key in presets:
                return presets[key]
            # Try parsing '1200x630'
            if "x" in key:
                parts = key.split("x")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    return cls(width=int(parts[0]), height=int(parts[1]), name=f"{parts[0]}x{parts[1]}")

        # Default fallback
        return CardDimension(1200, 630, "Standard Open Graph")


# Initialize class preset attributes
setattr(CardDimension, "STANDARD_OG", CardDimension(1200, 630, "Standard Open Graph"))
setattr(CardDimension, "SQUARE", CardDimension(1080, 1080, "Instagram / Square"))
setattr(CardDimension, "TWITTER_LARGE", CardDimension(1200, 675, "Twitter Large Summary"))
setattr(CardDimension, "TWITTER_SUMMARY", CardDimension(1200, 675, "Twitter Large Summary"))
setattr(CardDimension, "STORY", CardDimension(1080, 1920, "Mobile Story / Reels"))
setattr(CardDimension, "MOBILE", CardDimension(1080, 1920, "Mobile Story / Reels"))
setattr(CardDimension, "BANNER", CardDimension(1500, 500, "Header Banner"))
setattr(CardDimension, "YOUTUBE_THUMBNAIL", CardDimension(1280, 720, "YouTube Thumbnail"))


class CardLayout(str, Enum):
    """Layout archetype for OG card composition."""

    DEFAULT = "default"
    CENTERED = "centered"
    SPLIT = "split"
    MINIMAL = "minimal"
    DEV_CODE = "dev_code"
    PODCAST = "podcast"
    EVENT_TICKET = "event_ticket"

    @classmethod
    def from_str(cls, value: Union[str, CardLayout]) -> CardLayout:
        """Convert string or enum to CardLayout safely."""
        if isinstance(value, CardLayout):
            return value
        if isinstance(value, str):
            clean = value.strip().lower().replace("-", "_").replace(" ", "_")
            for member in cls:
                if member.value == clean or member.name.lower() == clean:
                    return member
        return cls.DEFAULT


@dataclass
class CardTheme:
    """Color palette and typography theme for SVG rendering."""

    id: str
    name: str
    bg_start: str
    bg_end: str
    accent: str
    text_primary: str
    text_secondary: str
    badge_bg: str
    badge_text: str
    border_color: str
    glow_color: str
    is_dark: bool = True
    gradient_angle: int = 135
    card_bg: Optional[str] = None
    font_primary: str = "Inter"
    font_secondary: str = "Inter"
    font_mono: str = "JetBrains Mono"

    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "bg_start": self.bg_start,
            "bg_end": self.bg_end,
            "accent": self.accent,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "badge_bg": self.badge_bg,
            "badge_text": self.badge_text,
            "border_color": self.border_color,
            "glow_color": self.glow_color,
            "is_dark": self.is_dark,
            "gradient_angle": self.gradient_angle,
            "card_bg": self.card_bg,
            "font_primary": self.font_primary,
            "font_secondary": self.font_secondary,
            "font_mono": self.font_mono,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CardTheme:
        """Instantiate CardTheme from dictionary."""
        return cls(
            id=str(data.get("id", "custom")),
            name=str(data.get("name", "Custom Theme")),
            bg_start=str(data.get("bg_start", "#0f172a")),
            bg_end=str(data.get("bg_end", "#1e293b")),
            accent=str(data.get("accent", "#38bdf8")),
            text_primary=str(data.get("text_primary", "#f8fafc")),
            text_secondary=str(data.get("text_secondary", "#94a3b8")),
            badge_bg=str(data.get("badge_bg", "rgba(56, 189, 248, 0.15)")),
            badge_text=str(data.get("badge_text", "#38bdf8")),
            border_color=str(data.get("border_color", "rgba(255, 255, 255, 0.1)")),
            glow_color=str(data.get("glow_color", "#38bdf8")),
            is_dark=bool(data.get("is_dark", True)),
            gradient_angle=int(data.get("gradient_angle", 135)),
            card_bg=data.get("card_bg"),
            font_primary=str(data.get("font_primary", "Inter")),
            font_secondary=str(data.get("font_secondary", "Inter")),
            font_mono=str(data.get("font_mono", "JetBrains Mono")),
        )


@dataclass
class BadgeSpec:
    """Badge pill specification with customizable styling and optional icon."""

    text: str
    bg_color: Optional[str] = None
    text_color: Optional[str] = None
    icon_svg: Optional[str] = None
    border_color: Optional[str] = None


@dataclass
class AuthorSpec:
    """Author attribution with avatar, title, and social handle."""

    name: str
    title: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_svg: Optional[str] = None
    handle: Optional[str] = None


@dataclass
class OGCardConfig:
    """Comprehensive configuration options for generating Open Graph cards."""

    title: str
    subtitle: Optional[str] = None
    author: Optional[Union[AuthorSpec, str]] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    site_name: Optional[str] = None
    theme: Union[CardTheme, str] = "aurora"
    layout: Union[CardLayout, str] = CardLayout.DEFAULT
    dimensions: Union[CardDimension, Tuple[int, int], str] = field(
        default_factory=lambda: CardDimension.STANDARD_OG
    )
    pattern: Optional[str] = "dot_grid"
    logo_svg: Optional[str] = None
    icon_svg: Optional[str] = None
    reading_time_min: Optional[int] = None
    date_str: Optional[str] = None
    code_snippet: Optional[str] = None
    code_language: Optional[str] = None
    episode_number: Optional[str] = None
    ticket_number: Optional[str] = None
    badge: Optional[Union[BadgeSpec, str]] = None
    watermark: Optional[str] = None
    custom_css: Optional[str] = None

    def __post_init__(self) -> None:
        """Normalize fields after initialization."""
        if isinstance(self.author, str):
            self.author = AuthorSpec(name=self.author)
        if isinstance(self.badge, str):
            self.badge = BadgeSpec(text=self.badge)
        if isinstance(self.layout, str):
            self.layout = CardLayout.from_str(self.layout)
        if not isinstance(self.dimensions, CardDimension):
            self.dimensions = CardDimension.from_value(self.dimensions)


@dataclass
class GeneratedCard:
    """Result of SVG rendering containing artifacts and conversion helpers."""

    svg: str
    html_meta: str
    width: int
    height: int
    title: str
    config: OGCardConfig

    def save_svg(self, file_path: Union[str, Path]) -> Path:
        """Save card SVG to disk atomically."""
        return atomic_write_text(file_path, self.svg, encoding="utf-8")

    def save_meta(self, file_path: Union[str, Path]) -> Path:
        """Save HTML meta tags to disk atomically."""
        return atomic_write_text(file_path, self.html_meta, encoding="utf-8")

    def save_html_meta(self, file_path: Union[str, Path]) -> Path:
        """Alias for save_meta."""
        return self.save_meta(file_path)

    def to_bmp(self) -> bytes:
        """Render standalone 24-bit BMP image bytes (zero third-party dependencies)."""
        from .card_generator import render_svg_to_bmp
        return render_svg_to_bmp(self.svg, self.width, self.height)

    def save_bmp(self, file_path: Union[str, Path]) -> Path:
        """Rasterize and save BMP image to disk atomically."""
        return atomic_write_bytes(file_path, self.to_bmp())

    def to_ppm(self) -> bytes:
        """Render standalone PPM (P6 binary) image bytes (zero third-party dependencies)."""
        from .card_generator import render_svg_to_ppm
        return render_svg_to_ppm(self.svg, self.width, self.height)

    def save_ppm(self, file_path: Union[str, Path]) -> Path:
        """Rasterize and save PPM image to disk atomically."""
        return atomic_write_bytes(file_path, self.to_ppm())


@dataclass
class TemplatePreset:
    """Preconfigured card template with archetype metadata."""

    id: str
    name: str
    category: str
    description: str
    config: OGCardConfig
    sample_data: Optional[Dict[str, Any]] = None
