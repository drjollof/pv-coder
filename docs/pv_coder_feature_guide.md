# PV-Coder: Feature & Infrastructure Guide

This document provides a high-level overview of what PV-Coder currently is, what it can do, and how it is built. Use this as a reference guide when brainstorming new features, UI enhancements, or architectural expansions.

---

## 1. Core Purpose
**PV-Coder** is an AI-assisted Pharmacovigilance (PV) intake system. Its primary goal is to take **unstructured clinical narratives** (e.g., patient emails, doctor notes) and automatically translate them into **structured ICH E2B-compliant cases** (the global standard for adverse event reporting). 

It is designed as a **Human-in-the-Loop (HITL)** system—it does the heavy lifting of extracting and coding medical terms, but flags ambiguous results for human review before final export.

---

## 2. Current Features & Capabilities

### 2.1 Single Intake Mode
- **Real-Time Processing**: Paste a clinical narrative and instantly extract Adverse Events and Suspected Drugs.
- **Context Filtering**: Automatically ignores negated events (*"no headache"*), historical events (*"history of diabetes"*), and hypothetical risks (*"may cause bleeding"*).
- **MedDRA Semantic Coding**: Matches extracted events to the official MedDRA dictionary using AI-driven semantic similarity (not just exact text matching).
- **Auto-Seriousness Detection**: Flags cases as "Serious" if they contain ICH E2A severity keywords (e.g., death, hospitalization, life-threatening).

### 2.2 Human-in-the-Loop (HITL) Review UI
- **Confidence Flagging**: High-confidence matches are marked as "Auto-coded". Low-confidence or ambiguous matches are flagged for "Human Review".
- **Interactive Resolution**: Reviewers are presented with the top 3 alternative MedDRA candidates to choose from.
- **Manual Override**: Reviewers can reject the AI's suggestions and manually type in a specific MedDRA Preferred Term and ID.

### 2.3 Batch Processing Mode
- **CSV Ingestion**: Upload a CSV containing hundreds of raw narratives.
- **Concurrent Processing**: The AI processes the entire batch sequentially (or concurrently, depending on hardware).
- **Analytics Dashboard**: Displays high-level metrics upon completion (Total Events, Serious Cases, Average Confidence).

### 2.4 Enterprise Exporting
- **E2B(R3) XML Generation**: Exports standard XML files ready for ingestion into enterprise safety databases (like Oracle Argus or Veeva Vault).
- **PDF Report Generation**: Generates printable, color-coded PDF reports for individual cases.
- **CSV & JSON Exports**: Export batch results for data science or reporting pipelines.

---

## 3. Infrastructure & Architecture

### 3.1 The Frontend (Client)
- **Framework**: React.js built with Vite.
- **Styling**: Vanilla CSS utilizing modern variables, CSS grid/flexbox, and a premium "Glassmorphism" aesthetic (frosted glass overlays, deep dark-mode backgrounds, subtle micro-animations).
- **Communication**: Uses `@gradio/client` to communicate with the backend via WebSockets. To prevent parsing bugs, all complex data (JSON objects and file uploads) are strictly serialized to strings or **Base64 encoded** before transmission.

### 3.2 The Backend (Server)
- **Framework**: Gradio Headless API (`app.py`). It acts purely as an invisible routing layer to receive data and trigger Python functions.
- **Intelligent Hardware Dispatch**: 
  - When deployed to **Hugging Face**, it detects the `SPACE_ID` environment variable and uses the `@spaces.GPU` decorator to dynamically route execution to an NVIDIA A100 GPU for blazing-fast inference.
  - When run locally on a developer laptop, it bypasses the cloud logic and loads pre-compiled **INT8 ONNX** models for fast CPU execution.

### 3.3 The AI Engine (NLP Pipeline)
- **NER (Extraction)**: Uses `d4data/biomedical-ner-all` (a BERT-based transformer fine-tuned on clinical data).
- **Context**: Uses `MedSpaCy ConText` for linguistic modifier propagation (detecting negation, history, etc.).
- **Normalization (Coding)**: Uses `SapBERT` to convert text into 768-dimensional mathematical vectors, and queries a pre-computed **FAISS Index** containing over 80,000 MedDRA terms to find the closest semantic match.

---

## 4. Brainstorming: Potential Future Features

If you are looking to expand PV-Coder, here are several high-impact areas for future development:

