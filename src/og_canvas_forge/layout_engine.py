"""Layout engine for og-canvas-forge.

Provides typography text wrapping, character width heuristics, dynamic font-size
auto-scaling, and multi-layout 2D bounding-box coordinate solvers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import CardDimension, CardLayout, OGCardConfig


# Relative character width metrics relative to 1.0em font-size for proportional sans fonts (Inter/Roboto)
_CHAR_WIDTHS: Dict[str, float] = {
    # Narrow punctuation & letters (~0.25 - 0.35 em)
    "i": 0.28, "l": 0.28, "j": 0.28, "!": 0.30, "|": 0.28, ":": 0.28, ";": 0.28,
    ".": 0.28, ",": 0.28, "'": 0.25, "\"": 0.35, "`": 0.25, " ": 0.28, "I": 0.32,
    "t": 0.35, "f": 0.35, "[": 0.32, "]": 0.32, "(": 0.34, ")": 0.34, "{": 0.34,
    "}": 0.34, "/": 0.38, "\\": 0.38, "-": 0.36, "_": 0.45,

    # Medium characters (~0.50 - 0.60 em)
    "a": 0.54, "b": 0.58, "c": 0.52, "d": 0.58, "e": 0.54, "g": 0.58, "h": 0.58,
    "k": 0.52, "n": 0.58, "o": 0.58, "p": 0.58, "q": 0.58, "r": 0.38, "s": 0.50,
    "u": 0.58, "v": 0.52, "x": 0.52, "y": 0.52, "z": 0.50,
    "0": 0.58, "1": 0.50, "2": 0.58, "3": 0.58, "4": 0.58, "5": 0.58, "6": 0.58,
    "7": 0.58, "8": 0.58, "9": 0.58, "?": 0.50, "$": 0.58, "%": 0.85, "&": 0.68,
    "+": 0.58, "=": 0.58, "<": 0.58, ">": 0.58, "#": 0.60, "*": 0.42, "@": 0.90,

    # Wide uppercase letters (~0.65 - 0.75 em)
    "A": 0.68, "B": 0.66, "C": 0.70, "D": 0.72, "E": 0.62, "F": 0.58, "G": 0.74,
    "H": 0.72, "J": 0.48, "K": 0.66, "L": 0.56, "N": 0.72, "O": 0.76, "P": 0.64,
    "Q": 0.76, "R": 0.66, "S": 0.62, "T": 0.60, "U": 0.72, "V": 0.66, "X": 0.66,
    "Y": 0.62, "Z": 0.62,

    # Extra wide (~0.80 - 0.95 em)
    "M": 0.88, "W": 0.92, "m": 0.84, "w": 0.78, "—": 0.85, "–": 0.55, "…": 0.80,
}


def char_width(char: str, font_size: float, font_family: str = "Inter") -> float:
    """Estimate the visual width of a single character in pixels."""
    if "mono" in font_family.lower():
        # Monospaced font standard ratio
        return font_size * 0.60

    # CJK and Full-width characters
    code = ord(char)
    if (
        (0x4E00 <= code <= 0x9FFF)
        or (0x3400 <= code <= 0x4DBF)
        or (0x3040 <= code <= 0x30FF)
        or (0xAC00 <= code <= 0xD7AF)
        or (0xFF01 <= code <= 0xFF60)
    ):
        return font_size * 1.05

    # Emojis & miscellaneous symbols
    if code > 0x1F000 or (0x2600 <= code <= 0x27BF):
        return font_size * 1.10

    # Proportional lookup with default 0.56em
    em_ratio = _CHAR_WIDTHS.get(char, 0.56)
    return font_size * em_ratio


def estimate_text_width(
    text: str,
    font_size: float,
    font_family: str = "Inter",
    letter_spacing: float = 0.0,
) -> float:
    """Calculate the total horizontal pixel width of a text string."""
    if not text:
        return 0.0
    total = sum(char_width(c, font_size, font_family) for c in text)
    if len(text) > 1 and letter_spacing != 0.0:
        total += (len(text) - 1) * letter_spacing
    return total


def estimate_text_height(
    lines_count: int,
    font_size: float,
    line_height_ratio: float = 1.25,
) -> float:
    """Calculate total bounding box height for a given number of lines."""
    if lines_count <= 0:
        return 0.0
    return (lines_count * font_size * line_height_ratio)


def truncate_with_ellipsis(
    text: str,
    max_width: float,
    font_size: float,
    font_family: str = "Inter",
    ellipsis: str = "...",
) -> str:
    """Truncate text to fit within max_width, appending an ellipsis if truncated."""
    if estimate_text_width(text, font_size, font_family) <= max_width:
        return text

    ellipsis_w = estimate_text_width(ellipsis, font_size, font_family)
    available = max(0.0, max_width - ellipsis_w)

    current_w = 0.0
    chars: List[str] = []
    for c in text:
        cw = char_width(c, font_size, font_family)
        if current_w + cw > available:
            break
        chars.append(c)
        current_w += cw

    truncated = "".join(chars).rstrip()
    return f"{truncated}{ellipsis}"


def wrap_text(
    text: str,
    max_width: float,
    font_size: float,
    font_family: str = "Inter",
    letter_spacing: float = 0.0,
) -> List[str]:
    """Wrap text into multiple lines respecting word boundaries and maximum width."""
    if not text:
        return []

    result_lines: List[str] = []
    raw_paragraphs = text.split("\n")

    for para in raw_paragraphs:
        words = para.split(" ")
        current_line_words: List[str] = []
        current_line_width = 0.0
        space_width = char_width(" ", font_size, font_family) + letter_spacing

        for word in words:
            if not word:
                continue

            word_w = estimate_text_width(word, font_size, font_family, letter_spacing)

            # Check if word alone exceeds max_width (e.g. huge URL or code token)
            if word_w > max_width and not current_line_words:
                # Force break word into chunks
                chunk: List[str] = []
                chunk_w = 0.0
                for c in word:
                    cw = char_width(c, font_size, font_family)
                    if chunk_w + cw > max_width and chunk:
                        result_lines.append("".join(chunk))
                        chunk = [c]
                        chunk_w = cw
                    else:
                        chunk.append(c)
                        chunk_w += cw
                if chunk:
                    current_line_words = ["".join(chunk)]
                    current_line_width = chunk_w
                continue

            if not current_line_words:
                current_line_words.append(word)
                current_line_width = word_w
            else:
                test_width = current_line_width + space_width + word_w
                if test_width <= max_width:
                    current_line_words.append(word)
                    current_line_width = test_width
                else:
                    result_lines.append(" ".join(current_line_words))
                    current_line_words = [word]
                    current_line_width = word_w

        if current_line_words:
            result_lines.append(" ".join(current_line_words))

    return result_lines if result_lines else [""]


def fit_text_to_box(
    text: str,
    max_width: float,
    max_height: float,
    initial_font_size: float = 64.0,
    min_font_size: float = 24.0,
    max_lines: int = 4,
    font_family: str = "Inter",
    line_height_ratio: float = 1.25,
) -> Tuple[List[str], float, float]:
    """Dynamically auto-scale font size to fit text within constraints.

    Returns:
        Tuple of (wrapped_lines, chosen_font_size, total_height_px)
    """
    if not text:
        return ([], initial_font_size, 0.0)

    best_size = min_font_size
    best_lines: List[str] = [text]
    step = 2.0

    current_size = initial_font_size
    while current_size >= min_font_size:
        lines = wrap_text(text, max_width, current_size, font_family)
        total_h = len(lines) * current_size * line_height_ratio

        if len(lines) <= max_lines and total_h <= max_height:
            best_size = current_size
            best_lines = lines
            return (best_lines, best_size, total_h)

        current_size -= step

    # Fallback to min_font_size with ellipsis truncation if still overflowing
    lines = wrap_text(text, max_width, min_font_size, font_family)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = truncate_with_ellipsis(lines[-1], max_width, min_font_size, font_family)

    total_h = len(lines) * min_font_size * line_height_ratio
    return (lines, min_font_size, total_h)


@dataclass
class BoundingBox:
    """2D rectangle with coordinates and dimensions."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass
