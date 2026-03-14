# doc-lint

ESLint for Word documents. Analyzes `.docx` files for formatting and structural issues, then auto-fixes the ones it can.

Works in three ways:

| Mode | Where | How |
| --- | --- | --- |
| **Claude Code CLI plugin** | Terminal / Claude Code | Runs Python scripts locally — full detection + auto-fix |
| **Claude.ai / coworker skill** | Claude.ai, Claude Projects, coworker | Claude reads document content — structural rules + fix guidance |
| **MCP server** | Any MCP-compatible client | AI calls Python tools over stdio — full detection + auto-fix |

---

## What it catches

| Code | Issue | Auto-fix |
| --- | --- | --- |
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
| W012 | Numbered heading continuity (manual numbers restart mid-document) | Yes |
| W013 | Template compliance (required sections missing for detected template) | No — requires adding content |
| W014 | Naming convention (filename doesn't match template naming pattern) | No — requires renaming the file |
| W015 | Style policy compliance (headings required by `.style-policy.md` are missing) | No — requires adding content |
| W016 | Excess blank paragraphs (more than one consecutive blank paragraph) | Yes |
| E017 | Placeholder text (TODO, TBD, Lorem ipsum, `[INSERT …]`, `<<…>>`) | No — requires real content |
| E018 | Unaccepted track changes remaining in the document | No — accept or reject in Word |
| W019 | Double spaces in paragraph text | Yes |
| W020 | Heading not in title case (configurable) | Yes |
| W021 | Raw unlinked URLs in body text | Yes |

---

## Option 1 — Claude Code CLI plugin

Install once, then use slash commands in Claude Code to lint and auto-fix `.docx` files.

**Requirements:** Claude Code, Python 3.9+, `python-docx`

### Install CLI plugin

```bash
claude plugin install https://github.com/dboneku/doc-lint
pip install python-docx
```

For reproducible local runs, install from [scripts/requirements.txt](scripts/requirements.txt):

```bash
pip install -r scripts/requirements.txt
```

### Commands

#### `/doc-lint:check <file>`

Analyze a file and report all issues. Read-only — nothing is modified.

```text
/doc-lint:check docs/HR-Policy.docx
```

#### `/doc-lint:fix <file> [--overwrite]`

Analyze and auto-fix all fixable issues. Saves as `filename.fixed.docx` by default.

```text
/doc-lint:fix docs/HR-Policy.docx
/doc-lint:fix docs/HR-Policy.docx --overwrite
```

#### `/doc-lint:check-folder <folder> [--fix-all]`

Check all `.docx` files in a folder and show a summary table.

```text
/doc-lint:check-folder ./HR-Policies
/doc-lint:check-folder ./HR-Policies --fix-all
```

The CLI plugin runs `scripts/lint.py` and `scripts/fix.py` against the real document XML, giving it full access to font names, font sizes, style definitions, and list numbering formats. It can detect all rules and auto-fix 13 of them.

---

## Option 2 — Claude.ai / coworker skill

No installation required. Upload a `.docx` file to Claude.ai (or any Claude interface that supports file uploads) and ask Claude to lint it.

**Works in:** Claude.ai, Claude Projects, Claude coworker, Claude API with file input

### How to use

1. Open Claude.ai (or your Claude coworker/project)
2. Upload your `.docx` file
3. Ask: *"Can you lint this document for formatting issues?"* or *"Check this Word doc for formatting problems"*

Claude will apply the doc-lint rule set to the document content and produce a report in the standard doc-lint format. For structural rules (heading structure, list format, numbered continuity, template compliance, naming convention), detection is identical to the CLI. For font and style metadata rules (W003, W004, W005, I010), Claude will flag obvious cases and recommend the CLI plugin for full accuracy.

For fixable issues, Claude provides:

- Word-by-word renumbering corrections for W012
- Section-by-section fix instructions for structural issues
- Recommended edits for list and heading problems

### Example prompt

```text
Here's our HR policy document. Can you lint it for formatting issues using the doc-lint rules?
The filename is ACME-HR-001 Recruitment Policy.docx
```

---

## Option 3 — MCP server

Runs as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server so any MCP-compatible AI client — Claude Desktop, Cursor, Copilot, or the MCP CLI — can lint and fix `.docx` files directly through tool calls.

**Requirements:** Python 3.9+, `python-docx`, `mcp[cli]>=1.0`

### Install MCP dependencies

```bash
pip install -r scripts/requirements.txt
```

### Add to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "doc-lint": {
      "command": "python",
      "args": ["/absolute/path/to/doc-lint/scripts/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop. The three tools below will be available automatically.
Use the Python interpreter from the environment where you installed `mcp[cli]` and `python-docx` if `python` is not already that interpreter.

### Tools

#### `lint_document`

Lints a `.docx` file and returns a structured report.

| Parameter | Type | Description |
| --- | --- | --- |
| `docx_base64` | string | Base64-encoded `.docx` file contents |
| `filename` | string | Original filename (used by naming-convention rule W014) |
| `config` | object \| null | Partial config override; omitted fields inherit defaults |

Returns `{ issues: [...], summary: { total, errors, warnings, info, fixable } }`

#### `fix_document`

Applies all auto-fixable corrections and returns the updated document.

| Parameter | Type | Description |
| --- | --- | --- |
| `docx_base64` | string | Base64-encoded `.docx` file contents |
| `filename` | string | Original filename (informational) |
| `config` | object \| null | Partial config override; omitted fields inherit defaults |

Returns `{ fixed_docx_base64: string, applied: [...], changes: [...] }`

#### `get_default_config`

Returns the built-in rule configuration as a JSON object — useful as a starting point for customisation.

Rule overrides are merged on top of the built-in defaults using the same semantics as `.doc-lint.json`. That means you can send only the rules you want to change instead of the full config object.

### Run standalone (stdio)

```bash
python scripts/mcp_server.py
```

Or via the MCP CLI:

```bash
mcp run scripts/mcp_server.py
```

---

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
    "orphaned-bold": { "enabled": false },
    "numbered-heading-continuity": { "enabled": true },
    "template-compliance": { "enabled": true },
    "naming-convention": { "enabled": true }
  }
}
```

For CLI use, place `.doc-lint.json` in your project directory. For Claude.ai use, paste the config contents into your prompt. For MCP use, pass the same object as the `config` argument to `lint_document` or `fix_document`; partial overrides are merged with defaults.

All rules are enabled by default. See the [full rule catalog](skills/doc-lint/references/rules.md) for all options.

---

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

---

## Development

### Validate MCP support

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -c "import sys; sys.path.insert(0, 'scripts'); import mcp_server; print('mcp_server OK')"
```

The test suite covers both mocked MCP tool behavior and `.docx` integration checks. CI also imports `scripts/mcp_server.py` directly as a smoke test.

---

## Skill files

| File | Purpose |
| --- | --- |
| [`skills/doc-lint/SKILL.md`](skills/doc-lint/SKILL.md) | Claude Code CLI skill definition |
| [`skills/doc-lint/SKILL-web.md`](skills/doc-lint/SKILL-web.md) | Claude.ai / coworker skill definition |
| [`skills/doc-lint/references/rules.md`](skills/doc-lint/references/rules.md) | Complete rule catalog |
| [`skills/doc-lint/references/fix-reference.md`](skills/doc-lint/references/fix-reference.md) | Auto-fix technical reference |

---

## Requirements

- **CLI plugin:** Claude Code, Python 3.9+, `python-docx` (`pip install python-docx`)
- **Claude.ai skill:** Claude.ai account or Claude API access — no local dependencies
- **MCP server:** Python 3.9+, `pip install -r scripts/requirements.txt` (`python-docx` + `mcp[cli]`)

## License

MIT
