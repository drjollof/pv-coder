from typing import Optional
import pandas as pd
from pathlib import Path

from src.extraction.entities import ExtractionPipeline
from src.extraction.events import EventBuilder, EventType
from src.normalization.retrieval import HybridRetriever
from src.normalization.lexical import LexicalNormalizer
from src.normalization.embeddings import SemanticNormalizer
from src.pv.case_schema import PharmacovigilanceCase, NormalizedEvent
from src.pv.seriousness import SeriousnessClassifier


class CaseBuilder:
    def __init__(self, dict_path: str, faiss_index_path: str = None):
        print("Initializing NER Pipeline...")
        self.ner = ExtractionPipeline()

        print("Initializing Event Builder...")
        self.event_builder = EventBuilder()

        print("Initializing Normalizer...")
        dictionary = pd.read_parquet(dict_path)
        self.semantic = SemanticNormalizer(dictionary, faiss_index_path=faiss_index_path)

        print("Initializing Seriousness Classifier...")
        self.seriousness = SeriousnessClassifier()

    def process(self, narrative: str, case_id: str) -> PharmacovigilanceCase:
        """
        Processes a raw clinical narrative into a structured PharmacovigilanceCase.
        """
        candidates = self.ner.extract(narrative)
        events = self.event_builder.build(candidates, narrative)
        adverse_events = [e for e in events if e.event_type == EventType.ADVERSE_EVENT]

        normalized_events = []
        for ae in adverse_events:
            norm_results, review_status = self.semantic.match(ae.effect.text, top_k=3)

            top_candidates = []
            if norm_results:
                meddra_pt, meddra_pt_id, conf = norm_results[0]
                for pt, pt_id, score in norm_results:
                    top_candidates.append({"pt": pt, "id": pt_id, "score": score})
            else:
                meddra_pt, meddra_pt_id, conf = "Unknown", "Unknown", 0.0

            suspected_drugs = [d.text for d in ae.drugs]
            is_serious = self.seriousness.is_serious(ae.effect.text, narrative)

            causality = getattr(ae, 'causality', None)
            outcome = getattr(ae, 'outcome', None)

            normalized_events.append(NormalizedEvent(
                effect_text=ae.effect.text,
                meddra_pt=meddra_pt,
                meddra_pt_id=meddra_pt_id,
                confidence_score=conf,
                review_status=review_status,
                top_candidates=top_candidates,
                suspected_drugs=suspected_drugs,
                is_serious=is_serious,
                is_speculated=ae.is_speculated,
                causality=causality,
                outcome=outcome
            ))

        is_serious_case = any(e.is_serious for e in normalized_events)

        return PharmacovigilanceCase(
            case_id=case_id,
            narrative=narrative,
            events=normalized_events,
            is_serious_case=is_serious_case
        )
