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
    CardAccessibilityReport,
    CardDimension,
    CardLayout,
    CardTheme,
    GeneratedCard,
    OGCardConfig,
    TemplatePreset,
)

# Dynamic import with fallback to guarantee seamless interoperability
try:
    from .card_generator import (
        calculate_contrast_ratio,
        calculate_relative_luminance,
        export_png,
        export_svg,
        generate_card,
        generate_card_image,
        generate_html_meta,
        generate_schema_json_ld,
        validate_card_accessibility,
    )
except ImportError:
    try:
        from .generator import export_svg, generate_card
        export_png = None
        generate_card_image = None
        generate_html_meta = None
        generate_schema_json_ld = None
        validate_card_accessibility = None
        calculate_contrast_ratio = None
        calculate_relative_luminance = None
    except ImportError:
        from .mcp_server import export_svg, generate_card
        export_png = None
        generate_card_image = None
        generate_html_meta = None
        generate_schema_json_ld = None
        validate_card_accessibility = None
        calculate_contrast_ratio = None
        calculate_relative_luminance = None

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
from .qr_matrix import generate_qr_matrix, render_barcode_svg, render_qr_svg
from .watermark import WatermarkSpec, render_watermark_svg

__all__ = [
    "__version__",
    "generate_card",
    "export_svg",
    "export_png",
    "generate_card_image",
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
    "CardAccessibilityReport",
    "validate_card_accessibility",
    "generate_schema_json_ld",
    "generate_html_meta",
    "calculate_contrast_ratio",
    "calculate_relative_luminance",
    "generate_qr_matrix",
    "render_qr_svg",
    "render_barcode_svg",
    "WatermarkSpec",
    "render_watermark_svg",
    "handle_jsonrpc_request",
    "process_request",
    "run_stdio_server",
]
