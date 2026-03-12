# Changelog

## Unreleased

### Added

- Added `clod.md` repository notes for maintainers and future agent context.
- Added regression tests for helper parsing and generated `.docx` integration cases under `tests/`.

### Changed

- Cleaned up command and README markdown so the public docs pass workspace diagnostics.
- Bounded the `python-docx` dependency range in `scripts/requirements.txt`.
- Clarified the real auto-fix count in the README.

### Fixed

- Improved style-policy parsing so inline required-section lists are handled correctly.
- Preserved original paragraph line numbers in lint output even when blank paragraphs exist.
- Normalized raw URL detection more safely before reporting and auto-fixing.
- Surfaced numbering/XML inspection warnings instead of silently swallowing them.