class ComputedTextElement:
    """Positioned text line or block."""

    text: str
    x: float
    y: float
    font_size: float
    font_weight: Union[str, int] = "normal"
    font_family: str = "Inter"
    fill: str = "#ffffff"
    opacity: float = 1.0
    text_anchor: str = "start"  # "start", "middle", "end"


@dataclass
class ComputedBadge:
    """Positioned badge element."""

    text: str
    x: float
    y: float
    width: float
    height: float
    bg_color: str
    text_color: str
    border_color: str
    font_size: float
    icon_svg: Optional[str] = None


@dataclass
class ComputedAuthor:
    """Positioned author element with optional avatar and handle."""

    name: str
    handle: Optional[str]
    title: Optional[str]
    x: float
    y: float
    avatar_cx: float
    avatar_cy: float
    avatar_radius: float
    avatar_url: Optional[str] = None
    avatar_svg: Optional[str] = None
    initials: str = ""


@dataclass
class ComputedCardLayout:
    """Complete computed 2D geometry ready for SVG generation."""

    width: int
    height: int
    layout_type: CardLayout
    margin_x: float
    margin_y: float
    safe_box: BoundingBox
    badge: Optional[ComputedBadge] = None
    title_lines: List[ComputedTextElement] = field(default_factory=list)
    subtitle_lines: List[ComputedTextElement] = field(default_factory=list)
    author: Optional[ComputedAuthor] = None
    site_name: Optional[ComputedTextElement] = None
    date_tag: Optional[ComputedTextElement] = None
    reading_time: Optional[ComputedTextElement] = None
    tags: List[ComputedBadge] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


