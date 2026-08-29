# PV-Coder — Consolidated Feature, UI/UX & Product Improvement Specification

## Objective

Improve PV-Coder without turning the project into an unnecessarily heavy enterprise stack.

The guiding constraint is:

> **Maximize clinical usability, explainability, reviewer efficiency, and pharmacovigilance workflow quality while preserving the existing lightweight architecture.**

Current architecture:

- React + Vite frontend
- Vanilla CSS design system
- `@gradio/client` communication
- Headless Gradio backend
- Biomedical NER
- MedSpaCy ConText
- SapBERT + FAISS MedDRA normalization
- Pydantic pharmacovigilance case schema
- Rule-based seriousness detection
- E2B(R3) XML generation
- PDF generation
- INT8 ONNX models for local CPU inference
- NVIDIA GPU dispatch on Hugging Face Spaces

Do not introduce an LLM, agent framework, vector database, PostgreSQL, Redis, Celery, Kubernetes, or another large model simply to implement UI/product improvements.

The existing architecture should remain the foundation.

---

# 1. Product Direction

PV-Coder should evolve from:

> "Paste text → AI extracts terms → download result"

into:

> "Intake → AI extraction → contextual interpretation → human review → case validation → regulatory/data export"

The product should feel like a lightweight PV case-processing workstation rather than an NLP demonstration.

The primary workflow should therefore become:

```text
INTAKE
   ↓
EXTRACTION
   ↓
REVIEW
   ↓
VALIDATION
   ↓
EXPORT
```

Use a persistent workflow indicator in Single Intake.

Example:

```text
● Intake ─── ● Extraction ─── ⚠ Review ─── ○ Validation ─── ○ Export
```

The active state should update automatically.

---

# 2. Single Intake — Redesign the Main Workflow

## 2.1 Add Case Overview

After analysis, display a compact summary before the detailed extraction table.

Example:

```text
CASE #006

Seriousness          Processing Status
● Serious            ⚠ Review Required

Events               Suspected Drugs
7                    2

Auto-coded           Review Required
5                    2
```

This should use information already returned by the existing pipeline.

Do not create additional model inference merely for this panel.

---

# 3. Add Event-Level Review Instead of a Separate HITL Block

The current HITL card should be redesigned.

Instead of:

```text
Extraction Table
      ↓
Separate HITL Card
```

use:

```text
Extraction Table
      ↓
Click/expand problematic event
      ↓
Inline review controls
```

Example:

```text
Effect             MedDRA PT             Confidence       Status

Severe tiredness   Fatigue               94%              ✓ Auto-coded

Skin became red    Rash                  61%              ⚠ Review
                  └────────────────────────────────────────
                    Top Candidates

                    [1] Rash
                        PT: 20002513
                        Confidence: 61%

                    [2] Erythema
                        PT: ...

                    [3] Skin discoloration
                        PT: ...

                    [4] Reject / Manual Input

                    [Save Correction]
```

Clicking a row should expand the review interface directly below that row.

This creates an obvious relationship between:

```text
Raw Effect
    ↓
AI Classification
    ↓
Candidate MedDRA Terms
    ↓
Human Decision
```

---

# 4. Add Keyboard Navigation for HITL

Implement keyboard shortcuts because repetitive review should not require constant mouse interaction.

Suggested behaviour:

```text
1 = select candidate 1
2 = select candidate 2
3 = select candidate 3
4 = select Reject / Other
Enter = Save Correction
Esc = Close review
↑ / ↓ = move between reviewable events
```

Display key hints visually:

```text
[1] Rash
[2] Erythema
[3] Skin discoloration
[4] Other
```

Use `useEffect` only while a review panel is active.

Prevent shortcuts from firing while the user is typing in a text input.

This is a frontend-only improvement.

---

# 5. Add Evidence / Source Text to Every Extracted Event

Every event should expose where it came from in the narrative.

Example:

```text
Effect:
Severe headache

Evidence:
"...patient subsequently developed a severe headache..."

Context:
Current event

Status:
✓ Auto-coded
```

The user should be able to click an event and see the associated source phrase.

This is particularly important for demonstrating that the application is not merely matching words blindly.

The existing pipeline already contains separate extraction and context-processing stages, so the preferred implementation is to preserve source spans through the pipeline rather than attempting to reconstruct them later.

---

# 6. Add In-Text Entity Highlighting

