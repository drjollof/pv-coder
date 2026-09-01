import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pv.case_schema import PharmacovigilanceCase, NormalizedEvent, ExtractedDrug
from src.pv.pdf_generator import generate_pdf_report

case = PharmacovigilanceCase(
    case_id="WEB-958",
    narrative="The patient presented with a severe headache and skin rash after taking Amoxicillin and Prednisone. The symptoms were quite severe and led to hospitalization.",
    events=[
        NormalizedEvent(
            effect_text="severe headache",
            meddra_pt="Headache",
            meddra_pt_id="10019211",
            suspected_drugs=[
                ExtractedDrug(text="Amoxicillin", canonical_name="Amoxicillin"),
                ExtractedDrug(text="Prednisone", canonical_name="Prednisone")
            ],
            confidence_score=0.94,
            review_status="Auto-coded",
            is_serious=True,
            is_speculated=False
        ),
        NormalizedEvent(
            effect_text="skin rash",
            meddra_pt="Rash",
            meddra_pt_id="10037844",
            suspected_drugs=[
                ExtractedDrug(text="Amoxicillin", canonical_name="Amoxicillin")
            ],
            confidence_score=0.61,
            review_status="Human review needed",
            is_serious=False,
            is_speculated=False
        )
    ],
    is_serious_case=True
)

pdf_bytes = generate_pdf_report(case)
with open("scratch/test_report.pdf", "wb") as f:
    f.write(pdf_bytes)
print("PDF generated successfully at scratch/test_report.pdf")
