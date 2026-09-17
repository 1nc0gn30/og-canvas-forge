"""Multi-OS Command Line Interface for og-canvas-forge.

Provides subcommands for card generation, batch processing, template listing,
theme exploration, HTML meta generation, Material 3 Studio Web UI hosting,
MCP stdio protocol execution, platform diagnostics, and self-verification test runner.
Zero external runtime dependencies.
"""

from __future__ import annotations

import argparse
import csv
import html
import http.server
import json
import os
import platform
import re
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .compat import (
    atomic_write_bytes,
    atomic_write_text,
    get_platform_info,
    normalize_path,
    safe_read_json,
    safe_read_text,
)
from .mcp_server import (
    PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    TEMPLATES_CATALOG,
    THEMES_CATALOG,
    export_svg,
    generate_card,
    get_template,
    get_theme,
    handle_jsonrpc_request,
    list_templates,
    list_themes,
    render_html_meta,
    run_diagnostics,
    run_stdio_server,
)
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

# ============================================================================
# TERMINAL FORMATTING & COLOR UTILITIES
# ============================================================================


class Term:
    """Terminal styling and ANSI color manager respecting NO_COLOR and TTY state."""

    _color_enabled: bool = True

    @classmethod
    def init(cls, no_color_flag: bool = False) -> None:
        """Initialize color state from flag, env, and terminal capabilities."""
        if (
            no_color_flag
            or "NO_COLOR" in os.environ
            or os.environ.get("TERM") == "dumb"
            or not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty())
        ):
            cls._color_enabled = False
        else:
            cls._color_enabled = True

    @classmethod
    def _c(cls, code: str, text: str) -> str:
        if not cls._color_enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    @classmethod
    def bold(cls, text: str) -> str:
        return cls._c("1", text)

    @classmethod
    def dim(cls, text: str) -> str:
        return cls._c("2", text)

    @classmethod
    def cyan(cls, text: str) -> str:
        return cls._c("36", text)

    @classmethod
    def green(cls, text: str) -> str:
        return cls._c("32", text)

    @classmethod
    def yellow(cls, text: str) -> str:
        return cls._c("33", text)

    @classmethod
    def magenta(cls, text: str) -> str:
        return cls._c("35", text)

    @classmethod
    def blue(cls, text: str) -> str:
        return cls._c("34", text)

    @classmethod
    def red(cls, text: str) -> str:
        return cls._c("31", text)

    @classmethod
    def white(cls, text: str) -> str:
        return cls._c("37", text)


def print_banner() -> None:
    """Display CLI startup banner."""
    banner = f"""
{Term.cyan(Term.bold("  ██████╗  ██████╗ "))}    {Term.bold("CANVAS FORGE")} {Term.dim(f"v{SERVER_VERSION}")}
{Term.cyan(Term.bold(" ██╔═══██╗██╔════╝ "))}    {Term.dim("Pure Python Zero-Dependency Social Card Engine & MCP Server")}
{Term.cyan(Term.bold(" ██║   ██║██║  ███╗"))}    {Term.dim("───────────────────────────────────────────────────────────")}
{Term.cyan(Term.bold(" ██║   ██║██║   ██║"))}    {Term.green("●")} {Term.white("Ready")}  {Term.dim("•")}  {Term.yellow(f"{len(THEMES_CATALOG)} Themes")}  {Term.dim("•")}  {Term.magenta(f"{len(TEMPLATES_CATALOG)} Templates")}
{Term.cyan(Term.bold(" ╚██████╔╝╚██████╔╝"))}
{Term.cyan(Term.bold("  ╚═════╝  ╚═════╝ "))}
"""
    sys.stderr.write(banner + "\n")


