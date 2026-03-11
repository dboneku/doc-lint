# Auto-Fix Implementation Reference

How each auto-fixable rule is applied at the python-docx level.

---

## General Pattern

All fixes operate on a `docx.Document` object. After applying fixes, save to a new file:

```python
doc = Document(input_path)
# ... apply fixes ...
output_path = input_path.replace('.docx', '.fixed.docx')
doc.save(output_path)
```

Never overwrite the original unless `--overwrite` is passed explicitly.

---

## W003 — Style Misuse Fix

Reclassify heading-styled paragraphs that are actually body text:

```python
from docx.shared import Pt

for para in doc.paragraphs:
    style = para.style.name
    size  = get_para_size(para)  # first run font size
    if 'Heading 1' in style and size and size <= 12:
        para.style = doc.styles['Normal']
    elif 'Heading 2' in style and size and size <= 10:
        para.style = doc.styles['Normal']
    elif 'Heading 3' in style and size and size <= 9:
        para.style = doc.styles['Normal']
```

---

## W004 — Font Normalization Fix

Normalize body text font family across all runs:

```python
MONOSPACE = {'Courier New', 'Consolas', 'Monaco', 'Courier', 'Lucida Console'}

for para in doc.paragraphs:
    if para.style.name not in ('Normal', 'Normal (Web)', 'Default Paragraph Style'):
        continue
    for run in para.runs:
        if run.font.name and run.font.name not in MONOSPACE:
            run.font.name = target_font  # e.g. 'Calibri'
```

---

## W005 — Font Size Normalization Fix

```python
from docx.shared import Pt

SIZE_MAP = {
    'Title': Pt(20), 'Heading 1': Pt(16), 'Heading 2': Pt(14),
    'Heading 3': Pt(12), 'Normal': Pt(11), 'Normal (Web)': Pt(11),
}

for para in doc.paragraphs:
    target = SIZE_MAP.get(para.style.name)
    if target:
        for run in para.runs:
            run.font.size = target
```

---

## W006 — List Normalization Fix

Change Roman/alphabetic numFmt to decimal in the numbering XML:

```python
from docx.oxml.ns import qn

NON_DECIMAL = {'lowerRoman', 'upperRoman', 'lowerLetter', 'upperLetter'}

try:
    numbering_el = doc.part.numbering_part._element
    for lvl in numbering_el.iter(qn('w:lvl')):
        numFmt = lvl.find(qn('w:numFmt'))
        if numFmt is not None and numFmt.get(qn('w:val')) in NON_DECIMAL:
            numFmt.set(qn('w:val'), 'decimal')
except Exception:
    pass  # no numbering part — nothing to fix
```

---

## W007 — Heading Level Skip Fix

Demote skipped headings to maintain sequential levels:

```python
HEADING_STYLES = ['Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Heading 5']

current_level = 0
for para in doc.paragraphs:
    style = para.style.name
    if style not in HEADING_STYLES:
        current_level = 0
        continue
    level = int(style.split()[-1])
    if level > current_level + 1:
        new_level = current_level + 1
        para.style = doc.styles[f'Heading {new_level}']
        level = new_level
    current_level = level
```

---

## I008 — Single-Item List Fix

Remove list formatting from single-item lists:

```python
from docx.oxml.ns import qn

def get_numid(para):
    pPr = para._element.find(qn('w:pPr'))
    if pPr is None: return None
    numPr = pPr.find(qn('w:numPr'))
    if numPr is None: return None
    numId = numPr.find(qn('w:numId'))
    return numId.get(qn('w:val')) if numId is not None else None

# Group consecutive same-numId paragraphs, fix single-item groups
groups = []
current_id, current_group = None, []
for para in doc.paragraphs:
    nid = get_numid(para)
    if nid and nid != '0':
        if nid == current_id:
            current_group.append(para)
        else:
            if current_group: groups.append((current_id, current_group))
            current_id, current_group = nid, [para]
    else:
        if current_group: groups.append((current_id, current_group))
        current_id, current_group = None, []

for nid, group in groups:
    if len(group) == 1:
        para = group[0]
        pPr = para._element.find(qn('w:pPr'))
        if pPr is not None:
            numPr = pPr.find(qn('w:numPr'))
            if numPr is not None:
                pPr.remove(numPr)
        para.style = doc.styles['Normal']
```

