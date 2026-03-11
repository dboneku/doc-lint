---
description: Analyze a .docx file for formatting issues and automatically fix all auto-fixable ones. Saves the result as filename.fixed.docx alongside the original. The original file is never modified unless --overwrite is passed.
argument-hint: path/to/file.docx [--overwrite]
allowed-tools: Bash
---

Lint and auto-fix a single .docx file. Write the cleaned version as `filename.fixed.docx`.

## Steps

1. Get the file path from the argument. If not provided, ask for it.
   Parse the `--overwrite` flag if present.

2. Run the linter first to establish a baseline:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py" --file "$FILE_PATH"
   ```
   Show the issues found.

3. Confirm with the user before applying fixes (unless `--overwrite` is passed, in which case warn clearly):
   ```
   Found 5 issues. 4 are auto-fixable. Apply fixes and save as filename.fixed.docx? [y/n]
   ```

4. Run the fixer:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fix.py" --file "$FILE_PATH" [--overwrite]
   ```

5. Re-run the linter on the output file:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py" --file "$OUTPUT_PATH"
   ```

6. Show a before/after comparison:
   - Issues before vs after
   - List of fixes applied
   - Any remaining issues that require manual attention
   - Path to the fixed file
