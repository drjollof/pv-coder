# PV-Coder PDF Export — Professional Redesign Specification

## Objective

Redesign the PDF export so that it looks like a polished pharmacovigilance case-processing report rather than a basic generated document.

The PDF must remain:

- professional
- clinically appropriate
- easy to scan
- printable
- accessible in grayscale
- compatible with the existing FPDF2-based generation architecture
- visually consistent across cases
- information-dense without becoming cluttered

Do NOT simply add more colors, decorative graphics, gradients, or unnecessary visual elements.

The target aesthetic is:

> Clinical + regulatory + modern enterprise report

Think of a professional medical/safety report rather than a generic PDF template.

---

# 1. Overall Page Structure

Move away from the current:

```text
Title
Case ID
Seriousness banner
Narrative
Events
```

and use a proper document hierarchy:

```text
┌──────────────────────────────────────────────────────────────┐
│ PV-CODER                                      CASE REPORT    │
│ Pharmacovigilance Case Report                                │
├──────────────────────────────────────────────────────────────┤
│ CASE SUMMARY                                                 │
│ Case ID | Report Type | Status | Seriousness                │
├──────────────────────────────────────────────────────────────┤
│ CASE ASSESSMENT                                              │
│ Seriousness / Review Status / Events / Drugs                │
├──────────────────────────────────────────────────────────────┤
│ CLINICAL NARRATIVE                                           │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ EXTRACTED ADVERSE EVENTS                                     │
│ Event 01                                                     │
│ Event 02                                                     │
│ Event 03                                                     │
├──────────────────────────────────────────────────────────────┤
│ REVIEW & CODING                                              │
│ AI decisions / human review                                  │
├──────────────────────────────────────────────────────────────┤
│ EXPORT / SYSTEM METADATA                                     │
└──────────────────────────────────────────────────────────────┘
```

Not every section needs to appear when data is unavailable.

---

# 2. Header Redesign

The current centered title should be replaced with a structured report header.

Use a two-column header.

Left:

```text
PV-CODER
PHARMACOVIGILANCE CASE REPORT
```

Right:

```text
CASE ID
WEB-958

REPORT STATUS
VALIDATED
```

The PV-Coder wordmark should use the application's purple accent sparingly.

The report title should be dark charcoal rather than pure black.

Example visual hierarchy:

```text
PV-CODER
Pharmacovigilance Case Report
```

with:

```text
WEB-958
VALIDATED
```

aligned on the right.

Add a thin horizontal divider underneath.

This immediately gives the PDF a report identity.

---

# 3. Add Report Metadata

Create a compact metadata strip immediately below the header.

Example:

```text
CASE ID             REPORT TYPE       CASE STATUS       GENERATED
WEB-958             Initial           Validated         31 Aug 2026
```

If report type is available:

```text
Initial
Follow-up #1
```

If not available, omit it.

Do not display placeholder values such as `N/A` everywhere.

Only show fields that actually exist.

---

# 4. Replace the Large Seriousness Banner

The existing full-width green rectangle is too visually dominant and resembles a web-app alert.

Replace it with a compact clinical status panel.

For example:

```text
┌──────────────────────────────────────────────────────────────┐
│ CASE SERIOUSNESS                                             │
│ ✓ NON-SERIOUS                                               │
│ No serious criteria detected                                │
└──────────────────────────────────────────────────────────────┘
```

For serious cases:

```text
┌──────────────────────────────────────────────────────────────┐
│ CASE SERIOUSNESS                                             │
│ ! SERIOUS                                                    │
│ Seriousness criterion detected: Hospitalization             │
└──────────────────────────────────────────────────────────────┘
```

Use a restrained pale green/red background.

Do not use highly saturated colors.

The border or small status indicator should carry the semantic color.

---

# 5. Add Case Summary Cards

Before the narrative, add four compact metrics.

