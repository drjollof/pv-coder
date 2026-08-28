import re
from typing import List

class SeriousnessClassifier:
    """
    Rule-based Seriousness Classifier.
    Follows ICH E2A guidelines via keyword matching on the event and narrative context.
    """
    
    # ICH E2A Seriousness Criteria Keywords
    SERIOUS_KEYWORDS = [
        r'\bfatal\b',
        r'\bdeath\b',
        r'\bdied\b',
        r'\blife[- ]threatening\b',
        r'\bhospitaliz(ed|ation|ing)\b',
        r'\binpatient\b',
        r'\bdisab(le|ling|ility)\b',
        r'\bincapacitat(ed|ing)\b',
        r'\bcongenital\b',
        r'\banomaly\b',
        r'\bsevere\b',
        r'\bicu\b',
        r'\bintensive care\b'
    ]
    
    def __init__(self):
        self.patterns = [re.compile(kw, re.IGNORECASE) for kw in self.SERIOUS_KEYWORDS]
        
    def is_serious(self, event_text: str, narrative: str) -> bool:
        """
        Determines if an event is serious based on its text and the surrounding narrative.
        We consider an event serious if it inherently contains a seriousness
        keyword, OR if the narrative contains a strong seriousness indicator (like death/hospitalization).
        
        For document-level keywords, if the document mentions death/hospitalization,
        we conservatively flag all extracted AEs in the document as serious.
        This is a common PV triage strategy to avoid missing critical cases.
        """
    
        for pattern in self.patterns:
            if pattern.search(event_text):
                return True
                
        for pattern in self.patterns:
            if pattern.search(narrative):
                return True
                
        return False
