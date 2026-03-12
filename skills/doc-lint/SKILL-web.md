---
name: doc-lint-web
description: Use this skill when the user uploads a .docx file and asks to "lint", "check formatting", "review this document", "standardize", "find formatting issues", "check my Word doc", "clean up this document", "enforce style standards", or mentions finding formatting inconsistencies in a Word file — and the user is NOT running Claude Code CLI. This skill applies doc-lint rules directly from document content without requiring Python scripts.
version: 0.1.0
---

# doc-lint Web Skill

Analyze an uploaded `.docx` file (or pasted document text) for formatting and structural problems using the doc-lint rule set. Report issues in the standard doc-lint format. Provide fix recommendations for all auto-fixable issues.

This skill works in Claude.ai, Claude coworker, Claude Projects, and any context where Python scripts cannot be executed. For local file auto-fixing with full formatting metadata, see the [Claude Code CLI plugin](../SKILL.md).

---

## What this skill can and cannot detect

Because this skill reads document content rather than running `lint.py` against the underlying XML, detection capability varies by rule:

| Code | Rule | Web detection |
|---|---|---|
| E001 | Consecutive headings | ✅ Full — detectable from structure |
| E002 | Empty section | ✅ Full — detectable from structure |
| W003 | Style misuse | ⚠ Partial — detectable when heading text is clearly body-sized |
| W004 | Font normalization | ⚠ Partial — requires user to describe or visible font info in upload |
| W005 | Font size normalization | ⚠ Partial — requires user to describe or visible size info in upload |
| W006 | List normalization (Roman/alpha) | ✅ Full — visible in list text |
| W007 | Heading level skip | ✅ Full — detectable from heading hierarchy |
| I008 | Single-item list | ✅ Full — detectable from structure |
| I009 | Orphaned bold | ✅ Full — visible in content |
| I010 | Mixed fonts | ⚠ Partial — only when font info visible |
| I011 | Multiline heading | ⚠ Partial — sometimes visible in content |
| W012 | Numbered heading continuity | ✅ Full — detectable from heading text |
| W013 | Template compliance | ✅ Full — detectable from section headings |
| W014 | Naming convention | ✅ Full — detectable from filename |

When a formatting-level rule (W003, W004, W005, W010, I011) cannot be assessed from content alone, tell the user and recommend running the CLI plugin for accurate detection.

---

## Step 1 — Receive the document

Accept input in any of these forms:

- **Uploaded `.docx` file** — Claude reads the extracted content directly
- **Pasted document text** — user pastes the text content
- **Described document** — user describes the structure and asks for a check

Ask for the **filename** if it is not already known (needed for W014 naming convention check).

If the user provides a `.doc-lint.json` config file or pastes its contents, apply those rule customizations. Otherwise use all defaults from `references/rules.md`.

---

## Step 2 — Build the document outline

Before checking rules, reconstruct the document structure from the content:

1. Identify all heading paragraphs (Heading 1 through Heading 6) in document order
2. Identify all body paragraphs (Normal style or equivalent)
3. Identify all lists (bulleted and numbered), including their item counts and numbering format
4. Note the filename

Use this outline to drive all rule checks in Step 3.

---

## Step 3 — Apply rules

Work through each enabled rule in order. For each rule, determine pass/fail from the document outline and content.

### E001 — Consecutive Headings

Walk heading paragraphs in document order. Count consecutive headings with no body paragraph between them. Flag any run that exceeds the threshold (default: 2).

```
✖ [E001] Consecutive headings: 4 in a row at lines 12–15 (no body content between them)
         Fix: add body content under each heading, or restructure as a bulleted list
```

### E002 — Empty Section

Flag any heading that is immediately followed by another heading with zero body paragraphs between them (single-heading case of E001).

```
✖ [E002] Empty section: "3. Policy Statement" at line 22 has no body content before the next heading
         Fix: add content under this heading or remove it
```

### W003 — Style Misuse