After analysis, transform the narrative display from a standard textarea into a read-only highlighted narrative view.

Do not attempt to build a complex rich-text editor at this stage.

Example:

```text
The patient started [Drug A] on Monday.

Two days later she developed
[severe headache] and [nausea].

She had [no fever].
```

Use semantic highlighting:

```text
Drug
Adverse Event
Negated Finding
Historical Finding
Hypothetical Finding
Review/ambiguous finding
```

Suggested visual hierarchy:

```text
Drug              → blue
Adverse Event     → purple/green semantic highlight
Negated           → muted/grey
Historical        → blue-grey
Hypothetical      → muted/orange
Needs Review      → orange
```

Do not use red for ordinary adverse events because red should remain reserved for serious/error states.

Clicking a highlighted entity should scroll/focus the corresponding extraction row.

Clicking the extraction row should highlight its source phrase.

This creates two-way navigation:

```text
Narrative ↔ Extraction Result
```

---

# 7. Add Excluded Findings

The current system explicitly filters negated, historical and hypothetical findings.

Expose this instead of silently hiding it.

Add:

```text
EXCLUDED FINDINGS (3)
```

Expandable sections:

```text
▸ Negated
  "no headache"

▸ Historical
  "history of diabetes"

▸ Hypothetical
  "may cause bleeding"
```

Each excluded finding should display:

- source text
- exclusion category
- optionally the linguistic modifier detected

Example:

```text
"history of diabetes"

Excluded as:
Historical finding
```

This is one of the strongest explainability features to add.

---

# 8. Add AI Decision Detail

Each event should have a collapsible diagnostic panel.

Example:

```text
AI CODING DETAIL

Extracted phrase
"severe tiredness"

Context
Current event

Normalized MedDRA PT
Fatigue

Confidence
94%

Alternative candidates

Fatigue              94%
Malaise                3%
Asthenia               2%
Lethargy               1%

Decision
✓ Auto-coded
```

Do not expose implementation details such as:

- 768-dimensional vector
- FAISS distance
- raw embedding values

unless there is a dedicated technical/debug mode.

The normal reviewer should see clinically meaningful information.

---

# 9. Improve Confidence Presentation

Do not rely only on:

```text
94%
61%
```

Use confidence as a decision-support signal.

Suggested categories:

```text
High confidence
≥ configured threshold

Review range
below auto-coding threshold

Low confidence
very weak match
```

The exact thresholds should remain configurable in one backend configuration location rather than scattered through the UI.

Do not label confidence as "accuracy".

Confidence is a model score, not proof of correctness.

---

# 10. Make Seriousness Explainable

The current system uses a rule-based seriousness detector.

Do not simply show:

```text
SERIOUS CASE DETECTED
```

Add:

```text
SERIOUSNESS ASSESSMENT

Status
● Serious

Detected basis
Hospitalization

Evidence
"...patient was admitted to hospital..."

Assessment source
Rule-based seriousness detection
```

Where appropriate, distinguish between:

```text
Seriousness detected
Seriousness evidence
Seriousness reason
```

This prevents the seriousness banner from looking like an unexplained black-box decision.

---

# 11. Add Case Validation Before Export

Introduce a dedicated validation stage.

Example:

```text
CASE VALIDATION

✓ Clinical narrative present
✓ Adverse event identified
✓ Suspected drug identified
✓ Seriousness assessed
⚠ 2 events require review
○ Reviewer confirmation required
```

Button:

```text
[Validate Case]
```

After validation:

```text
CASE VALIDATED ✓

[Download PDF]
[Download E2B XML]
[Export JSON]
```

Exports should become secondary to case validation, not the primary action beside the results header.

---

# 12. Add Export Center

Replace the current two-button arrangement with a structured export area.

```text
EXPORT CASE

Regulatory / Interchange
[ E2B(R3) XML ]

Documentation
[ PDF Report ]

Data
[ JSON ] [ CSV ]
```

After generation:

```text
✓ pv_case_006_e2b.xml generated
✓ pv_case_006_report.pdf generated
```

Do not claim an XML file is "regulatory-ready" simply because it was generated.

Provide a distinction such as:

```text
Generated
Structurally validated
Reviewer validated
```

A future XML validation layer should validate the generated document against the applicable E2B(R3) schema/business rules. FDA publishes the E2B(R3) XML schemas, reference instances and related guidance.

---

# 13. Add Local Case History — With Privacy Controls

