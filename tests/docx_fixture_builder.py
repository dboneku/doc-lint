from pathlib import Path

try:
    from docx import Document
except ImportError:  # pragma: no cover
    Document = None


class FixtureBuilderUnavailable(RuntimeError):
    pass


def require_document_class():
    if Document is None:
        raise FixtureBuilderUnavailable("python-docx is required to build .docx test fixtures")
    return Document


def build_basic_docx(path: Path, paragraphs: list[dict]):
    document_class = require_document_class()
    doc = document_class()
    for item in paragraphs:
        para = doc.add_paragraph(item.get("text", ""))
        style = item.get("style")
        if style:
            para.style = style
    doc.save(path)
    return path