Flag any paragraph that appears to use a heading style (Heading 1/2/3) but whose text is clearly body-length or body-sized. If font size information is visible in the upload, apply the size thresholds from `references/rules.md`. If not visible, note the limitation.

```
⚠ [W003] Style misuse: paragraph at line 8 uses Heading 1 style but text appears body-sized
          Fix: change style to Normal, or increase font size to ≥ 13pt
          Note: accurate detection requires the Claude Code CLI plugin (reads font metadata)
```

### W004 — Font Normalization

If font information is visible in the uploaded content, flag body paragraphs using non-standard fonts. Otherwise note the limitation and recommend CLI.

```
⚠ [W004] Font normalization: body text at lines 14–18 uses Times New Roman (expected Calibri)
          Fix: select affected text and change font to Calibri
          Note: accurate detection requires the Claude Code CLI plugin
```

### W005 — Font Size Normalization

If font size information is visible, flag mismatches against standard sizes (H1: 20pt, H2: 16pt, H3: 14pt, H4: 12pt, body: 11pt). Otherwise note the limitation.

```
⚠ [W005] Font size: "Introduction" heading at line 5 appears to use a non-standard size
          Fix: set Heading 1 font size to 20pt
          Note: accurate detection requires the Claude Code CLI plugin
```

### W006 — List Normalization

Scan all ordered list items. Flag any list where the numbering uses Roman numerals (I, II, III, IV) or letters (a, b, c, A, B, C) instead of Arabic numerals (1, 2, 3).

```
⚠ [W006] Non-standard list: Roman numeral ordered list at lines 34–38 (I. II. III.)
          Fix: change list numbering format to Arabic numerals (1. 2. 3.)
```

### W007 — Heading Level Skip

Walk headings in order. Flag any heading where the level increases by more than 1 from the previous heading (e.g. H1 → H3 with no H2).

```
⚠ [W007] Heading level skip: "1.3 Details" (H3) at line 41 follows "1. Overview" (H1) — H2 missing
          Fix: insert an H2 heading before line 41, or change this heading to H2
```

### I008 — Single-Item List

Flag any bulleted or numbered list that contains exactly one item.

```
ℹ [I008] Single-item list at line 67 — consider converting to a plain paragraph
          Fix: remove list formatting and use Normal paragraph style
```

### I009 — Orphaned Bold

Flag any short paragraph (≤ 80 characters) where all text is bold and the paragraph uses a Normal/body style. This likely should be a heading.

```
ℹ [I009] Orphaned bold at line 71: "Key Responsibilities" — entire paragraph is bold
          Consider: promote to a heading style (e.g. Heading 3) for proper document structure
```

### I010 — Mixed Fonts

If font information is available, flag body text that uses more than one font family (excluding monospace/code fonts).

```
ℹ [I010] Mixed fonts: body text uses Calibri and Times New Roman — standardize to one font
          Fix: select all body text and apply uniform font (recommend Calibri)
          Note: accurate detection requires the Claude Code CLI plugin
```

### I011 — Multiline Heading

Flag any heading that appears to contain body text after a line break (text that should be a separate Normal paragraph).

```
ℹ [I011] Multiline heading at line 12: heading text continues with body content after a line break
          Fix: split into two paragraphs — heading text, then Normal paragraph
```

### W012 — Numbered Heading Continuity

Scan heading text for a leading manual number pattern (`^\d+\.` or `^\d+\.\d+`). For each heading level that uses manual numbers, track the expected next number. Flag any heading where the number resets or skips backward.

Do not flag hierarchical sub-numbering that correctly resets per parent (1.1 → 2.1 is correct).

```
⚠ [W012] Numbered heading continuity: "1. Compliance" at line 88 restarts sequence (expected 4)
          Fix: renumber to "4. Compliance" and update all following headings at this level
```

### W013 — Template Compliance

Auto-detect the document's template from keyword scoring across all heading and body text. Compare headings found against the required sections list for that template from `references/rules.md`.