A browser-local history is a reasonable lightweight substitute for a database during the current development stage.

However, do not blindly store complete clinical narratives in `localStorage`.

Clinical narratives can contain sensitive information.

Preferred design:

```text
Recent Cases
────────────
Case #006
28 Aug 2026
7 events
Needs Review

Case #005
28 Aug 2026
4 events
Validated
```

Store only what is necessary by default:

- case ID
- timestamp
- processing status
- seriousness
- event summary
- review decisions
- generated output metadata

Optionally allow:

```text
[Remember full case locally]
```

with an explicit warning.

Avoid adding Redux/Zustand merely for this feature.

Use the simplest existing React state architecture possible.

A right-side drawer is appropriate:

```text
┌──────────────────────────────┐
│ CASE HISTORY            [×]  │
│                              │
│ #006                         │
│ Serious · Review Required    │
│ 7 events · 28 Aug 2026       │
│                              │
│ #005                         │
│ Non-serious · Validated      │
│ 4 events · 28 Aug 2026       │
└──────────────────────────────┘
```

---

# 14. Add New Case / Reset

Put this permanently in the header:

```text
Case #006                         [New Case]
```

A new case should cleanly reset:

- narrative
- extracted events
- HITL decisions
- validation state
- exports
- temporary UI state

Do not accidentally carry the previous case into the next one.

---

# 15. Batch Mode — Turn It Into a Real Dashboard

The current batch mode already supports total cases, serious cases and analytics.

Expand this into a proper dashboard.

Top-level cards:

```text
CASES PROCESSED
250

EVENTS DETECTED
431

SERIOUS CASES
37

REVIEW REQUIRED
46
```

Second row:

```text
AUTO-CODED
82%

REVIEW RATE
18%

AVG CONFIDENCE
89%
```

Do not create too many cards. Six metrics is sufficient.

---

# 16. Batch Processing Progress

The suggested real-time progress indicator is valuable, but do not assume that simply changing the backend function into a Python generator automatically gives reliable frontend progress through the existing Gradio client integration.

Implement it in stages.

Stage 1:

```text
PROCESSING BATCH

████████████████░░░░░░

Processing cases...
```

Stage 2, after confirming that the Gradio endpoint can provide incremental progress events:

```text
Processing case 45 of 500

██████████████████░░░░
```

Stage 3:

```text
Cases completed        45
Events extracted       83
Serious cases          6
Review required        9
```

The progress mechanism should be designed around the actual current `@gradio/client` API rather than assuming generator/yield semantics will work unchanged.

---

# 17. Batch Processing Error Handling

A large batch should never fail completely because one case is malformed.

Each case should have:

```text
✓ Completed
⚠ Review Required
✕ Processing Error
```

Example:

```text
Case 117
✕ Processing Error

Reason:
Invalid or missing narrative

[View Details]
```

The rest of the batch should continue where technically possible.

---

# 18. Batch Search and Filtering

Add:

```text
Search cases...
```

Filters:

```text
[All]
[Serious]
[Needs Review]
[Auto-coded]
[Errors]
```

Table:

```text
Case ID | Serious | Events | Confidence | Status
```

Clicking a case should open a case-detail view.

This is more important than adding many charts.

---

# 19. Batch Visualizations

Add only a few useful charts.

### Serious vs Non-serious

```text
Serious       █████
Non-serious   █████████████████
```

### Most Frequent MedDRA PTs

```text
Headache        █████████
Rash            ███████
Nausea          ██████
Fatigue         ████
```

### Review Distribution

```text
Auto-coded       82%
Needs Review     18%
```

Charts should be lightweight React components. Recharts/Chart.js is acceptable, but do not introduce a heavy analytics framework.

---

# 20. Drug Normalization — Implement Carefully

The idea of adding drug normalization is good, but do not describe it as:

> "Just add an RxNorm ID to the E2B XML."

That is too simplistic.

Implement this as a separate **Drug Identity Enrichment** layer:

```text
Raw Drug Mention
      ↓
Canonical Drug Name
      ↓
Optional Drug Terminology Identifier
      ↓
Internal Case Model
      ↓
Correct E2B mapping
```

RxNorm is a reasonable lightweight option for enrichment, but it is U.S.-centric and its full release requires a free UMLS license.

Do not present RxNorm as a replacement for WHODrug.

Do not add WHODrug data unless the required licensing/access is available.

For the portfolio version, a small deterministic drug dictionary may actually be the better first implementation.

