from typing import Optional
import pandas as pd
from pathlib import Path

from src.extraction.entities import ExtractionPipeline
from src.extraction.events import EventBuilder, EventType
from src.normalization.retrieval import HybridRetriever
from src.normalization.lexical import LexicalNormalizer
from src.normalization.embeddings import SemanticNormalizer
from src.normalization.drugs import DrugNormalizer
from src.pv.case_schema import PharmacovigilanceCase, NormalizedEvent, ExtractedDrug
from src.pv.seriousness import SeriousnessClassifier


class CaseBuilder:
    def __init__(self, dict_path: str, faiss_index_path: str = None):
        print("Initializing NER Pipeline...", flush=True)
        self.ner = ExtractionPipeline()

        print("Initializing Event Builder...", flush=True)
        self.event_builder = EventBuilder()

        print("Initializing Normalizer...", flush=True)
        dictionary = pd.read_parquet(dict_path)
        self.semantic = SemanticNormalizer(dictionary, faiss_index_path=faiss_index_path)

        print("Initializing Drug Normalizer...", flush=True)
        self.drug_normalizer = DrugNormalizer()

        print("Initializing Seriousness Classifier...", flush=True)
        self.seriousness = SeriousnessClassifier()

    def process(self, narrative: str, case_id: str) -> PharmacovigilanceCase:
        """
        Processes a raw clinical narrative into a structured PharmacovigilanceCase.
        """
        print(f"[{case_id}] Extracting entities...", flush=True)
        candidates = self.ner.extract(narrative)
        print(f"[{case_id}] Building events...", flush=True)
        events, excluded_findings = self.event_builder.build(candidates, narrative)
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

            suspected_drugs = []
            for d in ae.drugs:
                norm_dict = self.drug_normalizer.normalize(d.text)
                suspected_drugs.append(ExtractedDrug(
                    text=d.text,
                    start_char=d.start_char,
                    end_char=d.end_char,
                    canonical_name=norm_dict.get('canonical_name') if norm_dict else None,
                    identifiers=norm_dict.get('identifiers') if norm_dict else None
                ))

            is_serious, seriousness_reason, seriousness_evidence = self.seriousness.is_serious(ae.effect.text, narrative)

            causality = getattr(ae, 'causality', None)
            outcome = getattr(ae, 'outcome', None)

            normalized_events.append(NormalizedEvent(
                effect_text=ae.effect.text,
                start_char=ae.effect.start_char,
                end_char=ae.effect.end_char,
                meddra_pt=meddra_pt,
                meddra_pt_id=meddra_pt_id,
                confidence_score=conf,
                review_status=review_status,
                top_candidates=top_candidates,
                suspected_drugs=suspected_drugs,
                is_serious=is_serious,
                seriousness_reason=seriousness_reason,
                seriousness_evidence=seriousness_evidence,
                is_speculated=ae.is_speculated,
                causality=causality,
                outcome=outcome
            ))

        is_serious_case = False
        case_seriousness_reason = None
        case_seriousness_evidence = None
        for e in normalized_events:
            if e.is_serious:
                is_serious_case = True
                case_seriousness_reason = e.seriousness_reason
                case_seriousness_evidence = e.seriousness_evidence
                break

        extracted_drugs = []
        for d in candidates.drugs:
            norm_dict = self.drug_normalizer.normalize(d.text)
            extracted_drugs.append(ExtractedDrug(
                text=d.text,
                start_char=d.start_char,
                end_char=d.end_char,
                canonical_name=norm_dict.get('canonical_name') if norm_dict else None,
                identifiers=norm_dict.get('identifiers') if norm_dict else None
            ))

        return PharmacovigilanceCase(
            case_id=case_id,
            narrative=narrative,
            events=normalized_events,
            extracted_drugs=extracted_drugs,
            excluded_findings=excluded_findings,
            is_serious_case=is_serious_case,
            case_seriousness_reason=case_seriousness_reason,
            case_seriousness_evidence=case_seriousness_evidence
        )
