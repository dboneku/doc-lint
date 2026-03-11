---
description: Lint all .docx files in a folder and show a summary table of issues per file. Useful for auditing a library of documents for formatting consistency. Does not modify any files.
argument-hint: path/to/folder [--fix-all]
allowed-tools: Bash, Glob
---

Lint all .docx files in a folder and display a summary report.

## Steps

1. Get the folder path from the argument. If not provided, ask for it.
   Parse the `--fix-all` flag if present.

2. Find all .docx files:
   ```bash
   find "$FOLDER_PATH" -name "*.docx" | sort
   ```
   Report the count. If none found, stop and tell the user.

3. Run the linter on each file:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py" --file "$FILE" --json
   ```

4. Display a summary table:
   ```
   doc-lint: ./HR-Policies/ (8 files)
   ══════════════════════════════════════════════════════════════════════
   File                                    Errors  Warnings  Info  Fixable
   ────────────────────────────────────────────────────────────────────────
   1090-OHH-POL-Screening Policy.docx         1       3       1     4/5
   1036-OHH-FRM-Applicant Consent.docx        0       1       0     1/1
   ...
   ────────────────────────────────────────────────────────────────────────
   Total: 8 files │ 3 errors │ 14 warnings │ 6 info │ 18/23 auto-fixable
   ```

5. If `--fix-all` is passed:
   - Confirm with the user before proceeding
   - Run `/doc-lint:fix` on each file with issues
   - Show per-file fix results
   - Print final totals

6. If `--fix-all` is not passed, suggest:
   ```
   To fix individual files: /doc-lint:fix path/to/file.docx
   To fix all:              /doc-lint:check-folder path/to/folder --fix-all
   ```
