# doc-lint

ESLint for Word documents. Analyzes `.docx` files for formatting and structural issues, then auto-fixes the ones it can.

## What it catches

| Code | Issue | Auto-fix |
|---|---|---|
| E001 | Consecutive headings with no body content between them | No — needs content or restructuring |
| E002 | Empty sections (heading immediately followed by another heading) | No |
| W003 | Heading style misused for body text (e.g. Heading 1 at 11pt) | Yes |
| W004 | Non-standard font family in body text | Yes |
| W005 | Non-standard font size for content type | Yes |
| W006 | Roman numeral or alphabetic ordered lists | Yes |
| W007 | Heading level skip (H1 → H3 with no H2) | Yes |
| I008 | Single-item list (should be a paragraph) | Yes |
| I009 | Entire short paragraph is bold (possible heading) | No |
| I010 | Mixed fonts in body text | Yes |
| I011 | Section title and body text in same paragraph (soft line break) | Yes |

## Installation

```bash
claude plugin install https://github.com/dboneku/doc-lint
```

Install Python dependency:

```bash
pip install python-docx
```

## Commands

### `/doc-lint:check <file>`
Analyze a file and report all issues. Read-only — nothing is modified.

```
/doc-lint:check docs/HR-Policy.docx
```

### `/doc-lint:fix <file> [--overwrite]`
Analyze and auto-fix all fixable issues. Saves as `filename.fixed.docx` by default.

```
/doc-lint:fix docs/HR-Policy.docx
/doc-lint:fix docs/HR-Policy.docx --overwrite
```

### `/doc-lint:check-folder <folder> [--fix-all]`
Check all `.docx` files in a folder and show a summary table.

```
/doc-lint:check-folder ./HR-Policies
/doc-lint:check-folder ./HR-Policies --fix-all
```

## Configuration

Create a `.doc-lint.json` in your project to customize rules:

```json
{
  "rules": {
    "consecutive-headings": { "severity": "error", "max": 2 },
    "font-normalization": { "enabled": true, "target-font": "Calibri" },
    "font-size-normalization": {
      "enabled": true,
      "sizes": { "h1": 20, "h2": 16, "h3": 14, "h4": 12, "body": 11 }
    },
    "list-normalization": { "enabled": true },
    "single-item-list": { "severity": "info" },
    "orphaned-bold": { "enabled": false }
  }
}
```

All rules are enabled by default. See the [full rule catalog](skills/doc-lint/references/rules.md) for all options.

## Run directly (without Claude)

```bash
# Check a file
python3 scripts/lint.py --file path/to/file.docx

# Fix a file
python3 scripts/fix.py --file path/to/file.docx

# JSON output (for scripting)
python3 scripts/lint.py --file path/to/file.docx --json
```

The linter exits with code `1` if any errors are found, `0` otherwise — making it suitable for CI/CD pipelines.

## Requirements

- Claude Code
- Python 3.9+
- `python-docx` (`pip install python-docx`)

## License

MIT