---

## I011 — Multiline Heading Fix

Split paragraphs at `<w:br>` soft line breaks:

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

def split_at_breaks(doc):
    body = doc.element.body
    for para_el in list(body):
        tag = para_el.tag.split('}')[-1] if '}' in para_el.tag else para_el.tag
        if tag != 'p': continue

        # Find all <w:br> positions
        breaks = []
        for r in para_el.findall(qn('w:r')):
            for br in r.findall(qn('w:br')):
                breaks.append((r, br))

        if not breaks: continue

        # Only split heading-sized Normal paragraphs
        # (check style and size via Paragraph wrapper if needed)
        for run_el, br_el in breaks:
            run_el.remove(br_el)
            # Insert a new paragraph after this one with remaining runs
            new_para = OxmlElement('w:p')
            # Copy pPr but set style to Normal
            pPr = para_el.find(qn('w:pPr'))
            if pPr is not None:
                new_pPr = copy.deepcopy(pPr)
                pStyle = new_pPr.find(qn('w:pStyle'))
                if pStyle is not None:
                    pStyle.set(qn('w:val'), 'Normal')
                new_para.insert(0, new_pPr)
            # Move subsequent runs to new paragraph
            found = False
            for child in list(para_el):
                if child == run_el:
                    found = True
                    continue
                if found and child.tag.split('}')[-1] == 'r':
                    para_el.remove(child)
                    new_para.append(child)
            para_el.addnext(new_para)
            break  # one split per paragraph per pass — re-scan if multiple breaks
```

---

## What Cannot Be Auto-Fixed

| Rule | Why |
|---|---|
| E001 Consecutive headings | Requires deciding between adding content or converting to bullet list |
| E002 Empty section | Requires adding content |
| I009 Orphaned bold | Requires deciding whether to promote to heading or keep as emphasis |
| W013 Template compliance | Requires writing the missing section content |
| W014 Naming convention | Requires renaming the file |

These are always flagged in the report but left for the user to resolve manually.

---

## W012 — Numbered Heading Continuity Fix

Renumber headings at each level so manual numbers are continuous:

```python
import re

def fix_numbered_headings(doc, cfg, applied):
    if not cfg.get("numbered-heading-continuity", {}).get("enabled", True):
        return
    HEADING_STYLES = {f"Heading {i}" for i in range(1, 7)}
    NUM_PAT = re.compile(r'^(\d+)\.\s')
    # Collect headings grouped by level
    level_counter = {}   # level -> current expected number
    level_parent  = {}   # level -> text of current parent heading
    fixed = 0
    for para in doc.paragraphs:
        if para.style.name not in HEADING_STYLES:
            # Reset sub-level tracking when non-heading appears
            continue
        level = int(para.style.name.split()[-1])
        text  = para.text.strip()
        m = NUM_PAT.match(text)
        if not m:
            continue
        found_num = int(m.group(1))
        expected  = level_counter.get(level, 0) + 1
        # Reset counters for levels deeper than this one
        for deeper in list(level_counter.keys()):
            if deeper > level:
                del level_counter[deeper]
        if found_num != expected:
            # Rewrite the first run
            new_prefix = f"{expected}. "
            old_prefix = m.group(0)
            for run in para.runs:
                if old_prefix in run.text:
                    run.text = run.text.replace(old_prefix, new_prefix, 1)
                    fixed += 1
                    break
        level_counter[level] = expected
    if fixed:
        applied.append(f"W012: Renumbered {fixed} heading(s) for continuity")
```