def compute_card_layout(
    config: OGCardConfig,
    width: int = 1200,
    height: int = 630,
) -> ComputedCardLayout:
    """Compute exact pixel coordinates and typographic wrapping for all card components."""
    layout = CardLayout.from_str(config.layout)
    margin_x = 72.0 if width >= 1080 else 40.0
    margin_y = 64.0 if height >= 600 else 36.0
    safe_width = width - (2 * margin_x)
    safe_height = height - (2 * margin_y)
    safe_box = BoundingBox(x=margin_x, y=margin_y, width=safe_width, height=safe_height)

    theme_font_primary = getattr(config.theme, "font_primary", "Inter") if hasattr(config.theme, "font_primary") else "Inter"
    theme_font_secondary = getattr(config.theme, "font_secondary", "Inter") if hasattr(config.theme, "font_secondary") else "Inter"

    # Layout router
    if layout == CardLayout.CENTERED:
        return _compute_centered_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)
    elif layout == CardLayout.SPLIT:
        return _compute_split_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)
    elif layout == CardLayout.MINIMAL:
        return _compute_minimal_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)
    elif layout == CardLayout.DEV_CODE:
        return _compute_dev_code_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)
    elif layout == CardLayout.PODCAST:
        return _compute_podcast_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)
    elif layout == CardLayout.EVENT_TICKET:
        return _compute_event_ticket_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)
    else:
        return _compute_default_layout(config, width, height, safe_box, theme_font_primary, theme_font_secondary)


def _compute_default_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for default editorial / blog layout."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.DEFAULT,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    current_y = safe_box.y

    # 1. Header Area: Badge / Category & Site Name
    badge_text = ""
    if config.badge:
        badge_text = config.badge.text if hasattr(config.badge, "text") else str(config.badge)
    elif config.category:
        badge_text = config.category

    if badge_text:
        badge_font_size = 15.0
        bw = estimate_text_width(badge_text, badge_font_size, font_primary) + 32.0
        bh = 34.0
        layout_obj.badge = ComputedBadge(
            text=badge_text,
            x=safe_box.x,
            y=current_y,
            width=bw,
            height=bh,
            bg_color="",
            text_color="",
            border_color="",
            font_size=badge_font_size,
            icon_svg=getattr(config.badge, "icon_svg", None) if hasattr(config.badge, "icon_svg") else None,
        )

    if config.site_name:
        site_font_size = 18.0
        layout_obj.site_name = ComputedTextElement(
            text=config.site_name,
            x=safe_box.right,
            y=current_y + 24.0,
            font_size=site_font_size,
            font_weight=600,
            font_family=font_primary,
            text_anchor="end",
        )

    current_y += 60.0 if badge_text or config.site_name else 0.0

    # 2. Title & Subtitle calculations
    # Calculate available height for title + subtitle (leave ~120px for footer)
    footer_reserve = 120.0
    available_body_height = max(180.0, safe_box.bottom - current_y - footer_reserve)

    title_max_w = safe_box.width
    init_title_size = 62.0 if width >= 1200 else 48.0
    min_title_size = 32.0 if width >= 1200 else 24.0

    has_subtitle = bool(config.subtitle and config.subtitle.strip())
    max_title_lines = 3 if has_subtitle else 4

    title_lines_raw, title_size, title_h = fit_text_to_box(
        config.title,
        title_max_w,
        available_body_height * (0.65 if has_subtitle else 0.95),
        initial_font_size=init_title_size,
        min_font_size=min_title_size,
        max_lines=max_title_lines,
        font_family=font_primary,
        line_height_ratio=1.20,
    )

    title_elements: List[ComputedTextElement] = []
    line_y = current_y + (title_size * 0.9)
    for line in title_lines_raw:
        title_elements.append(
            ComputedTextElement(
                text=line,
                x=safe_box.x,
                y=line_y,
                font_size=title_size,
                font_weight=800,
                font_family=font_primary,
                text_anchor="start",
            )
        )
        line_y += title_size * 1.20

    layout_obj.title_lines = title_elements
    current_y = line_y + 12.0

    # Subtitle
    if has_subtitle and config.subtitle:
        sub_font_size = max(18.0, min(24.0, title_size * 0.42))
        sub_lines_raw = wrap_text(config.subtitle, title_max_w, sub_font_size, font_secondary)
        max_sub_lines = 2
        if len(sub_lines_raw) > max_sub_lines:
            sub_lines_raw = sub_lines_raw[:max_sub_lines]
            sub_lines_raw[-1] = truncate_with_ellipsis(sub_lines_raw[-1], title_max_w, sub_font_size, font_secondary)

        sub_elements: List[ComputedTextElement] = []
        sub_y = current_y + (sub_font_size * 0.9)
        for sline in sub_lines_raw:
            sub_elements.append(
                ComputedTextElement(
                    text=sline,
                    x=safe_box.x,
                    y=sub_y,
                    font_size=sub_font_size,
                    font_weight=400,
                    font_family=font_secondary,
                    text_anchor="start",
                )
            )
            sub_y += sub_font_size * 1.35
        layout_obj.subtitle_lines = sub_elements

    # 3. Footer Area (Author, Date, Reading Time, Tags)
    footer_y = safe_box.bottom - 20.0
    if config.author:
        author_name = config.author.name if hasattr(config.author, "name") else str(config.author)
        handle = getattr(config.author, "handle", None) if hasattr(config.author, "handle") else None
        title = getattr(config.author, "title", None) if hasattr(config.author, "title") else None
        avatar_url = getattr(config.author, "avatar_url", None) if hasattr(config.author, "avatar_url") else None
        avatar_svg = getattr(config.author, "avatar_svg", None) if hasattr(config.author, "avatar_svg") else None

        initials = "".join([part[0].upper() for part in author_name.split() if part])[:2] if author_name else "A"

        layout_obj.author = ComputedAuthor(
            name=author_name,
            handle=handle,
            title=title,
            x=safe_box.x + 56.0,
            y=footer_y,
            avatar_cx=safe_box.x + 22.0,
            avatar_cy=footer_y - 12.0,
            avatar_radius=22.0,
            avatar_url=avatar_url,
            avatar_svg=avatar_svg,
            initials=initials,
        )

    # Right footer: date / reading time / tags
    right_x = safe_box.right
    meta_parts: List[str] = []
    if config.date_str:
        meta_parts.append(config.date_str)
    if config.reading_time_min:
        meta_parts.append(f"{config.reading_time_min} min read")
    elif config.tags:
        meta_parts.append(" • ".join([f"#{t}" for t in config.tags[:3]]))

    if meta_parts:
        meta_text = " • ".join(meta_parts)
        layout_obj.date_tag = ComputedTextElement(
            text=meta_text,
            x=right_x,
            y=footer_y,
            font_size=17.0,
            font_weight=500,
            font_family=font_secondary,
            text_anchor="end",
        )

    return layout_obj


