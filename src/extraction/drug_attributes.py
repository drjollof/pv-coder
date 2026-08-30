import re
from typing import Optional, Dict

class DrugAttributeExtractor:
    """
    Deterministic clinical regex-based extractor for drug attributes
    (dose, frequency, route) using a proximity windowing technique.
    """
    
    def __init__(self):
        # Dose: digits (optional decimal) followed by mg, g, mcg, ml, units, u
        self.dose_pattern = re.compile(r'\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|units?|u))\b', re.IGNORECASE)
        
        # Frequency: BID, TID, QID, daily, qd, q4h, etc.
        self.freq_pattern = re.compile(r'\b(bid|tid|qid|daily|qd|q[1-9]h(?:rs)?|twice a day|three times a day|every \d+ hours)\b', re.IGNORECASE)
        
        # Route: PO, IV, IM, subq, oral, orally, intravenous, subcutaneous
        self.route_pattern = re.compile(r'\b(po|iv|im|subq|oral(?:ly)?|intravenous(?:ly)?|subcutaneous(?:ly)?)\b', re.IGNORECASE)

    def extract_for_drug(self, drug_end_char: int, narrative: str, window_size: int = 75) -> Dict[str, Optional[str]]:
        """
        Scans the text immediately following a drug mention for dosing patterns.
        """
        # Ensure we don't go out of bounds
        end_idx = min(drug_end_char + window_size, len(narrative))
        window = narrative[drug_end_char:end_idx]
        
        result = {
            "dose": None,
            "frequency": None,
            "route": None
        }
        
        dose_match = self.dose_pattern.search(window)
        if dose_match:
            result["dose"] = dose_match.group(1).lower()
            
        freq_match = self.freq_pattern.search(window)
        if freq_match:
            result["frequency"] = freq_match.group(1).lower()
            
        route_match = self.route_pattern.search(window)
        if route_match:
            result["route"] = route_match.group(1).lower()
            
        return result
