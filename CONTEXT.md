# PV-Coder Project Context

## Project Goal
PV-Coder is an NLP-assisted Pharmacovigilance Case Intake System designed to automate the extraction and coding of adverse events from clinical narratives into MedDRA preferred terms. The system provides both a Single Intake view for deep-dive analysis and a Batch Upload dashboard for processing large CSV files, featuring Human-in-the-Loop (HitL) validation flows to ensure accuracy.

## Phase Tracker
| Phase | Status | Description |
|-------|--------|-------------|
| 1 | DONE | Core UI layout improvements and MedSpaCy context styling (excluded findings). |
| 2 | DONE | Single Intake HitL Review implementation. |
| 3 | DONE | PDF Export generation. |
| 4 | DONE | Batch Dashboard UI and real-time processing metric cards. |
| 5 | DONE | Batch HitL Inline Review and Validated JSON export. |
| 6 | PENDING | Implementation of Drug Dictionary & Entity tracking. |
| Future | PENDING | Global SQL Database to track historical validated cases across sessions. |

## What Was Built
- **Backend**: FastAPI/Gradio backend (`app.py`, `src/pv/builder.py`) wrapping HuggingFace Token Classification and MedSpaCy ConText. Includes yield-based generators for real-time progress streaming.
- **Frontend**: React-based UI in `client/src/App.jsx` using `@gradio/client` for websocket streaming. Features interactive text highlighting, case tables, and inline manual review forms.
- **Export Capabilities**: Supports exporting validated cases to JSON (for ML retraining), CSV, E2B XML, and PDF.

## Key Design Decisions
- **HitL Workflow**: In Batch Mode, human reviews are auto-saved in React State to accelerate the validation workflow, rather than forcing the user to click "Validate Case" for every single event.
- **Context Exclusion**: Pre-existing medical conditions (e.g., following "Medical history included...") are explicitly flagged as `HISTORICAL` and excluded from adverse event extraction.
- **Future Database Architecture**: To support cross-session analysis and keep a global record of all reviewed cases, a centralized database (SQLite/Postgres) will be added in a future phase. For now, JSON exports serve as the portable ground-truth dataset.

## Next Session Prompt
> "Read pv-coder-consolidated-feature-Improvement-specification.md and let's move on to Phase 6: Drug Normalization and the internal Drug Dictionary."
