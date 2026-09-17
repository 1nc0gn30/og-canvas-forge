"""Pure SVG geometric background pattern synthesizer for og-canvas-forge.

Provides mathematical vector pattern generators for Dot Matrix, Blueprint Grid,
Isometric Hex, Diagonal Hatching, Circuit Traces, Concentric Rings, and Cross Grids.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


def _pattern_dot_grid(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    size = round(28 * scale, 2)
    r = round(1.6 * scale, 2)
    mid = round(size / 2.0, 2)
    return (
        f'<pattern id="{pattern_id}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">\n'
        f'  <circle cx="{mid}" cy="{mid}" r="{r}" fill="{color}" fill-opacity="{opacity}" />\n'
        f"</pattern>"
    )


def _pattern_blueprint(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    sub_size = round(10 * scale, 2)
    major_size = round(50 * scale, 2)
    sub_id = f"{pattern_id}_sub"
    return (
        f'<pattern id="{sub_id}" width="{sub_size}" height="{sub_size}" patternUnits="userSpaceOnUse">\n'
        f'  <path d="M {sub_size} 0 L 0 0 0 {sub_size}" fill="none" stroke="{color}" stroke-width="0.75" stroke-opacity="{round(opacity * 0.5, 3)}" />\n'
        f"</pattern>\n"
        f'<pattern id="{pattern_id}" width="{major_size}" height="{major_size}" patternUnits="userSpaceOnUse">\n'
        f'  <rect width="{major_size}" height="{major_size}" fill="url(#{sub_id})" />\n'
        f'  <path d="M {major_size} 0 L 0 0 0 {major_size}" fill="none" stroke="{color}" stroke-width="1.5" stroke-opacity="{opacity}" />\n'
        f"</pattern>"
    )


def _pattern_hex_grid(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    w = round(48 * scale, 2)
    h = round(27.71 * scale, 2)
    w_half = round(w / 2.0, 2)
    h_half = round(h / 2.0, 2)
    w_quart = round(w / 4.0, 2)
    w_3quart = round(3 * w / 4.0, 2)
    return (
        f'<pattern id="{pattern_id}" width="{w}" height="{h * 2}" patternUnits="userSpaceOnUse">\n'
        f'  <path d="M 0 {h_half} L {w_quart} 0 L {w_3quart} 0 L {w} {h_half} L {w_3quart} {h} L {w_quart} {h} Z '
        f'M 0 {h + h_half} L {w_quart} {h} L {w_3quart} {h} L {w} {h + h_half} L {w_3quart} {h * 2} L {w_quart} {h * 2} Z" '
        f'fill="none" stroke="{color}" stroke-width="1.2" stroke-opacity="{opacity}" />\n'
        f"</pattern>"
    )


def _pattern_hatching(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    size = round(20 * scale, 2)
    return (
        f'<pattern id="{pattern_id}" width="{size}" height="{size}" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">\n'
        f'  <line x1="0" y1="0" x2="0" y2="{size}" stroke="{color}" stroke-width="{round(2 * scale, 2)}" stroke-opacity="{opacity}" />\n'
        f"</pattern>"
    )


def _pattern_circuits(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    size = round(80 * scale, 2)
    s = scale
    return (
        f'<pattern id="{pattern_id}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">\n'
        f'  <g fill="none" stroke="{color}" stroke-width="{round(1.5 * s, 2)}" stroke-opacity="{opacity}">\n'
        f'    <path d="M {round(10*s,1)} 0 v {round(30*s,1)} h {round(20*s,1)} v {round(40*s,1)}" />\n'
        f'    <path d="M {round(50*s,1)} 0 v {round(20*s,1)} h {round(20*s,1)} v {round(30*s,1)} h {round(10*s,1)}" />\n'
        f'    <path d="M 0 {round(40*s,1)} h {round(15*s,1)} v {round(25*s,1)} h {round(35*s,1)}" />\n'
        f'    <circle cx="{round(30*s,1)}" cy="{round(30*s,1)}" r="{round(3*s,1)}" fill="{color}" fill-opacity="{opacity}" stroke="none" />\n'
        f'    <circle cx="{round(70*s,1)}" cy="{round(50*s,1)}" r="{round(3*s,1)}" fill="{color}" fill-opacity="{opacity}" stroke="none" />\n'
        f'    <circle cx="{round(50*s,1)}" cy="{round(65*s,1)}" r="{round(3*s,1)}" fill="{color}" fill-opacity="{opacity}" stroke="none" />\n'
        f"  </g>\n"
        f"</pattern>"
    )


def _pattern_crosses(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    size = round(36 * scale, 2)
    mid = round(size / 2.0, 2)
    arm = round(4 * scale, 2)
    return (
        f'<pattern id="{pattern_id}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">\n'
        f'  <path d="M {mid - arm} {mid} H {mid + arm} M {mid} {mid - arm} V {mid + arm}" '
        f'stroke="{color}" stroke-width="{round(1.5 * scale, 2)}" stroke-opacity="{opacity}" stroke-linecap="round" />\n'
        f"</pattern>"
    )


def _pattern_rings(color: str, opacity: float, scale: float, pattern_id: str) -> str:
    size = round(120 * scale, 2)
    mid = round(size / 2.0, 2)
    r1 = round(18 * scale, 2)
    r2 = round(36 * scale, 2)
    r3 = round(54 * scale, 2)
    return (
        f'<pattern id="{pattern_id}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">\n'
        f'  <g fill="none" stroke="{color}" stroke-width="{round(1.2 * scale, 2)}" stroke-opacity="{opacity}">\n'
        f'    <circle cx="{mid}" cy="{mid}" r="{r1}" />\n'
        f'    <circle cx="{mid}" cy="{mid}" r="{r2}" stroke-dasharray="4 4" />\n'
        f'    <circle cx="{mid}" cy="{mid}" r="{r3}" />\n'
        f"  </g>\n"
        f"</pattern>"
    )


_PATTERN_GENERATORS = {
    "dot_grid": _pattern_dot_grid,
    "dots": _pattern_dot_grid,
    "blueprint": _pattern_blueprint,
    "grid": _pattern_blueprint,
    "hex_grid": _pattern_hex_grid,
    "hexagons": _pattern_hex_grid,
    "hatching": _pattern_hatching,
    "stripes": _pattern_hatching,
    "circuits": _pattern_circuits,
    "circuit": _pattern_circuits,
    "crosses": _pattern_crosses,
    "plus": _pattern_crosses,
    "rings": _pattern_rings,
    "concentric": _pattern_rings,
}


def list_patterns() -> List[str]:
    """List all supported geometric pattern identifiers."""
    return [
        "dot_grid",
        "blueprint",
        "hex_grid",
        "hatching",
        "circuits",
        "crosses",
        "rings",
    ]


def get_pattern_svg(
    pattern_type: Optional[str],
    color: str = "#ffffff",
    opacity: float = 0.08,
    scale: float = 1.0,
    pattern_id: str = "bg_pattern",
) -> Tuple[str, str]:
    """Generate SVG pattern definition and background fill rectangle.

    Returns:
        Tuple of (pattern_def_xml, rect_fill_xml)
    """
    if not pattern_type or pattern_type.lower() in ("none", "null", "false", "empty"):
        return ("", "")

    key = pattern_type.lower().strip().replace("-", "_").replace(" ", "_")
    generator = _PATTERN_GENERATORS.get(key, _pattern_dot_grid)
    pattern_def = generator(color, opacity, scale, pattern_id)
    rect_fill = f'<rect width="100%" height="100%" fill="url(#{pattern_id})" />'
    return (pattern_def, rect_fill)