```text
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ EVENTS     │ │ DRUGS      │ │ AUTO-CODED │ │ REVIEW     │
│    7       │ │    2       │ │     5      │ │     2      │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

These should be subtle white cards with light borders.

Use dark text.

Only the semantic status categories need accent colors:

Auto-coded → green
Review → orange

Do not create excessive card shadows.

FPDF2 can achieve this with simple rectangles and text; no external graphics framework is necessary.

---

# 6. Clinical Narrative Redesign

Current:

```text
Clinical Narrative:
paragraph
```

Change to:

```text
CLINICAL NARRATIVE

────────────────────────────────────────────

[original narrative]

────────────────────────────────────────────

Source: Clinical case narrative
```

Use a slightly tinted background box around the narrative.

For example:

```text
┌────────────────────────────────────────────┐
│ The patient presented with...              │
│                                            │
│ ...                                        │
└────────────────────────────────────────────┘
```

The narrative should have generous internal padding.

Do not justify the text if doing so creates awkward word spacing.

Use a highly readable font size around 10–11 pt.

---

# 7. Make Adverse Events the Visual Centerpiece

The current event cards are too generic.

Create a structured event report component.

Example:

```text
EVENT 01                                      AUTO-CODED

Clinical Effect
Severe headache

MedDRA Preferred Term
Headache

MedDRA ID
10019211

Suspected Drug
Amoxicillin

Context
Current event

AI Confidence
94%
```

Use a small event number/index in the upper-left.

Example:

```text
01
ADVERSE EVENT
```

The status should be displayed in the upper-right:

```text
✓ AUTO-CODED
```

or:

```text
! HUMAN REVIEW
```

This creates a much stronger scan pattern.

---

# 8. Stop Using Blue Hyperlink-Looking Labels

This is one of the biggest visual problems in the current PDF.

The bright blue labels:

```text
Effect:
MedDRA PT:
Drugs:
Status:
```

look like hyperlinks.

Instead use:

```text
Clinical Effect
MedDRA Preferred Term
MedDRA ID
Suspected Drug
Status
```

Labels should be dark grey or muted slate.

Use weight to distinguish labels from values rather than bright color.

Recommended:

```text
LABEL
10 pt / semibold / muted grey

VALUE
10–11 pt / regular / charcoal
```

Purple can be used selectively for section headings, not every label.

---

# 9. Add a Dedicated Coding Information Block

For every event, separate clinical information from coding information.

Example:

```text
CLINICAL FINDING

Effect
Severe headache

Source
"...developed a severe headache..."

────────────────────────────────────────────

MEDDRA CODING

Preferred Term
Headache

MedDRA ID
10019211

Confidence
94%

Status
✓ Auto-coded
```

This mirrors the logical structure of your application much better.

---

# 10. Show Evidence for Review-Required Events

For events requiring human review, add a dedicated review panel.

Example:

```text
HUMAN REVIEW REQUIRED

Extracted phrase
"skin became very red"

Selected term
Rash

AI confidence
61%

Alternative candidates

1. Rash
2. Erythema
3. Skin discoloration

Reviewer decision
Pending
```

Use a pale orange background.

For already-reviewed cases:

```text
Reviewer decision
Rash

Decision status
Reviewed
```

Do not expose raw model internals unless technical debug mode is enabled.

---

# 11. Add Source Evidence Carefully

When the source span is available, show:

```text
SOURCE EVIDENCE

"...patient subsequently developed severe headache..."
```

Use a smaller font and lightly shaded quotation block.

This is valuable because PV-Coder performs context-aware clinical extraction.

It allows the report reader to understand why the event exists.

---

# 12. Handle Long Drug Lists Properly

Instead of:

```text
Drugs: Amoxicillin, Prednisone, Paracetamol, ...
```

allow wrapping naturally.

For multiple drugs:

```text
Suspected Drugs

• Amoxicillin
• Prednisone
• Paracetamol
```

For a single drug:

```text
Suspected Drug
Amoxicillin
```

Do not force everything into one horizontal row.

---

# 13. Improve Section Headers

Replace:

```text
Clinical Narrative:
Extracted Adverse Events:
```

with editorial section headings:

```text
01  CLINICAL NARRATIVE

02  ADVERSE EVENT EXTRACTION

03  CODING & REVIEW

