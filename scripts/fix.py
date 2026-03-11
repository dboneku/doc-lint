#!/usr/bin/env python3
"""
doc-lint fixer: Apply auto-fixable formatting corrections to a .docx file.
Usage: python fix.py --file path/to/file.docx [--config .doc-lint.json] [--overwrite]
"""

import sys
import re
import json
import copy
import argparse
from pathlib import Path

try:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt
except ImportError:
    print("ERROR: python-docx not installed. Run: pip install python-docx")
    sys.exit(1)

MONOSPACE   = {'Courier New', 'Consolas', 'Monaco', 'Courier', 'Lucida Console'}
NON_DECIMAL = {'lowerRoman', 'upperRoman', 'lowerLetter', 'upperLetter'}
DEFAULT_CONFIG = {
    "rules": {
        "style-misuse":            {"enabled": True},
        "font-normalization":      {"enabled": True, "target-font": "Calibri"},
        "font-size-normalization": {"enabled": True, "sizes": {"h1": 20, "h2": 16, "h3": 14, "h4": 12, "body": 11}},
        "list-normalization":      {"enabled": True},
        "heading-level-skip":      {"enabled": True},
        "single-item-list":        {"enabled": True},
        "mixed-fonts":             {"enabled": True},
        "multiline-heading":       {"enabled": True},
        "numbered-heading-continuity": {"enabled": True},
    }
}


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path and Path(path).exists():
        with open(path) as f:
            user = json.load(f)
        for rule, settings in user.get("rules", {}).items():
            if rule in cfg["rules"]:
                cfg["rules"][rule].update(settings)
    return cfg


def rule_enabled(cfg, rule):
    return cfg["rules"].get(rule, {}).get("enabled", True)


def get_para_size(para):
    for run in para.runs:
        if run.font.size:
            return run.font.size.pt
    try:
        sz = para.style.font.size
        if sz:
            return sz.pt
    except Exception:
        pass
    return None


def get_numpr(pPr):
    if pPr is None:
        return None, None
    numPr = pPr.find(qn('w:numPr'))
    if numPr is None:
        return None, None
    ilvl_el  = numPr.find(qn('w:ilvl'))
    numid_el = numPr.find(qn('w:numId'))
    numid = numid_el.get(qn('w:val')) if numid_el is not None else None
    return numid, int(ilvl_el.get(qn('w:val'))) if ilvl_el is not None else 0


def fix_style_misuse(doc, cfg, applied):
    """W003 — Reclassify heading-styled body paragraphs as Normal."""
    if not rule_enabled(cfg, 'style-misuse'):
        return
    count = 0
    for para in doc.paragraphs:
        style = para.style.name
        size  = get_para_size(para)
        thresholds = {'Heading 1': 12, 'Heading 2': 10, 'Heading 3': 9}
        for h, thresh in thresholds.items():
            if h in style and size and size <= thresh:
                para.style = doc.styles['Normal']
                count += 1
                break
    if count:
        applied.append(f"W003: Reclassified {count} misused heading paragraph(s) as Normal")


def fix_font_normalization(doc, cfg, applied):
    """W004 — Normalize body text font family."""
    if not rule_enabled(cfg, 'font-normalization'):
        return
    target = cfg["rules"]["font-normalization"].get("target-font", "Calibri")
    count = 0
    for para in doc.paragraphs:
        if para.style.name not in ('Normal', 'Normal (Web)', 'Default Paragraph Style'):
            continue
        for run in para.runs:
            if run.font.name and run.font.name not in MONOSPACE and run.font.name != target:
                run.font.name = target
                count += 1
    if count:
        applied.append(f"W004: Normalized {count} run(s) to {target}")


def fix_font_size(doc, cfg, applied):
    """W005 — Normalize font sizes to standard scale."""
    if not rule_enabled(cfg, 'font-size-normalization'):
        return
    sizes = cfg["rules"]["font-size-normalization"].get("sizes", {})
    size_map = {
        'Heading 1': sizes.get('h1', 16),
        'Heading 2': sizes.get('h2', 14),
        'Heading 3': sizes.get('h3', 12),
        'Heading 4': sizes.get('h4', 12),
        'Normal':    sizes.get('body', 11),
        'Normal (Web)': sizes.get('body', 11),
    }
    count = 0
    for para in doc.paragraphs:
        target = next((v for k, v in size_map.items() if k in para.style.name), None)
        if target:
            for run in para.runs:
                if run.font.size and run.font.size.pt != target:
                    run.font.size = Pt(target)
                    count += 1
    if count:
        applied.append(f"W005: Normalized {count} run(s) to standard font sizes")


def fix_list_normalization(doc, cfg, applied):
    """W006 — Convert Roman/alphabetic ordered lists to decimal."""
    if not rule_enabled(cfg, 'list-normalization'):
        return
    count = 0
    try:
        numbering_el = doc.part.numbering_part._element
        for lvl in numbering_el.iter(qn('w:lvl')):
            el = lvl.find(qn('w:numFmt'))
            if el is not None and el.get(qn('w:val')) in NON_DECIMAL:
                el.set(qn('w:val'), 'decimal')
                count += 1
    except Exception:
        pass
    if count:
        applied.append(f"W006: Normalized {count} list level(s) to decimal numbering")


