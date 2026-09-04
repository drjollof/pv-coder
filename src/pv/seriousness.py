import re
from typing import List, Tuple, Optional

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
        r'\bserious\b',
        r'\bicu\b',
        r'\bintensive care\b'
    ]
    
    def __init__(self):
        self.patterns = [(kw.strip(r'\b'), re.compile(kw, re.IGNORECASE)) for kw in self.SERIOUS_KEYWORDS]
        
    def is_serious(self, event_text: str, narrative: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Determines if an event is serious based on its text and the surrounding narrative.
        We consider an event serious if it inherently contains a seriousness
        keyword, OR if the narrative contains a strong seriousness indicator (like death/hospitalization).
        
        For document-level keywords, if the document mentions death/hospitalization,
        we conservatively flag all extracted AEs in the document as serious.
        This is a common PV triage strategy to avoid missing critical cases.
        """
    
        for reason, pattern in self.patterns:
            match = pattern.search(event_text)
            if match:
                # Find the sentence containing the match for evidence
                start = max(0, event_text.rfind('.', 0, match.start()) + 1)
                end = event_text.find('.', match.end())
                end = end if end != -1 else len(event_text)
                evidence = event_text[start:end].strip()
                return True, reason.capitalize(), evidence
                
        for reason, pattern in self.patterns:
            match = pattern.search(narrative)
            if match:
                # Find the sentence containing the match for evidence
                start = max(0, narrative.rfind('.', 0, match.start()) + 1)
                end = narrative.find('.', match.end())
                end = end if end != -1 else len(narrative)
                evidence = narrative[start:end].strip()
                return True, reason.capitalize(), evidence
                
        return False, None, None