def _compute_centered_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for clean, symmetrical centered layout."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.CENTERED,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    center_x = width / 2.0
    content_max_w = min(safe_box.width * 0.90, 960.0)

    # Calculate overall content height to center vertically
    init_title_size = 64.0 if width >= 1200 else 50.0
    min_title_size = 32.0

    has_subtitle = bool(config.subtitle and config.subtitle.strip())
    title_lines_raw, title_size, title_h = fit_text_to_box(
        config.title,
        content_max_w,
        safe_box.height * 0.55,
        initial_font_size=init_title_size,
        min_font_size=min_title_size,
        max_lines=3,
        font_family=font_primary,
        line_height_ratio=1.20,
    )

    sub_lines_raw: List[str] = []
    sub_font_size = max(18.0, title_size * 0.38)
    sub_h = 0.0
    if has_subtitle and config.subtitle:
        sub_lines_raw = wrap_text(config.subtitle, content_max_w, sub_font_size, font_secondary)
        if len(sub_lines_raw) > 2:
            sub_lines_raw = sub_lines_raw[:2]
            sub_lines_raw[-1] = truncate_with_ellipsis(sub_lines_raw[-1], content_max_w, sub_font_size, font_secondary)
        sub_h = len(sub_lines_raw) * sub_font_size * 1.35

    badge_h = 44.0 if (config.badge or config.category) else 0.0
    footer_h = 50.0 if (config.author or config.site_name) else 0.0

    total_block_h = badge_h + title_h + (sub_h + 16.0 if sub_h > 0 else 0) + footer_h + 30.0
    start_y = max(safe_box.y + 20.0, (height - total_block_h) / 2.0)

    current_y = start_y

    # Badge
    badge_text = ""
    if config.badge:
        badge_text = config.badge.text if hasattr(config.badge, "text") else str(config.badge)
    elif config.category:
        badge_text = config.category

    if badge_text:
        badge_font_size = 15.0
        bw = estimate_text_width(badge_text, badge_font_size, font_primary) + 36.0
        bh = 34.0
        layout_obj.badge = ComputedBadge(
            text=badge_text,
            x=center_x - (bw / 2.0),
            y=current_y,
            width=bw,
            height=bh,
            bg_color="",
            text_color="",
            border_color="",
            font_size=badge_font_size,
        )
        current_y += bh + 24.0

    # Title
    title_elements: List[ComputedTextElement] = []
    line_y = current_y + (title_size * 0.9)
    for line in title_lines_raw:
        title_elements.append(
            ComputedTextElement(
                text=line,
                x=center_x,
                y=line_y,
                font_size=title_size,
                font_weight=800,
                font_family=font_primary,
                text_anchor="middle",
            )
        )
        line_y += title_size * 1.20

    layout_obj.title_lines = title_elements
    current_y = line_y + 14.0

    # Subtitle
    if sub_lines_raw:
        sub_elements: List[ComputedTextElement] = []
        sub_y = current_y + (sub_font_size * 0.9)
        for sline in sub_lines_raw:
            sub_elements.append(
                ComputedTextElement(
                    text=sline,
                    x=center_x,
                    y=sub_y,
                    font_size=sub_font_size,
                    font_weight=400,
                    font_family=font_secondary,
                    text_anchor="middle",
                )
            )
            sub_y += sub_font_size * 1.35
        layout_obj.subtitle_lines = sub_elements
        current_y = sub_y + 20.0

    # Center footer
    footer_parts: List[str] = []
    if config.author:
        author_name = config.author.name if hasattr(config.author, "name") else str(config.author)
        footer_parts.append(author_name)
    if config.site_name:
        footer_parts.append(config.site_name)
    if config.reading_time_min:
        footer_parts.append(f"{config.reading_time_min} min read")
    elif config.date_str:
        footer_parts.append(config.date_str)

    if footer_parts:
        layout_obj.site_name = ComputedTextElement(
            text=" • ".join(footer_parts),
            x=center_x,
            y=safe_box.bottom - 16.0,
            font_size=18.0,
            font_weight=600,
            font_family=font_primary,
            text_anchor="middle",
        )

    return layout_obj


