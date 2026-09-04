import re
from typing import Optional, Dict

class DemographicsExtractor:
    """
    Deterministic clinical regex-based extractor for patient demographics.
    """
    
    def __init__(self):
        # Age patterns: "45-year-old", "45 y/o", "age 45", "12 months old"
        # Explicitly avoid bare "12 months" (could be drug duration) unless it has age context.
        self.age_pattern = re.compile(
            r'\b(?:'
            r'age\s+\d{1,3}(?:\s*(?:years?|months?|weeks?|days?))?|'
            r'\d{1,3}\s*(?:years?|yrs?|months?|mos?|weeks?|wks?|days?)\s+(?:old|of\s+age)|'
            r'\d{1,3}\s*-\s*(?:year|yr|month|mo|week|wk|day)\s*-\s*old|'
            r'\d{1,3}\s*(?:y/o|yo)'
            r')\b', 
            re.IGNORECASE
        )
        
        # Gender patterns
        self.gender_pattern = re.compile(r'\b(male|female|man|woman|boy|girl|gentleman|lady)\b', re.IGNORECASE)
        
        # Weight patterns: "70 kg", "70kg", "150 lbs", "70.5 kg"
        self.weight_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:kg|kilos|kilograms|lbs|pounds)\b', re.IGNORECASE)

        # Family member context to avoid attributing family demographics to the patient
        self.family_pattern = re.compile(r'\b(mother|father|brother|sister|son|daughter|wife|husband|uncle|aunt|grandmother|grandfather|cousin|niece|nephew)\b', re.IGNORECASE)

    def _get_sentence(self, text: str, start: int, end: int) -> str:
        s_start = max(0, text.rfind('.', 0, start) + 1)
        s_end = text.find('.', end)
        s_end = s_end if s_end != -1 else len(text)
        return text[s_start:s_end]

    def extract(self, narrative: str) -> Optional[Dict[str, Optional[str]]]:
        """
        Extracts age, gender, and weight from the narrative.
        Ignores mentions that appear in the same sentence as family members.
        """
        result = {"age": None, "gender": None, "weight": None}

        # Extract Age
        for match in self.age_pattern.finditer(narrative):
            sentence = self._get_sentence(narrative, match.start(), match.end())
            if not self.family_pattern.search(sentence):
                result["age"] = match.group(0).strip()
                break

        # Extract Gender
        for match in self.gender_pattern.finditer(narrative):
            sentence = self._get_sentence(narrative, match.start(), match.end())
            if not self.family_pattern.search(sentence):
                result["gender"] = match.group(1).lower().capitalize()
                break

        # Extract Weight
        for match in self.weight_pattern.finditer(narrative):
            sentence = self._get_sentence(narrative, match.start(), match.end())
            if not self.family_pattern.search(sentence):
                result["weight"] = match.group(0).strip()
                break

        if not any(result.values()):
            return None

        return result