def fix_heading_level_skip(doc, cfg, applied):
    """W007 — Demote heading level skips to maintain sequential levels."""
    if not rule_enabled(cfg, 'heading-level-skip'):
        return
    current = 0
    count = 0
    for para in doc.paragraphs:
        style = para.style.name
        level = None
        for i in range(1, 7):
            if f'Heading {i}' in style:
                level = i
                break
        if level is None:
            current = 0
            continue
        if current > 0 and level > current + 1:
            new_level = current + 1
            try:
                para.style = doc.styles[f'Heading {new_level}']
                count += 1
                level = new_level
            except Exception:
                pass
        current = level
    if count:
        applied.append(f"W007: Fixed {count} heading level skip(s)")


def fix_single_item_lists(doc, cfg, applied):
    """I008 — Convert single-item lists to plain paragraphs."""
    if not rule_enabled(cfg, 'single-item-list'):
        return
    groups = {}
    paras  = list(doc.paragraphs)
    for para in paras:
        pPr = para._element.find(qn('w:pPr'))
        numid, _ = get_numpr(pPr)
        if numid and numid != '0':
            groups.setdefault(numid, []).append(para)

    count = 0
    for numid, group in groups.items():
        if len(group) == 1:
            para = group[0]
            pPr  = para._element.find(qn('w:pPr'))
            if pPr is not None:
                numPr = pPr.find(qn('w:numPr'))
                if numPr is not None:
                    pPr.remove(numPr)
            para.style = doc.styles['Normal']
            count += 1
    if count:
        applied.append(f"I008: Converted {count} single-item list(s) to paragraph(s)")


def fix_multiline_headings(doc, cfg, applied):
    """I011 — Split multiline heading paragraphs at <w:br> soft breaks."""
    if not rule_enabled(cfg, 'multiline-heading'):
        return
    body  = doc.element.body
    count = 0
    for para_el in list(body):
        tag = para_el.tag.split('}')[-1] if '}' in para_el.tag else para_el.tag
        if tag != 'p':
            continue
        # Find runs with <w:br>
        split_run = None
        split_br  = None
        for r in para_el.findall(qn('w:r')):
            for br in r.findall(qn('w:br')):
                split_run = r
                split_br  = br
                break
            if split_run is not None:
                break
        if split_run is None:
            continue

        # Remove the <w:br>
        split_run.remove(split_br)

        # Build new paragraph for content after the break
        new_para = OxmlElement('w:p')
        pPr = para_el.find(qn('w:pPr'))
        if pPr is not None:
            new_pPr = copy.deepcopy(pPr)
            pStyle  = new_pPr.find(qn('w:pStyle'))
            if pStyle is not None:
                pStyle.set(qn('w:val'), 'Normal')
            new_para.insert(0, new_pPr)

        # Move runs after the split run to new paragraph
        after = False
        for child in list(para_el):
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if child == split_run:
                after = True
                continue
            if after and child_tag == 'r':
                para_el.remove(child)
                new_para.append(child)

        para_el.addnext(new_para)
        count += 1

    if count:
        applied.append(f"I011: Split {count} multiline heading paragraph(s) at line breaks")


def fix_numbered_headings(doc, cfg, applied):
    """W012 — Renumber headings where manual numbering restarts mid-document at the same level."""
    if not rule_enabled(cfg, 'numbered-heading-continuity'):
        return
    numbered_pat = re.compile(r'^(\d+)\.\s')
    counters = {}  # hlevel -> current sequential count
    count = 0
    for para in doc.paragraphs:
        style = para.style.name
        hlevel = None
        for i in range(1, 7):
            if f'Heading {i}' in style:
                hlevel = i
                break
        if hlevel is None:
            continue
        # Reset sub-level counters when a higher heading is encountered
        for k in list(counters.keys()):
            if k > hlevel:
                del counters[k]
        m = numbered_pat.match(para.text.strip())
        if not m:
            continue
        original_num = int(m.group(1))
        expected_num = counters.get(hlevel, 0) + 1
        counters[hlevel] = expected_num
        if original_num != expected_num:
            old_prefix = f"{original_num}. "
            new_prefix = f"{expected_num}. "
            if para.runs and para.runs[0].text.startswith(old_prefix):
                para.runs[0].text = new_prefix + para.runs[0].text[len(old_prefix):]
                count += 1
    if count:
        applied.append(f"W012: Renumbered {count} heading(s) to restore sequential continuity")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Auto-fix formatting issues in a .docx file")
    parser.add_argument("--file",      required=True,  help="Path to .docx file")
    parser.add_argument("--config",    default=".doc-lint.json", help="Config file path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite original file")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    cfg     = load_config(args.config)
    doc     = Document(str(path))
    applied = []

    fix_style_misuse(doc, cfg, applied)
    fix_font_normalization(doc, cfg, applied)
    fix_font_size(doc, cfg, applied)
    fix_list_normalization(doc, cfg, applied)
    fix_heading_level_skip(doc, cfg, applied)
    fix_single_item_lists(doc, cfg, applied)
    fix_multiline_headings(doc, cfg, applied)
    fix_numbered_headings(doc, cfg, applied)

    out = path if args.overwrite else path.with_suffix('').with_suffix('').parent / (path.stem + '.fixed.docx')
    doc.save(str(out))

    print(f"\nFixed: {out}")
    if applied:
        for a in applied:
            print(f"  ✓  {a}")
    else:
        print("  No auto-fixable issues found.")
    print(f"\nRun /doc-lint:check {out} to verify.")


if __name__ == "__main__":
    main()