04  CASE VALIDATION
```

Use a small section number plus heading.

Example:

```text
02
ADVERSE EVENT EXTRACTION
```

This makes a multi-page report much easier to navigate.

---

# 14. Add Case Validation Section

Before the export metadata, show:

```text
CASE VALIDATION

✓ Clinical narrative present
✓ Adverse events identified
✓ Suspected drug identified
✓ Seriousness assessed
✓ All extracted events reviewed
```

If review is incomplete:

```text
CASE VALIDATION

✓ Clinical narrative present
✓ Adverse events identified
✓ Suspected drug identified
✓ Seriousness assessed
⚠ 2 events require human review
```

Do not state that a case is "validated" unless the application's validation state actually says so.

---

# 15. Add Processing Summary

A compact technical summary can be placed near the end:

```text
PROCESSING SUMMARY

Extraction              Completed
Context filtering       Completed
MedDRA normalization    Completed
Human review            2 events
Case validation         Completed
```

This is useful for demonstrating the processing pipeline without exposing implementation details.

---

# 16. Add System Metadata Footer

Every page should have a professional footer.

Example:

```text
PV-Coder | Pharmacovigilance Intake System

Case WEB-958                                      Page 1 of 2
```

For multi-page reports:

```text
PV-Coder                                      WEB-958
Pharmacovigilance Case Report                 Page 2 of 3
```

Use a thin horizontal line above the footer.

The page number should be generated dynamically.

---

# 17. Add a Document Generation Timestamp

The report should contain:

```text
Generated
31 Aug 2026 · 09:42
```

Do not fabricate the timestamp.

Use the actual generation time.

---

# 18. Add MedDRA Terminology Metadata

If available from the loaded terminology/index:

```text
Terminology
MedDRA version: [actual version]
```

Do not hardcode a version.

If the current application does not expose the version, leave this out until reliable metadata is available.

---

# 19. Add a Small Disclaimer / Scope Note

At the end:

```text
PV-Coder provides NLP-assisted extraction and coding support.
Human review remains required for ambiguous or review-flagged
findings before final case disposition.
```

Use small muted text.

Do not use alarming legal language.

The wording should accurately reflect the actual application's HITL workflow.

---

# 20. Typography

Move away from "large title + basic body text."

Recommended hierarchy:

```text
PV-CODER
9–10 pt
uppercase
accent colour

MAIN REPORT TITLE
20–22 pt
semibold/bold

SECTION NUMBER
8–9 pt
semibold
accent colour

SECTION TITLE
12–14 pt
bold

SUBSECTION
10–11 pt
semibold

BODY
10–11 pt

METADATA
8–9 pt
muted grey
```

Avoid using too many font sizes.

---

# 21. Color System

Do not reproduce the dark web UI.

Use a restrained print palette.

Suggested:

```text
Charcoal
#1F2937

Muted Slate
#64748B

Border
#D9DEE7

Light Surface
#F8FAFC

Primary Purple
#6D28D9

Success
#059669

Warning
#D97706

Serious/Error
#B91C1C
```

Use purple primarily for:

- PV-Coder branding
- section numbers
- small accents

Use green/orange/red strictly for semantic statuses.

Do not use bright hyperlink blue for labels.

---

# 22. Border and Shape System

Use:

- thin 0.5–1 pt borders
- subtle rectangular containers
- 3–6 pt corner radius if supported

Avoid:

- heavy outlines
- large shadows
- gradients
- excessive rounded cards
- decorative shapes

The PDF should look good when printed in black and white.

---

# 23. Multi-Page Behaviour

This is important.

Do not manually assume the report fits on one page.

Event cards must be allowed to break naturally where possible.

Avoid orphaned headings.

For example:

```text
02 ADVERSE EVENT EXTRACTION
```

should not appear at the bottom of one page with the event beginning on the next.

Keep the section heading together with at least the beginning of its first content block.

Each event should preferably remain together on one page when its size permits.

If an event is too large, allow controlled splitting rather than shrinking the font excessively.

---

# 24. Page 1 Composition

The ideal first page should feel intentionally designed.

Suggested order:

```text
PV-CODER                         WEB-958
Pharmacovigilance Case Report