```
⚠ [W013] Template compliance (Policy): missing required sections — Compliance, Revision History
          Required: Purpose ✔, Scope ✔, Policy Statement ✔, Compliance ✖, Revision History ✖
          Fix: add the missing sections with appropriate content
```

### W014 — Naming Convention

Check the filename against the expected pattern for the detected template. Patterns are defined in `references/rules.md`.

```
⚠ [W014] Naming convention: "HR-Policy.docx" does not match Policy pattern
          Expected pattern: ORG-POL-NNN Title  (e.g. ACME-POL-001 HR Policy)
          Fix: rename the file to match the naming convention
```

---

## Step 4 — Report

Print the full report before offering any fixes. Use the standard doc-lint format:

```
doc-lint: HR-Policy.docx
══════════════════════════════════════════════════════
  ✖  [E001] Consecutive headings: 4 in a row at lines 12–15 (no body content)
  ✖  [E002] Empty section: "3. Policy Statement" at line 22 has no body content
  ⚠  [W006] Non-standard list: Roman numeral ordered list at lines 34–38
  ⚠  [W007] Heading level skip: H1 → H3 at line 41 (no H2)
  ⚠  [W012] Numbered heading continuity: "1. Compliance" at line 88 restarts (expected 4)
  ⚠  [W013] Template compliance (Policy): missing — Compliance, Revision History
  ⚠  [W014] Naming convention: "HR-Policy.docx" doesn't match Policy pattern
  ℹ  [I008] Single-item list at line 67
  ℹ  [I009] Orphaned bold at line 71: "Key Responsibilities"
──────────────────────────────────────────────────────
  9 issues  (2 errors, 5 warnings, 2 info)
  Fixable via document edits: W006, W007, W012, I008, I009
  Requires content: E001, E002, W013
  Requires file rename: W014
  Formatting rules (W003, W004, W005, I010): use Claude Code CLI for accurate detection
══════════════════════════════════════════════════════
```

---

## Step 5 — Fix guidance

After the report, offer fix guidance. Since this skill cannot write files, provide clear instructions the user can follow in Word, or offer to produce a corrected plain-text outline.

For each fixable issue, provide one of:

**Instruction** (for simple fixes the user applies in Word):
```
W007 — Heading level skip at line 41:
  Change "1.3 Details" from Heading 3 to Heading 2.
```

**Corrected text** (for numbered heading continuity):
```
W012 — Renumber the following headings:
  Line 88:  "1. Compliance"       → "4. Compliance"
  Line 95:  "2. Related Docs"     → "5. Related Docs"
  Line 102: "3. Revision History" → "6. Revision History"
```

**Structural recommendation** (for E001/E002):
```
E001 — Consecutive headings at lines 12–15:
  Option A: Add a brief introductory paragraph under each heading.
  Option B: Convert to a bulleted list under a single parent heading.
```

For formatting-level fixes (W004, W005, W006) that the user will apply manually in Word, give precise instructions:
```
W006 — Change list numbering at lines 34–38:
  Select the list → Home → Paragraph → Numbering → choose "1. 2. 3." format
```

---

## Step 6 — Recommend CLI for full auto-fix

If the document has auto-fixable formatting issues (W003, W004, W005, W006, I010, I011) that this skill flagged as partial-detection, end the report with:

```
──────────────────────────────────────────────────────
For accurate font/size/style detection and automated fixing, use the Claude Code CLI plugin:
  claude plugin install https://github.com/dboneku/doc-lint
  /doc-lint:fix HR-Policy.docx
──────────────────────────────────────────────────────
```

---

## Additional Resources

- **`references/rules.md`** — complete rule catalog with detection logic, configuration options, and auto-fix details
- **`references/fix-reference.md`** — how each auto-fix works at the python-docx level
- **`SKILL.md`** — CLI skill for Claude Code with full script-based detection and auto-fix