def _compute_split_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for split pane (60% content / 40% visual feature) layout."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.SPLIT,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    left_w = safe_box.width * 0.58
    right_w = safe_box.width * 0.38
    right_x = safe_box.x + left_w + (safe_box.width * 0.04)

    layout_obj.extra["right_pane_box"] = BoundingBox(
        x=right_x,
        y=safe_box.y,
        width=right_w,
        height=safe_box.height,
    )

    current_y = safe_box.y

    # Badge
    badge_text = ""
    if config.badge:
        badge_text = config.badge.text if hasattr(config.badge, "text") else str(config.badge)
    elif config.category:
        badge_text = config.category

    if badge_text:
        badge_font_size = 14.0
        bw = estimate_text_width(badge_text, badge_font_size, font_primary) + 28.0
        bh = 32.0
        layout_obj.badge = ComputedBadge(
            text=badge_text,
            x=safe_box.x,
            y=current_y,
            width=bw,
            height=bh,
            bg_color="",
            text_color="",
            border_color="",
            font_size=badge_font_size,
        )
        current_y += bh + 24.0

    # Left Title & Subtitle
    init_title_size = 52.0 if width >= 1200 else 42.0
    min_title_size = 28.0
    has_sub = bool(config.subtitle and config.subtitle.strip())

    title_lines_raw, title_size, title_h = fit_text_to_box(
        config.title,
        left_w,
        safe_box.height * 0.50,
        initial_font_size=init_title_size,
        min_font_size=min_title_size,
        max_lines=3,
        font_family=font_primary,
        line_height_ratio=1.20,
    )

    title_elements: List[ComputedTextElement] = []
    line_y = current_y + (title_size * 0.9)
    for line in title_lines_raw:
        title_elements.append(
            ComputedTextElement(
                text=line,
                x=safe_box.x,
                y=line_y,
                font_size=title_size,
                font_weight=800,
                font_family=font_primary,
                text_anchor="start",
            )
        )
        line_y += title_size * 1.20

    layout_obj.title_lines = title_elements
    current_y = line_y + 12.0

    if has_sub and config.subtitle:
        sub_font_size = max(17.0, title_size * 0.40)
        sub_lines_raw = wrap_text(config.subtitle, left_w, sub_font_size, font_secondary)
        if len(sub_lines_raw) > 2:
            sub_lines_raw = sub_lines_raw[:2]
            sub_lines_raw[-1] = truncate_with_ellipsis(sub_lines_raw[-1], left_w, sub_font_size, font_secondary)

        sub_elements: List[ComputedTextElement] = []
        sub_y = current_y + (sub_font_size * 0.9)
        for sline in sub_lines_raw:
            sub_elements.append(
                ComputedTextElement(
                    text=sline,
                    x=safe_box.x,
                    y=sub_y,
                    font_size=sub_font_size,
                    font_weight=400,
                    font_family=font_secondary,
                    text_anchor="start",
                )
            )
            sub_y += sub_font_size * 1.35
        layout_obj.subtitle_lines = sub_elements

    # Bottom left metadata
    footer_y = safe_box.bottom - 16.0
    if config.author:
        author_name = config.author.name if hasattr(config.author, "name") else str(config.author)
        initials = "".join([p[0].upper() for p in author_name.split() if p])[:2] if author_name else "A"
        layout_obj.author = ComputedAuthor(
            name=author_name,
            handle=getattr(config.author, "handle", None) if hasattr(config.author, "handle") else None,
            title=getattr(config.author, "title", None) if hasattr(config.author, "title") else None,
            x=safe_box.x + 50.0,
            y=footer_y,
            avatar_cx=safe_box.x + 20.0,
            avatar_cy=footer_y - 10.0,
            avatar_radius=20.0,
            avatar_url=getattr(config.author, "avatar_url", None) if hasattr(config.author, "avatar_url") else None,
            avatar_svg=getattr(config.author, "avatar_svg", None) if hasattr(config.author, "avatar_svg") else None,
            initials=initials,
        )
    elif config.site_name:
        layout_obj.site_name = ComputedTextElement(
            text=config.site_name,
            x=safe_box.x,
            y=footer_y,
            font_size=18.0,
            font_weight=600,
            font_family=font_primary,
            text_anchor="start",
        )

    return layout_obj


