import re
from typing import Optional, Dict

class DemographicsExtractor:
    """
    Deterministic clinical regex-based extractor for patient demographics.
    """
    
    def __init__(self):
        # Age patterns: "45-year-old", "45 y/o", "age 45", "12 months", "3 weeks old"
        self.age_pattern = re.compile(r'\b(?:age\s+)?(\d{1,3})\s*(?:year(?:s)?|yr(?:s)?|month(?:s)?|mo(?:s)?|week(?:s)?|wk(?:s)?|day(?:s)?|-year-old|-yr-old)\s*(?:old|of\s*age)?\b|(?:\b|^)(\d{1,3})\s*(?:y/o|yo)\b', re.IGNORECASE)
        
        # Gender patterns
        self.gender_pattern = re.compile(r'\b(male|female|man|woman|boy|girl|gentleman|lady)\b', re.IGNORECASE)
        
        # Weight patterns: "70 kg", "70kg", "150 lbs", "70.5 kg"
        self.weight_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:kg|kilos|kilograms|lbs|pounds)\b', re.IGNORECASE)

    def extract(self, narrative: str) -> Optional[Dict[str, Optional[str]]]:
        """
        Extracts age, gender, and weight from the narrative.
        Returns a dictionary suitable for the PatientDemographics schema.
        """
        result = {
            "age": None,
            "gender": None,
            "weight": None
        }

        # Extract Age
        age_match = self.age_pattern.search(narrative)
        if age_match:
            # Re-extract the full matched phrase for the UI
            start, end = age_match.span()
            result["age"] = narrative[start:end].strip()

        # Extract Gender
        gender_match = self.gender_pattern.search(narrative)
        if gender_match:
            result["gender"] = gender_match.group(1).lower().capitalize()

        # Extract Weight
        weight_match = self.weight_pattern.search(narrative)
        if weight_match:
            start, end = weight_match.span()
            result["weight"] = narrative[start:end].strip()

        # Return None for all if nothing was found (optional, but cleaner)
        if not result["age"] and not result["gender"] and not result["weight"]:
            return None

        return result
