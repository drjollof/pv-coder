import xml.etree.ElementTree as ET
from src.pv.case_schema import PharmacovigilanceCase

def generate_e2b_xml(case: PharmacovigilanceCase) -> str:
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