─────────────────────────────────────────

CASE SUMMARY

Seriousness       Status        Events    Drugs
Non-serious      Validated         7        2

─────────────────────────────────────────

01  CLINICAL NARRATIVE

[clinical narrative box]

─────────────────────────────────────────

02  ADVERSE EVENT EXTRACTION

[Event 01]
[Event 02]
```

Do not force all events onto page 1.

---

# 25. Page 2+ Composition

Continuation pages should not repeat the huge document title.

Use a compact running header:

```text
PV-CODER · WEB-958
Pharmacovigilance Case Report
```

Then continue:

```text
02  ADVERSE EVENT EXTRACTION

[Event 03]
[Event 04]

03  CODING & REVIEW
...
```

This gives the PDF a genuine report-document feel.

---

# 26. PDF Should Reflect Case State

The report should visually distinguish:

### Non-serious + validated

```text
✓ NON-SERIOUS
✓ VALIDATED
```

### Serious + validated

```text
! SERIOUS
✓ VALIDATED
```

### Serious + review pending

```text
! SERIOUS
⚠ REVIEW REQUIRED
```

### Failed/incomplete

```text
! PROCESSING INCOMPLETE
```

Do not make all reports visually identical regardless of case state.

The structure remains the same; semantic status changes.

---

# 27. Filename Improvements

Use informative filenames.

For example:

```text
PV-Coder_WEB-958_Report.pdf
```

For follow-up cases:

```text
PV-Coder_WEB-958_FollowUp-01_Report.pdf
```

Do not use generic:

```text
report.pdf
output.pdf
case.pdf
```

---

# 28. Preserve Existing PDF Generator Architecture

Do not rewrite the entire backend unless necessary.

The existing project uses FPDF2 for PDF generation.

Refactor the current `pdf_generator.py` into reusable rendering functions/components.

Conceptually:

```text
generate_report()
    ├── render_header()
    ├── render_case_metadata()
    ├── render_seriousness()
    ├── render_case_summary()
    ├── render_narrative()
    ├── render_events()
    ├── render_review()
    ├── render_validation()
    ├── render_processing_summary()
    └── render_footer()
```

Do not add another PDF library unless FPDF2 genuinely cannot support a required feature.

---

# 29. Keep Data Logic Separate From Rendering

The PDF generator should not independently infer:

- seriousness
- confidence
- MedDRA codes
- review status

Those values should come from the existing `PharmacovigilanceCase` structure.

The generator's job is:

```text
Existing Case Object
        ↓
Presentation
        ↓
PDF
```

not:

```text
Raw Case Object
        ↓
Additional business logic
        ↓
PDF
```

This prevents discrepancies between the web UI and PDF.

---

# 30. Final Quality Requirements

Before considering the redesign complete, test at minimum:

### Case types

- one auto-coded event
- multiple events
- serious case
- non-serious case
- review-required event
- multiple review-required events
- no suspected drug
- multiple suspected drugs
- long narrative
- long event text
- many events causing multiple pages

### Layout

Verify:

- no text overlaps
- no clipped text
- no orphaned headings
- event cards do not unexpectedly split
- long drug names wrap
- long MedDRA terms wrap
- page numbers are correct
- headers/footers remain aligned
- status colors remain readable when printed
- PDF looks good in grayscale

### Consistency

The same case must show the same:

- case ID
- seriousness
- event count
- MedDRA terms
- drugs
- statuses
- validation state

in both the React UI and PDF.

---

# 31. Desired End Result

The final PDF should visually communicate:

```text
PV-Coder
      ↓
Professional case report
      ↓
Case summary
      ↓
Clinical evidence
      ↓
Extracted events
      ↓
MedDRA coding
      ↓
Human review
      ↓
Validation state
```

The report should feel closer to a professional internal pharmacovigilance case dossier than a generic programmatically generated PDF.

Do not add visual decoration merely to make it look "fancier."

The improvement should come primarily from:

- stronger hierarchy
- better spacing
- better typography
- better metadata presentation
- structured event presentation
- clear review status
- evidence visibility
- professional headers/footers
- multi-page composition
- consistent status semantics