def print_table(headers: List[str], rows: List[List[str]]) -> None:
    """Print a clean tabular grid to standard output."""
    if not rows:
        print(Term.dim("  (No items found)"))
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(str(cell)))

    # Header Row
    header_line = "  " + "  ".join(
        Term.bold(headers[i].ljust(col_widths[i])) for i in range(len(headers))
    )
    separator = "  " + "  ".join("─" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(Term.dim(separator))

    # Data Rows
    for row in rows:
        row_line = "  " + "  ".join(
            str(row[i] if i < len(row) else "").ljust(col_widths[i])
            for i in range(len(headers))
        )
        print(row_line)
    print()


# ============================================================================
# SUBCOMMAND HANDLERS
# ============================================================================


def handle_generate(args: argparse.Namespace) -> int:
    """Handle `generate` subcommand: synthesize single card."""
    title = args.title
    if not title:
        sys.stderr.write(Term.red("Error: Title is required for card generation.\n"))
        return 1

    tags_list: List[str] = []
    if args.tags:
        tags_list = [t.strip() for t in args.tags.split(",") if t.strip()]

    # Resolve layout
    layout_val = CardLayout.from_str(args.layout) if args.layout else CardLayout.DEFAULT

    # Resolve dimensions
    width = int(args.width) if args.width else 1200
    height = int(args.height) if args.height else 630
    dim = CardDimension(width, height, f"{width}x{height}")

    config = OGCardConfig(
        title=title,
        subtitle=args.subtitle,
        author=AuthorSpec(name=args.author) if args.author else None,
        category=args.category,
        tags=tags_list,
        theme=args.theme or "aurora",
        layout=layout_val,
        dimensions=dim,
        site_name=args.brand,
        reading_time_min=args.reading_time,
        date_str=args.date,
        code_snippet=args.code,
        code_language=args.code_lang,
        episode_number=args.episode,
        ticket_number=args.ticket,
        badge=BadgeSpec(text=args.badge) if args.badge else None,
        watermark=getattr(args, "watermark", None),
        qr_code=getattr(args, "qr_code", None),
    )

    card = generate_card(config, template=args.template)

    # Determine format
    fmt = args.format.lower() if args.format else "svg"
    output_path = args.output

    if output_path and not args.format:
        ext = Path(output_path).suffix.lower()
        if ext == ".html":
            fmt = "html"
        elif ext == ".json":
            fmt = "json"
        elif ext == ".bmp":
            fmt = "bmp"
        else:
            fmt = "svg"

    # Generate output payload
    if fmt == "html":
        content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(card.title)}</title>
  {card.html_meta}
  <style>
    body {{ margin: 0; background: #0b0f19; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: system-ui, -apple-system, sans-serif; }}
    .preview-wrap {{ max-width: 92vw; max-height: 92vh; box-shadow: 0 30px 60px -12px rgba(0,0,0,0.8); border-radius: 16px; overflow: hidden; }}
    svg {{ display: block; width: 100%; height: auto; }}
  </style>
</head>
<body>
  <div class="preview-wrap">
    {card.svg}
  </div>
</body>
</html>"""
    elif fmt == "json":
        data = {
            "title": card.title,
            "width": card.width,
            "height": card.height,
            "theme": card.config.theme if isinstance(card.config.theme, str) else card.config.theme.id,
            "layout": card.config.layout.value if isinstance(card.config.layout, CardLayout) else str(card.config.layout),
            "svg": card.svg,
            "html_meta": card.html_meta,
        }
        content = json.dumps(data, indent=2)
    elif fmt == "bmp":
        content = None
        bmp_bytes = card.to_bmp()
    else:
        content = card.svg

    # Write output
    if output_path and output_path != "-":
        target = normalize_path(output_path)
        if fmt == "bmp":
            atomic_write_bytes(target, bmp_bytes)
        else:
            atomic_write_text(target, content or "")

        if not args.quiet:
            file_size = target.stat().st_size
            print(f"{Term.green('✔ Successfully generated:')} {Term.bold(str(target))} {Term.dim(f'({file_size:,} bytes, {card.width}x{card.height})')}")

        if getattr(args, "preview", False):
            webbrowser.open(target.as_uri())
    else:
        if fmt == "bmp":
            sys.stdout.buffer.write(bmp_bytes)
        else:
            sys.stdout.write(content or "")
            if not content.endswith("\n"):
                sys.stdout.write("\n")

    if getattr(args, "audit", False):
        report = card.audit_accessibility()
        status_str = Term.green("PASS") if report.is_compliant else Term.red("FAIL")
        sys.stderr.write(f"\n{Term.bold(Term.cyan('WCAG 2.2 Accessibility Report:'))} [{status_str}] (Score: {report.score}/100)\n")
        for el, ratio in report.contrast_ratios.items():
            comp = report.wcag_compliance.get(el, {})
            aa = Term.green("AA Pass") if comp.get("aa_pass") else Term.red("AA Fail")
            sys.stderr.write(f"  • {el.capitalize():<10}: {ratio:.2f}:1 [{aa}]\n")
        sys.stderr.write("\n")

    return 0


def handle_qr(args: argparse.Namespace) -> int:
    """Handle `qr` subcommand: synthesize standalone scannable QR Code SVG."""
    from .qr_matrix import render_qr_svg
    text = args.text
    size = getattr(args, "size", 120)
    fg = getattr(args, "fg", "#ffffff")
    label = getattr(args, "label", None)
    svg = render_qr_svg(text, size=size, fg=fg, label=label)
    if getattr(args, "output", None) and args.output != "-":
        atomic_write_text(args.output, svg, encoding="utf-8")
        if not getattr(args, "quiet", False):
            sys.stdout.write(Term.green(f"✔ QR Code SVG saved to: {args.output}\n"))
    else:
        sys.stdout.write(svg)
    return 0


def handle_batch(args: argparse.Namespace) -> int:
    """Handle `batch` subcommand: generate cards in bulk from JSON or CSV."""
    batch_file = args.file
    if not batch_file:
        sys.stderr.write(Term.red("Error: Batch input file path is required.\n"))
        return 1

    path = normalize_path(batch_file)
    if not path.exists() or not path.is_file():
        sys.stderr.write(Term.red(f"Error: Batch file '{batch_file}' not found.\n"))
        return 1

    # Load items from JSON or CSV
    items: List[Dict[str, Any]] = []
    if path.suffix.lower() == ".json":
        data = safe_read_json(path)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "cards" in data:
            items = data["cards"]
    else:
        # CSV reading
        raw_text = safe_read_text(path) or ""
        reader = csv.DictReader(raw_text.splitlines())
        for row in reader:
            items.append(dict(row))

    if not items:
        sys.stderr.write(Term.red(f"Error: No card records found in '{batch_file}'.\n"))
        return 1

    out_dir = normalize_path(args.output_dir or "./og-cards")
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    def_theme = args.theme or "aurora"
    def_layout = args.layout or "default"
    def_template = args.template
    fmt = (args.format or "svg").lower()
    prefix = args.prefix or ""

    if not args.quiet:
        print(f"{Term.cyan('● Processing Batch:')} {Term.bold(str(len(items)))} cards from {Term.dim(str(path))}")
        print(f"  Output Directory: {Term.bold(str(out_dir))}")
        print()

    generated_count = 0
    start_time = time.time()

    for idx, item in enumerate(items, 1):
        title = item.get("title")
        if not title:
            continue

        raw_tags = item.get("tags")
        tags_list: List[str] = []
        if isinstance(raw_tags, list):
            tags_list = [str(t) for t in raw_tags]
        elif isinstance(raw_tags, str):
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]

        cfg = OGCardConfig(
            title=title,
            subtitle=item.get("subtitle"),
            author=AuthorSpec(name=item["author"]) if item.get("author") else None,
            category=item.get("category"),
            tags=tags_list,
            theme=item.get("theme") or def_theme,
            layout=CardLayout.from_str(item.get("layout") or def_layout),
            site_name=item.get("site_name"),
            date_str=item.get("date_str") or item.get("date"),
            badge=BadgeSpec(text=item["badge"]) if item.get("badge") else None,
        )

        template_to_use = item.get("template") or def_template
        card = generate_card(cfg, template=template_to_use)

        # File slug
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower())[:40].strip("_")
        out_filename = f"{prefix}{idx:02d}_{safe_slug}.{fmt}"
        target_file = out_dir / out_filename

        if not args.dry_run:
            if fmt == "html":
                html_out = f"<!DOCTYPE html><html><head>{card.html_meta}</head><body style='margin:0;background:#0b0f19;display:flex;align-items:center;justify-content:center;height:100vh'>{card.svg}</body></html>"
                atomic_write_text(target_file, html_out)
            elif fmt == "bmp":
                atomic_write_bytes(target_file, card.to_bmp())
            elif fmt == "json":
                atomic_write_text(target_file, json.dumps({"title": card.title, "svg": card.svg, "html_meta": card.html_meta}, indent=2))
            else:
                atomic_write_text(target_file, card.svg)

        generated_count += 1
        if not args.quiet:
            print(f"  {Term.green('✔')} [{idx}/{len(items)}] {Term.bold(title[:45])} -> {Term.dim(out_filename)}")

    elapsed = time.time() - start_time
    if not args.quiet:
        print()
        print(f"{Term.green('✔ Batch Complete:')} {generated_count} cards processed in {elapsed:.2f}s ({generated_count / max(0.001, elapsed):.1f} cards/sec)")

    return 0


def handle_templates(args: argparse.Namespace) -> int:
    """Handle `templates` subcommand: list built-in templates."""
    templates = list_templates(getattr(args, "category", None))

    if getattr(args, "json", False):
        data = [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "default_layout": t.config.layout.value if isinstance(t.config.layout, CardLayout) else str(t.config.layout),
                "default_theme": t.config.theme if isinstance(t.config.theme, str) else t.config.theme.id,
                "sample_data": t.sample_data,
            }
            for t in templates
        ]
        print(json.dumps(data, indent=2))
        return 0

    if not getattr(args, "quiet", False):
        print(f"\n{Term.bold('Built-in OG Card Templates')} {Term.dim(f'({len(templates)} available)')}\n")

    headers = ["ID", "Category", "Name", "Layout", "Theme", "Description"]
    rows = []
    for t in templates:
        layout_str = t.config.layout.value if isinstance(t.config.layout, CardLayout) else str(t.config.layout)
        theme_str = t.config.theme if isinstance(t.config.theme, str) else t.config.theme.id
        rows.append([
            Term.cyan(t.id),
            Term.yellow(t.category),
            Term.bold(t.name),
            layout_str,
            theme_str,
            t.description[:60] + "..." if len(t.description) > 60 else t.description,
        ])

    print_table(headers, rows)
    return 0


def handle_themes(args: argparse.Namespace) -> int:
    """Handle `themes` subcommand: list color themes and palettes."""
    themes = list_themes(getattr(args, "category", None))

    if getattr(args, "json", False):
        data = [t.to_dict() for t in themes]
        print(json.dumps(data, indent=2))
        return 0

    if not getattr(args, "quiet", False):
        print(f"\n{Term.bold('Built-in Color Themes & Palettes')} {Term.dim(f'({len(themes)} available)')}\n")

    headers = ["ID", "Name", "Mode", "Background Gradient", "Accent", "Text Color"]
    rows = []
    for t in themes:
        mode_str = Term.dim("Dark") if t.is_dark else Term.yellow("Light")
        bg_desc = f"{t.bg_start} -> {t.bg_end}"
        rows.append([
            Term.cyan(t.id),
            Term.bold(t.name),
            mode_str,
            bg_desc,
            Term.green(t.accent),
            t.text_primary,
        ])

    print_table(headers, rows)
    return 0


def handle_meta(args: argparse.Namespace) -> int:
    """Handle `meta` subcommand: generate HTML meta tags."""
    title = args.title
    image_url = args.image
    if not title or not image_url:
        sys.stderr.write(Term.red("Error: Both --title and --image are required for meta generation.\n"))
        return 1

    tags_list: Optional[List[str]] = None
    if getattr(args, "tags", None):
        tags_list = [t.strip() for t in args.tags.split(",") if t.strip()]

    meta_html = render_html_meta(
        title=title,
        image_url=image_url,
        description=args.description,
        url=args.url,
        site_name=args.site_name,
        twitter_handle=args.twitter,
        twitter_card=args.twitter_card or "summary_large_image",
        card_type=args.type or "article",
        author=args.author,
        tags=tags_list,
    )

    if args.output and args.output != "-":
        target = normalize_path(args.output)
        atomic_write_text(target, meta_html)
        if not getattr(args, "quiet", False):
            print(f"{Term.green('✔ Saved HTML meta tags to:')} {Term.bold(str(target))}")
    else:
        print(meta_html)

    return 0


def handle_audit(args: argparse.Namespace) -> int:
    """Handle `audit` subcommand: audit card accessibility and contrast against WCAG 2.2."""
    target = getattr(args, "target", None)
    theme = getattr(args, "theme", None)
    template = getattr(args, "template", None) or (target if target in TEMPLATES_CATALOG else None)

    from .card_generator import validate_card_accessibility
    if template:
        report = validate_card_accessibility(template)
    else:
        title = getattr(args, "title", None) or target or "Card Headline"
        subtitle = getattr(args, "subtitle", None) or "Card Subtitle"
        cfg = OGCardConfig(title=title, subtitle=subtitle, theme=theme or "aurora")
        report = validate_card_accessibility(cfg)

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(Term.bold(Term.cyan("\n--- WCAG 2.2 Social Card Accessibility Report ---")))
    status_str = Term.green("PASS") if report.is_compliant else Term.red("FAIL")
    print(f"Compliance Status : {status_str} (Score: {report.score}/100)")
    print(Term.bold("\nContrast Ratios:"))
    for el, ratio in report.contrast_ratios.items():
        comp = report.wcag_compliance.get(el, {})
        aa = Term.green("AA Pass") if comp.get("aa_pass") else Term.red("AA Fail")
        aaa = Term.green("AAA Pass") if comp.get("aaa_pass") else Term.yellow("AAA Fail")
        print(f"  • {el.capitalize():<10}: {ratio:.2f}:1 [{aa} | {aaa}]")

    print(Term.bold("\nPlatform Readability:"))
    for plat, rating in report.platform_readability.items():
        clr = Term.green if rating == "Excellent" else (Term.cyan if rating == "Good" else Term.yellow)
        print(f"  • {plat.capitalize():<10}: {clr(rating)}")

    print(Term.bold("\nRecommendations:"))
    for rec in report.recommendations:
        print(f"  - {rec}")
    print()
    return 0


def handle_schema(args: argparse.Namespace) -> int:
    """Handle `schema` subcommand: generate complete Schema.org JSON-LD snippet."""
    from .card_generator import generate_schema_json_ld
    cfg = OGCardConfig(
        title=args.title,
        subtitle=getattr(args, "subtitle", None),
        author=AuthorSpec(name=args.author) if getattr(args, "author", None) else None,
        site_name=getattr(args, "publisher", None),
    )
    snippet = generate_schema_json_ld(
        cfg,
        page_url=getattr(args, "url", None),
        image_url=getattr(args, "image", None),
        schema_type=getattr(args, "schema_type", None),
        publisher_name=getattr(args, "publisher", None),
        as_script_tag=True,
    )
    if args.output and args.output != "-":
        target = normalize_path(args.output)
        atomic_write_text(target, snippet)
        if not getattr(args, "quiet", False):
            print(f"{Term.green('✔ Saved Schema.org JSON-LD to:')} {Term.bold(str(target))}")
    else:
        print(snippet)
    return 0


def handle_diagnostics(args: argparse.Namespace) -> int:
    """Handle `platform` / `doctor` / `diagnostics` subcommand."""
    detailed = getattr(args, "detailed", False)
    diag = run_diagnostics(detailed=detailed)

    if getattr(args, "json", False):
        print(json.dumps(diag, indent=2))
        return 0

    p = diag["platform"]
    c = diag["catalogs"]
    t = diag["terminal"]

    print(f"\n{Term.bold('og-canvas-forge Diagnostics & Platform Check')}")
    print(Term.dim("═" * 58))
    print(f"  Service Version:     {Term.cyan(f'{SERVER_NAME} v{SERVER_VERSION}')}")
    print(f"  Protocol Version:    {Term.cyan(PROTOCOL_VERSION)}")
    print(f"  Overall Status:      {Term.green('● OPERATIONAL')}")
    print()
    print(f"  Operating System:    {Term.bold(p['system'])} {p['release']} ({p['os_name']})")
    print(f"  Python Runtime:      {Term.bold(p['python_version'])} ({platform.python_implementation()})")
    print(f"  Environment Flags:   Linux={p['is_linux']}, macOS={p['is_macos']}, Windows={p['is_windows']}, WSL={p['is_wsl']}, Termux={p['is_termux']}")
    print()
    print(f"  Registered Themes:   {Term.bold(str(c['themes_count']))} themes")
    print(f"  Registered Templates:{Term.bold(str(c['templates_count']))} templates")
    print(f"  MCP Tools:           {Term.bold(str(c['tools_count']))} tools")
    print(f"  MCP Resources:       {Term.bold(str(c['resources_count']))} resources")
    print(f"  MCP Prompts:         {Term.bold(str(c['prompts_count']))} prompts")
    print()
    print(f"  Terminal TTY:        {t['isatty']}")
    print(f"  Stdout Encoding:     {t['stdout_encoding']}")
    print(f"  NO_COLOR Active:     {t['no_color_env']}")
    print(Term.dim("═" * 58))
    print()
    return 0


def handle_mcp(args: argparse.Namespace) -> int:
    """Handle `mcp` subcommand: launch stdio server."""
    run_stdio_server()
    return 0


# ============================================================================
# MATERIAL 3 STUDIO WEB UI HTTP SERVER
# ============================================================================

STUDIO_HTML_PAGE = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OG Canvas Forge Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;700&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --md-sys-color-primary: #a8c7fa;
      --md-sys-color-on-primary: #062e6f;
      --md-sys-color-primary-container: #0842a0;
      --md-sys-color-on-primary-container: #d3e3fd;
      --md-sys-color-surface: #111318;
      --md-sys-color-on-surface: #e2e2e9;
      --md-sys-color-surface-variant: #1a1c22;
      --md-sys-color-on-surface-variant: #c4c6cf;
      --md-sys-color-outline: #44474f;
      --md-sys-color-outline-variant: #282a30;
      --md-sys-color-background: #0b0d12;
      --md-sys-color-secondary: #7cacf8;
      --md-sys-color-tertiary: #6dd58c;
      --md-sys-shape-corner-small: 8px;
      --md-sys-shape-corner-medium: 16px;
      --md-sys-shape-corner-large: 24px;
      --md-sys-shape-corner-full: 9999px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--md-sys-color-background);
      color: var(--md-sys-color-on-surface);
      font-family: 'Google Sans', 'Roboto', system-ui, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Top App Bar */
    header {
      background-color: var(--md-sys-color-surface);
      border-bottom: 1px solid var(--md-sys-color-outline-variant);
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 20px;
      letter-spacing: -0.2px;
    }
    .brand-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #1a73e8, #a8c7fa);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #062e6f;
      font-weight: 900;
      font-size: 18px;
    }
    .badge-chip {
      background-color: rgba(168, 199, 250, 0.15);
      color: var(--md-sys-color-primary);
      padding: 4px 10px;
      border-radius: var(--md-sys-shape-corner-full);
      font-size: 12px;
      font-weight: 500;
    }

    /* Main Workspace Layout */
    .workspace {
      display: grid;
      grid-template-columns: 420px 1fr;
      flex: 1;
      height: calc(100vh - 65px);
    }
    @media (max-width: 980px) {
      .workspace { grid-template-columns: 1fr; height: auto; }
    }

    /* Left Controls Sidebar */
    .sidebar {
      background-color: var(--md-sys-color-surface);
      border-right: 1px solid var(--md-sys-color-outline-variant);
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    label {
      font-size: 13px;
      font-weight: 500;
      color: var(--md-sys-color-on-surface-variant);
    }
    input, select, textarea {
      background-color: var(--md-sys-color-surface-variant);
      border: 1px solid var(--md-sys-color-outline);
      color: var(--md-sys-color-on-surface);
      padding: 12px 14px;
      border-radius: var(--md-sys-shape-corner-small);
      font-size: 14px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    input:focus, select:focus, textarea:focus {
      border-color: var(--md-sys-color-primary);
      box-shadow: 0 0 0 2px rgba(168, 199, 250, 0.2);
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    /* Theme Pill Selector */
    .theme-selector {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }
    .theme-btn {
      background-color: var(--md-sys-color-surface-variant);
      border: 1px solid var(--md-sys-color-outline-variant);
      color: var(--md-sys-color-on-surface);
      padding: 10px;
      border-radius: var(--md-sys-shape-corner-small);
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .theme-btn:hover {
      border-color: var(--md-sys-color-outline);
    }
    .theme-btn.active {
      border-color: var(--md-sys-color-primary);
      background-color: rgba(168, 199, 250, 0.1);
    }
    .color-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    /* Action Buttons */
    .btn-row {
      display: flex;
      gap: 10px;
      margin-top: 10px;
    }
    button.btn-primary {
      background-color: var(--md-sys-color-primary);
      color: var(--md-sys-color-on-primary);
      border: none;
      padding: 12px 20px;
      border-radius: var(--md-sys-shape-corner-full);
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: opacity 0.2s, transform 0.1s;
    }
    button.btn-primary:hover { opacity: 0.9; }
    button.btn-primary:active { transform: scale(0.98); }

    button.btn-tonal {
      background-color: var(--md-sys-color-surface-variant);
      color: var(--md-sys-color-on-surface);
      border: 1px solid var(--md-sys-color-outline);
      padding: 12px 16px;
      border-radius: var(--md-sys-shape-corner-full);
      font-weight: 500;
      font-size: 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: background-color 0.2s;
    }
    button.btn-tonal:hover { background-color: rgba(255, 255, 255, 0.08); }

    /* Canvas Preview Area */
    .preview-stage {
      background-color: var(--md-sys-color-background);
      padding: 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow: auto;
      gap: 24px;
    }
    .card-frame {
      max-width: 90%;
      width: 880px;
      box-shadow: 0 32px 64px -16px rgba(0, 0, 0, 0.85), 0 0 0 1px var(--md-sys-color-outline-variant);
      border-radius: 16px;
      overflow: hidden;
      transition: all 0.3s ease;
    }
    .card-frame svg {
      display: block;
      width: 100%;
      height: auto;
    }
    .specs-bar {
      display: flex;
      gap: 16px;
      color: var(--md-sys-color-on-surface-variant);
      font-size: 13px;
      font-family: 'JetBrains Mono', monospace;
    }
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--md-sys-color-primary-container);
      color: var(--md-sys-color-on-primary-container);
      padding: 12px 20px;
      border-radius: var(--md-sys-shape-corner-full);
      font-size: 14px;
      font-weight: 500;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.3s;
      pointer-events: none;
      box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }
    .toast.show { opacity: 1; transform: translateY(0); }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-icon">❖</div>
      <span>OG Canvas Studio</span>
      <span class="badge-chip">Material 3</span>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
      <span style="font-size: 13px; color: var(--md-sys-color-on-surface-variant)">MCP Protocol Ready</span>
      <button class="btn-tonal" style="padding: 6px 14px; font-size: 13px;" onclick="copyMetaTags()">📋 Copy HTML Meta</button>
    </div>
  </header>

  <div class="workspace">
    <div class="sidebar">
      <div class="form-group">
        <label>Template Preset</label>
        <select id="templateSelect" onchange="applyTemplate()">
          <option value="">Custom Design</option>
          <option value="modern-blog" selected>Modern Editorial Blog</option>
          <option value="tech-launch">Product & Tech Launch</option>
          <option value="podcast-episode">Podcast Episode</option>
          <option value="dev-tutorial">Developer Code Tutorial</option>
          <option value="newsletter">Curated Weekly Newsletter</option>
          <option value="minimalist">Minimalist Editorial</option>
          <option value="quote-card">Thought Leader Quote</option>
          <option value="event-summit">Conference & Event Ticket</option>
          <option value="ecommerce-drop">Product & Merchandise Drop</option>
          <option value="changelog-release">Release Notes & Changelog</option>
          <option value="documentation">API Documentation Reference</option>
          <option value="split-showcase">Split Visual Showcase</option>
        </select>
      </div>

      <div class="form-group">
        <label>Headline Title *</label>
        <input type="text" id="titleInput" value="Mastering Distributed Systems Architecture in 2026" oninput="renderCard()">
      </div>

      <div class="form-group">
        <label>Subtitle / Tagline</label>
        <textarea id="subtitleInput" rows="2" oninput="renderCard()">A comprehensive deep dive into consensus protocols, raft algorithms, and event sourcing.</textarea>
      </div>

      <div class="grid-2">
        <div class="form-group">
          <label>Category / Badge</label>
          <input type="text" id="categoryInput" value="Architecture" oninput="renderCard()">
        </div>
        <div class="form-group">
          <label>Author / Speaker</label>
          <input type="text" id="authorInput" value="Alex Rivera" oninput="renderCard()">
        </div>
      </div>

      <div class="grid-2">
        <div class="form-group">
          <label>Tags (comma-separated)</label>
          <input type="text" id="tagsInput" value="DistributedSystems, Raft, Cloud" oninput="renderCard()">
        </div>
        <div class="form-group">
          <label>Brand / Site Name</label>
          <input type="text" id="siteInput" value="devnotes.io" oninput="renderCard()">
        </div>
      </div>

      <div class="grid-2">
        <div class="form-group">
          <label>Layout Style</label>
          <select id="layoutSelect" onchange="renderCard()">
            <option value="default">Default / Standard</option>
            <option value="centered">Centered Hero</option>
            <option value="split">Split 60/40 Hero</option>
            <option value="minimal">Minimalist</option>
            <option value="dev_code">Developer Code</option>
            <option value="podcast">Podcast Waveform</option>
            <option value="event_ticket">Event Ticket</option>
          </select>
        </div>
        <div class="form-group">
          <label>Dimensions Preset</label>
          <select id="dimSelect" onchange="renderCard()">
            <option value="1200x630">1200 × 630 (Standard OG)</option>
            <option value="1200x675">1200 × 675 (Twitter Large)</option>
            <option value="1080x1080">1080 × 1080 (Square)</option>
            <option value="1500x500">1500 × 500 (Header Banner)</option>
            <option value="1280x720">1280 × 720 (YouTube HD)</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>Theme & Palette</label>
        <div class="theme-selector" id="themeButtons"></div>
      </div>

      <div class="btn-row">
        <button class="btn-primary" onclick="downloadSvg()">⬇ Download SVG</button>
        <button class="btn-tonal" onclick="copySvg()">Copy SVG</button>
      </div>
    </div>

    <div class="preview-stage">
      <div class="card-frame" id="cardContainer"></div>
      <div class="specs-bar" id="specsBar">
        <span>RESOLUTION: <strong id="specRes">1200x630</strong></span>
        <span>THEME: <strong id="specTheme">aurora</strong></span>
        <span>FORMAT: <strong>SVG Vector (Lossless)</strong></span>
      </div>
    </div>
  </div>

  <div class="toast" id="toast">Copied to clipboard!</div>

  <script>
    let currentTheme = 'aurora';
    let cachedCard = null;

    const THEMES_LIST = [
      { id: 'aurora', name: 'Aurora', color: '#10b981' },
      { id: 'cyberpunk', name: 'Cyberpunk', color: '#00f0ff' },
      { id: 'dark', name: 'Slate Dark', color: '#6366f1' },
      { id: 'light', name: 'Clean Light', color: '#2563eb' },
      { id: 'ocean', name: 'Deep Ocean', color: '#38bdf8' },
      { id: 'sunset', name: 'Sunset', color: '#f43f5e' },
      { id: 'emerald', name: 'Emerald', color: '#10b981' },
      { id: 'matrix', name: 'Matrix', color: '#22c55e' },
      { id: 'gold', name: 'Luxury Gold', color: '#f59e0b' },
      { id: 'monochrome', name: 'Monochrome', color: '#ffffff' }
    ];

    function initThemes() {
      const container = document.getElementById('themeButtons');
      container.innerHTML = THEMES_LIST.map(t => `
        <button class="theme-btn ${t.id === currentTheme ? 'active' : ''}" onclick="selectTheme('${t.id}')">
          <span class="color-dot" style="background: ${t.color}"></span>
          <span>${t.name}</span>
        </button>
      `).join('');
    }

    function selectTheme(themeId) {
      currentTheme = themeId;
      initThemes();
      renderCard();
    }

    async function renderCard() {
      const title = document.getElementById('titleInput').value || 'Untitled';
      const subtitle = document.getElementById('subtitleInput').value;
      const category = document.getElementById('categoryInput').value;
      const author = document.getElementById('authorInput').value;
      const site_name = document.getElementById('siteInput').value;
      const layout = document.getElementById('layoutSelect').value;
      const dim = document.getElementById('dimSelect').value.split('x');
      const tags = document.getElementById('tagsInput').value.split(',').map(s => s.trim()).filter(Boolean);

      const width = parseInt(dim[0], 10);
      const height = parseInt(dim[1], 10);

      document.getElementById('specRes').innerText = `${width}x${height}`;
      document.getElementById('specTheme').innerText = currentTheme;

      try {
        const resp = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title, subtitle, category, author, site_name, layout,
            theme: currentTheme, width, height, tags
          })
        });
        const data = await resp.json();
        cachedCard = data;
        document.getElementById('cardContainer').innerHTML = data.svg;
      } catch (err) {
        console.error('Error rendering card:', err);
      }
    }

    async function applyTemplate() {
      const templateId = document.getElementById('templateSelect').value;
      if (!templateId) return;
      try {
        const resp = await fetch('/api/templates');
        const templates = await resp.json();
        const t = templates.find(item => item.id === templateId);
        if (t && t.sample_data) {
          document.getElementById('titleInput').value = t.sample_data.title || '';
          document.getElementById('subtitleInput').value = t.sample_data.subtitle || '';
          document.getElementById('categoryInput').value = t.sample_data.category || '';
          document.getElementById('authorInput').value = t.sample_data.author || '';
          document.getElementById('siteInput').value = t.sample_data.site_name || '';
          if (t.sample_data.tags) {
            document.getElementById('tagsInput').value = t.sample_data.tags.join(', ');
          }
          if (t.default_theme) {
            currentTheme = t.default_theme;
            initThemes();
          }
          if (t.default_layout) {
            document.getElementById('layoutSelect').value = t.default_layout;
          }
          renderCard();
        }
      } catch (e) {
        console.error('Error applying template:', e);
      }
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2400);
    }

    function copySvg() {
      if (cachedCard && cachedCard.svg) {
        navigator.clipboard.writeText(cachedCard.svg);
        showToast('SVG XML copied to clipboard!');
      }
    }

    function copyMetaTags() {
      if (cachedCard && cachedCard.html_meta) {
        navigator.clipboard.writeText(cachedCard.html_meta);
        showToast('HTML Meta tags copied to clipboard!');
      }
    }

    function downloadSvg() {
      if (!cachedCard || !cachedCard.svg) return;
      const blob = new Blob([cachedCard.svg], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(document.getElementById('titleInput').value || 'card').toLowerCase().replace(/[^a-z0-9]/g, '_')}.svg`;
      a.click();
      URL.revokeObjectURL(url);
    }

    initThemes();
    renderCard();
  </script>
</body>
</html>
"""


class StudioHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Zero-dependency HTTP request handler for Material 3 Studio Web UI & REST API."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server access logs unless debugging."""
        pass

    def do_GET(self) -> None:
        """Handle GET requests for UI and API."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(STUDIO_HTML_PAGE.encode("utf-8"))

        elif path == "/api/templates":
            templates = list_templates()
            data = [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category,
                    "description": t.description,
                    "default_layout": t.config.layout.value if isinstance(t.config.layout, CardLayout) else str(t.config.layout),
                    "default_theme": t.config.theme if isinstance(t.config.theme, str) else t.config.theme.id,
                    "sample_data": t.sample_data,
                }
                for t in templates
            ]
            self.send_json(data)

        elif path == "/api/themes":
            themes = list_themes()
            data = [t.to_dict() for t in themes]
            self.send_json(data)

        elif path == "/api/diagnostics":
            self.send_json(run_diagnostics())

        else:
            self.send_error(404, "File Not Found")

    def do_POST(self) -> None:
        """Handle POST requests for card generation."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/generate":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            try:
                params = json.loads(body)
            except Exception:
                params = {}

            title = params.get("title", "Untitled")
            tags = params.get("tags", [])
            width = int(params.get("width", 1200))
            height = int(params.get("height", 630))

            cfg = OGCardConfig(
                title=title,
                subtitle=params.get("subtitle"),
                author=AuthorSpec(name=params["author"]) if params.get("author") else None,
                category=params.get("category"),
                tags=tags,
                theme=params.get("theme", "aurora"),
                layout=CardLayout.from_str(params.get("layout", "default")),
                dimensions=CardDimension(width, height, f"{width}x{height}"),
                site_name=params.get("site_name"),
            )

            card = generate_card(cfg)
            self.send_json({
                "title": card.title,
                "width": card.width,
                "height": card.height,
                "svg": card.svg,
                "html_meta": card.html_meta,
            })
        else:
            self.send_error(404, "API Endpoint Not Found")

    def send_json(self, data: Any) -> None:
        """Send JSON response helper."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def handle_serve(args: argparse.Namespace) -> int:
    """Handle `serve` subcommand: launch Material 3 Studio web application."""
    host = args.host or "127.0.0.1"
    port = int(args.port or 8080)

    server = http.server.HTTPServer((host, port), StudioHTTPRequestHandler)
    url = f"http://{host}:{port}"

    if not getattr(args, "quiet", False):
        print(f"\n{Term.green('🚀 OG Canvas Forge Studio is Live!')}")
        print(f"  URL:            {Term.bold(Term.cyan(url))}")
        print(f"  Host:           {host}:{port}")
        print(f"  REST API:       {url}/api/generate, {url}/api/templates, {url}/api/themes")
        print(f"  Press {Term.bold('Ctrl+C')} to stop the studio server.\n")

    if not getattr(args, "no_browser", False):
        threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if not getattr(args, "quiet", False):
            print(f"\n{Term.yellow('Studio server stopped.')}")
    finally:
        server.server_close()

    return 0


# ============================================================================
# SELF-VERIFICATION TEST RUNNER
# ============================================================================


def handle_test(args: argparse.Namespace) -> int:
    """Run internal test suite verifying all engine and protocol components."""
    verbose = getattr(args, "verbose", False)
    test_filter = getattr(args, "filter", None)

    tests: List[Tuple[str, Any]] = []

    def test(name: str):
        def decorator(fn):
            tests.append((name, fn))
            return fn
        return decorator

    @test("1. Verify Themes Catalog Completeness")
    def _test_themes():
        themes = list_themes()
        assert len(themes) >= 10, f"Expected at least 10 themes, got {len(themes)}"
        for t in themes:
            assert t.id and t.name and t.bg_start and t.bg_end and t.accent
            d = t.to_dict()
            assert d["id"] == t.id

    @test("2. Verify Templates Catalog Completeness")
    def _test_templates():
        templates = list_templates()
        assert len(templates) >= 12, f"Expected at least 12 templates, got {len(templates)}"
        for t in templates:
            assert t.id and t.category and t.name and t.config.title
            card = generate_card(t.config)
            assert "<svg" in card.svg and "</svg>" in card.svg

    @test("3. Verify SVG Card Generation on All Layouts")
    def _test_layouts():
        layouts = [
            CardLayout.DEFAULT,
            CardLayout.CENTERED,
            CardLayout.SPLIT,
            CardLayout.MINIMAL,
            CardLayout.DEV_CODE,
            CardLayout.PODCAST,
            CardLayout.EVENT_TICKET,
        ]
        for l in layouts:
            cfg = OGCardConfig(
                title=f"Testing Layout {l.value}",
                subtitle="Testing full vector output pipeline",
                author="DeepMind Engineer",
                category="Testing",
                tags=["Python", "SVG"],
                layout=l,
            )
            card = generate_card(cfg)
            assert "<svg" in card.svg
            assert "</svg>" in card.svg
            assert f"{card.width}" in card.svg

    @test("4. Verify HTML Meta Tag Compliance")
    def _test_meta():
        html_out = render_html_meta(
            title="Meta Tag Test",
            image_url="https://example.com/og.svg",
            description="Testing meta tag generation",
            site_name="Example Site",
            twitter_handle="@example",
        )
        assert 'property="og:title" content="Meta Tag Test"' in html_out
        assert 'property="og:image" content="https://example.com/og.svg"' in html_out
        assert 'name="twitter:card" content="summary_large_image"' in html_out
        assert 'name="twitter:creator" content="@example"' in html_out

    @test("5. Verify MCP Protocol JSON-RPC Handshake")
    def _test_mcp_handshake():
        res = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert res is not None
        assert res["result"]["serverInfo"]["name"] == SERVER_NAME
        assert res["result"]["protocolVersion"] == PROTOCOL_VERSION

    @test("6. Verify MCP Tool Call execution")
    def _test_mcp_tool_call():
        res = handle_jsonrpc_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "og_generate_card",
                "arguments": {
                    "title": "MCP Tool Test",
                    "theme": "cyberpunk",
                },
            },
        })
        assert res is not None
        assert not res["result"].get("isError")
        assert "<svg" in res["result"]["content"][0]["text"]

    @test("7. Verify MCP Resources and Prompts Discovery")
    def _test_mcp_resources_and_prompts():
        # Resources
        res_list = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
        assert len(res_list["result"]["resources"]) >= 3

        res_read = handle_jsonrpc_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "og://specs/social-card-guide"},
        })
        assert "Open Graph Social Card Specifications" in res_read["result"]["contents"][0]["text"]

        # Prompts
        prompts_list = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 5, "method": "prompts/list"})
        assert len(prompts_list["result"]["prompts"]) >= 2

    @test("8. Verify Diagnostics Multi-OS Inspection")
    def _test_diagnostics():
        diag = run_diagnostics(detailed=True)
        assert diag["status"] == "OK"
        assert diag["catalogs"]["themes_count"] >= 10
        assert diag["catalogs"]["templates_count"] >= 12

    # Execute tests
    print(f"\n{Term.bold('Running og-canvas-forge Internal Test Suite')}")
    print(Term.dim("─" * 60))

    passed = 0
    failed = 0
    start = time.time()

    for name, fn in tests:
        if test_filter and test_filter.lower() not in name.lower():
            continue
        try:
            fn()
            print(f"  {Term.green('✔ PASS')} {name}")
            passed += 1
        except Exception as e:
            print(f"  {Term.red('✖ FAIL')} {name} -> {Term.red(str(e))}")
            failed += 1

    elapsed = time.time() - start
    print(Term.dim("─" * 60))
    if failed == 0:
        print(f"{Term.green(Term.bold('ALL TESTS PASSED'))} ({passed}/{len(tests)} tests passed in {elapsed:.3f}s)\n")
        return 0
    else:
        print(f"{Term.red(Term.bold('TEST FAILURES DETECTED'))} ({failed} failed, {passed} passed in {elapsed:.3f}s)\n")
        return 1


# ============================================================================
# CLI PARSER & ENTRY POINT
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser with robust parent parser for global flags."""
    # Common flags inherited by root and all subcommands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--no-color", action="store_true", help="Disable ANSI terminal colors")
    common_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential output banners")
    common_parser.add_argument("-v", "--version", action="store_true", help="Show package version and exit")

    root_parser = argparse.ArgumentParser(
        prog="og-canvas-forge",
        description="High-performance pure-Python Open Graph social card canvas forge, Studio UI & MCP server.",
        parents=[common_parser],
    )

    subparsers = root_parser.add_subparsers(dest="subcommand", title="Subcommands", metavar="<command>")

    # 1. `generate`
    p_gen = subparsers.add_parser("generate", help="Synthesize an Open Graph social card SVG", parents=[common_parser])
    p_gen.add_argument("title_pos", nargs="?", help="Title headline text (positional shortcut)")
    p_gen.add_argument("-t", "--title", help="Main title headline of the card")
    p_gen.add_argument("-s", "--subtitle", help="Subtitle or description text")
    p_gen.add_argument("-a", "--author", help="Author name or attribution handle")
    p_gen.add_argument("-c", "--category", help="Category or topic pill badge")
    p_gen.add_argument("--tags", help="Comma-separated keyword tags (e.g. 'Python,AI,MCP')")
    p_gen.add_argument("--theme", help="Color theme name (aurora, cyberpunk, dark, light, ocean, sunset, emerald, matrix, gold, monochrome)")
    p_gen.add_argument("--layout", help="Layout style (default, centered, split, minimal, dev_code, podcast, event_ticket)")
    p_gen.add_argument("--template", help="Preset template ID to inherit from")
    p_gen.add_argument("-o", "--output", help="Output file path (SVG, HTML, BMP, JSON) or '-' for stdout")
    p_gen.add_argument("-f", "--format", choices=["svg", "html", "bmp", "json"], help="Output format")
    p_gen.add_argument("-W", "--width", type=int, default=1200, help="Card width in pixels (default: 1200)")
    p_gen.add_argument("-H", "--height", type=int, default=630, help="Card height in pixels (default: 630)")
    p_gen.add_argument("--brand", "--site-name", dest="brand", help="Brand or site name watermark")
    p_gen.add_argument("--reading-time", type=int, help="Reading time estimate in minutes")
    p_gen.add_argument("--date", help="Publication date string")
    p_gen.add_argument("--code", help="Code snippet for dev_code layout")
    p_gen.add_argument("--code-lang", help="Programming language for code snippet")
    p_gen.add_argument("--episode", help="Episode or issue number for podcast/newsletter layout")
    p_gen.add_argument("--ticket", help="Ticket identifier for event_ticket layout")
    p_gen.add_argument("--badge", help="Custom badge pill text")
    p_gen.add_argument("--watermark", help="Watermark text or prefix (e.g. 'CONFIDENTIAL:draft', 'STAMP:approved', 'preview')")
    p_gen.add_argument("--qr", "--qr-code", dest="qr_code", help="URL or text to encode as scannable QR Code badge on card")
    p_gen.add_argument("--preview", action="store_true", help="Open generated card in default web browser")
    p_gen.add_argument("--audit", action="store_true", help="Audit card contrast and accessibility against WCAG 2.2 criteria")

    # 1b. `qr`
    p_qr = subparsers.add_parser("qr", help="Synthesize a standalone scannable QR Code SVG badge", parents=[common_parser])
    p_qr.add_argument("text", help="URL or text payload to encode")
    p_qr.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p_qr.add_argument("-s", "--size", type=int, default=120, help="Pixel size (default: 120)")
    p_qr.add_argument("--fg", default="#ffffff", help="Foreground color (default: #ffffff)")
    p_qr.add_argument("--label", help="Optional label beneath QR code")

    # 2. `batch`
    p_batch = subparsers.add_parser("batch", help="Batch generate cards from JSON or CSV file", parents=[common_parser])
    p_batch.add_argument("file", help="Path to JSON or CSV file containing post metadata")
    p_batch.add_argument("-d", "--output-dir", default="./og-cards", help="Directory to save generated cards (default: ./og-cards)")
    p_batch.add_argument("-f", "--format", choices=["svg", "html", "bmp", "json"], default="svg", help="Output file format")
    p_batch.add_argument("--theme", help="Default theme for cards without explicit theme")
    p_batch.add_argument("--layout", help="Default layout for cards without explicit layout")
    p_batch.add_argument("--template", help="Default template for cards without explicit template")
    p_batch.add_argument("--prefix", default="", help="Filename prefix for generated cards")
    p_batch.add_argument("--dry-run", action="store_true", help="Simulate batch generation without writing files")

    # 3. `templates`
    p_tmpl = subparsers.add_parser("templates", help="List available built-in card templates", parents=[common_parser])
    p_tmpl.add_argument("-c", "--category", help="Filter templates by category")
    p_tmpl.add_argument("--json", action="store_true", help="Output templates catalog as JSON")

    # 4. `themes`
    p_thm = subparsers.add_parser("themes", help="List available color themes and palettes", parents=[common_parser])
    p_thm.add_argument("-c", "--category", choices=["dark", "light"], help="Filter themes by mode")
    p_thm.add_argument("--json", action="store_true", help="Output themes catalog as JSON")

    # 5. `meta`
    p_meta = subparsers.add_parser("meta", help="Generate HTML <meta> tags for social cards", parents=[common_parser])
    p_meta.add_argument("-t", "--title", required=True, help="Page and card headline title")
    p_meta.add_argument("-i", "--image", "--image-url", dest="image", required=True, help="Absolute URL to the OG image")
    p_meta.add_argument("-d", "--description", help="Page description")
    p_meta.add_argument("-u", "--url", help="Canonical page URL")
    p_meta.add_argument("-a", "--author", help="Author name")
    p_meta.add_argument("--site-name", help="Site name")
    p_meta.add_argument("--twitter", "--twitter-handle", dest="twitter", help="Twitter @handle")
    p_meta.add_argument("--twitter-card", choices=["summary_large_image", "summary"], default="summary_large_image", help="Twitter card type")
    p_meta.add_argument("--type", default="article", help="OG type (default: article)")
    p_meta.add_argument("--tags", help="Comma-separated article tags")
    p_meta.add_argument("-o", "--output", help="File to write meta tags to (or stdout if omitted)")

    # 6. `audit`
    p_aud = subparsers.add_parser("audit", help="Audit OG card contrast and accessibility against WCAG 2.2 AA/AAA", parents=[common_parser])
    p_aud.add_argument("target", nargs="?", help="Template ID, theme ID, or custom card title to audit")
    p_aud.add_argument("--theme", help="Theme ID to audit")
    p_aud.add_argument("--template", help="Template ID to audit")
    p_aud.add_argument("-t", "--title", help="Card title")
    p_aud.add_argument("-s", "--subtitle", help="Card subtitle")
    p_aud.add_argument("--json", action="store_true", help="Output accessibility report as JSON")

    # 7. `schema`
    p_sch = subparsers.add_parser("schema", help="Generate complete Schema.org Rich Snippet JSON-LD for social card", parents=[common_parser])
    p_sch.add_argument("-t", "--title", required=True, help="Card headline title")
    p_sch.add_argument("-s", "--subtitle", help="Card subtitle / description")
    p_sch.add_argument("-u", "--url", help="Canonical page URL")
    p_sch.add_argument("-i", "--image", "--image-url", dest="image", help="Social card image URL")
    p_sch.add_argument("-a", "--author", help="Author name")
    p_sch.add_argument("--type", dest="schema_type", help="Schema.org type (BlogPosting, Article, Event, PodcastEpisode, TechArticle)")
    p_sch.add_argument("--publisher", help="Publisher or organization name")
    p_sch.add_argument("-o", "--output", help="Write JSON-LD to file")

    # 8. `serve`
    p_srv = subparsers.add_parser("serve", help="Launch Material 3 OG Canvas Forge Studio Web UI", parents=[common_parser])
    p_srv.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    p_srv.add_argument("-p", "--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    p_srv.add_argument("--no-browser", action="store_true", help="Do not automatically open browser on launch")

    # 9. `mcp`
    subparsers.add_parser("mcp", help="Run Model Context Protocol (MCP) server over stdio", parents=[common_parser])

    # 10. `platform` / `doctor` / `diagnostics`
    for alias in ["platform", "doctor", "diagnostics"]:
        p_diag = subparsers.add_parser(alias, help="Perform multi-OS diagnostics check", parents=[common_parser])
        p_diag.add_argument("--json", action="store_true", help="Output diagnostics report as JSON")
        p_diag.add_argument("--detailed", action="store_true", help="Include verbose environment details")

    # 11. `test`
    p_tst = subparsers.add_parser("test", help="Run self-verification test suite", parents=[common_parser])
    p_tst.add_argument("--verbose", action="store_true", help="Verbose test execution")
    p_tst.add_argument("-k", "--filter", help="Filter tests by name substring")

    return root_parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI Main Entry Point."""
    if argv is None:
        argv = sys.argv[1:]

    # Parse arguments
    parser = build_parser()
    args = parser.parse_args(argv)

    # Global color configuration
    Term.init(no_color_flag=getattr(args, "no_color", False))

    # Version check
    if getattr(args, "version", False):
        print(f"{SERVER_NAME} {SERVER_VERSION}")
        return 0

    subcommand = args.subcommand

    if not subcommand:
        # Default behavior with no arguments: show banner and help
        if not getattr(args, "quiet", False):
            print_banner()
        parser.print_help()
        return 0

    # Subcommand routing
    if subcommand == "generate":
        # Handle title positional vs option fallback
        if not args.title and getattr(args, "title_pos", None):
            args.title = args.title_pos
        return handle_generate(args)
    elif subcommand == "qr":
        return handle_qr(args)
    elif subcommand == "batch":
        return handle_batch(args)
    elif subcommand == "templates":
        return handle_templates(args)
    elif subcommand == "themes":
        return handle_themes(args)
    elif subcommand == "meta":
        return handle_meta(args)
    elif subcommand == "audit":
        return handle_audit(args)
    elif subcommand == "schema":
        return handle_schema(args)
    elif subcommand == "serve":
        return handle_serve(args)
    elif subcommand == "mcp":
        return handle_mcp(args)
    elif subcommand in ("platform", "doctor", "diagnostics"):
        return handle_diagnostics(args)
    elif subcommand == "test":
        return handle_test(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
