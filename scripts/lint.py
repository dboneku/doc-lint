#!/usr/bin/env python3
"""
doc-lint: Lint .docx files for formatting and structural issues.
Usage: python lint.py --file path/to/file.docx [--config .doc-lint.json] [--json]
"""

import sys
import re
import json
import argparse
from pathlib import Path

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    print("ERROR: python-docx not installed. Run: pip install python-docx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "rules": {
        "consecutive-headings": {"enabled": True, "severity": "error", "max": 2},
        "empty-section":        {"enabled": True, "severity": "error"},
        "style-misuse":         {"enabled": True, "severity": "warning"},
        "font-normalization":   {"enabled": True, "severity": "warning", "target-font": "Calibri"},
        "font-size-normalization": {
            "enabled": True, "severity": "warning",
            "sizes": {"h1": 20, "h2": 16, "h3": 14, "h4": 12, "body": 11}
        },
        "list-normalization":   {"enabled": True, "severity": "warning"},
        "heading-level-skip":   {"enabled": True, "severity": "warning"},
        "single-item-list":     {"enabled": True, "severity": "info"},
        "orphaned-bold":        {"enabled": True, "severity": "info"},
        "mixed-fonts":          {"enabled": True, "severity": "info"},
        "multiline-heading":    {"enabled": True, "severity": "info"},
        "numbered-heading-continuity": {"enabled": True, "severity": "warning"},
        "template-compliance": {"enabled": True, "severity": "warning"},
        "naming-convention":   {"enabled": True, "severity": "warning"},
    }
}

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
SEVERITY_SYMBOL = {"error": "✖", "warning": "⚠", "info": "ℹ"}
AUTO_FIXABLE = {
    "style-misuse", "font-normalization", "font-size-normalization",
    "list-normalization", "heading-level-skip", "single-item-list",
    "mixed-fonts", "multiline-heading", "numbered-heading-continuity"
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_template(text: str) -> str:
    """Infer document template type from plain text content."""
    t = text.lower()
    if any(k in t for k in ['annex a', 'iso 27001', '27001', 'isms']):
        return 'iso27001'
    if sum(1 for k in ['purpose', 'scope', 'policy statement', 'shall'] if k in t) >= 3:
        return 'policy'
    if sum(1 for k in ['steps', 'procedure', 'prerequisites'] if k in t) >= 2:
        return 'procedure'
    if sum(1 for k in ['attendees', 'agenda', 'action items', 'decisions'] if k in t) >= 2:
        return 'meeting_minutes'
    if sum(1 for k in ['trigger', 'flow steps', 'decision points'] if k in t) >= 2:
        return 'workflow'
    if t.count('\u2610') >= 5:
        return 'checklist'
    if t.count('\u2610') >= 3 or '___' in t:
        return 'form'
    return 'general'


_REQUIRED_SECTIONS = {
    'policy': [
        'Purpose', 'Scope', 'Definitions', 'Roles and Responsibilities',
        'Policy Statements', 'Compliance and Exceptions', 'Related Documents', 'Revision History',
    ],
    'procedure': [
        'Purpose', 'Scope', 'Prerequisites', 'Procedure Steps',
        'Exceptions and Escalations', 'Related Documents', 'Revision History',
    ],
    'workflow': [
        'Purpose', 'Trigger', 'Roles Involved', 'Flow Steps',
        'Decision Points', 'Outcomes', 'Related Documents',
    ],
    'form':          ['Instructions', 'Fields', 'Submission Guidance'],
    'checklist':     ['Instructions', 'Checklist Items', 'Completion'],
    'meeting_minutes': ['Attendees', 'Agenda', 'Decisions', 'Action Items'],
    'iso27001': [
        'Purpose', 'Scope', 'Definitions', 'Roles and Responsibilities',
        'Policy Statements', 'Control Mapping', 'Compliance and Exceptions',
        'Related Documents', 'Revision History',
    ],
}

_NAMING_PATTERNS = {
    'policy':          (re.compile(r'^[A-Z]+-POL-\d+[\s\-].+', re.I), 'ORG-POL-001 Title'),
    'procedure':       (re.compile(r'^[A-Z]+-PRO-\d+[\s\-].+', re.I), 'ORG-PRO-001 Title'),
    'workflow':        (re.compile(r'^[A-Z]+-WF-\d+[\s\-].+',  re.I), 'ORG-WF-001 Title'),
    'form':            (re.compile(r'^[A-Z]+-FRM-\d+[\s\-].+', re.I), 'ORG-FRM-001 Title'),
    'checklist':       (re.compile(r'^[A-Z]+-CHK-\d+[\s\-].+', re.I), 'ORG-CHK-001 Title'),
    'meeting_minutes': (re.compile(r'^\d{4}-\d{2}-\d{2}.+',    re.I), '2026-01-01 Team Meeting Minutes'),
    'iso27001':        (re.compile(r'^[A-Z]+-\d+[\s\-].+',     re.I), 'ORG-001-DOMAIN Title (Type)'),
}

def load_config(config_path):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            user = json.load(f)
        for rule, settings in user.get("rules", {}).items():
            if rule in cfg["rules"]:
                cfg["rules"][rule].update(settings)
    return cfg


def rule_enabled(cfg, rule):
    return cfg["rules"].get(rule, {}).get("enabled", True)


def rule_severity(cfg, rule):
    return cfg["rules"].get(rule, {}).get("severity", "warning")


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


def get_num_type_map(doc):
    try:
        numbering_el = doc.part.numbering_part._element
    except Exception:
        return {}
    abstract_nums = {}
    for an in numbering_el.findall(qn('w:abstractNum')):
        an_id = an.get(qn('w:abstractNumId'))
        for lvl in an.findall(qn('w:lvl')):
            if lvl.get(qn('w:ilvl')) == '0':
                el = lvl.find(qn('w:numFmt'))
                if el is not None:
                    abstract_nums[an_id] = el.get(qn('w:val'), 'bullet')
                break
    num_map = {}
    for num in numbering_el.findall(qn('w:num')):
        nid = num.get(qn('w:numId'))
        ref = num.find(qn('w:abstractNumId'))
        if ref is not None:
            num_map[nid] = abstract_nums.get(ref.get(qn('w:val')), 'bullet')
    return num_map


def heading_style_level(style_name):
    """Return heading level from style name, or None."""
    if style_name == 'Title':
        return 0
    for i in range(1, 7):
        if f'Heading {i}' in style_name:
            return i
    return None


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

def lint(path, cfg):
    doc    = Document(path)
    issues = []
    num_map = get_num_type_map(doc)

    MONOSPACE = {'Courier New', 'Consolas', 'Monaco', 'Courier', 'Lucida Console'}
    NON_DECIMAL = {'lowerRoman', 'upperRoman', 'lowerLetter', 'upperLetter'}

    paras = [p for p in doc.paragraphs if p.text.strip()]
    body_fonts = set()
    consec_count = 0
    prev_was_heading = False
    current_heading_level = 0
    list_groups = {}   # numid -> list of para indices
    para_idx = 0

    for idx, para in enumerate(paras):
        style      = para.style.name
        size       = get_para_size(para)
        pPr        = para._element.find(qn('w:pPr'))
        numid, _   = get_numpr(pPr)
        hlevel     = heading_style_level(style)
        is_list    = numid and numid != '0'
        is_heading = hlevel is not None and not is_list

        # Collect body fonts
        if style in ('Normal', 'Normal (Web)', 'Default Paragraph Style'):
            for run in para.runs:
                if run.font.name and run.font.name not in MONOSPACE:
                    body_fonts.add(run.font.name)

        # --- W003 Style misuse ---
        if rule_enabled(cfg, 'style-misuse') and is_heading and hlevel and hlevel >= 1:
            thresholds = {1: 12, 2: 10, 3: 9}
            thresh = thresholds.get(hlevel)
            if thresh and size and size <= thresh:
                issues.append({
                    "rule": "style-misuse", "code": "W003",
                    "severity": rule_severity(cfg, 'style-misuse'),
                    "message": f'"Heading {hlevel}" style used at {size}pt (body-text size) — reclassify as Normal',
                    "line": idx + 1, "text": para.text[:60], "fixable": True
                })
                is_heading = False  # treat as body for further checks

        # --- E001 Consecutive headings ---
        if rule_enabled(cfg, 'consecutive-headings'):
            max_consec = cfg["rules"]["consecutive-headings"].get("max", 2)
            if is_heading:
                consec_count += 1
                if consec_count > max_consec:
                    issues.append({
                        "rule": "consecutive-headings", "code": "E001",
                        "severity": rule_severity(cfg, 'consecutive-headings'),
                        "message": f'Heading #{consec_count} in a row with no body content: "{para.text[:50]}"',
                        "line": idx + 1, "text": para.text[:60], "fixable": False
                    })
            else:
                consec_count = 0

        # --- E002 Empty section ---
        if rule_enabled(cfg, 'empty-section') and prev_was_heading and is_heading:
            issues.append({
                "rule": "empty-section", "code": "E002",
                "severity": rule_severity(cfg, 'empty-section'),
                "message": f'Empty section: heading immediately followed by another heading',
                "line": idx + 1, "text": para.text[:60], "fixable": False
            })

        # --- W007 Heading level skip ---
        if rule_enabled(cfg, 'heading-level-skip') and is_heading and hlevel:
            if hlevel > current_heading_level + 1 and current_heading_level > 0:
                issues.append({
                    "rule": "heading-level-skip", "code": "W007",
                    "severity": rule_severity(cfg, 'heading-level-skip'),
                    "message": f'Heading level skip: H{current_heading_level} → H{hlevel} (missing H{current_heading_level + 1})',
                    "line": idx + 1, "text": para.text[:60], "fixable": True
                })
            if hlevel:
                current_heading_level = hlevel

        # --- W005 Font size normalization ---
        if rule_enabled(cfg, 'font-size-normalization') and size:
            sizes = cfg["rules"]["font-size-normalization"].get("sizes", {})
            expected = None
            if 'Heading 1' in style: expected = sizes.get('h1')
            elif 'Heading 2' in style: expected = sizes.get('h2')
            elif 'Heading 3' in style: expected = sizes.get('h3')
            elif 'Heading 4' in style: expected = sizes.get('h4')
            elif style in ('Normal', 'Normal (Web)'): expected = sizes.get('body')
            if expected and size != expected:
                issues.append({
                    "rule": "font-size-normalization", "code": "W005",
                    "severity": rule_severity(cfg, 'font-size-normalization'),
                    "message": f'Non-standard size: {size}pt (expected {expected}pt for {style})',
                    "line": idx + 1, "text": para.text[:60], "fixable": True
                })

        # --- I008 Single-item list (group tracking) ---
        if is_list:
            list_groups.setdefault(numid, []).append(idx)

        # --- I009 Orphaned bold ---
        if rule_enabled(cfg, 'orphaned-bold') and not is_heading and not is_list:
            if para.runs and all(r.bold for r in para.runs if r.text.strip()):
                if len(para.text) <= 80:
                    issues.append({
                        "rule": "orphaned-bold", "code": "I009",
                        "severity": rule_severity(cfg, 'orphaned-bold'),
                        "message": f'Fully bold short paragraph — possible heading: "{para.text[:50]}"',
                        "line": idx + 1, "text": para.text[:60], "fixable": False
                    })

        # --- I011 Multiline heading ---
        if rule_enabled(cfg, 'multiline-heading'):
            has_br = any(
                child.tag.split('}')[-1] == 'br'
                for r in para._element.findall(qn('w:r'))
                for child in r
            )
            if has_br and (is_heading or (style in ('Normal', 'Normal (Web)') and size and size >= 13)):
                issues.append({
                    "rule": "multiline-heading", "code": "I011",
                    "severity": rule_severity(cfg, 'multiline-heading'),
                    "message": f'Multiline heading paragraph — split section title from body text',
                    "line": idx + 1, "text": para.text[:60], "fixable": True
                })

        # --- W004 Font normalization (per-paragraph) ---
        if rule_enabled(cfg, 'font-normalization') and style in ('Normal', 'Normal (Web)', 'Default Paragraph Style'):
            target = cfg["rules"]["font-normalization"].get("target-font", "Calibri")
            for run in para.runs:
                if run.font.name and run.font.name not in MONOSPACE and run.font.name != target:
                    issues.append({
                        "rule": "font-normalization", "code": "W004",
                        "severity": rule_severity(cfg, 'font-normalization'),
                        "message": f'Non-standard font: "{run.font.name}" (expected "{target}")',
                        "line": idx + 1, "text": para.text[:60], "fixable": True
                    })
                    break  # one issue per paragraph

        prev_was_heading = is_heading

    # --- I008 Single-item list (emit after full scan) ---
    if rule_enabled(cfg, 'single-item-list'):
        for numid, idxs in list_groups.items():
            if len(idxs) == 1:
                para = paras[idxs[0]]
                issues.append({
                    "rule": "single-item-list", "code": "I008",
                    "severity": rule_severity(cfg, 'single-item-list'),
                    "message": f'Single-item list — convert to paragraph',
                    "line": idxs[0] + 1, "text": para.text[:60], "fixable": True
                })

    # --- W006 List normalization ---
    if rule_enabled(cfg, 'list-normalization'):
        try:
            numbering_el = doc.part.numbering_part._element
            for an in numbering_el.findall(qn('w:abstractNum')):
                for lvl in an.findall(qn('w:lvl')):
                    el = lvl.find(qn('w:numFmt'))
                    if el is not None and el.get(qn('w:val')) in NON_DECIMAL:
                        issues.append({
                            "rule": "list-normalization", "code": "W006",
                            "severity": rule_severity(cfg, 'list-normalization'),
                            "message": f'Non-decimal ordered list format: "{el.get(qn("w:val"))}" — normalize to Arabic numerals',
                            "line": None, "text": "", "fixable": True
                        })
                        break
        except Exception:
            pass

    # --- I010 Mixed fonts ---
    if rule_enabled(cfg, 'mixed-fonts') and len(body_fonts) > 1:
        issues.append({
            "rule": "mixed-fonts", "code": "I010",
            "severity": rule_severity(cfg, 'mixed-fonts'),
            "message": f'Mixed fonts in body text: {", ".join(sorted(body_fonts))}',
            "line": None, "text": "", "fixable": True
        })

    # --- W012 Numbered heading continuity ---
    if rule_enabled(cfg, 'numbered-heading-continuity'):
        numbered_pat = re.compile(r'^(\d+)\.')
        level_seqs = {}  # hlevel -> [(para_idx, number)]
        for idx, para in enumerate(paras):
            hlevel = heading_style_level(para.style.name)
            if hlevel is None:
                continue
            m = numbered_pat.match(para.text.strip())
            if m:
                level_seqs.setdefault(hlevel, []).append((idx, int(m.group(1))))
        for hlevel, seq in level_seqs.items():
            if len(seq) < 2:
                continue
            for i in range(1, len(seq)):
                prev_num = seq[i - 1][1]
                curr_num, curr_idx = seq[i][1], seq[i][0]
                if curr_num <= prev_num and curr_num == 1:
                    issues.append({
                        "rule": "numbered-heading-continuity", "code": "W012",
                        "severity": rule_severity(cfg, 'numbered-heading-continuity'),
                        "message": (
                            f'Heading numbering restarts at H{hlevel}: '
                            f'"{paras[curr_idx].text.strip()[:50]}" '
                            f'(expected >{prev_num})'
                        ),
                        "line": curr_idx + 1, "text": paras[curr_idx].text[:60], "fixable": True
                    })

    # --- W013 Template compliance ---
    if rule_enabled(cfg, 'template-compliance'):
        full_text = ' '.join(p.text for p in paras)
        template  = _detect_template(full_text)
        required  = _REQUIRED_SECTIONS.get(template, [])
        if required:
            heading_texts = {
                p.text.lower().strip()
                for p in paras
                if heading_style_level(p.style.name) is not None
            }
            missing = [s for s in required if s.lower() not in heading_texts]
            if missing:
                issues.append({
                    "rule": "template-compliance", "code": "W013",
                    "severity": rule_severity(cfg, 'template-compliance'),
                    "message": (
                        f'Template "{template}": missing required section(s): '
                        f'{", ".join(missing)}'
                    ),
                    "line": None, "text": "", "fixable": False
                })

    # --- W014 Naming convention ---
    if rule_enabled(cfg, 'naming-convention'):
        full_text = ' '.join(p.text for p in paras)
        template  = _detect_template(full_text)
        if template in _NAMING_PATTERNS:
            pattern, example = _NAMING_PATTERNS[template]
            stem = Path(path).stem
            if not pattern.match(stem):
                issues.append({
                    "rule": "naming-convention", "code": "W014",
                    "severity": rule_severity(cfg, 'naming-convention'),
                    "message": (
                        f'Filename "{stem}" does not match {template} naming convention '
                        f'(expected: {example})'
                    ),
                    "line": None, "text": "", "fixable": False
                })

    issues.sort(key=lambda x: SEVERITY_ORDER.get(x["severity"], 9))
    return issues


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_report(path, issues, as_json=False):
    fixable = sum(1 for i in issues if i.get("fixable"))
    manual  = len(issues) - fixable
    errors   = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    infos    = sum(1 for i in issues if i["severity"] == "info")

    if as_json:
        print(json.dumps({"file": str(path), "issues": issues,
                          "summary": {"total": len(issues), "errors": errors,
                                      "warnings": warnings, "info": infos,
                                      "fixable": fixable}}))
        return

    print(f"\ndoc-lint: {path}")
    print("═" * 60)
    if not issues:
        print("  ✓  No issues found.")
    for issue in issues:
        sym  = SEVERITY_SYMBOL.get(issue["severity"], "?")
        loc  = f"line {issue['line']} — " if issue.get("line") else ""
        fix  = " [auto-fixable]" if issue.get("fixable") else " [manual]"
        print(f"  {sym}  [{issue['code']}] {loc}{issue['message']}{fix}")
    print("─" * 60)
    print(f"  {len(issues)} issue{'s' if len(issues) != 1 else ''} "
          f"({errors}E {warnings}W {infos}I)  │  "
          f"{fixable} auto-fixable, {manual} manual")
    if fixable:
        stem = Path(path).stem
        print(f"\n  Run: /doc-lint:fix {path}")
    print("═" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Lint a .docx file for formatting issues")
    parser.add_argument("--file",   required=True, help="Path to .docx file")
    parser.add_argument("--config", default=".doc-lint.json", help="Config file path")
    parser.add_argument("--json",   action="store_true", help="Output JSON instead of human-readable")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    if path.suffix.lower() != ".docx":
        print(f"ERROR: Only .docx files are supported (got {path.suffix})")
        sys.exit(1)

    cfg    = load_config(args.config)
    issues = lint(path, cfg)
    print_report(path, issues, as_json=args.json)
    sys.exit(1 if any(i["severity"] == "error" for i in issues) else 0)


if __name__ == "__main__":
    main()
