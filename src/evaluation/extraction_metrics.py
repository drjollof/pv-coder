"""
Extraction evaluation metrics: token-level Precision, Recall, F1.

Token-level soft matching is used throughout because entity spans rarely align
perfectly at character boundaries when comparing NER predictions against human
annotations in biomedical corpora. A prediction counts as correct when its
token F1 with the gold span meets or exceeds the configured threshold (default 0.5).

All functions operate on plain Python strings and lists; no spaCy dependency.
"""

from __future__ import annotations

from typing import Optional


def token_f1(gold: str, pred: str) -> float:
    """
    Token-level F1 between two strings.

    Case-insensitive; whitespace-tokenised. Returns 0.0 when either string is empty.
    """
    gold_tokens = set(gold.lower().split())
    pred_tokens = set(pred.lower().split())

    if not gold_tokens or not pred_tokens:
        return 0.0

    common = gold_tokens & pred_tokens
    if not common:
        return 0.0

    precision = len(common) / len(pred_tokens)
    recall    = len(common) / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def _best_match(gold_text: str, predictions: list[str]) -> float:
    """Highest token F1 between gold_text and any element of predictions."""
    if not predictions:
        return 0.0
    return max(token_f1(gold_text, p) for p in predictions)


def compute_prf(
    gold_list: list[Optional[str]],
    pred_lists: list[list[str]],
    threshold: float = 0.5,
) -> dict[str, float]:
    """
    Compute Precision, Recall, F1 over paired gold strings and predicted span lists.

    Precision is computed at the example level: an example is counted as a true
    positive if at least one prediction's token F1 with the gold exceeds threshold.
    False positives are examples where predictions exist but none matched gold.
    False negatives are examples with gold but no prediction exceeded threshold.

    Args:
        gold_list:  One gold annotation per example (None or empty str → no gold).
        pred_lists: One list of predicted span strings per example.
        threshold:  Minimum token F1 to count as a match (default 0.5).

    Returns:
        Dict: precision, recall, f1, n_gold, n_pred, n_matched.
    """
    n_gold = n_pred = n_matched = 0

    for gold, preds in zip(gold_list, pred_lists):
        has_gold = bool(gold and str(gold).strip())
        if has_gold:
            n_gold += 1
        n_pred += len(preds)

        if has_gold and preds:
            if _best_match(str(gold), preds) >= threshold:
                n_matched += 1

    precision = n_matched / n_pred  if n_pred  > 0 else 0.0
    recall    = n_matched / n_gold  if n_gold  > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "n_gold":    n_gold,
        "n_pred":    n_pred,
        "n_matched": n_matched,
    }


def evaluate_extraction(
    results: list,
    phee_df,
    entity_type: str,
    apply_context_filter: bool = True,
    threshold: float = 0.5,
) -> dict[str, float]:
    """
    Evaluate ExtractionResult list against PHEE ground truth columns.

    The DISEASE entity type is evaluated against PHEE's effect_text column,
    which holds the annotated adverse-event text. This is a recall-oriented
    proxy: it asks whether the extraction pipeline captured the AE span as a
    disease entity at all — not whether it correctly classified it as an AE.
    Classification is downstream of this metric.

    Args:
        results:              list[ExtractionResult] aligned row-for-row with phee_df.
        phee_df:              PHEE DataFrame with columns drug_text_primary, effect_text.
        entity_type:          "drug"    → evaluates vs drug_text_primary
                              "disease" → evaluates vs effect_text
        apply_context_filter: When True, only current-context entities are scored.
        threshold:            Token F1 threshold (default 0.5).

    Returns:
        Dict: precision, recall, f1, n_gold, n_pred, n_matched.

    Raises:
        ValueError: if entity_type is not "drug" or "disease".
    """
    if entity_type == "drug":
        gold_col  = "drug_text_primary"
        get_preds = (
            (lambda r: [e.text for e in r.current_drugs()])
            if apply_context_filter
            else (lambda r: [e.text for e in r.drugs])
        )
    elif entity_type == "disease":
        gold_col  = "effect_text"
        get_preds = (
            (lambda r: [e.text for e in r.current_diseases()])
            if apply_context_filter
            else (lambda r: [e.text for e in r.diseases])
        )
    else:
        raise ValueError(
            f"Unknown entity_type {entity_type!r}. Expected 'drug' or 'disease'."
        )

    gold_list  = phee_df[gold_col].tolist()
    pred_lists = [get_preds(r) for r in results]
    return compute_prf(gold_list, pred_lists, threshold=threshold)
