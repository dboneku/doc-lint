import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    sys.modules.setdefault("docx", types.SimpleNamespace(Document=object))
    sys.modules.setdefault("docx.oxml", types.ModuleType("docx.oxml"))
    sys.modules.setdefault("docx.oxml.ns", types.SimpleNamespace(qn=lambda value: value))
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


lint = load_module("doc_lint_script", "scripts/lint.py")


class TestLintHelpers(unittest.TestCase):
    def test_strip_yaml_frontmatter(self):
        raw = "---\nsource: test\nset_date: 2026-03-12\n---\n\n# Body\nText\n"
        self.assertEqual(lint._strip_yaml_frontmatter(raw), "# Body\nText")

    def test_clean_detected_url_trims_trailing_punctuation(self):
        self.assertEqual(
            lint._clean_detected_url("https://example.com/path)."),
            "https://example.com/path",
        )
        self.assertEqual(
            lint._clean_detected_url("https://example.com/path?q=1]"),
            "https://example.com/path?q=1",
        )

    def test_extract_required_headings_from_policy_handles_inline_list(self):
        policy = "Required sections: Purpose, Scope, Revision History"
        self.assertEqual(
            lint._extract_required_headings_from_policy(policy),
            ["Purpose", "Scope", "Revision History"],
        )


if __name__ == "__main__":
    unittest.main()
