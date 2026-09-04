from fpdf import FPDF
from src.pv.case_schema import PharmacovigilanceCase
from datetime import datetime

# Colors
C_CHARCOAL = (31, 41, 55)
C_SLATE = (100, 116, 139)
C_BORDER = (180, 185, 195) # Darkened so boundaries are clearly visible
C_SURFACE = (248, 250, 252)
C_PURPLE = (109, 40, 217)
C_SUCCESS = (5, 150, 105)
C_WARNING = (217, 119, 6)
C_ERROR = (185, 28, 28)

C_BG_SUCCESS = (209, 250, 229)
C_BG_WARNING = (254, 243, 199)
C_BG_ERROR = (254, 226, 226)

class PDFReportGenerator(FPDF):
    def __init__(self, case: PharmacovigilanceCase):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.case = case
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(left=15, top=15, right=15)
        self.add_page()

    def safe_str(self, text):
        if not isinstance(text, str):
            text = str(text)
        # Replace common smart quotes and dashes for cleaner output before falling back to ?
        text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"').replace('—', '-').replace('–', '-')
        return text.encode('latin-1', 'replace').decode('latin-1')

    def cell(self, *args, **kwargs):
        # fpdf2 cell signature: cell(w, h=None, text='', border=0, ln='DEPRECATED', align='', fill=False, link='')
        # Since arguments can be positional, it's safer to intercept text if it's the 3rd arg or named 'txt'/'text'
        if 'txt' in kwargs:
            kwargs['txt'] = self.safe_str(kwargs['txt'])
        elif 'text' in kwargs:
            kwargs['text'] = self.safe_str(kwargs['text'])
        elif len(args) > 2:
            args = list(args)
            args[2] = self.safe_str(args[2])
            args = tuple(args)
        super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if 'txt' in kwargs:
            kwargs['txt'] = self.safe_str(kwargs['txt'])
        elif 'text' in kwargs:
            kwargs['text'] = self.safe_str(kwargs['text'])
        elif len(args) > 2:
            args = list(args)
            args[2] = self.safe_str(args[2])
            args = tuple(args)
        super().multi_cell(*args, **kwargs)

    def header(self):
        # Left side
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_PURPLE)
        self.cell(90, 5, "PV-CODER", ln=0, align='L')
        
        # Right side
        self.set_text_color(*C_CHARCOAL)
        self.cell(90, 5, str(self.case.case_id), ln=1, align='R')
        
        # Second line
        if self.page_no() == 1:
            self.set_font("Arial", 'B', 18)
            self.set_text_color(*C_CHARCOAL)
            self.cell(120, 8, "Pharmacovigilance Case Report", ln=0, align='L')
        else:
            self.set_font("Arial", 'B', 12)
            self.set_text_color(*C_CHARCOAL)
            self.cell(120, 8, "Pharmacovigilance Case Report", ln=0, align='L')
            
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_SUCCESS)
        self.cell(60, 8, "VALIDATED", ln=1, align='R')
        
        # Horizontal divider
        self.ln(2)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.line(self.get_x(), self.get_y(), 210 - 15, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.line(self.get_x(), self.get_y(), 210 - 15, self.get_y())
        self.ln(2)
        
        self.set_font("Arial", '', 8)
        self.set_text_color(*C_SLATE)
        self.cell(90, 5, f"PV-Coder | Pharmacovigilance Intake System", ln=0, align='L')
        self.cell(90, 5, f"Page {self.page_no()}", ln=1, align='R')

    def render_seriousness(self):
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_SLATE)
        self.cell(0, 5, "CASE SERIOUSNESS", ln=1, align='L')
        self.ln(2)
        
        is_serious = self.case.is_serious_case
        bg_color = C_BG_ERROR if is_serious else C_BG_SUCCESS
        border_color = C_ERROR if is_serious else C_SUCCESS
        
        self.set_fill_color(*bg_color)
        self.set_draw_color(*border_color)
        
        # We simulate a block with border and background
        x = self.get_x()
        y = self.get_y()
        self.rect(x, y, 180, 16, style='DF')
        
        self.set_xy(x + 5, y + 2)
        self.set_font("Arial", 'B', 10)
        if is_serious:
            self.set_text_color(*C_ERROR)
            self.cell(0, 6, "! SERIOUS", ln=1, align='L')
            self.set_xy(x + 5, y + 8)
            self.set_font("Arial", '', 9)
            self.cell(0, 6, "Seriousness criteria detected.", ln=1, align='L')
        else:
            self.set_text_color(*C_SUCCESS)
            self.cell(0, 6, "v NON-SERIOUS", ln=1, align='L')
            self.set_xy(x + 5, y + 8)
            self.set_font("Arial", '', 9)
            self.cell(0, 6, "No serious criteria detected.", ln=1, align='L')
            
        self.set_xy(x, y + 20)

    def render_case_summary_cards(self):
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_SLATE)
        self.cell(0, 5, "METRICS", ln=1, align='L')
        self.ln(2)
        
        events_count = len(self.case.events)
        drugs_count = len(set(d.canonical_name or d.text for e in self.case.events for d in e.suspected_drugs))
        auto_count = sum(1 for e in self.case.events if e.review_status == 'Auto-coded')
        review_count = events_count - auto_count
        
        # Render 4 boxes horizontally
        x = self.get_x()
        y = self.get_y()
        
        w = 42
        gap = 4
        
        metrics = [
            ("EVENTS", str(events_count), C_CHARCOAL),
            ("DRUGS", str(drugs_count), C_CHARCOAL),
            ("AUTO-CODED", str(auto_count), C_SUCCESS),
            ("REVIEW", str(review_count), C_WARNING)
        ]
        
        for i, (label, val, color) in enumerate(metrics):
            cur_x = x + (w + gap) * i
            self.set_xy(cur_x, y)
            self.set_fill_color(*C_SURFACE)
            self.set_draw_color(*C_BORDER)
            self.rect(cur_x, y, w, 16, style='DF')
            
            self.set_xy(cur_x, y + 2)
            self.set_font("Arial", 'B', 8)
            self.set_text_color(*C_SLATE)
            self.cell(w, 5, label, ln=1, align='C')
            
            self.set_xy(cur_x, y + 7)
            self.set_font("Arial", 'B', 12)
            self.set_text_color(*color)
            self.cell(w, 7, val, ln=1, align='C')
            
        self.set_xy(15, y + 20)
        self.set_draw_color(*C_BORDER)
        self.line(15, self.get_y(), 210 - 15, self.get_y())
        self.ln(6)

    def render_clinical_narrative(self):
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_PURPLE)
        self.cell(10, 6, "01", ln=0)
        self.set_font("Arial", 'B', 12)
        self.set_text_color(*C_CHARCOAL)
        self.cell(0, 6, "CLINICAL NARRATIVE", ln=1)
        self.ln(3)
        
        # Draw a tinted background box around narrative
        self.set_fill_color(*C_SURFACE)
        self.set_draw_color(*C_BORDER)
        
        self.set_font("Arial", '', 10)
        self.set_text_color(*C_CHARCOAL)
        self.multi_cell(0, 6, self.case.narrative, border=1, fill=True)
        
        self.ln(6)

    def render_adverse_events(self):
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_PURPLE)
        self.cell(10, 6, "02", ln=0)
        self.set_font("Arial", 'B', 12)
        self.set_text_color(*C_CHARCOAL)
        self.cell(0, 6, "ADVERSE EVENT EXTRACTION", ln=1)
        self.ln(3)

        for i, event in enumerate(self.case.events):
            with self.unbreakable():
                # Header of the event card
                self.set_fill_color(*C_SURFACE)
                self.set_draw_color(*C_BORDER)
                
                # Event index and status
                self.set_font("Arial", 'B', 9)
                self.set_text_color(*C_SLATE)
                self.cell(90, 8, f"  EVENT {i+1:02d}", border='L T B', fill=True, align='L')
                
                status_text = event.review_status
                if status_text == 'Auto-coded':
                    self.set_text_color(*C_SUCCESS)
                    status_disp = "v AUTO-CODED  "
                else:
                    self.set_text_color(*C_WARNING)
                    status_disp = "! HUMAN REVIEW  "
                    
                self.cell(90, 8, status_disp, border='R T B', fill=True, align='R', ln=1)
                
                # Clinical Finding Section
                self.cell(180, 2, "", border='L R', fill=True, ln=1) # Top padding
                self.set_font("Arial", 'B', 8)
                self.set_text_color(*C_SLATE)
                self.cell(180, 5, "  Clinical Effect", border='L R', fill=True, align='L', ln=1)
                
                self.set_font("Arial", '', 10)
                self.set_text_color(*C_CHARCOAL)
                safe_effect = event.effect_text.encode('latin-1', 'replace').decode('latin-1')
                self.cell(180, 6, f"  {safe_effect}", border='L R', fill=True, align='L', ln=1)
                self.cell(180, 2, "", border='L B R', fill=True, ln=1) # Spacer with bottom border
                
                # MedDRA Section
                self.cell(180, 2, "", border='L R', fill=True, ln=1) # Top padding
                self.set_font("Arial", 'B', 8)
                self.set_text_color(*C_SLATE)
                self.cell(180, 5, "  MedDRA Preferred Term", border='L R', fill=True, align='L', ln=1)
                
                self.set_font("Arial", '', 10)
                self.set_text_color(*C_CHARCOAL)
                safe_pt = event.meddra_pt.encode('latin-1', 'replace').decode('latin-1')
                self.cell(180, 6, f"  {safe_pt}", border='L R', fill=True, align='L', ln=1)
                self.cell(180, 2, "", border='L B R', fill=True, ln=1) # Spacer with bottom border
                
                # MedDRA ID
                self.cell(180, 2, "", border='L R', fill=True, ln=1) # Top padding
                self.set_font("Arial", 'B', 8)
                self.set_text_color(*C_SLATE)
                self.cell(180, 5, "  MedDRA ID", border='L R', fill=True, align='L', ln=1)
                
                self.set_font("Arial", '', 10)
                self.set_text_color(*C_CHARCOAL)
                self.cell(180, 6, f"  {event.meddra_pt_id}", border='L R', fill=True, align='L', ln=1)
                self.cell(180, 2, "", border='L B R', fill=True, ln=1) # Spacer with bottom border
                
                # Drugs
                self.cell(180, 2, "", border='L R', fill=True, ln=1) # Top padding
                self.set_font("Arial", 'B', 8)
                self.set_text_color(*C_SLATE)
                self.cell(180, 5, "  Suspected Drugs", border='L R', fill=True, align='L', ln=1)
                
                self.set_font("Arial", '', 10)
                self.set_text_color(*C_CHARCOAL)
                drugs = [d.canonical_name or d.text for d in event.suspected_drugs] if event.suspected_drugs else ["None"]
                for d in drugs:
                    safe_drug = d.encode('latin-1', 'replace').decode('latin-1')
                    self.cell(180, 6, f"  - {safe_drug}", border='L R', fill=True, align='L', ln=1)
                
                # Bottom border
                self.cell(180, 4, "", border='L B R', fill=True, ln=1)
                self.ln(6)
            
    def render_processing_summary(self):
        self.set_font("Arial", 'B', 9)
        self.set_text_color(*C_PURPLE)
        self.cell(10, 6, "03", ln=0)
        self.set_font("Arial", 'B', 12)
        self.set_text_color(*C_CHARCOAL)
        self.cell(0, 6, "SYSTEM METADATA", ln=1)
        self.ln(2)
        
        self.set_font("Arial", '', 9)
        self.set_text_color(*C_SLATE)
        self.cell(40, 5, "Generated:", ln=0)
        self.set_text_color(*C_CHARCOAL)
        self.cell(0, 5, datetime.now().strftime("%d %b %Y . %H:%M"), ln=1)
        
        self.set_text_color(*C_SLATE)
        self.cell(40, 5, "MedDRA Version:", ln=0)
        self.set_text_color(*C_CHARCOAL)
        self.cell(0, 5, "27.0 (Default)", ln=1)
        
        self.ln(5)
        self.set_font("Arial", '', 8)
        self.set_text_color(*C_SLATE)
        self.multi_cell(0, 4, "PV-Coder provides NLP-assisted extraction and coding support. Human review remains required for ambiguous or review-flagged findings before final case disposition.")

def generate_pdf_report(case: PharmacovigilanceCase) -> bytes:
    pdf = PDFReportGenerator(case)
    pdf.render_seriousness()
    pdf.render_case_summary_cards()
    pdf.render_clinical_narrative()
    pdf.render_adverse_events()
    pdf.render_processing_summary()
    return bytes(pdf.output())
