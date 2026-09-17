"""Pure Python stdlib ThreadingHTTPServer for OG Canvas Forge Studio UI and REST API.

Provides local development server, REST API endpoints for card generation, templates,
themes, meta tags, and batch processing, plus embedded fallback UI support.
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import sys
import time
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .compat import get_platform_info, normalize_path, safe_read_bytes, safe_read_text
from .models import CardDimension, CardLayout, CardTheme, GeneratedCard, OGCardConfig


def _get_default_public_dir() -> Path:
    """Resolve the default public/ directory location."""
    # Try repository root public/
    curr = Path(__file__).resolve().parent
    repo_public = curr.parent.parent / "public"
    if repo_public.is_dir():
        return repo_public
    # Try package internal public/
    pkg_public = curr / "public"
    if pkg_public.is_dir():
        return pkg_public
    return repo_public


# Built-in fallback template catalog metadata if catalog module not yet loaded
_DEFAULT_TEMPLATES = [
    {
        "id": "modern_minimal",
        "name": "Modern Minimal",
        "category": "General",
        "description": "Clean, spacious composition with high-contrast typography and accent badge.",
    },
    {
        "id": "dev_code",
        "name": "Developer Terminal",
        "category": "Developer",
        "description": "Dark developer console window with colored dots, prompt symbols, and monospace font.",
    },
    {
        "id": "saas_hero",
        "name": "SaaS Launch Hero",
        "category": "Product",
        "description": "Bold headline layout with dual pill badges, gradient glow orb, and metric highlights.",
    },
    {
        "id": "blog_post",
        "name": "Editorial Blog Post",
        "category": "Content",
        "description": "Editorial layout featuring author avatar spotlight, estimated reading time, and date badge.",
    },
    {
        "id": "tech_conference",
        "name": "Keynote Conference",
        "category": "Events",
        "description": "Stage keynote card with conference date badge, speaker details, and dynamic mesh backdrop.",
    },
    {
        "id": "podcast",
        "name": "Podcast Episode",
        "category": "Media",
        "description": "Media player card with animated waveform bars, episode number chip, and host attribution.",
    },
    {
        "id": "newsletter",
        "name": "Newsletter Issue",
        "category": "Content",
        "description": "Clean newsletter banner with issue number chip, topic pills, and subscriber highlights.",
    },
    {
        "id": "google_clean",
        "name": "Google Material 3",
        "category": "Brand",
        "description": "Signature Google quad-color accent strip (Blue, Red, Yellow, Green) with clean Material 3 card.",
    },
    {
        "id": "matrix_cyber",
        "name": "Matrix Cyberpunk",
        "category": "Developer",
        "description": "Cyberpunk terminal with green phosphor palette, hex matrix pattern, and glowing telemetry border.",
    },
    {
        "id": "retro_arcade",
        "name": "Retro Arcade",
        "category": "Gaming",
        "description": "8-bit retro synthwave aesthetic with neon grid lines and pixel arcade typography styling.",
    },
]

# Built-in fallback themes
_DEFAULT_THEMES = [
    {
        "id": "aurora",
        "name": "Aurora Gradient",
        "bg_start": "#0f172a",
        "bg_end": "#1e1b4b",
        "accent": "#38bdf8",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "is_dark": True,
    },
    {
        "id": "google_blue",
        "name": "Google Material Signature",
        "bg_start": "#ffffff",
        "bg_end": "#f8f9fa",
        "accent": "#1a73e8",
        "text_primary": "#202124",
        "text_secondary": "#5f6368",
        "is_dark": False,
    },
    {
        "id": "cyber_neon",
        "name": "Cyber Neon",
        "bg_start": "#0b0f19",
        "bg_end": "#000000",
        "accent": "#00ffcc",
        "text_primary": "#f0f6fc",
        "text_secondary": "#8b949e",
        "is_dark": True,
    },
    {
        "id": "emerald_matrix",
        "name": "Emerald Matrix",
        "bg_start": "#022c22",
        "bg_end": "#064e3b",
        "accent": "#34d399",
        "text_primary": "#ecfdf5",
        "text_secondary": "#6ee7b7",
        "is_dark": True,
    },
    {
        "id": "crimson_nebula",
        "name": "Crimson Nebula",
        "bg_start": "#1f1124",
        "bg_end": "#3b0764",
        "accent": "#f43f5e",
        "text_primary": "#fff1f2",
        "text_secondary": "#fda4af",
        "is_dark": True,
    },
    {
        "id": "sunset_amber",
        "name": "Sunset Amber",
        "bg_start": "#1c1917",
        "bg_end": "#451a03",
        "accent": "#f59e0b",
        "text_primary": "#fef3c7",
        "text_secondary": "#fde68a",
        "is_dark": True,
    },
    {
        "id": "deep_purple",
        "name": "Deep Purple",
        "bg_start": "#0f0c1b",
        "bg_end": "#2e1065",
        "accent": "#8b5cf6",
        "text_primary": "#f5f3ff",
        "text_secondary": "#c4b5fd",
        "is_dark": True,
    },
    {
        "id": "monokai_dark",
        "name": "Monokai Hacker",
        "bg_start": "#272822",
        "bg_end": "#1e1f1c",
        "accent": "#a6e22e",
        "text_primary": "#f8f8f2",
        "text_secondary": "#a5a5a5",
        "is_dark": True,
    },
    {
        "id": "slate_dark",
        "name": "Titanium Slate",
        "bg_start": "#0f172a",
        "bg_end": "#1e293b",
        "accent": "#38bdf8",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "is_dark": True,
    },
    {
        "id": "pure_dark",
        "name": "Pure OLED Black",
        "bg_start": "#000000",
        "bg_end": "#121212",
        "accent": "#ffffff",
        "text_primary": "#ffffff",
        "text_secondary": "#a1a1aa",
        "is_dark": True,
    },
    {
        "id": "platinum_light",
        "name": "Platinum Light",
        "bg_start": "#f8fafc",
        "bg_end": "#e2e8f0",
        "accent": "#2563eb",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "is_dark": False,
    },
]


def _generate_fallback_svg(config: OGCardConfig) -> str:
    """Generate a clean SVG card when external generator module is loading or standalone."""
    w = config.dimensions.width if isinstance(config.dimensions, CardDimension) else 1200
    h = config.dimensions.height if isinstance(config.dimensions, CardDimension) else 630

    theme_id = config.theme if isinstance(config.theme, str) else config.theme.id
    selected_theme = next((t for t in _DEFAULT_THEMES if t["id"] == theme_id), _DEFAULT_THEMES[0])

    bg_start = selected_theme.get("bg_start", "#0f172a")
    bg_end = selected_theme.get("bg_end", "#1e1b4b")
    accent = selected_theme.get("accent", "#38bdf8")
    text_primary = selected_theme.get("text_primary", "#f8fafc")
    text_secondary = selected_theme.get("text_secondary", "#94a3b8")
    is_dark = selected_theme.get("is_dark", True)

    title_safe = html.escape(config.title or "OpenGraph Social Card")
    sub_safe = html.escape(config.subtitle or "")
    cat_safe = html.escape(config.category or "").upper()
    author_name = ""
    author_handle = ""
    if config.author:
        if isinstance(config.author, str):
            author_name = config.author
        else:
            author_name = config.author.name or ""
            author_handle = config.author.handle or ""
    author_safe = html.escape(author_name)
    handle_safe = html.escape(author_handle)
    site_safe = html.escape(config.site_name or "og-canvas-forge")

    badge_bg = "rgba(56, 189, 248, 0.15)" if is_dark else "rgba(26, 115, 232, 0.12)"

    # Wrap title into lines
    words = (config.title or "OpenGraph Social Card").split()
    lines = []
    curr = ""
    for word in words:
        if len(curr + " " + word) > 30:
            if curr:
                lines.append(curr)
            curr = word
        else:
            curr = (curr + " " + word).strip()
    if curr:
        lines.append(curr)
    if not lines:
        lines = [title_safe]

    title_spans = "".join(
        f'<tspan x="80" dy="{0 if idx == 0 else 64}">{html.escape(l)}</tspan>'
        for idx, l in enumerate(lines)
    )

    tags_svg = ""
    if config.tags:
        for i, tag in enumerate(config.tags[:4]):
            tx = 80 + i * 140
            tags_svg += (
                f'<g transform="translate({tx}, 510)">\n'
                f'  <rect width="120" height="32" rx="16" fill="{badge_bg}" />\n'
                f'  <text x="60" y="21" font-family="\'Google Sans\', \'Inter\', sans-serif" font-size="13" font-weight="600" fill="{accent}" text-anchor="middle">#{html.escape(tag)}</text>\n'
                f'</g>\n'
            )

    is_google = str(config.layout).lower() in ("google_clean", "cardlayout.google_clean") or theme_id == "google_blue"
    google_strip = (
        '<rect x="0" y="0" width="100%" height="8" fill="url(#googleStrip)" />\n'
        if is_google
        else ""
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_start}" />
      <stop offset="100%" stop-color="{bg_end}" />
    </linearGradient>
    <linearGradient id="googleStrip" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#4285f4" />
      <stop offset="25%" stop-color="#4285f4" />
      <stop offset="25%" stop-color="#ea4335" />
      <stop offset="50%" stop-color="#ea4335" />
      <stop offset="50%" stop-color="#fbbc04" />
      <stop offset="75%" stop-color="#fbbc04" />
      <stop offset="75%" stop-color="#34a853" />
      <stop offset="100%" stop-color="#34a853" />
    </linearGradient>
    <pattern id="dotGrid" width="32" height="32" patternUnits="userSpaceOnUse">
      <circle cx="16" cy="16" r="1.5" fill="{accent}" opacity="0.15" />
    </pattern>
  </defs>

  <rect width="100%" height="100%" fill="url(#bgGradient)" />
  <rect width="100%" height="100%" fill="url(#dotGrid)" />
  {google_strip}

  {f'''<g transform="translate(80, 80)">
    <rect width="140" height="34" rx="17" fill="{badge_bg}" stroke="{accent}" stroke-opacity="0.3" stroke-width="1" />
    <text x="70" y="22" font-family="'Google Sans', 'Inter', sans-serif" font-size="13" font-weight="700" fill="{accent}" text-anchor="middle" letter-spacing="0.5">{cat_safe}</text>
  </g>''' if cat_safe else ''}

  <text x="{w - 80}" y="100" font-family="'Google Sans Mono', 'JetBrains Mono', monospace" font-size="14" font-weight="600" fill="{text_secondary}" text-anchor="end">{site_safe}</text>

  <text x="80" y="190" font-family="'Google Sans', 'Outfit', 'Inter', sans-serif" font-size="52" font-weight="800" fill="{text_primary}" letter-spacing="-1">
    {title_spans}
  </text>

  {f'''<text x="80" y="320" font-family="'Google Sans', 'Inter', sans-serif" font-size="22" font-weight="400" fill="{text_secondary}">
    {sub_safe}
  </text>''' if sub_safe else ''}

  {tags_svg}

  {f'''<g transform="translate(80, {h - 80})">
    <circle cx="20" cy="0" r="20" fill="{accent}" />
    <text x="20" y="6" font-family="'Google Sans', sans-serif" font-size="14" font-weight="700" fill="#ffffff" text-anchor="middle">{author_safe[0] if author_safe else 'O'}</text>
    <text x="52" y="-4" font-family="'Google Sans', sans-serif" font-size="15" font-weight="700" fill="{text_primary}">{author_safe}</text>
    <text x="52" y="14" font-family="'Google Sans', sans-serif" font-size="12" fill="{text_secondary}">{handle_safe or site_safe}</text>
  </g>''' if author_safe else ''}
</svg>"""


