# PV-Coder Documentation — Part 1: Pharmacovigilance Domain & Project History

---

## 1.1 What is Pharmacovigilance?

Pharmacovigilance (often abbreviated as "PV") is the science of detecting, assessing, understanding, and preventing adverse drug effects. The word comes from the Latin *pharmaco* (relating to drugs) and *vigilare* (to keep watch).

Every medicine sold on the market has gone through clinical trials before approval — but clinical trials typically involve only a few thousand patients. Once a drug is approved and sold to millions of people worldwide, completely new side effects can emerge that were invisible during the trials. Someone's pre-existing medical condition, age, body weight, or a combination with another drug can produce unexpected and dangerous reactions.

**Pharmacovigilance is the global legal system that catches these dangers before they become catastrophes.**

By law, pharmaceutical companies (like Pfizer, AstraZeneca, Roche) and regulatory agencies (the US FDA, the European Medicines Agency, Japan's PMDA) are required to monitor drug safety continuously after a drug is on the market. This process is called **post-market surveillance**.

---

## 1.2 The Regulatory Framework

The key regulatory guidelines for Pharmacovigilance are set by the **ICH (International Council for Harmonisation of Technical Requirements for Pharmaceuticals for Human Use)**, a global body that produces globally accepted scientific and technical guidelines.

The most important guideline for our purposes is **ICH E2A**: *"Clinical Safety Data Management: Definitions and Standards for Expedited Reporting."*

ICH E2A defines two critical rules:

### Serious vs. Non-Serious Cases

A drug reaction is classified as **Serious** if it meets any of the following criteria:
- Results in **death**
- Is **life-threatening**
- Requires **in-patient hospitalization** or prolongation of existing hospitalization
- Results in **persistent or significant disability or incapacity**
- Is a **congenital anomaly or birth defect**
- Is an **important medical event** that may jeopardize the patient and may require medical or surgical intervention to prevent one of the above outcomes

All other adverse events are classified as **Non-Serious**.

### Reporting Timelines

- **Serious, Unexpected Cases:** Must be reported to the regulatory agency within **15 calendar days** (often called a "15-day alert report")
- **Serious, Expected Cases:** Must be reported within **15 days**
- **Non-Serious Cases:** Aggregated and reported in periodic safety updates (PSURs), usually every 6 or 12 months

This 15-day legal deadline is the single biggest reason the pharmaceutical industry desperately needs AI tools to help speed up the case intake process. If a company receives 50,000 reports in a month and it takes human scientists 2 hours to manually code each one, the math simply doesn't work. **PV-Coder's purpose is to automate that initial intake.**

---

## 1.3 The MedDRA Dictionary — The Global Language of Side Effects

The **Medical Dictionary for Regulatory Activities (MedDRA)** is the global gold standard, standardized, multilingual medical terminology developed under the auspices of the ICH.

Think of MedDRA as a universal dictionary that all countries and companies agreed to use so that data can be exchanged without translation errors. If a US company codes "heart attack" as PT ID 10028596 and sends it to a Japanese regulator, both systems understand it is "Myocardial infarction."

### The MedDRA Hierarchy

MedDRA is organized as a 5-level hierarchy:

```
SOC (System Organ Class)           — broadest level (e.g., "Cardiac disorders")
  HLGT (High Level Group Term)     — (e.g., "Ischaemic coronary artery disorders")
    HLT (High Level Term)          — (e.g., "Coronary artery disorders NEC")
      PT (Preferred Term)          — (e.g., "Myocardial infarction")    ← WE USE THIS
        LLT (Lowest Level Term)    — (e.g., "Heart attack")             ← maps up to PT
```

In PV-Coder, we work at the **Preferred Term (PT)** level. This is the standard level used for safety reporting. Every LLT (like "heart attack", "MI", "cardiac arrest") maps up to a single PT.

The current MedDRA dictionary contains over **80,000 terms** across all levels. Our compressed version in `data/processed/tac_meddra_dict.parquet` focuses on PTs and their IDs.

---

## 1.4 The E2B(R3) XML Format — How Reports are Transmitted

Reports are not sent to the FDA as emails or PDFs. They are transmitted in a strict electronic format called **E2B(R3)**, an ICH standard for electronic transmission of individual case safety reports (ICSRs).

An E2B XML file is a precisely structured XML document containing every field of the safety report: patient demographics, drug information, adverse event reactions (with MedDRA codes), and the seriousness assessment. This is the format that ingests into safety databases like Oracle Argus, Veeva Vault, or ArisGlobal LifeSphere.

**PV-Coder's E2B export feature (`POST /api/export/xml`) generates this exact format** so that the coded case can be uploaded directly into a safety database. Here is a simplified example of what we generate:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ichicsr lang="en">
  <ichheader>
    <messageid>CASE-001</messageid>
  </ichheader>
  <safetyreport>
    <safetyreportid>CASE-001</safetyreportid>
    <serious>1</serious>  <!-- 1=Serious, 2=Non-Serious -->
    <patient>
      <reaction>
        <primarysourcereaction>severe chest pain</primarysourcereaction>
        <reactionmeddraversionllt>Chest pain</reactionmeddraversionllt>
        <reactionmeddralocalllt>10008479</reactionmeddralocalllt>
      </reaction>
      <drug>
        <medicinalproduct>Aspirin</medicinalproduct>
      </drug>
    </patient>
  </safetyreport>
</ichicsr>
```

---

## 1.5 Project History — How PV-Coder Was Built

### Phase 1: Data Inspection

Before writing any AI code, we started by deeply understanding the raw data available to us.

**The two primary datasets we used were:**

1. **TAC 2017 ADR Dataset:** The TAC (Text Analysis Conference) 2017 Adverse Drug Reaction corpus. This dataset consists of FDA-approved drug label documents (like a Tylenol package insert) annotated with the exact character spans of adverse event mentions and their gold-standard MedDRA codes. It is split into `train_xml/` (development) and `gold_xml/` (evaluation, locked).

2. **PHEE Dataset:** The Pharmacovigilance Event Extraction (PHEE) dataset. This is a corpus of real consumer medical case reports from biomedical literature, annotated with full event structures: the drug (Treatment), the adverse effect (Effect), the patient (Subject), and metadata like Severity and Speculated.

During Phase 1, we ran deep inspection scripts on both datasets to understand:
- How many cases contain multiple events?
- How frequently are drugs mentioned together (combination therapy)?
- What is the distribution of serious vs. non-serious cases?
- What is the ratio of negated mentions (e.g., "no nausea") to real ones?

The results of this inspection informed every single design decision in the NLP pipeline. For example, finding that ~22% of extracted entity spans in the TAC data were negated is what drove us to build the aggressive MedSpaCy ConText filtering stage (explained in detail in Part 2).

### Phase 2: Model Selection

We evaluated multiple model architectures for the NER stage. The final choice, `d4data/biomedical-ner-all`, uses the **BioNLP13CG annotation schema**, which distinguishes between Medication, Disease_disorder, Sign_symptom, and Clinical_event labels. This granularity is exactly what pharmacovigilance needs.

For semantic normalization, we selected **SapBERT** (Self-Aligning Pretrained BERT from Cambridge LTL), because it was trained specifically on UMLS medical synonyms — making it the state-of-the-art model for mapping informal patient language to formal medical terminology.

### Phase 3: Optimization (ONNX Quantization)

The original PyTorch models were very large and slow. We quantized them to **INT8 ONNX format** using the HuggingFace Optimum library. This reduced both models' sizes by approximately 75% and made inference significantly faster on CPU — essential for running this tool on a standard laptop.

### Phase 4: The Web Application

Originally built on Streamlit (a Python-only dashboard framework), we migrated to a proper production-grade architecture:
- **FastAPI** backend (`server/`) — a high-performance asynchronous API server
- **React.js** frontend (`client/`) — a modern, interactive user interface built with Vite

This separation allows the backend to be deployed independently (e.g., on AWS Fargate) and the frontend to be hosted anywhere (e.g., Vercel) for a globally accessible tool.

---

*Continue to Part 2: The Raw Data Processing Pipeline*