def _compute_minimal_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for high-impact minimalist layout."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.MINIMAL,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    current_y = safe_box.y + 20.0

    # Massive Bold Title
    init_title_size = 72.0 if width >= 1200 else 56.0
    min_title_size = 36.0

    title_lines_raw, title_size, title_h = fit_text_to_box(
        config.title,
        safe_box.width,
        safe_box.height * 0.68,
        initial_font_size=init_title_size,
        min_font_size=min_title_size,
        max_lines=3,
        font_family=font_primary,
        line_height_ratio=1.15,
    )

    title_elements: List[ComputedTextElement] = []
    line_y = current_y + (title_size * 0.9)
    for line in title_lines_raw:
        title_elements.append(
            ComputedTextElement(
                text=line,
                x=safe_box.x,
                y=line_y,
                font_size=title_size,
                font_weight=900,
                font_family=font_primary,
                text_anchor="start",
            )
        )
        line_y += title_size * 1.15

    layout_obj.title_lines = title_elements

    # Accent divider bar below title
    accent_bar_y = line_y + 16.0
    layout_obj.extra["accent_bar"] = BoundingBox(
        x=safe_box.x,
        y=accent_bar_y,
        width=96.0,
        height=6.0,
    )

    # Subtitle or description
    if config.subtitle:
        sub_font_size = 20.0
        sub_lines_raw = wrap_text(config.subtitle, safe_box.width, sub_font_size, font_secondary)
        if len(sub_lines_raw) > 2:
            sub_lines_raw = sub_lines_raw[:2]
            sub_lines_raw[-1] = truncate_with_ellipsis(sub_lines_raw[-1], safe_box.width, sub_font_size, font_secondary)

        sub_elements: List[ComputedTextElement] = []
        sub_y = accent_bar_y + 36.0
        for sline in sub_lines_raw:
            sub_elements.append(
                ComputedTextElement(
                    text=sline,
                    x=safe_box.x,
                    y=sub_y,
                    font_size=sub_font_size,
                    font_weight=400,
                    font_family=font_secondary,
                    text_anchor="start",
                )
            )
            sub_y += sub_font_size * 1.35
        layout_obj.subtitle_lines = sub_elements

    # Bottom minimal metadata
    footer_y = safe_box.bottom - 12.0
    left_meta = config.site_name or (config.author.name if hasattr(config.author, "name") else str(config.author or ""))
    if left_meta:
        layout_obj.site_name = ComputedTextElement(
            text=left_meta,
            x=safe_box.x,
            y=footer_y,
            font_size=18.0,
            font_weight=700,
            font_family=font_primary,
            text_anchor="start",
        )

    right_meta = config.category or config.date_str or (f"{config.reading_time_min} min read" if config.reading_time_min else "")
    if right_meta:
        layout_obj.date_tag = ComputedTextElement(
            text=right_meta,
            x=safe_box.right,
            y=footer_y,
            font_size=16.0,
            font_weight=500,
            font_family=font_secondary,
            text_anchor="end",
        )

    return layout_obj


