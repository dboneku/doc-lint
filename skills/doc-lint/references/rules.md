# doc-lint Rule Catalog

All rules, their codes, default severity, auto-fix status, and configuration options.

---

## Rule Codes

| Code | Name | Default Severity | Auto-fixable |
|---|---|---|---|
| E001 | consecutive-headings | error | No — requires content or restructuring |
| E002 | empty-section | error | No — requires content |
| W003 | style-misuse | warning | Yes |
| W004 | font-normalization | warning | Yes |
| W005 | font-size-normalization | warning | Yes |
| W006 | list-normalization | warning | Yes |
| W007 | heading-level-skip | warning | Yes |
| I008 | single-item-list | info | Yes |
| I009 | orphaned-bold | info | No — requires judgment |
| I010 | mixed-fonts | info | Yes |
| I011 | multiline-heading | info | Yes |
| W012 | numbered-heading-continuity | warning | Yes |
| W013 | template-compliance | warning | No — requires adding content |
| W014 | naming-convention | warning | No — requires renaming the file |

---

## E001 — Consecutive Headings

**Description:** More than N headings in a row with no body content between them.

**Why it matters:** Headings without content are either structural mistakes or list items formatted as headings. Both hurt readability and document accessibility.

**Detection:** Walk paragraphs; count consecutive non-empty heading nodes. Flag when run length exceeds threshold.

**Auto-fix:** No. The fix requires either adding content or restructuring headings as a bullet list — both require human judgment. The linter flags the location and suggests the right fix.

**Configuration:**
```json
"consecutive-headings": { "severity": "error", "max": 2 }
```
`max`: Maximum allowed consecutive headings before flagging (default: 2).

---

## E002 — Empty Section

**Description:** A heading immediately followed by another heading with no content at all.

**Why it matters:** Empty sections indicate incomplete documents or accidental heading duplication.

**Auto-fix:** No.

**Configuration:**
```json
"empty-section": { "severity": "error" }
```

---

## W003 — Style Misuse

**Description:** A paragraph uses a heading style (Heading 1, 2, 3) but has a font size consistent with body text (≤ 12pt for Heading 1, ≤ 10pt for Heading 2).

**Why it matters:** Heading styles carry semantic meaning used by screen readers, navigation panels, and export tools. Misusing them for visual formatting breaks all of these.

**Detection:**

| Style | Expected min size | Flag if size ≤ |
|---|---|---|
| Heading 1 | 13pt | 12pt |
| Heading 2 | 11pt | 10pt |
| Heading 3 | 10pt | 9pt |

**Auto-fix:** Yes — reclassify the paragraph's style to `Normal`.

**Configuration:**
```json
"style-misuse": { "severity": "warning" }
```

---

## W004 — Font Normalization

**Description:** Body text uses a non-standard font family.

**Why it matters:** Mixed fonts look unprofessional and often result from copy-pasting content from external sources.

**Detection:** Collect all font families used in body (`Normal` style) runs. Flag any that differ from the target font.

**Auto-fix:** Yes — set `run.font.name` to the target font on all affected runs. Preserves monospace fonts (Courier New, Consolas, Monaco).

**Configuration:**
```json
"font-normalization": { "enabled": true, "target-font": "Calibri" }
```
`target-font`: The font to normalize body text to (default: `"Calibri"`). Set to `"auto"` to use the document's declared default font.

---

## W005 — Font Size Normalization

**Description:** A paragraph's font size doesn't match the standard for its content type.

**Standard size scale:**

| Content type | Standard size |
|---|---|
| Heading 1 | 20pt |
| Heading 2 | 16pt |
| Heading 3 | 14pt |
| Heading 4 | 12pt |
| Body / Normal | 11pt |
| Table cell | 11pt |
| Caption | 9pt |

**Auto-fix:** Yes — set `run.font.size` to the standard size for the paragraph's style.

**Configuration:**
```json
"font-size-normalization": {
  "enabled": true,
  "sizes": { "h1": 20, "h2": 16, "h3": 14, "h4": 12, "body": 11 }
}
```

---

## W006 — List Normalization

**Description:** An ordered list uses Roman numerals (I/II/III) or alphabetic labels (a/b/c) instead of Arabic numerals (1/2/3).

**Why it matters:** Roman numeral and alphabetic lists are non-standard and render inconsistently across platforms and export formats.

**Detection:** Check `numFmt` in the Word numbering definition for `lowerRoman`, `upperRoman`, `lowerLetter`, `upperLetter`.

**Auto-fix:** Yes — update the `numFmt` element in the numbering XML to `decimal`.

**Configuration:**
```json
"list-normalization": { "enabled": true }
```

---

## W007 — Heading Level Skip

**Description:** A heading jumps more than one level (e.g., H1 → H3 with no H2).

**Why it matters:** Skipped heading levels break document outline structure and accessibility tools.

**Auto-fix:** Yes — demote the skipped heading to `current_level + 1`.

**Configuration:**
```json
"heading-level-skip": { "severity": "warning" }
```

---

## I008 — Single-Item List

**Description:** A bulleted or numbered list containing only one item.

**Why it matters:** A single-item list provides no benefit over a plain paragraph and adds unnecessary indentation.

**Auto-fix:** Yes — remove the list formatting, apply `Normal` style.

**Configuration:**
```json
"single-item-list": { "severity": "info" }
```

---

## I009 — Orphaned Bold

**Description:** An entire short paragraph (≤ 80 characters) where every run is bold. Usually indicates a heading formatted as bold body text instead of using a heading style.

**Auto-fix:** No — requires judgment about whether to promote to a heading or keep as emphasis.

**Configuration:**
```json
"orphaned-bold": { "severity": "info" }
```

---

## I010 — Mixed Fonts

