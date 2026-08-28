````carousel
# 1. Pharmacovigilance & Project Overview

Welcome to the Master Documentation for **PV-Coder**. If you are taking ownership of this codebase, this document is your definitive guide to both the Medical Domain and the Data Science Architecture.

## What is Pharmacovigilance (PV)?
Pharmacovigilance (PV) is the science of detecting, assessing, understanding, and preventing adverse drug effects. 

By law, pharmaceutical companies and regulators (FDA, EMA) must monitor drug safety post-approval. Every day, they receive thousands of unstructured narratives (emails, phone call transcripts) like:
> *"I took Drug X for a headache, but then I felt really dizzy and threw up."*

A human scientist must read this, identify the **Drugs**, identify the **Adverse Events**, and translate the events into strict medical codes using the **MedDRA Dictionary** (e.g. "Dizziness" -> PT Code 10013573). 

**PV-Coder automates this process using Artificial Intelligence.**

### Serious vs. Non-Serious Cases
Time is legally critical in PV.
- **Serious Cases:** Reports containing keywords indicating death, hospitalization, or life-threatening situations must be reported to the FDA within **15 days**.
- **Non-Serious Cases:** Routine side effects are aggregated and reported periodically.
- PV-Coder automatically scans narratives for Seriousness criteria and flags them with a red 🚨 **SERIOUS CASE** badge for immediate triage.

---
<!-- slide -->
# 2. Raw Data Processing & The Dictionary

Before the AI could do its job, we had to process the raw datasets. 

## The MedDRA Dictionary
MedDRA (Medical Dictionary for Regulatory Activities) is the global gold standard containing over 80,000 specific medical terms (Preferred Terms or PTs). 
- *Example:* "Heart attack", "Myocardial Infarction", and "Ticker stopped" all map to the exact same MedDRA PT ID: **10028596**.

## How we processed the Raw Data (`src/data/tac_parser.py`)
We utilized the **TAC 2017 ADR XML dataset** to train and test our models. This raw data came in heavily nested XML files.

Our preprocessing script `tac_parser.py` does the heavy lifting to clean this raw data:
1. It uses Python's `xml.etree.ElementTree` to parse the raw `<Mentions>`, `<Relations>`, and `<Reactions>` tags.
2. It extracts the raw strings (e.g. "felt dizzy") and matches them against the annotated `meddra_pt_id`.
3. It flattens the complex XML into clean Pandas DataFrames.
4. We then saved this normalized data into two highly optimized files for production:
   - `data/processed/tac_meddra_dict.parquet`: A highly compressed, columnar dictionary of the 80k terms.
   - `data/processed/faiss.index`: A pre-computed mathematical search index (more on this in the next slide).

---
<!-- slide -->
# 3. The NLP Pipeline (Data Science Deep-Dive)

The brain of PV-Coder lives in the `src/` folder. When you paste a medical narrative, it goes through a 4-step assembly line:

### Step 1: Named Entity Recognition (NER)
*Code: `src/extraction/entities.py`*
- We use a **HuggingFace Transformer model** trained specifically on clinical documents. 
- To make it run lightning-fast locally, we converted it into an **INT8 Quantized ONNX format**. This shrank the model size by 75% and massively sped up inference.
- It extracts raw spans like `[DRUG: Advil]` and `[ADVERSE_EVENT: really bad headache]`.

### Step 2: Context Filtering (SpaCy)
*Code: `src/extraction/context.py`*
- NER is "dumb" and will extract negated terms (e.g., "patient did *not* have nausea").
- We use **SpaCy** to perform **Dependency Parsing**. It breaks the sentence into a grammatical tree. 
- `context.py` crawls the tree to find negation ("no", "denies") or family history ("father had cancer") and deletes those false-positive events.

### Step 3: Semantic Normalization (SapBERT)
*Code: `src/normalization/meddra.py`*
- We must convert the patient's messy term ("tummy ache") into a MedDRA PT ("Abdominal Pain").
- We use a neural network called **SapBERT**. It converts the text "tummy ache" into a 768-dimensional **Mathematical Vector**. Due to SapBERT's training, the mathematical array for "tummy ache" is nearly identical to the array for "abdominal pain".

### Step 4: High-Speed Dictionary Search (FAISS)
*Code: `src/pv/builder.py`*
- We use **FAISS (Facebook AI Similarity Search)**. FAISS holds the 80,000 vectors from our processed MedDRA dictionary in memory.
- It takes the SapBERT vector for "tummy ache" and uses C++ algorithms to instantly find the closest vector in the dictionary via **Cosine Similarity**. It returns a **Confidence Score** from 0.0 to 1.0.

---
<!-- slide -->
# 4. Codebase Architecture

This is the literal map of the repository. If you need to fix a bug or add a feature, this guide tells you exactly which file to open.

```text
pv-coder/
├── client/           # React.js Frontend (Vite, CSS Modules)
├── server/           # FastAPI Backend (API Routes)
│   └── main.py       # Exposes /api/analyze, /api/batch, /api/export
├── src/              # Core Python AI Logic
│   ├── data/         # Raw XML parsers (tac_parser.py)
│   ├── extraction/   # NER (entities.py) & Context filtering (context.py)
│   ├── normalization/# SapBERT semantic matching (meddra.py)
│   └── pv/           # The Orchestrator (builder.py) & Data Types
├── data/             # CSVs and processed dictionaries (.parquet, .index)
└── models/           # Downloaded ONNX and SapBERT neural network files
```

### The "Human-in-the-Loop" Threshold
In `server/main.py`, the backend checks the Confidence Score returned by FAISS.
- If score **> 0.90**, it is tagged as `Auto-coded`.
- If score **< 0.90**, the AI is unsure. It tags it as `Human Review` and sends it to the React frontend, which pops open a UI panel allowing the scientist to select the correct MedDRA ID manually.

---
<!-- slide -->
# 5. Frontend & Deployment Strategy

## The React Interface (`client/src/App.jsx`)
- **State Management:** Uses React's `useState` for tabs, batch JSON results, and manual input corrections.
- **Styling (`index.css`):** Built with premium Vanilla CSS. Uses CSS variables for colors, `backdrop-filter: blur(10px)` for glassmorphism, and professional SVG icons from `lucide-react`.
- **Exporting Files:** The React app handles CSV generation locally in the browser, while it relies on FastAPI to generate PDFs and XML ZIP archives.

## Running the Application Locally
Because the backend and frontend are separated, you must run them in **two terminals**:
1. **FastAPI Server:** `uvicorn server.main:app --reload --port 8000` (Crucial: must run on port 8000)
2. **React UI:** `cd client && npm run dev` (Runs on port 5173)

## Production Deployment
To deploy this for other scientists to use:
1. **Backend (Docker & AWS Fargate/GCP Run):** You will containerize the `src/`, `server/`, and `models/` folders using Docker. Deploy this to a cloud provider with at least 4GB to 8GB of RAM (required for the SapBERT/ONNX models in memory).
2. **Frontend (Vercel/S3):** Run `npm run build` in the `client/` folder. Deploy the resulting static HTML/JS files to a cheap static hosting provider.
````
