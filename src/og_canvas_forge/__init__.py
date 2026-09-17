"""og-canvas-forge: High-performance pure-Python Open Graph social card generator, Studio UI & MCP server.

Zero external runtime dependencies. Standards-compliant SVG synthesis, HTML meta generator,
interactive Studio web interface, and Model Context Protocol (MCP) server.
"""

from __future__ import annotations

__version__ = "0.1.0"
__title__ = "og-canvas-forge"
__author__ = "OG Canvas Forge Team"
__license__ = "MIT"

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

# Dynamic import with fallback to guarantee seamless interoperability
try:
    from .card_generator import export_svg, generate_card
except ImportError:
    try:
        from .generator import export_svg, generate_card
    except ImportError:
        from .mcp_server import export_svg, generate_card

try:
    from .catalog import get_template, list_templates
except ImportError:
    try:
        from .templates import get_template, list_templates
    except ImportError:
        from .mcp_server import get_template, list_templates

try:
    from .gradients import get_theme, list_themes
except ImportError:
    try:
        from .themes import get_theme, list_themes
    except ImportError:
        from .mcp_server import get_theme, list_themes

from .mcp_server import handle_jsonrpc_request, process_request, run_stdio_server

__all__ = [
    "__version__",
    "generate_card",
    "export_svg",
    "get_template",
    "list_templates",
    "get_theme",
    "list_themes",
    "OGCardConfig",
    "GeneratedCard",
    "CardTheme",
    "CardLayout",
    "CardDimension",
    "AuthorSpec",
    "BadgeSpec",
    "TemplatePreset",
    "handle_jsonrpc_request",
    "process_request",
    "run_stdio_server",
]
