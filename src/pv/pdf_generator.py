from fpdf import FPDF
from src.pv.case_schema import PharmacovigilanceCase

def generate_pdf_report(case: PharmacovigilanceCase) -> bytes:
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
        drugs = ", ".join([d.canonical_name or d.text for d in event.suspected_drugs]) if event.suspected_drugs else "None"
        
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
        
    return pdf.output(dest='S')
