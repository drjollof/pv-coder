from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
import xml.etree.ElementTree as ET
import re
from typing import List
import zipfile
from pydantic import BaseModel
import sys
import io
import pandas as pd
from pathlib import Path
import tempfile
from fpdf import FPDF

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.pv.builder import CaseBuilder
from src.pv.case_schema import PharmacovigilanceCase

app = FastAPI(title="PV-Coder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_builder = None

def get_builder() -> CaseBuilder:
    global _builder
    if _builder is None:
        dict_path = str(ROOT / "data" / "processed" / "tac_meddra_dict.parquet")
        faiss_path = str(ROOT / "data" / "processed" / "faiss.index")
        if not Path(faiss_path).exists():
            faiss_path = None
        _builder = CaseBuilder(dict_path, faiss_index_path=faiss_path)
    return _builder

class AnalyzeRequest(BaseModel):
    narrative: str
    case_id: str = "CASE-1"

@app.post("/api/analyze", response_model=PharmacovigilanceCase)
def analyze_case(req: AnalyzeRequest):
    builder = get_builder()
    case = builder.process(narrative=req.narrative, case_id=req.case_id)
    return case

@app.get("/api/examples")
def get_examples():
    path = ROOT / "data" / "test_narratives.md"
    content = path.read_text(encoding="utf-8")
    
    blocks = re.split(r'\n\d+\.\s', '\n' + content)
    examples = []
    for block in blocks:
        block = block.strip()
        if block and not block.startswith("Section"):
            text = " ".join([line.strip() for line in block.split('\n') if line.strip()])
            examples.append(text)
            
    return {"examples": examples}

@app.post("/api/batch", response_model=List[PharmacovigilanceCase])
async def batch_process(file: UploadFile = File(...)):
    """
    Accepts a CSV with a 'narrative' column, runs the extraction, 
    and returns a JSON array of processed cases.
    """
    builder = get_builder()
    
    # Read uploaded CSV
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    
    if "narrative" not in df.columns:
        return {"error": "CSV must contain a 'narrative' column"}
    
    results = []
    for idx, row in df.iterrows():
        narrative = row["narrative"]
        case_id = row.get("case_id", f"BATCH-{idx}")
        case = builder.process(narrative=narrative, case_id=case_id)
        results.append(case)
            
    return results

def generate_xml_string(case: PharmacovigilanceCase) -> str:
    root = ET.Element("ichicsr", lang="en")
    ich_header = ET.SubElement(root, "ichheader")
    ET.SubElement(ich_header, "messageid").text = case.case_id
    
    safety_report = ET.SubElement(root, "safetyreport")
    ET.SubElement(safety_report, "safetyreportid").text = case.case_id
    
    serious = "1" if case.is_serious_case else "2"
    ET.SubElement(safety_report, "serious").text = serious
    
    patient = ET.SubElement(safety_report, "patient")
    patient_narrative = ET.SubElement(patient, "patientepisodenamemeddracode")
    patient_narrative.text = case.narrative
    
    for event in case.events:
        reaction = ET.SubElement(patient, "reaction")
        ET.SubElement(reaction, "primarysourcereaction").text = event.effect_text
        ET.SubElement(reaction, "reactionmeddraversionllt").text = event.meddra_pt
        ET.SubElement(reaction, "reactionmeddralocalllt").text = event.meddra_pt_id
        if event.suspected_drugs:
            for drug in event.suspected_drugs:
                drug_elem = ET.SubElement(patient, "drug")
                ET.SubElement(drug_elem, "medicinalproduct").text = drug
                
    xml_str = ET.tostring(root, encoding='utf-8', method='xml').decode()
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

@app.post("/api/export/batch/xml-zip")
def export_batch_xml_zip(cases: List[PharmacovigilanceCase]):
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for case in cases:
            xml_str = generate_xml_string(case)
            zipf.writestr(f"{case.case_id}.xml", xml_str)
            
    return FileResponse(
        temp_zip.name,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=pv_coder_batch_xmls.zip"}
    )

@app.post("/api/export/xml")
def export_xml(case: PharmacovigilanceCase):
    xml_str = generate_xml_string(case)
    return Response(content=xml_str, media_type="application/xml", headers={"Content-Disposition": f"attachment; filename={case.case_id}.xml"})

@app.post("/api/export/pdf")
def export_pdf(case: PharmacovigilanceCase):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(31, 34, 41)
    pdf.cell(0, 15, "Pharmacovigilance Intake Report", ln=True, align='C')
    
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Case ID: {case.case_id}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 14)
    if case.is_serious_case:
        pdf.set_fill_color(254, 226, 226) # red-100
        pdf.set_text_color(220, 38, 38) # red-600
        pdf.cell(0, 12, "  SERIOUS CASE DETECTED  ", ln=True, align='C', fill=True)
    else:
        pdf.set_fill_color(209, 250, 229) # emerald-100
        pdf.set_text_color(5, 150, 105) # emerald-600
        pdf.cell(0, 12, "  Non-Serious Case  ", ln=True, align='C', fill=True)
        
    pdf.ln(10)
    
    pdf.set_text_color(31, 34, 41)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Clinical Narrative:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(60, 60, 60)
    
    safe_narrative = case.narrative.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_narrative)
    pdf.ln(10)
    
    pdf.set_text_color(31, 34, 41)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Extracted Adverse Events:", ln=True)
    pdf.ln(2)
    
    for event in case.events:
        pdf.set_fill_color(248, 250, 252) # slate-50
        pdf.set_draw_color(226, 232, 240) # slate-200
        
        safe_effect = event.effect_text.encode('latin-1', 'replace').decode('latin-1')
        safe_pt = event.meddra_pt.encode('latin-1', 'replace').decode('latin-1')
        drugs = ", ".join(event.suspected_drugs) if event.suspected_drugs else "None"
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(79, 70, 229) # indigo-600
        pdf.cell(40, 8, " Effect:", border='L T', fill=True)
        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(31, 34, 41)
        pdf.cell(0, 8, f" {safe_effect}", border='R T', fill=True, ln=True)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(40, 8, " MedDRA PT:", border='L', fill=True)
        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(31, 34, 41)
        pdf.cell(0, 8, f" {safe_pt} (ID: {event.meddra_pt_id})", border='R', fill=True, ln=True)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(40, 8, " Drugs:", border='L', fill=True)
        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(31, 34, 41)
        pdf.cell(0, 8, f" {drugs}", border='R', fill=True, ln=True)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(40, 8, " Status:", border='L B', fill=True)
        pdf.set_font("Arial", 'I', 10)
        if event.review_status == 'Auto-coded':
            pdf.set_text_color(16, 185, 129)
        else:
            pdf.set_text_color(245, 158, 11)
        pdf.cell(0, 8, f" {event.review_status}", border='R B', fill=True, ln=True)
        
        pdf.ln(5)
        
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    
    return FileResponse(
        temp.name, 
        media_type='application/pdf', 
        headers={"Content-Disposition": f"attachment; filename={case.case_id}_report.pdf"}
    )
