# doc-lint Repository Notes

## Purpose

`doc-lint` is a Claude-oriented document quality tool for `.docx` files. It provides a command/skill layer plus local Python implementations for detecting and fixing document formatting and structural issues.

## Main Components

- `commands/` contains the Claude command definitions.
- `scripts/lint.py` is the authoritative lint engine.
- `scripts/fix.py` applies the auto-fixable subset of rules.
- `skills/doc-lint/` contains the Claude Code and web skill definitions.
- `skills/doc-lint/references/` documents the rules and fix behavior.
- `tests/` now contains helper-focused tests plus generated `.docx` integration cases.

## Important Behaviors

- The linter is the source of truth for rule detection and severity.
- The fixer writes a separate `.fixed.docx` unless `--overwrite` is used.
- The tool relies on `python-docx`, including direct XML access for numbering and hyperlink manipulation.
- The public contract is split across commands, README content, and the skill reference docs, so those must stay synchronized.

## Current Maintenance Focus

- Keep markdown command docs and skill docs lint-clean.
- Make failure paths visible instead of silently swallowing XML or subprocess errors.
- Preserve safe fallback behavior when a fix cannot be applied.
- Keep both helper tests and `.docx` integration tests current before expanding the rule surface.
- Keep CI running both Python regression tests and markdown lint so command and README drift gets caught early.