---

# 21. Drug Dictionary

Create something like:

```text
data/
└── drug_dictionary.json
```

Example concept:

```text
methotrexate
  canonical_name: Methotrexate
  identifiers:
    rxnorm: ...
```

Use normalized lowercase matching.

The dictionary should support:

- brand names
- generic names
- common abbreviations
- spelling variants

Do not let dictionary normalization overwrite the original source text.

Always retain:

```text
raw_drug = "MTX"
normalized_drug = "Methotrexate"
```

---

# 22. Custom Synonym / Acronym Layer

This is a good low-compute feature.

Create:

```text
data/
└── custom_synonyms.json
```

Example:

```text
"SOB" → "shortness of breath"
"MTX" → "methotrexate"
```

But do not destructively replace text before NER.

Preferred approach:

```text
Original narrative
        ↓
Terminology normalization view
        ↓
NER
        ↓
Mapped source span
```

The application should retain the original phrase for evidence and auditability.

If deterministic normalization is applied, keep both:

```text
surface_form
normalized_form
```

This avoids destroying evidence.

---

# 23. Follow-Up Case Support

This is a high-value PV feature, but implement it correctly.

UI:

```text
[ ] Follow-up report

Original Case ID
[________________]
```

When selected:

```text
Report Type
Follow-up

Original Case ID
CASE-0006
```

Case model should eventually support:

```text
report_type
original_case_id
follow_up_number
case_version
```

Do not directly manipulate arbitrary XML tags without first mapping the internal case fields to the applicable E2B(R3) data elements and business rules.

Follow-up support should be validated against the E2B(R3) implementation specification rather than implemented as a simple XML string modification. FDA publishes the relevant implementation guide, schema set, reference instances and business rules.

---

# 24. Case Versioning

Once follow-up cases exist, support:

```text
CASE-0006
Initial report

CASE-0006
Follow-up #1

CASE-0006
Follow-up #2
```

Longer term:

```text
Case
 ├── Initial report
 ├── Follow-up 1
 └── Follow-up 2
```

Do not build this before the basic single-case workflow is stable.

---

# 25. Model / Pipeline Transparency

Add a subtle technical information section.

Example:

```text
PROCESSING ENGINE

Extraction
Biomedical NER

Context
MedSpaCy ConText

Normalization
SapBERT

Terminology Search
FAISS · MedDRA

Inference
ONNX INT8 / GPU
```

This information is already supported by the architecture.

This can be placed inside the User Guide or an "About PV-Coder" drawer rather than the primary case workspace.

---

# 26. System Status Indicator

Add a small header status:

```text
● NLP Engine Ready
```

When appropriate:

```text
● Local CPU
```

or:

```text
● GPU Inference
```

This should reflect actual runtime state rather than being hardcoded.

The current architecture already distinguishes Hugging Face GPU execution from local INT8 ONNX inference.

---

# 27. Loading States

Do not let the UI appear frozen during inference.

Single Intake:

```text
Analyzing case...

✓ Extracting entities
✓ Resolving clinical context
● Mapping MedDRA terms
○ Building case
```

After completion:

```text
Analysis complete
```

This should represent real pipeline stages where possible. Do not fake detailed progress if the backend cannot provide it.

---

# 28. Error States

Every major operation needs a useful error state.

Bad:

```text
Error occurred.
```

Better:

```text
ANALYSIS FAILED

The clinical narrative could not be processed.

Possible causes:
• Empty or malformed input
• Backend unavailable
• Model inference failure

[Try Again]
```

Batch:

```text
43 cases completed
2 cases failed
205 remaining
```

Never hide backend failures behind a generic spinner.

---

# 29. Empty States

Design these deliberately.

Single Intake:

```text
No case analyzed yet.

Paste a clinical narrative above and select
"Analyze Case" to begin.
```

Batch:

```text
No batch loaded.

Upload a CSV containing clinical narratives
to begin batch processing.
```

History:

```text
No recent cases.

Analyzed cases will appear here.
```

---

# 30. Improve Navigation

Current:

```text
Single Intake | Batch Upload | User Guide
```

Keep this structure.

Do not add ten navigation tabs.

Potential future structure:

```text
Single Intake | Batch Processing | Case History | User Guide
```

But Case History should only become a full navigation section when persistent/local case history is actually implemented.

---

# 31. Visual Design Improvements

Retain the existing dark aesthetic.

