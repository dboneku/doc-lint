#!/usr/bin/env python3
"""
doc-lint MCP server.

Exposes lint and fix operations as MCP tools so any MCP-compatible AI client
(Claude Desktop, Copilot, Cursor, etc.) can lint and fix Word documents directly.

Run the server:
    python scripts/mcp_server.py

Add to Claude Desktop  (~/.config/claude/claude_desktop_config.json  or
~/Library/Application Support/Claude/claude_desktop_config.json on macOS):

    {
      "mcpServers": {
        "doc-lint": {
          "command": "python",
          "args": ["/absolute/path/to/doc-lint/scripts/mcp_server.py"]
        }
      }
    }

The existing CLI plugin (commands/) and skill files (skills/) continue to work
unchanged — this is a separate, additive deployment option.
"""

import base64
import binascii
import copy
import sys
import tempfile
from pathlib import Path

# Allow importing sibling scripts (lint.py, fix.py)
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "ERROR: mcp not installed. Run: pip install 'mcp[cli]>=1.0'",
        file=sys.stderr,
    )
    sys.exit(1)

import lint as _lint_mod
import fix as _fix_mod

mcp = FastMCP("doc-lint")

_FIXER_NAMES = (
    "fix_style_misuse",
    "fix_font_normalization",
    "fix_font_size",
    "fix_list_normalization",
    "fix_heading_level_skip",
    "fix_single_item_lists",
    "fix_multiline_headings",
    "fix_numbered_headings",
    "fix_excess_blank_paragraphs",
    "fix_double_spaces",
    "fix_heading_capitalization",
    "fix_raw_urls",
)


def _decode_docx_base64(docx_base64: str) -> bytes:
    try:
        return base64.b64decode(docx_base64, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ValueError(
            "docx_base64 must be valid base64-encoded .docx bytes"
        ) from exc


def _merge_config(default_config: dict, overrides: dict | None) -> dict:
    cfg = copy.deepcopy(default_config)
    if overrides is None:
        return cfg
    if not isinstance(overrides, dict):
        raise ValueError("config must be a JSON object")

    for key, value in overrides.items():
        if key == "rules":
            continue
        cfg[key] = copy.deepcopy(value)

    for rule, settings in overrides.get("rules", {}).items():
        if isinstance(settings, str):
            if settings == "off":
                cfg["rules"].setdefault(rule, {})["enabled"] = False
            else:
                cfg["rules"].setdefault(rule, {}).update(
                    {"enabled": True, "severity": settings}
                )
        elif isinstance(settings, dict):
            cfg["rules"].setdefault(rule, {}).update(copy.deepcopy(settings))
        else:
            raise ValueError(
                f'config.rules.{rule} must be an object or one of "off", '
                '"error", "warning", "info"'
            )
    return cfg


def _safe_filename(filename: str) -> str:
    basename = Path(filename or "document.docx").name or "document.docx"
    if basename.lower().endswith(".docx"):
        return basename
    return f"{basename}.docx"


# ---------------------------------------------------------------------------
# Tool: lint_document
# ---------------------------------------------------------------------------

@mcp.tool()
def lint_document(
    docx_base64: str,
    filename: str = "document.docx",
    config: dict | None = None,
) -> dict:
    """
    Lint a .docx document for formatting and structural issues.

    Args:
        docx_base64: Base64-encoded .docx file contents.
        filename:    Original filename — used by the naming-convention rule (W014).
        config:      Optional lint configuration dict. Omit to use built-in defaults.
                     Retrieve the default shape with the get_default_config tool.

    Returns a dict with:
      - issues:  list of {rule, code, severity, message, line, text, fixable}
      - summary: {total, errors, warnings, info, fixable}
    """
    data = _decode_docx_base64(docx_base64)
    cfg = _merge_config(_lint_mod.DEFAULT_CONFIG, config)

    with tempfile.TemporaryDirectory(prefix="doc-lint-") as tmpdir:
        tmp_path = Path(tmpdir) / _safe_filename(filename)
        tmp_path.write_bytes(data)
        issues = _lint_mod.lint(tmp_path, cfg)

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    infos = sum(1 for i in issues if i["severity"] == "info")
    fixable = sum(1 for i in issues if i.get("fixable"))

    return {
        "issues": issues,
        "summary": {
            "total": len(issues),
            "errors": errors,
            "warnings": warnings,
            "info": infos,
            "fixable": fixable,
        },
    }


# ---------------------------------------------------------------------------
# Tool: fix_document
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_document(
    docx_base64: str,
    filename: str = "document.docx",
    config: dict | None = None,
) -> dict:
    """
    Apply all auto-fixable formatting corrections to a .docx document.

    Fixes: style misuse (W003), non-standard fonts (W004), font sizes (W005),
    list formatting (W006), heading level skips (W007), single-item lists
    (I008), multiline headings (I011), numbered heading continuity (W012),
    excess blank paragraphs (W016), double spaces (W019), heading
    capitalisation (W020), and raw unlinked URLs (W021).

    Args:
        docx_base64: Base64-encoded .docx file contents.
        filename:    Original filename (informational only).
        config:      Optional fix configuration dict. Omit to use built-in defaults.

    Returns a dict with:
      - fixed_docx_base64: Base64-encoded corrected .docx file contents.
      - applied: list of human-readable descriptions of fixes applied.
      - changes: list of {code, before, after} for each text-level change.
    """
    from docx import Document as _Document

    data = _decode_docx_base64(docx_base64)
    cfg = _merge_config(_fix_mod.DEFAULT_CONFIG, config)

    with tempfile.TemporaryDirectory(prefix="doc-lint-") as tmpdir:
        tmp_path = Path(tmpdir) / _safe_filename(filename)
        out_path = tmp_path.with_name(tmp_path.stem + ".fixed.docx")
        tmp_path.write_bytes(data)

        doc = _Document(str(tmp_path))
        applied: list[str] = []
        changes: list[tuple] = []

        for fixer_name in _FIXER_NAMES:
            fixer = getattr(_fix_mod, fixer_name)
            fixer(doc, cfg, applied, changes)

        doc.save(str(out_path))
        fixed_bytes = out_path.read_bytes()

    return {
        "fixed_docx_base64": base64.b64encode(fixed_bytes).decode(),
        "applied": applied,
        "changes": [
            {"code": code, "before": before, "after": after}
            for code, before, after in changes
        ],
    }


# ---------------------------------------------------------------------------
# Tool: get_default_config
# ---------------------------------------------------------------------------

@mcp.tool()
def get_default_config() -> dict:
    """
    Return the built-in doc-lint configuration.

    Useful as a starting point when you want to customise rules before passing
    a config dict to lint_document or fix_document. The returned dict is a
    deep copy — mutations do not affect the server's defaults.
    """
    return copy.deepcopy(_lint_mod.DEFAULT_CONFIG)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
