import gradio as gr
import spaces
from pathlib import Path
import json
import os
import tempfile
import zipfile
import pandas as pd
from typing import Dict, Any

from src.pv.builder import CaseBuilder
from src.pv.case_schema import PharmacovigilanceCase
from src.pv.xml_generator import generate_e2b_xml
from src.pv.pdf_generator import generate_pdf_report

# Global builder
_builder = None

def get_builder():
    global _builder
    if _builder is None:
        ROOT = Path(__file__).parent
        dict_path = str(ROOT / "data" / "processed" / "tac_meddra_dict.parquet")
        faiss_path = str(ROOT / "data" / "processed" / "faiss.index")
        if not Path(faiss_path).exists():
            faiss_path = None
        _builder = CaseBuilder(dict_path, faiss_index_path=faiss_path)
    return _builder

@spaces.GPU
def analyze_api(narrative: str, case_id: str):
    builder = get_builder()
    case = builder.process(narrative=narrative, case_id=case_id)
    return case.model_dump()

def export_pdf_api(case_dict: Dict[str, Any]):
    case = PharmacovigilanceCase(**case_dict)
    pdf_bytes = generate_pdf_report(case)
    
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f"{case.case_id}_report.pdf")
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)
    return filepath

def export_xml_api(case_dict: Dict[str, Any]):
    case = PharmacovigilanceCase(**case_dict)
    xml_str = generate_e2b_xml(case)
    
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f"{case.case_id}_e2b.xml")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_str)
    return filepath

@spaces.GPU
def batch_api(csv_filepath: str):
    builder = get_builder()
    df = pd.read_csv(csv_filepath)
    if 'narrative' not in df.columns:
        raise ValueError("CSV must contain a 'narrative' column")
        
    results = []
    for idx, row in df.iterrows():
        case_id = str(row.get('case_id', f"BATCH-{idx}"))
        case = builder.process(narrative=str(row['narrative']), case_id=case_id)
        results.append(case.model_dump())
    return results

def batch_xml_zip_api(results_list: list):
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "batch_xmls.zip")
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for case_dict in results_list:
            case = PharmacovigilanceCase(**case_dict)
            xml_str = generate_e2b_xml(case)
            xml_filename = f"{case.case_id}_e2b.xml"
            zipf.writestr(xml_filename, xml_str)
            
    return zip_path

# Get examples
def get_examples():
    try:
        from server.main import load_examples
        return load_examples()
    except Exception:
        return []

# Create the Gradio App
with gr.Blocks(title="PV-Coder Engine API") as demo:
    gr.Markdown("# PV-Coder API Endpoint\nThis space hosts the headless API for PV-Coder. Use the `/api/...` endpoints.")
    
    # Hidden components for API routing
    with gr.Row(visible=False):
        # Analyze
        t_narrative = gr.Textbox()
        t_case_id = gr.Textbox()
        j_out_case = gr.JSON()
        btn_analyze = gr.Button("Analyze")
        btn_analyze.click(fn=analyze_api, inputs=[t_narrative, t_case_id], outputs=j_out_case, api_name="analyze")
        
        # PDF Export
        j_in_case = gr.JSON()
        f_out_pdf = gr.File()
        btn_pdf = gr.Button("PDF")
        btn_pdf.click(fn=export_pdf_api, inputs=j_in_case, outputs=f_out_pdf, api_name="export_pdf")
        
        # XML Export
        f_out_xml = gr.File()
        btn_xml = gr.Button("XML")
        btn_xml.click(fn=export_xml_api, inputs=j_in_case, outputs=f_out_xml, api_name="export_xml")
        
        # Batch
        f_in_csv = gr.File()
        j_out_batch = gr.JSON()
        btn_batch = gr.Button("Batch")
        btn_batch.click(fn=batch_api, inputs=f_in_csv, outputs=j_out_batch, api_name="batch")
        
        # Batch XML Zip
        j_in_batch = gr.JSON()
        f_out_zip = gr.File()
        btn_zip = gr.Button("Zip")
        btn_zip.click(fn=batch_xml_zip_api, inputs=j_in_batch, outputs=f_out_zip, api_name="batch_xml_zip")
        
        # Examples
        j_out_examples = gr.JSON()
        btn_examples = gr.Button("Examples")
        btn_examples.click(fn=get_examples, inputs=None, outputs=j_out_examples, api_name="examples")

if __name__ == "__main__":
    demo.launch()
