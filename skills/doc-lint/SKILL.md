---
name: doc-lint
description: This skill should be used when the user asks to "lint a document", "check document formatting", "standardize a Word doc", "fix formatting issues", "check my .docx", "clean up this document", "enforce style standards", "check a folder of documents", or mentions finding formatting inconsistencies in Word files. Analyzes .docx files for structural and formatting problems and optionally auto-fixes them.
version: 0.1.0
---

# doc-lint Skill

Analyze `.docx` files for formatting and structural problems, then optionally auto-fix them. Works on single files or entire folders. No Confluence or external services required — this is purely local document standardization.

---

## Modes

| Mode | Command | What it does |
|---|---|---|
| Check | `/doc-lint:check` | Report all issues. Read-only, no changes. |
| Fix | `/doc-lint:fix` | Report issues, then apply all auto-fixable ones. Writes a `.fixed.docx` file. |
| Check folder | `/doc-lint:check-folder` | Check all `.docx` files in a directory and print a summary table. |

---

## Step 1 — Load Rules

Check for a `.doc-lint.json` config file in the current directory. If present, load custom rule settings. If absent, apply all default rules.

See `references/rules.md` for the full rule set and configuration options.

---

## Step 2 — Analyze

Run the linter script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py" --file "$PATH" [--config .doc-lint.json]
```

The script outputs structured JSON results. Parse and display as a human-readable report.

### Issue severity levels

| Level | Symbol | Meaning |
|---|---|---|
| Error | ✖ | Structural problem that will break conversion or readability |
| Warning | ⚠ | Formatting inconsistency that should be fixed |
| Info | ℹ | Stylistic suggestion |

---

## Step 3 — Report

Always print the full report before asking about fixes:

```
doc-lint: HR-Policy.docx
══════════════════════════════════════════════════════
  ✖  [E001] Consecutive headings: 5 in a row at lines 12–16 (no body content)
  ⚠  [W003] Style misuse: 14 paragraphs use "Heading 1" style at 11pt (body size)
  ℹ  [I010] Mixed fonts: 3 font families in body text (Calibri, Times New Roman, Arial)
  ⚠  [W006] Non-standard list: Roman numeral ordered list (lines 34–38)
  ℹ  [I008] Single-item list at line 42 — consider converting to a paragraph
  ⚠  [W012] Numbered heading continuity: heading "1. Overview" at line 51 restarts sequence (expected 4)
  ⚠  [W013] Template compliance (Policy): missing required sections — Compliance, Revision History
  ⚠  [W014] Naming convention: "HR-Policy.docx" does not match Policy pattern (e.g. ACME-POL-001 HR Policy)
──────────────────────────────────────────────────────
  8 issues  (1 error, 5 warnings, 2 info)
  Auto-fixable: 5 of 8
  Manual fix required: E001 (consecutive headings), W013 (add missing sections), W014 (rename file)
══════════════════════════════════════════════════════
Run /doc-lint:fix to apply 5 auto-fixes and save HR-Policy.fixed.docx
```

---

## Step 4 — Fix (if requested)

Run the fixer script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fix.py" --file "$PATH" [--config .doc-lint.json] [--overwrite]
```

The fixer applies all auto-fixable rules and writes `filename.fixed.docx` alongside the original. The original is never modified unless `--overwrite` is explicitly passed.

After fixing, re-run the linter on the fixed file and show a before/after comparison:

```
Fixed: HR-Policy.fixed.docx
  Before: 5 issues (1E 3W 1I)
  After:  1 issue  (0E 0W 1I)
  Applied fixes: style reclassification, font normalization, list normalization, single-item list → paragraph
  Remaining: E001 consecutive headings — requires manual restructuring
```

---

## Step 5 — Folder summary (check-folder mode)

```
doc-lint: ./HR-Policies/ (8 files)
══════════════════════════════════════════════════════
  File                                  Errors  Warnings  Info  Auto-fixable
  ────────────────────────────────────────────────────────────────────────
  1090-OHH-POL-Screening Policy.docx       1       3       1        4/5
  1036-OHH-FRM-Applicant Consent.docx      0       1       0        1/1
  1034-OHH-PRO-Screening Procedure.docx    0       2       1        3/3
  ...
  ────────────────────────────────────────────────────────────────────────
  Total: 8 files, 3 errors, 14 warnings, 6 info
  Run /doc-lint:fix on individual files or pass --all to fix the whole folder.
```

---

## Configuration

Users can create `.doc-lint.json` in their project to customize rules:

```json
{
  "rules": {
    "consecutive-headings": { "severity": "error", "max": 2 },
    "style-misuse": { "severity": "warning" },
    "font-normalization": { "enabled": true, "target-font": "Calibri" },
    "font-size-normalization": {
      "enabled": true,
      "sizes": { "h1": 20, "h2": 16, "h3": 14, "h4": 12, "body": 11 }
    },
    "list-normalization": { "enabled": true },
    "single-item-list": { "severity": "info" },
    "orphaned-bold": { "severity": "info" },
    "numbered-heading-continuity": { "enabled": true },
    "template-compliance": { "enabled": true },
    "naming-convention": { "enabled": true }
  }
}
```

See `references/rules.md` for all available rules and their defaults.

---

## Additional Resources

- **`references/rules.md`** — complete rule catalog with codes, descriptions, auto-fix status, and configuration
- **`references/fix-reference.md`** — how each auto-fix works at the python-docx level, what can and cannot be fixed programmatically
