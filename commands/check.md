---
description: Analyze a .docx file for formatting and structural issues. Reports errors, warnings, and suggestions without modifying anything. Shows issue codes, locations, and which issues are auto-fixable.
argument-hint: path/to/file.docx
allowed-tools: Bash
---

Lint a single .docx file and report all formatting issues. Do not modify any files.

## Steps

1. Get the file path from the argument. If not provided, ask for it.

2. Run the linter:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py" --file "$FILE_PATH" --json
   ```

3. Parse the JSON output and display a formatted report following the doc-lint skill format:
   - Show file name and total issue count
   - Group by severity: Errors first, then Warnings, then Info
   - Show rule code, description, and location for each issue
   - Show how many are auto-fixable
   - Suggest running `/doc-lint:fix` if any auto-fixable issues exist

4. Exit without modifying any files.
