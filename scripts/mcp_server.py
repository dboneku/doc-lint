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
    data = base64.b64decode(docx_base64)
    cfg = config or copy.deepcopy(_lint_mod.DEFAULT_CONFIG)

    stem = Path(filename).stem
    with tempfile.NamedTemporaryFile(
        suffix=".docx", prefix=f"{stem}_", delete=False
    ) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        issues = _lint_mod.lint(tmp_path, cfg)
    finally:
        tmp_path.unlink(missing_ok=True)

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

    data = base64.b64decode(docx_base64)
    cfg = config or copy.deepcopy(_fix_mod.DEFAULT_CONFIG)

    stem = Path(filename).stem
    with tempfile.NamedTemporaryFile(
        suffix=".docx", prefix=f"{stem}_", delete=False
    ) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    out_path = tmp_path.with_name(tmp_path.stem + ".fixed.docx")

    try:
        doc = _Document(str(tmp_path))
        applied: list[str] = []
        changes: list[tuple] = []

        _fix_mod.fix_style_misuse(doc, cfg, applied, changes)
        _fix_mod.fix_font_normalization(doc, cfg, applied, changes)
        _fix_mod.fix_font_size(doc, cfg, applied, changes)
        _fix_mod.fix_list_normalization(doc, cfg, applied, changes)
        _fix_mod.fix_heading_level_skip(doc, cfg, applied, changes)
        _fix_mod.fix_single_item_lists(doc, cfg, applied, changes)
        _fix_mod.fix_multiline_headings(doc, cfg, applied, changes)
        _fix_mod.fix_numbered_headings(doc, cfg, applied, changes)
        _fix_mod.fix_excess_blank_paragraphs(doc, cfg, applied, changes)
        _fix_mod.fix_double_spaces(doc, cfg, applied, changes)
        _fix_mod.fix_heading_capitalization(doc, cfg, applied, changes)
        _fix_mod.fix_raw_urls(doc, cfg, applied, changes)

        doc.save(str(out_path))
        fixed_bytes = out_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

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