**Description:** More than one font family appears in body text paragraphs (excluding monospace/code fonts).

**Auto-fix:** Yes — normalizes all body text to target font (same as W004, but reported separately when the count of font families is high).

**Configuration:**
```json
"mixed-fonts": { "severity": "info", "allowed-count": 1 }
```

---

## W012 — Numbered Heading Continuity

**Description:** Headings use manual numbering in their text (e.g. "1. Purpose", "2. Scope") but the sequence restarts at 1 mid-document at the same heading level.

**Why it matters:** Manual heading numbers that reset mid-document confuse readers and indicate copy-paste errors or incomplete reorganization. Continuous numbering is required for regulatory documents (policies, procedures, ISO 27001 controls).

**Detection:** A document uses manual numbered headings if ≥ 2 headings at any level begin with an Arabic numeral pattern (`^\d+\.`, `^\d+\.\d+`, etc.). Walk all headings at each level in document order; flag any heading where the number ≤ the previous number at the same level.

**Exception:** Hierarchical sub-numbering that resets per parent (e.g. 1.1, 1.2 under section 1, then 2.1, 2.2 under section 2) is correct and must NOT be flagged.

**Auto-fix:** Yes — replace the leading number with the correct sequential value. Preserve everything after the number. If the pattern is ambiguous, flag for review rather than auto-fixing.

**Configuration:**
```json
"numbered-heading-continuity": { "enabled": true }
```

---

## W013 — Template Compliance

**Description:** The document is missing one or more required sections for its detected template type (Policy, Procedure, Form, etc.).

**Why it matters:** Regulatory templates require specific sections to be compliant. Missing sections indicate incomplete documents that should not be published.

**Detection:** Auto-detect the document's template from keyword scoring across all paragraph text. Compare headings found in the document against the required sections list for that template. Flag any required section that has no heading matching its name (case-insensitive, partial match allowed).

**Required sections by template:**

| Template | Required sections |
|---|---|
| Policy | Purpose, Scope, Policy Statement, Compliance, Revision History |
| Procedure | Purpose, Scope, Prerequisites, Procedure Steps, Revision History |
| Workflow | Purpose, Trigger, Flow Steps, Outcomes |
| Form | Instructions, Fields, Submission Guidance |
| Checklist | Instructions, Checklist Items |
| Meeting Minutes | Attendees, Agenda, Action Items |
| ISO 27001 | Purpose, Scope, Policy Statement, Control Mapping, Revision History |
| General | No required sections |

**Auto-fix:** No — missing sections require the user to write content.

**Configuration:**
```json
"template-compliance": { "enabled": true }
```

---

## W014 — Naming Convention

**Description:** The filename does not follow the expected naming pattern for the document's detected template.

**Why it matters:** Consistent naming makes document libraries searchable and allows automated processing to correctly identify document type without opening each file.

**Expected patterns:**

| Template | Pattern | Example |
|---|---|---|
| Policy | `ORG-POL-NNN Title` | `ACME-POL-001 Information Security Policy` |
| Procedure | `ORG-PRO-NNN Title` | `ACME-PRO-003 Onboarding Procedure` |
| Workflow | `ORG-WF-NNN Title` | `ACME-WF-002 Approval Workflow` |
| Form | `ORG-FRM-NNN Title` | `ACME-FRM-005 Access Request Form` |
| Checklist | `ORG-CHK-NNN Title` | `ACME-CHK-001 New Hire Checklist` |
| Meeting Minutes | `YYYY-MM-DD Team Meeting Minutes` | `2026-03-11 Security Team Meeting Minutes` |
| ISO 27001 | `ORG-NNN-DOMAIN Title (Type)` | `ACME-001-SEC Data Classification Policy (ISO 27001)` |

**Auto-fix:** No — requires renaming the file.

**Configuration:**
```json
"naming-convention": { "enabled": true }
```

---

## I011 — Multiline Heading

**Description:** A heading-sized paragraph (Normal style at ≥ 13pt) contains a soft line break (`<w:br>`), meaning a section title and body text are in the same paragraph.

**Why it matters:** The section title and body text should be separate paragraphs for proper semantic structure.

**Auto-fix:** Yes — split at the `<w:br>` element: first segment becomes a proper heading paragraph, remaining segments become Normal paragraphs.

**Configuration:**
```json
"multiline-heading": { "severity": "info" }
```

---

## W012 — Numbered Heading Continuity

**Description:** Headings at the same level use manual Arabic numbering (e.g. "1. Purpose", "2. Scope") but the sequence resets mid-document instead of continuing.

**Why it matters:** Restarting the count mid-document (e.g. "3. Policy" followed later by "1. Compliance") makes the document harder to navigate and breaks references like "see section 4".

**Detection:** Scan heading text for a leading number pattern (`^\d+\.` or `^\d+\.\d+`). For each heading level that uses numbering, track the expected next value. Flag any heading where the number is ≤ the previous number at the same level.

**Exception:** Hierarchical sub-numbering that resets per parent (1.1, 1.2 → 2.1, 2.2) is correct — only flag flat restarts at the same level.

**Example (flagged):**
```
H2: 1. Introduction
H2: 2. Scope
H2: 3. Policy Statements
H2: 1. Compliance         ← W012: expected 4, found 1
H2: 2. Related Documents  ← W012: expected 5, found 2
```

**Auto-fix:** Yes — replace the leading number in the heading text with the correct sequential value. Preserves everything after the number (title text, punctuation style).

**Configuration:**
```json
"numbered-heading-continuity": { "severity": "warning" }
```

---

## Disabling Rules

To disable a rule entirely:
```json
"consecutive-headings": { "enabled": false }
```

To change severity without disabling:
```json
"consecutive-headings": { "severity": "warning" }
```
Valid severities: `"error"`, `"warning"`, `"info"`.
