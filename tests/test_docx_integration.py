import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx_fixture_builder import Document, build_basic_docx


def load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


if Document is not None:
    lint = load_module("doc_lint_integration", "scripts/lint.py")
else:  # pragma: no cover
    lint = None


@unittest.skipUnless(Document is not None, "python-docx is required for .docx integration tests")
class TestDocxIntegration(unittest.TestCase):
    def test_lint_reports_original_paragraph_lines(self):
        assert lint is not None
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "line-check.docx"
            build_basic_docx(
                path,
                [
                    {"text": "Purpose", "style": "Heading 1"},
                    {"text": ""},
                    {"text": "Visit https://example.com/test).", "style": "Normal"},
                    {"text": ""},
                    {"text": ""},
                ],
            )
            issues = lint.lint(path, lint.load_config(None))

        raw_url = next(issue for issue in issues if issue["code"] == "W021")
        blank_run = next(issue for issue in issues if issue["code"] == "W016")
        self.assertEqual(raw_url["line"], 3)
        self.assertEqual(blank_run["line"], 4)
        self.assertEqual(raw_url["text"], "https://example.com/test")

    def test_style_policy_applies_to_docx_fixture(self):
        assert lint is not None
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy.docx"
            build_basic_docx(
                path,
                [
                    {"text": "Purpose", "style": "Heading 1"},
                    {"text": "This policy explains the objective.", "style": "Normal"},
                ],
            )
            policy_path = Path(tmpdir) / ".style-policy.md"
            policy_path.write_text("Required sections: Purpose, Scope\n", encoding="utf-8")
            with patch("os.getcwd", return_value=tmpdir):
                issues = lint.lint(path, lint.load_config(None))

        style_policy_issues = [issue for issue in issues if issue["code"] == "W015"]
        self.assertEqual(len(style_policy_issues), 1)
        self.assertIn('"Scope"', style_policy_issues[0]["message"])


if __name__ == "__main__":
    unittest.main()
