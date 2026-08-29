import gradio as gr
import spaces
from pathlib import Path
import json
import base64
import os
import tempfile
import zipfile
import pandas as pd

from src.pv.builder import CaseBuilder
from src.pv.case_schema import PharmacovigilanceCase
from src.pv.xml_generator import generate_e2b_xml
from src.pv.pdf_generator import generate_pdf_report

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
def analyze_api(narrative: str, case_id: str) -> str:
    try:
        builder = get_builder()
        case = builder.process(narrative=narrative, case_id=case_id)
        return json.dumps(case.model_dump())
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        return json.dumps({"error": str(e), "traceback": err_str})

def export_pdf_api(case_dict_str: str) -> str:
    case = PharmacovigilanceCase(**json.loads(case_dict_str))
    pdf_bytes = generate_pdf_report(case)
    return base64.b64encode(pdf_bytes).decode("utf-8")

def export_xml_api(case_dict_str: str) -> str:
    case = PharmacovigilanceCase(**json.loads(case_dict_str))
    return generate_e2b_xml(case)

@spaces.GPU
def batch_api(csv_b64: str):
    csv_bytes = base64.b64decode(csv_b64.encode("utf-8"))
    import io
    df = pd.read_csv(io.BytesIO(csv_bytes))
    if 'narrative' not in df.columns:
        yield json.dumps({"status": "error", "error": "CSV must contain a 'narrative' column"})
        return
    builder = get_builder()
    results = []
    total = len(df)
    
    for idx, row in df.iterrows():
        case_id = str(row.get('case_id', f"BATCH-{idx}"))
        try:
            case = builder.process(narrative=str(row['narrative']), case_id=case_id)
            results.append(case.model_dump())
        except Exception as e:
            results.append({
                "case_id": case_id,
                "error": str(e),
                "narrative": str(row.get('narrative', ''))
            })
            
        yield json.dumps({
            "status": "processing",
            "current": idx + 1,
            "total": total,
            "latest_case_id": case_id
        })
        
    yield json.dumps({
        "status": "complete",
        "results": results
    })

def batch_xml_zip_api(results_list_str: str) -> str:
    results_list = json.loads(results_list_str)
    buf = {}
    for case_dict in results_list:
        case = PharmacovigilanceCase(**case_dict)
        buf[f"{case.case_id}_e2b.xml"] = generate_e2b_xml(case)

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "batch_xmls.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for fname, content in buf.items():
            zipf.writestr(fname, content)

    with open(zip_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_examples() -> str:
    try:
        ROOT = Path(__file__).parent
        content = (ROOT / "data" / "test_narratives.md").read_text(encoding="utf-8")
        import re
        blocks = re.split(r'\n\d+\.\s', '\n' + content)
        examples = []
        for block in blocks:
            block = block.strip()
            if block and not block.startswith("Section"):
                text = " ".join(line.strip() for line in block.split('\n') if line.strip())
                examples.append(text)
        return json.dumps(examples)
    except Exception:
        return json.dumps([])

with gr.Blocks(title="PV-Coder Engine API") as demo:
    gr.Markdown("## PV-Coder API\nHeadless NLP backend for pharmacovigilance case coding.")

    with gr.Row(visible=False):
        i_narrative = gr.Textbox()
        i_case_id = gr.Textbox()
        o_case = gr.Textbox()
        gr.Button("Analyze").click(fn=analyze_api, inputs=[i_narrative, i_case_id], outputs=o_case, api_name="analyze")

        i_case_for_pdf = gr.Textbox()
        o_pdf_b64 = gr.Textbox()
        gr.Button("PDF").click(fn=export_pdf_api, inputs=i_case_for_pdf, outputs=o_pdf_b64, api_name="export_pdf")

        i_case_for_xml = gr.Textbox()
        o_xml_str = gr.Textbox()
        gr.Button("XML").click(fn=export_xml_api, inputs=i_case_for_xml, outputs=o_xml_str, api_name="export_xml")

        i_csv_b64 = gr.Textbox()
        o_batch = gr.Textbox()
        gr.Button("Batch").click(fn=batch_api, inputs=i_csv_b64, outputs=o_batch, api_name="batch")

        i_results = gr.Textbox()
        o_zip_b64 = gr.Textbox()
        gr.Button("ZIP").click(fn=batch_xml_zip_api, inputs=i_results, outputs=o_zip_b64, api_name="batch_xml_zip")

        o_examples = gr.Textbox()
        gr.Button("Examples").click(fn=get_examples, inputs=None, outputs=o_examples, api_name="examples")

if __name__ == "__main__":
    demo.launch()