Do not redesign the entire visual identity.

Use a three-level surface system:

```text
Background
#0B0F19

Primary Surface
#1A1D24

Interactive / Nested Surface
#11151F
```

Reserve semantic colors:

```text
Purple → primary action/navigation

Green → success/validated/complete

Orange → review required

Red → serious/error

Blue → informational/source/drug identity
```

Do not use purple for every possible visual element.

Do not add glow effects to every button.

Use glow sparingly for primary actions.

---

# 32. Reduce Card Nesting

Avoid:

```text
Card
 └── Card
      └── Card
           └── Card
```

Use hierarchy instead:

```text
Page
 ├── Case Overview
 ├── Narrative
 ├── Extraction Results
 ├── Review
 ├── Validation
 └── Export
```

Only visually separate sections that represent different tasks.

---

# 33. Typography and Spacing

Keep the current modern sans-serif style.

Use stronger hierarchy:

```text
Page title
Section heading
Subsection heading
Primary data
Secondary metadata
Helper text
```

Do not make everything bold.

Do not make every metric huge.

Use whitespace to separate workflow stages.

---

# 34. Accessibility

Add basic accessibility now rather than later.

Ensure:

- keyboard navigation
- visible focus states
- semantic buttons
- accessible labels
- sufficient contrast
- status messages announced appropriately
- color is not the only indicator of status

For example:

Instead of:

```text
Orange icon = Review
```

use:

```text
⚠ Review Needed
```

The text itself must communicate the status.

---

# 35. User Guide Improvements

The current User Guide is documentation-heavy.

Turn it into a workflow guide.

Suggested structure:

```text
1. Start a Case
2. Review Extracted Events
3. Resolve Review-Needed Terms
4. Validate the Case
5. Export the Case
6. Process a Batch
7. Understand Status and Confidence
```

Include small UI examples.

Add a "How the AI works" section:

```text
Clinical Narrative
      ↓
Entity Extraction
      ↓
Context Filtering
      ↓
MedDRA Semantic Coding
      ↓
Human Review
      ↓
E2B/PDF Export
```

---

# 36. Optional Technical Debug Mode

For development only, add:

```text
[Technical Details]
```

Containing:

```text
NER entities
Context modifiers
Normalization candidates
Similarity scores
Raw E2B-style JSON
Pipeline timings
```

Do not expose this by default to normal reviewers.

The existing JSON accordion can effectively become part of this mode.

---

# 37. Pipeline Timing

A very useful technical/portfolio feature is execution timing.

Example:

```text
PROCESSING TIME

Extraction       0.8 s
Context          0.1 s
MedDRA coding    0.4 s
Case building    0.02 s

Total            1.32 s
```

Keep this developer-facing or behind "Technical Details".

This gives you useful information when optimizing CPU/GPU inference.

---

# 38. Performance Metrics for Batch

After batch completion:

```text
PROCESSING PERFORMANCE

250 cases processed
431 events extracted

Average case time
0.83 s

Serious cases
37

Review required
46

Processing errors
2
```

Do not claim throughput benchmarks unless actually measured.

---

# 39. MedDRA Version Visibility

Add terminology metadata to the UI/export.

Example:

```text
MedDRA
Version: [actual loaded version]
```

This is important because terminology mappings are version-dependent.

Do not hardcode a version number.

Read it from the loaded dictionary/index metadata where possible.

---

# 40. Add a Review Queue Concept

Even without a database, the batch interface can expose a lightweight review queue.

Example:

```text
REVIEW QUEUE

46 cases require attention

[Open Next Reviewable Case]
```

Then:

```text
Case #117
2 events require review

[Review Case]
```

This is a better future direction than simply showing "Review Needed" in a table.

---

# 41. Long-Term Authentication / Roles

Do not implement authentication yet.

Design the interface so it can eventually support:

```text
Data Entry
     ↓
AI Processing
     ↓
Medical Reviewer
     ↓
Validated
     ↓
Exported
```

Potential future roles:

```text
Data Entry
Medical Reviewer
Administrator
```

This should become a later phase because it requires persistent state and proper identity management.

The existing project guide already identifies authentication and role differentiation as a future feature.

---

# 42. Long-Term Database

Do not add PostgreSQL/MongoDB simply to preserve cases during the current portfolio/development phase.

Database persistence should come after:

- case schema is stable
- review workflow is stable
- follow-up model is defined
- user roles are defined
- audit requirements are defined