def _compute_dev_code_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for developer / terminal IDE window layout."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.DEV_CODE,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    current_y = safe_box.y

    # Header: Category / Repo Name & Language Badge
    repo_title = config.title
    title_font_size = 38.0 if width >= 1200 else 30.0
    layout_obj.title_lines = [
        ComputedTextElement(
            text=repo_title,
            x=safe_box.x,
            y=current_y + 30.0,
            font_size=title_font_size,
            font_weight=800,
            font_family=font_primary,
            text_anchor="start",
        )
    ]

    badge_text = config.code_language or config.category or "Python"
    bw = estimate_text_width(badge_text, 14.0, font_primary) + 28.0
    layout_obj.badge = ComputedBadge(
        text=badge_text,
        x=safe_box.right - bw,
        y=current_y + 6.0,
        width=bw,
        height=32.0,
        bg_color="",
        text_color="",
        border_color="",
        font_size=14.0,
    )

    current_y += 62.0

    # Terminal IDE Window Box
    term_w = safe_box.width
    term_h = safe_box.height - (current_y - safe_box.y) - 60.0
    layout_obj.extra["terminal_box"] = BoundingBox(
        x=safe_box.x,
        y=current_y,
        width=term_w,
        height=term_h,
    )

    # Footer stats: Stars, Forks, Author
    footer_y = safe_box.bottom - 12.0
    if config.author:
        author_name = config.author.name if hasattr(config.author, "name") else str(config.author)
        layout_obj.author = ComputedAuthor(
            name=author_name,
            handle=getattr(config.author, "handle", None) if hasattr(config.author, "handle") else None,
            title=getattr(config.author, "title", None) if hasattr(config.author, "title") else None,
            x=safe_box.x + 36.0,
            y=footer_y,
            avatar_cx=safe_box.x + 14.0,
            avatar_cy=footer_y - 8.0,
            avatar_radius=14.0,
            avatar_url=getattr(config.author, "avatar_url", None) if hasattr(config.author, "avatar_url") else None,
            avatar_svg=getattr(config.author, "avatar_svg", None) if hasattr(config.author, "avatar_svg") else None,
            initials=author_name[:2].upper() if author_name else "GH",
        )

    stats_str = config.subtitle or config.site_name or "github.com"
    layout_obj.site_name = ComputedTextElement(
        text=stats_str,
        x=safe_box.right,
        y=footer_y,
        font_size=16.0,
        font_weight=500,
        font_family="JetBrains Mono",
        text_anchor="end",
    )

    return layout_obj


def _compute_podcast_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for podcast episode card with album frame & waveform."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.PODCAST,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    # Left: Album Art / Cover Box (square)
    album_size = min(safe_box.height, 460.0)
    layout_obj.extra["album_art_box"] = BoundingBox(
        x=safe_box.x,
        y=safe_box.y + ((safe_box.height - album_size) / 2.0),
        width=album_size,
        height=album_size,
    )

    right_x = safe_box.x + album_size + 48.0
    right_w = safe_box.right - right_x
    current_y = safe_box.y + 24.0

    # Episode Number Badge
    ep_badge_text = config.episode_number or "EPISODE"
    if not ep_badge_text.upper().startswith("EP"):
        ep_badge_text = f"EPISODE {ep_badge_text}"

    bw = estimate_text_width(ep_badge_text, 14.0, font_primary) + 28.0
    layout_obj.badge = ComputedBadge(
        text=ep_badge_text,
        x=right_x,
        y=current_y,
        width=bw,
        height=32.0,
        bg_color="",
        text_color="",
        border_color="",
        font_size=14.0,
    )
    current_y += 56.0

    # Episode Title
    title_lines_raw, title_size, title_h = fit_text_to_box(
        config.title,
        right_w,
        safe_box.height * 0.45,
        initial_font_size=48.0 if width >= 1200 else 38.0,
        min_font_size=26.0,
        max_lines=3,
        font_family=font_primary,
        line_height_ratio=1.20,
    )

    title_elements: List[ComputedTextElement] = []
    line_y = current_y + (title_size * 0.9)
    for line in title_lines_raw:
        title_elements.append(
            ComputedTextElement(
                text=line,
                x=right_x,
                y=line_y,
                font_size=title_size,
                font_weight=800,
                font_family=font_primary,
                text_anchor="start",
            )
        )
        line_y += title_size * 1.20

    layout_obj.title_lines = title_elements
    current_y = line_y + 14.0

    # Host / Guest Subtitle
    if config.subtitle:
        sub_font_size = 20.0
        sub_lines_raw = wrap_text(config.subtitle, right_w, sub_font_size, font_secondary)
        sub_elements: List[ComputedTextElement] = []
        sub_y = current_y + (sub_font_size * 0.9)
        for sline in sub_lines_raw[:2]:
            sub_elements.append(
                ComputedTextElement(
                    text=sline,
                    x=right_x,
                    y=sub_y,
                    font_size=sub_font_size,
                    font_weight=500,
                    font_family=font_secondary,
                    text_anchor="start",
                )
            )
            sub_y += sub_font_size * 1.35
        layout_obj.subtitle_lines = sub_elements

    # Bottom Right Info: Podcast Name & Duration
    footer_y = safe_box.bottom - 20.0
    show_name = config.site_name or "Podcast Network"
    duration = f"{config.reading_time_min} MIN" if config.reading_time_min else (config.date_str or "LISTEN NOW")

    layout_obj.site_name = ComputedTextElement(
        text=show_name,
        x=right_x,
        y=footer_y,
        font_size=18.0,
        font_weight=700,
        font_family=font_primary,
        text_anchor="start",
    )

    layout_obj.date_tag = ComputedTextElement(
        text=duration,
        x=safe_box.right,
        y=footer_y,
        font_size=16.0,
        font_weight=600,
        font_family=font_primary,
        text_anchor="end",
    )

    return layout_obj