### Feature Expansions (Backend & NLP)
1. **Full Patient Extraction**: Train the NER pipeline to extract patient demographics (Age, Gender, Weight) to fully populate the E2B XML `patient` block.
2. **Drug Dosage & Route**: Extract dosage (e.g., "50mg"), frequency ("twice daily"), and route ("oral") to link directly to the suspected drugs.
3. **Database Integration**: Instead of just exporting files, integrate a PostgreSQL or MongoDB database to actually *save* the cases permanently.
4. **Follow-Up Cases**: Add logic to detect if a narrative is an "Initial" report or a "Follow-up" to an existing case ID.

### UI / UX Enhancements (Frontend)
1. **Authentication & Roles**: Add a login screen. Differentiate between "Data Entry" users and "Medical Reviewer" users.
2. **Text Highlighting**: In Single Intake mode, visually highlight the extracted drugs and diseases directly inside the input text box using different colors.
3. **Batch Data Visualization**: In Batch Mode, add interactive charts (using a library like Recharts or Chart.js) to show the distribution of serious vs. non-serious cases, or a bar chart of the most frequently detected MedDRA terms in the batch.
4. **Dark/Light Mode Toggle**: Currently, the app is strictly dark mode. A premium light mode theme would increase enterprise accessibility.
5. **Drag-and-Drop Narrative Editor**: Allow users to highlight text manually to force the AI to extract it if the NER model missed something.

---

## 5. Complete Repository Map

For any AI or developer stepping into this project, here is the exact layout of the codebase and the responsibility of every critical file.

```text
pv-coder/
├── app.py                      # (Backend Entry Point) The Gradio Headless API server. Defines /analyze and /batch endpoints and `@spaces.GPU` decorators.
├── requirements.txt            # Python dependencies (gradio, transformers, spacy, torch, etc.).
├── README.md                   # Project overview and quickstart guide.
│
├── client/                     # (React Frontend) Built with Vite.
│   ├── package.json            # Node dependencies (@gradio/client, lucide-react, etc.).
│   ├── vite.config.js          # Vite bundler configuration.
│   └── src/
│       ├── App.jsx             # The ENTIRE React application. Contains state management, WebSocket communication, and all UI components (Tabs, Single Intake, Batch Upload).
│       ├── index.css           # Vanilla CSS defining the design system, CSS variables, and glassmorphism styling.
│       └── main.jsx            # React mounting point.
│
├── src/                        # (Core Python AI Engine)
│   ├── extraction/             # NLP Stage 1 & 2: Entity Extraction and Context Filtering
│   │   ├── entities.py         # Defines ExtractionPipeline. Loads the PyTorch/ONNX NER model to extract drugs/diseases from text.
│   │   └── context.py          # Defines ContextFilter. Uses MedSpaCy to detect negation, historical, hypothetical, and other-experiencer modifiers.
│   │
│   ├── normalization/          # NLP Stage 3: Semantic Normalization
│   │   └── embeddings.py       # Defines SemanticNormalizer. Loads SapBERT and queries the FAISS index to map extracted text to MedDRA IDs.
│   │
│   └── pv/                     # Stage 4: Pharmacovigilance Orchestration & Data Models
│       ├── case_schema.py      # Pydantic data models (NormalizedEvent, PharmacovigilanceCase). Defines the strict JSON shape of all data.
│       ├── builder.py          # Defines CaseBuilder. The master orchestrator that connects extraction, context, and normalization into a single pipeline.
│       ├── seriousness.py      # Rule-based ICH E2A keyword scanner to flag cases as "Serious".
│       ├── xml_generator.py    # Converts a PharmacovigilanceCase object into standard E2B(R3) XML.
│       └── pdf_generator.py    # Uses FPDF2 to generate a printable, formatted PDF report.
│
├── models/                     # (Git LFS) Pre-compiled INT8 ONNX models for fast local CPU inference.
│   ├── ner_onnx_quantized/     # Quantized version of d4data/biomedical-ner-all.
│   └── sapbert_onnx_quantized/ # Quantized version of SapBERT.
│
├── data/                       # Processed dictionaries and test data.
│   ├── test_narratives.md      # Sample clinical narratives used by the frontend examples.
│   └── processed/
│       ├── faiss.index         # The pre-computed 768-dimension vector search index.
│       └── tac_meddra_dict...  # The MedDRA dictionary lookup tables.
│
└── scripts/                    # Utility scripts for data preprocessing and pipeline evaluation.
    ├── run_e2e.py              # End-to-end evaluation script on the TAC 2017 Gold Standard dataset.
    ├── run_extraction_eval.py  # Precision/Recall evaluation specifically for the NER extraction stage.
    └── precompute_faiss.py     # Script used to build the FAISS index from the MedDRA dictionary.
```