Then introduce persistence deliberately.

Potential architecture:

```text
React
  ↓
API
  ↓
Case Service
  ↓
PostgreSQL
```

Do not prematurely introduce a database into the current stateless architecture.

---

# 43. Audit Trail — Future

When persistent storage is eventually added, every human decision should be auditable.

Example:

```text
CASE-006

AI coding:
Fatigue
Confidence: 0.94

Reviewer:
Changed to Malaise

Reviewer:
[user]

Timestamp:
2026-08-28 18:42
```

This becomes particularly important as the application moves closer to real PV workflow use.

---

# 44. Recommended Feature Prioritization

## P0 — Build First

These should be implemented without architectural redesign.

```text
1. Case overview
2. Workflow progress indicator
3. Inline HITL review
4. Source/evidence display
5. In-text entity highlighting
6. Excluded findings
7. AI decision detail
8. Better seriousness explanation
9. Case validation checklist
10. Improved export center
11. Loading/error/empty states
12. New Case/reset
13. Batch filtering/search
14. Batch metrics
15. Basic batch charts
```

These provide the greatest improvement in perceived product quality.

---

## P1 — Build Next

Still compatible with the lightweight architecture.

```text
1. Keyboard shortcuts
2. Batch progress reporting
3. Batch error isolation
4. Local recent-case history
5. Drug dictionary
6. Custom synonym dictionary
7. Processing-time metrics
8. MedDRA version display
9. System/runtime status
10. Technical/debug view
```

---

## P2 — Build After the Core Workflow Is Stable

These require more careful backend/schema work.

```text
1. Patient demographics
2. Drug dose/frequency/route
3. Follow-up cases
4. Case versioning
5. Drug terminology enrichment
6. Structural E2B validation
7. Review queue
8. More complete case completeness validation
```

The current project guide already identifies patient demographics, drug dosage/route, database persistence and follow-up handling as future backend expansion areas.

---

## P3 — Long-Term Enterprise Direction

Do not implement these during the current UX phase.

```text
1. Authentication
2. User roles
3. PostgreSQL persistence
4. Case assignment
5. Multi-user review
6. Persistent audit trail
7. Follow-up history
8. Advanced case management
```

---

# 45. Features Explicitly NOT Recommended Right Now

Do not add:

- Large language models purely for "AI enhancement"
- RAG systems
- vector databases
- chatbot assistants
- autonomous agents
- massive new NLP models
- Redis/Celery job infrastructure
- Kubernetes/container orchestration
- complex microservices
- full enterprise authentication
- WHODrug integration without proper access/licensing
- arbitrary E2B XML tag manipulation
- complex rich-text clinical editors
- unnecessarily large frontend state libraries
- local storage of sensitive narratives by default

The objective is to improve the product, not inflate the technology stack.

---

# 46. Target Architecture After These Improvements

The architecture should still look approximately like:

```text
                    ┌────────────────────┐
                    │   React / Vite UI   │
                    │                    │
                    │ Intake              │
                    │ Review              │
                    │ Validation          │
                    │ Batch Dashboard     │
                    │ Export              │
                    └─────────┬──────────┘
                              │
                       @gradio/client
                              │
                              ▼
                    ┌────────────────────┐
                    │ Headless Gradio    │
                    │ API                │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ CaseBuilder        │
                    └─────────┬──────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
              NER          ConText      SapBERT
                │             │             │
                └─────────────┴──────┬──────┘
                                    ▼
                              FAISS / MedDRA
                                    │
                                    ▼
                         PharmacovigilanceCase
                                    │
                      ┌─────────────┼─────────────┐
                      ▼             ▼             ▼
                    PDF          E2B XML        JSON/CSV
```

The UI should become considerably more sophisticated without making the core architecture proportionally more complicated.

---

# 47. The Most Important Product Principle

Do not optimize PV-Coder around:

> "How many AI features can we add?"

Optimize it around:

> "How quickly and confidently can a reviewer turn an unstructured report into a validated pharmacovigilance case?"

Every proposed feature should be judged against that question.

The strongest product loop is:

```text
Narrative
   ↓
What did the AI find?
   ↓
Why did it find it?
   ↓
What did it exclude?
   ↓
What is uncertain?
   ↓
What should the reviewer change?
   ↓
Has the case been validated?
   ↓
What can now be exported?
```

That should be the central design philosophy for the next version of PV-Coder.