def _generate_html_meta_tags(
    title: str,
    description: str = "",
    image_url: str = "https://example.com/og-image.svg",
    site_name: str = "example.com",
    twitter_handle: str = "@antigravity",
    card_type: str = "summary_large_image",
    width: int = 1200,
    height: int = 630,
) -> str:
    """Generate standard OpenGraph and Twitter HTML meta tags."""
    t_safe = html.escape(title)
    d_safe = html.escape(description)
    img_safe = html.escape(image_url)
    site_safe = html.escape(site_name)
    tw_safe = html.escape(twitter_handle)

    return f"""<!-- Open Graph / Facebook -->
<meta property="og:type" content="website">
<meta property="og:url" content="https://{site_safe}">
<meta property="og:title" content="{t_safe}">
<meta property="og:description" content="{d_safe}">
<meta property="og:image" content="{img_safe}">
<meta property="og:image:width" content="{width}">
<meta property="og:image:height" content="{height}">

<!-- Twitter / X -->
<meta name="twitter:card" content="{card_type}">
<meta name="twitter:site" content="{tw_safe}">
<meta name="twitter:creator" content="{tw_safe}">
<meta name="twitter:title" content="{t_safe}">
<meta name="twitter:description" content="{d_safe}">
<meta name="twitter:image" content="{img_safe}">"""


class StudioHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler implementing Google OG Canvas Studio UI and REST endpoints."""

    server_version = "OGCanvasStudio/0.1.0"
    sys_version = ""

    @property
    def studio_server(self) -> StudioServer:
        """Type helper for accessing server properties."""
        return self.server  # type: ignore[return-value]

    def _send_cors_headers(self) -> None:
        """Send standard Cross-Origin Resource Sharing (CORS) headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        """Serialize and send JSON response."""
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_svg(self, svg_content: str, status: int = HTTPStatus.OK) -> None:
        """Send raw SVG response."""
        content = svg_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_html(self, html_content: str, status: int = HTTPStatus.OK) -> None:
        """Send HTML document response."""
        content = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_error_json(self, message: str, status: int = HTTPStatus.BAD_REQUEST, details: Any = None) -> None:
        """Send structured JSON error response."""
        err_data = {
            "error": message,
            "status": status,
            "details": details,
            "timestamp": time.time(),
        }
        self._send_json(err_data, status=status)

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight HTTP requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for static assets and REST endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # 1. API: List Templates
        if path == "/api/templates":
            self._handle_api_templates()
            return

        # 2. API: List Themes
        if path == "/api/themes":
            self._handle_api_themes()
            return

        # 3. API: Session Statistics
        if path == "/api/stats":
            self._handle_api_stats()
            return

        # 4. API: System Diagnostics
        if path == "/api/diagnostics":
            self._handle_api_diagnostics()
            return

        # 5. API: Card Accessibility Audit
        if path == "/api/audit":
            query = urllib.parse.parse_qs(parsed_url.query)
            theme = query.get("theme", ["aurora"])[0]
            template = query.get("template", [None])[0]
            self._handle_api_audit({"theme": theme, "template": template})
            return

        # 5b. API: QR Code Generation
        if path == "/api/qr":
            query = urllib.parse.parse_qs(parsed_url.query)
            text = query.get("text", ["https://example.com"])[0]
            size = int(query.get("size", [120])[0])
            from .qr_matrix import render_qr_svg
            qr_svg = render_qr_svg(text, size=size)
            self._send_json({"text": text, "svg": qr_svg, "size": size})
            return

        # 6. UI Root and Static Files
        if path in ("/", "/index.html", "/studio"):
            self._serve_studio_index()
            return

        # Serve static file if exists in public directory
        public_dir = self.studio_server.public_dir
        rel_path = path.lstrip("/")
        target_file = (public_dir / rel_path).resolve()

        # Prevent directory traversal
        try:
            target_file.relative_to(public_dir.resolve())
        except ValueError:
            self._send_error_json("Access denied: Invalid path traversal", status=HTTPStatus.FORBIDDEN)
            return

        if target_file.is_file():
            mime_type, _ = mimetypes.guess_type(str(target_file))
            if not mime_type:
                mime_type = "application/octet-stream"
            data = safe_read_bytes(target_file)
            if data is not None:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(data)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(data)
                return

        # Not found fallback
        self._send_error_json(f"Endpoint or asset not found: {path}", status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        """Handle POST requests for card rendering and batch generation."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read request body
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            self._send_error_json("Invalid Content-Length header", status=HTTPStatus.BAD_REQUEST)
            return

        if length > 10 * 1024 * 1024:  # 10MB limit
            self._send_error_json("Request payload too large (>10MB)", status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body_str = body_bytes.decode("utf-8")
            payload = json.loads(body_str) if body_str.strip() else {}
        except Exception as err:
            self._send_error_json(f"Malformed JSON payload: {err}", status=HTTPStatus.BAD_REQUEST)
            return

        # Route POST endpoints
        if path == "/api/generate":
            self._handle_api_generate(payload)
            return
        elif path == "/api/meta":
            self._handle_api_meta(payload)
            return
        elif path == "/api/batch":
            self._handle_api_batch(payload)
            return
        elif path == "/api/audit":
            self._handle_api_audit(payload)
            return
        elif path == "/api/schema-ld":
            self._handle_api_schema_ld(payload)
            return
        elif path == "/api/qr":
            self._handle_api_qr(payload)
            return

        self._send_error_json(f"POST endpoint not found: {path}", status=HTTPStatus.NOT_FOUND)

    def _serve_studio_index(self) -> None:
        """Serve public/index.html or embedded fallback HTML."""
        public_dir = self.studio_server.public_dir
        index_file = public_dir / "index.html"

        html_content = safe_read_text(index_file)
        if html_content is not None:
            self._send_html(html_content)
            return

        # Fallback embedded HTML
        fallback_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>OG Canvas Forge Studio (Embedded)</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; padding: 40px; background: #f8f9fa; color: #202124; }
    .card { background: white; border-radius: 16px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }
    h1 { color: #1a73e8; margin-top: 0; }
  </style>
</head>
<body>
  <div class="card">
    <h1>OG Canvas Forge Studio</h1>
    <p>The Studio UI server is running successfully in pure Python stdlib mode!</p>
    <p>Please ensure <code>public/index.html</code> is present for the complete Material 3 visual studio.</p>
    <p>API status: <a href="/api/stats">/api/stats</a> | Templates: <a href="/api/templates">/api/templates</a></p>
  </div>
</body>
</html>"""
        self._send_html(fallback_html)

    def _handle_api_templates(self) -> None:
        """Return available templates catalog."""
        try:
            from .catalog import get_all_templates, TEMPLATE_REGISTRY  # type: ignore
            if callable(get_all_templates):
                templates = [
                    {
                        "id": t.id if hasattr(t, "id") else str(k),
                        "name": t.name if hasattr(t, "name") else str(t),
                        "category": getattr(t, "category", "General"),
                        "description": getattr(t, "description", ""),
                    }
                    for k, t in (TEMPLATE_REGISTRY.items() if isinstance(TEMPLATE_REGISTRY, dict) else enumerate(get_all_templates()))
                ]
                self._send_json({"templates": templates, "count": len(templates)})
                return
        except Exception:
            pass

        self._send_json({"templates": _DEFAULT_TEMPLATES, "count": len(_DEFAULT_TEMPLATES)})

    def _handle_api_themes(self) -> None:
        """Return available color themes."""
        try:
            from .catalog import get_all_themes, THEMES  # type: ignore
            if callable(get_all_themes):
                themes = [t.to_dict() if hasattr(t, "to_dict") else t for t in get_all_themes()]
                self._send_json({"themes": themes, "count": len(themes)})
                return
            elif isinstance(THEMES, list):
                themes = [t.to_dict() if hasattr(t, "to_dict") else t for t in THEMES]
                self._send_json({"themes": themes, "count": len(themes)})
                return
        except Exception:
            pass

        self._send_json({"themes": _DEFAULT_THEMES, "count": len(_DEFAULT_THEMES)})

    def _handle_api_stats(self) -> None:
        """Return runtime statistics."""
        uptime = time.time() - self.studio_server.start_time
        stats = {
            "status": "healthy",
            "server": "OG Canvas Forge Studio",
            "version": "0.1.0",
            "uptime_seconds": round(uptime, 2),
            "cards_generated": self.studio_server.cards_generated,
            "templates_count": len(_DEFAULT_TEMPLATES),
            "themes_count": len(_DEFAULT_THEMES),
        }
        self._send_json(stats)

    def _handle_api_diagnostics(self) -> None:
        """Return platform and environment diagnostics."""
        plat = get_platform_info()
        diag = {
            "version": "0.1.0",
            "platform": {
                "os": plat.os_name,
                "system": plat.system,
                "release": plat.release,
                "is_windows": plat.is_windows,
                "is_linux": plat.is_linux,
                "is_macos": plat.is_macos,
                "is_termux": plat.is_termux,
                "is_wsl": plat.is_wsl,
                "python_version": plat.python_version,
            },
            "public_dir": str(self.studio_server.public_dir),
            "public_dir_exists": self.studio_server.public_dir.is_dir(),
            "uptime_seconds": round(time.time() - self.studio_server.start_time, 2),
            "cards_generated": self.studio_server.cards_generated,
        }
        self._send_json(diag)

    def _handle_api_generate(self, payload: Dict[str, Any]) -> None:
        """Generate OpenGraph card SVG from configuration."""
        title = payload.get("title", "OpenGraph Card")
        subtitle = payload.get("subtitle")
        author = payload.get("author")
        category = payload.get("category")
        tags = payload.get("tags", [])
        site_name = payload.get("site_name", "og-canvas-forge")
        theme = payload.get("theme", "aurora")
        layout = payload.get("layout", "modern_minimal")
        pattern = payload.get("pattern", "dot_grid")
        dims = payload.get("dimensions", {"width": 1200, "height": 630})
        watermark = payload.get("watermark")
        qr_code = payload.get("qr_code") or payload.get("qr")

        dim_obj = CardDimension.from_value(dims)
        config = OGCardConfig(
            title=title,
            subtitle=subtitle,
            author=author,
            category=category,
            tags=tags if isinstance(tags, list) else [],
            site_name=site_name,
            theme=theme,
            layout=layout,
            dimensions=dim_obj,
            pattern=pattern,
            watermark=watermark,
            qr_code=qr_code,
        )

        svg_content = None
        html_meta = ""

        # Try using core card generator module
        try:
            from .card_generator import generate_card  # type: ignore
            card = generate_card(config)
            svg_content = card.svg
            html_meta = card.html_meta
        except Exception:
            try:
                from .generator import generate_card  # type: ignore
                card = generate_card(config)
                svg_content = card.svg
                html_meta = getattr(card, "html_meta", "")
            except Exception:
                # Fallback to local synthesizer
                svg_content = _generate_fallback_svg(config)
                html_meta = _generate_html_meta_tags(
                    title=config.title,
                    description=config.subtitle or "",
                    site_name=config.site_name or "example.com",
                    width=dim_obj.width,
                    height=dim_obj.height,
                )

        self.studio_server.cards_generated += 1

        # Check Accept header for raw SVG response
        accept_header = self.headers.get("Accept", "")
        if "image/svg+xml" in accept_header and "application/json" not in accept_header:
            self._send_svg(svg_content)
            return

        res = {
            "svg": svg_content,
            "html_meta": html_meta,
            "width": dim_obj.width,
            "height": dim_obj.height,
            "title": config.title,
            "format": "svg",
        }
        self._send_json(res)

    def _handle_api_meta(self, payload: Dict[str, Any]) -> None:
        """Generate HTML OpenGraph meta tags."""
        title = payload.get("title", "Social Card Title")
        desc = payload.get("description", "")
        img_url = payload.get("image_url", "https://example.com/og-image.svg")
        site_name = payload.get("site_name", "example.com")
        twitter_handle = payload.get("twitter_handle", "@antigravity")
        card_type = payload.get("card_type", "summary_large_image")
        w = int(payload.get("width", 1200))
        h = int(payload.get("height", 630))

        html_tags = _generate_html_meta_tags(
            title=title,
            description=desc,
            image_url=img_url,
            site_name=site_name,
            twitter_handle=twitter_handle,
            card_type=card_type,
            width=w,
            height=h,
        )
        self._send_json({"html": html_tags, "title": title})

    def _handle_api_batch(self, payload: Union[Dict[str, Any], List[Any]]) -> None:
        """Batch generate multiple cards."""
        items: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and "cards" in payload:
            items = payload["cards"]
        else:
            items = [payload]

        results = []
        for idx, item in enumerate(items):
            title = item.get("title", f"Card #{idx + 1}")
            dims = CardDimension.from_value(item.get("dimensions", (1200, 630)))
            config = OGCardConfig(
                title=title,
                subtitle=item.get("subtitle"),
                author=item.get("author"),
                category=item.get("category"),
                tags=item.get("tags", []),
                site_name=item.get("site_name"),
                theme=item.get("theme", "aurora"),
                layout=item.get("layout", "modern_minimal"),
                dimensions=dims,
                pattern=item.get("pattern", "dot_grid"),
            )
            try:
                from .card_generator import generate_card  # type: ignore
                card = generate_card(config)
                svg_out = card.svg
            except Exception:
                svg_out = _generate_fallback_svg(config)

            self.studio_server.cards_generated += 1
            results.append({
                "index": idx,
                "title": title,
                "filename": f"og-card-{idx + 1}.svg",
                "width": dims.width,
                "height": dims.height,
                "svg": svg_out,
            })

        self._send_json({"count": len(results), "cards": results})

    def _handle_api_audit(self, payload: Dict[str, Any]) -> None:
        """Audit card accessibility against WCAG 2.2 criteria."""
        template_id = payload.get("template")
        theme_id = payload.get("theme", "aurora")
        title = payload.get("title", "Sample Card Headline")
        subtitle = payload.get("subtitle", "Sample Card Subtitle")
        try:
            from .card_generator import validate_card_accessibility
            if template_id:
                report = validate_card_accessibility(template_id)
            else:
                cfg = OGCardConfig(title=title, subtitle=subtitle, theme=theme_id)
                report = validate_card_accessibility(cfg)
            self._send_json(report.to_dict())
        except Exception as err:
            self._send_error_json(f"Accessibility audit failed: {err}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_api_schema_ld(self, payload: Dict[str, Any]) -> None:
        """Generate complete Schema.org JSON-LD snippet."""
        title = payload.get("title", "Sample Card Headline")
        subtitle = payload.get("subtitle")
        page_url = payload.get("page_url")
        image_url = payload.get("image_url")
        schema_type = payload.get("schema_type")
        publisher = payload.get("publisher")
        try:
            from .card_generator import generate_schema_json_ld
            cfg = OGCardConfig(title=title, subtitle=subtitle, site_name=publisher)
            json_str = generate_schema_json_ld(
                cfg,
                page_url=page_url,
                image_url=image_url,
                schema_type=schema_type,
                publisher_name=publisher,
                as_script_tag=False,
            )
            self._send_json({"schema_ld": json.loads(json_str), "raw_script": f'<script type="application/ld+json">\n{json_str}\n</script>'})
        except Exception as err:
            self._send_error_json(f"Schema.org generation failed: {err}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_api_qr(self, payload: Dict[str, Any]) -> None:
        """Synthesize QR Code SVG from payload."""
        text = str(payload.get("text", "")).strip()
        if not text:
            self._send_error_json("Missing required parameter 'text'")
            return
        size = int(payload.get("size", 120))
        fg = str(payload.get("fg", "#ffffff"))
        bg = str(payload.get("bg", "rgba(15, 23, 42, 0.75)"))
        label = payload.get("label")
        from .qr_matrix import render_qr_svg
        qr_svg = render_qr_svg(text, size=size, fg=fg, bg=bg, label=label)
        self._send_json({"text": text, "svg": qr_svg, "size": size})

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy request logs in test/silent mode unless DEBUG is set."""
        if os.environ.get("OG_SERVER_DEBUG"):
            super().log_message(format, *args)


class StudioServer(ThreadingHTTPServer):
    """Multi-threaded HTTP Server for Google OG Canvas Studio."""

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler] = StudioHTTPRequestHandler,
        public_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.start_time = time.time()
        self.cards_generated = 0
        if public_dir is not None:
            self.public_dir = normalize_path(public_dir)
        else:
            self.public_dir = _get_default_public_dir()


def create_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    public_dir: Optional[Union[str, Path]] = None,
) -> StudioServer:
    """Instantiate and configure StudioServer instance."""
    return StudioServer((host, port), StudioHTTPRequestHandler, public_dir=public_dir)


def start_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = False,
    public_dir: Optional[Union[str, Path]] = None,
) -> None:
    """Start and run the OG Canvas Forge Studio server."""
    server = create_server(host, port, public_dir=public_dir)
    url = f"http://{host}:{port}"

    print(f"🎨 OG Canvas Forge Studio Server running at: {url}")
    print(f"📁 Serving static assets from: {server.public_dir}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping OG Canvas Forge Studio Server...")
    finally:
        server.server_close()


def main() -> None:
    """CLI entry point for running the Studio UI server."""
    parser = argparse.ArgumentParser(
        prog="og-canvas-forge-server",
        description="OG Canvas Forge Studio Local UI & REST API Server",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--open", action="store_true", help="Automatically open browser on start")
    parser.add_argument("--public-dir", default=None, help="Custom path to public static assets folder")

    args = parser.parse_args()
    start_server(host=args.host, port=args.port, open_browser=args.open, public_dir=args.public_dir)


if __name__ == "__main__":
    main()
