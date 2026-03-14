"""
Unit tests for the MCP server tool functions (scripts/mcp_server.py).

Tests mock the docx layer so no real .docx files are needed.
The mcp package must be installed (it is listed in requirements.txt).
"""

import base64
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub docx before importing any script module that requires it.
# ---------------------------------------------------------------------------
_docx_stub = types.SimpleNamespace(Document=MagicMock())
sys.modules.setdefault("docx", _docx_stub)
sys.modules.setdefault("docx.oxml", types.SimpleNamespace(OxmlElement=MagicMock()))
sys.modules.setdefault("docx.oxml.ns", types.SimpleNamespace(qn=lambda v: v))
sys.modules.setdefault("docx.shared", types.SimpleNamespace(Pt=lambda v: v))
sys.modules.setdefault("docx.opc", types.ModuleType("docx.opc"))
sys.modules.setdefault(
    "docx.opc.constants",
    types.SimpleNamespace(RELATIONSHIP_TYPE=types.SimpleNamespace()),
)

# Add scripts/ to path so 'import mcp_server' resolves
_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

import mcp_server  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64(data: bytes = b"PK\x03\x04") -> str:
    return base64.b64encode(data).decode()


# ---------------------------------------------------------------------------
# get_default_config
# ---------------------------------------------------------------------------

class TestGetDefaultConfig(unittest.TestCase):
    def setUp(self):
        mcp_server._lint_mod.DEFAULT_CONFIG = {
            "rules": {"test-rule": {"enabled": True}}
        }

    def test_returns_rules_key(self):
        result = mcp_server.get_default_config()
        self.assertIn("rules", result)

    def test_returns_deep_copy(self):
        result = mcp_server.get_default_config()
        result["rules"]["injected"] = True
        self.assertNotIn("injected", mcp_server._lint_mod.DEFAULT_CONFIG["rules"])


# ---------------------------------------------------------------------------
# lint_document
# ---------------------------------------------------------------------------

class TestLintDocument(unittest.TestCase):
    def setUp(self):
        mcp_server._lint_mod.DEFAULT_CONFIG = {"rules": {}}

    def test_summary_counts_by_severity(self):
        mcp_server._lint_mod.lint = MagicMock(return_value=[
            {"rule": "empty-section", "code": "E002", "severity": "error",
             "message": "empty", "line": 2, "text": "", "fixable": False},
            {"rule": "double-spaces", "code": "W019", "severity": "warning",
             "message": "spaces", "line": 4, "text": "hi  there", "fixable": True},
            {"rule": "orphaned-bold", "code": "I009", "severity": "info",
             "message": "bold", "line": 6, "text": "Bold", "fixable": False},
        ])

        result = mcp_server.lint_document(_b64(), filename="test.docx")

        self.assertEqual(result["summary"]["total"], 3)
        self.assertEqual(result["summary"]["errors"], 1)
        self.assertEqual(result["summary"]["warnings"], 1)
        self.assertEqual(result["summary"]["info"], 1)
        self.assertEqual(result["summary"]["fixable"], 1)

    def test_zero_issues_returns_empty_list(self):
        mcp_server._lint_mod.lint = MagicMock(return_value=[])

        result = mcp_server.lint_document(_b64())

        self.assertEqual(result["issues"], [])
        self.assertEqual(result["summary"]["total"], 0)

    def test_issues_list_is_forwarded_unchanged(self):
        fake = [{"rule": "style-misuse", "code": "W003", "severity": "warning",
                 "message": "test", "line": 1, "text": "heading", "fixable": True}]
        mcp_server._lint_mod.lint = MagicMock(return_value=fake)

        result = mcp_server.lint_document(_b64())

        self.assertEqual(result["issues"], fake)

    def test_temp_file_is_cleaned_up(self):
        """lint is called; no temp files should linger."""
        created_paths: list[Path] = []

        original_lint = mcp_server._lint_mod.lint

        def capturing_lint(path, cfg):
            created_paths.append(Path(path))
            return []

        mcp_server._lint_mod.lint = capturing_lint
        try:
            mcp_server.lint_document(_b64())
        finally:
            mcp_server._lint_mod.lint = original_lint

        for p in created_paths:
            self.assertFalse(p.exists(), f"Temp file not removed: {p}")


# ---------------------------------------------------------------------------
# fix_document
# ---------------------------------------------------------------------------

class TestFixDocument(unittest.TestCase):
    def setUp(self):
        mcp_server._fix_mod.DEFAULT_CONFIG = {"rules": {}}
        self._fixer_names = [
            "fix_style_misuse", "fix_font_normalization", "fix_font_size",
            "fix_list_normalization", "fix_heading_level_skip",
            "fix_single_item_lists", "fix_multiline_headings",
            "fix_numbered_headings", "fix_excess_blank_paragraphs",
            "fix_double_spaces", "fix_heading_capitalization", "fix_raw_urls",
        ]
        for fn in self._fixer_names:
            setattr(mcp_server._fix_mod, fn, MagicMock())

    def _run_fix(self, extra_bytes: bytes = b"fixed") -> dict:
        fake_doc = MagicMock()
        # Patch docx.Document so the local import inside fix_document gets the mock
        # regardless of whether the real package is already loaded in sys.modules.
        with patch("docx.Document", return_value=fake_doc), \
             patch.object(Path, "read_bytes", return_value=extra_bytes), \
             patch.object(Path, "unlink"):
            return mcp_server.fix_document(_b64(), filename="test.docx")

    def test_returns_fixed_docx_base64(self):
        fixed_bytes = b"fixed-docx-bytes"
        result = self._run_fix(fixed_bytes)
        self.assertEqual(base64.b64decode(result["fixed_docx_base64"]), fixed_bytes)

    def test_returns_applied_and_changes_lists(self):
        result = self._run_fix()
        self.assertIsInstance(result["applied"], list)
        self.assertIsInstance(result["changes"], list)

    def test_all_fixers_are_called(self):
        self._run_fix()
        for fn in self._fixer_names:
            mock = getattr(mcp_server._fix_mod, fn)
            mock.assert_called_once(), f"{fn} was not called"

    def test_changes_serialised_as_dicts(self):
        """If a fixer appends a (code, before, after) tuple it appears in output."""
        def fake_fixer(doc, cfg, applied, changes):
            applied.append("W019: fixed 1 double space")
            changes.append(("W019", "hello  world", "hello world"))

        mcp_server._fix_mod.fix_double_spaces = fake_fixer

        result = self._run_fix()

        self.assertIn("W019: fixed 1 double space", result["applied"])
        self.assertEqual(
            result["changes"],
            [{"code": "W019", "before": "hello  world", "after": "hello world"}],
        )


if __name__ == "__main__":
    unittest.main()