def _compute_event_ticket_layout(
    config: OGCardConfig,
    width: int,
    height: int,
    safe_box: BoundingBox,
    font_primary: str,
    font_secondary: str,
) -> ComputedCardLayout:
    """Compute coordinates for event ticket stub layout with perforated separator."""
    layout_obj = ComputedCardLayout(
        width=width,
        height=height,
        layout_type=CardLayout.EVENT_TICKET,
        margin_x=safe_box.x,
        margin_y=safe_box.y,
        safe_box=safe_box,
    )

    # Perforated divider at 74% width
    divider_x = width * 0.74
    layout_obj.extra["divider_x"] = divider_x
    layout_obj.extra["notch_radius"] = 24.0

    left_w = divider_x - safe_box.x - 40.0
    current_y = safe_box.y + 12.0

    # Event category / pass badge
    badge_text = config.ticket_number or config.badge.text if hasattr(config.badge, "text") else (config.category or "VIP PASS")
    bw = estimate_text_width(badge_text, 14.0, font_primary) + 28.0
    layout_obj.badge = ComputedBadge(
        text=badge_text,
        x=safe_box.x,
        y=current_y,
        width=bw,
        height=32.0,
        bg_color="",
        text_color="",
        border_color="",
        font_size=14.0,
    )
    current_y += 54.0

    # Event Title
    title_lines_raw, title_size, title_h = fit_text_to_box(
        config.title,
        left_w,
        safe_box.height * 0.45,
        initial_font_size=52.0 if width >= 1200 else 42.0,
        min_font_size=28.0,
        max_lines=3,
        font_family=font_primary,
        line_height_ratio=1.20,
    )

    title_elements: List[ComputedTextElement] = []
    line_y = current_y + (title_size * 0.9)
    for line in title_lines_raw:
        title_elements.append(
            ComputedTextElement(
                text=line,
                x=safe_box.x,
                y=line_y,
                font_size=title_size,
                font_weight=900,
                font_family=font_primary,
                text_anchor="start",
            )
        )
        line_y += title_size * 1.20

    layout_obj.title_lines = title_elements
    current_y = line_y + 12.0

    # Event Venue / Subtitle
    if config.subtitle:
        sub_font_size = 20.0
        sub_lines_raw = wrap_text(config.subtitle, left_w, sub_font_size, font_secondary)
        sub_elements: List[ComputedTextElement] = []
        sub_y = current_y + (sub_font_size * 0.9)
        for sline in sub_lines_raw[:2]:
            sub_elements.append(
                ComputedTextElement(
                    text=sline,
                    x=safe_box.x,
                    y=sub_y,
                    font_size=sub_font_size,
                    font_weight=500,
                    font_family=font_secondary,
                    text_anchor="start",
                )
            )
            sub_y += sub_font_size * 1.35
        layout_obj.subtitle_lines = sub_elements

    # Bottom left details (Date, Time, Location)
    footer_y = safe_box.bottom - 16.0
    date_str = config.date_str or "OCTOBER 24-26, 2026"
    layout_obj.site_name = ComputedTextElement(
        text=date_str,
        x=safe_box.x,
        y=footer_y,
        font_size=18.0,
        font_weight=700,
        font_family=font_primary,
        text_anchor="start",
    )

    # Right Stub Area
    stub_box = BoundingBox(
        x=divider_x + 32.0,
        y=safe_box.y,
        width=width - divider_x - 32.0 - safe_box.x,
        height=safe_box.height,
    )
    layout_obj.extra["stub_box"] = stub_box

    return layout_obj
