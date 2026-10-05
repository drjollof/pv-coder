#!/usr/bin/env python3
"""
Event-Level Evaluation Script.

Evaluates PharmacovigilanceEvent reconstruction against the PHEE dev set.

This evaluator measures whether the reconstructed event contains:
- the expected effect, and
- the expected primary drug.

EventBuilder.build() returns:
    (events, excluded_findings)
"""

from pathlib import Path

import pandas as pd

from src.extraction.entities import ExtractionPipeline
from src.extraction.events import EventBuilder


def spans_overlap(span1: str, span2: str) -> bool:
    """Return True when two text spans share at least one token."""
    if not span1 or not span2:
        return False

    s1 = set(span1.lower().split())
    s2 = set(span2.lower().split())

    return bool(s1.intersection(s2))


def main():
    phee_path = Path("data/processed/phee_events.parquet")

    if not phee_path.exists():
        print(f"PHEE parquet not found: {phee_path}")
        return

    df = pd.read_parquet(phee_path)
    df = df[df["split"] == "dev"]

    pipeline = ExtractionPipeline()
    builder = EventBuilder()

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    evaluated_records = 0
    skipped_records = 0

    print(
        f"Evaluating {len(df)} dev records "
        "for event reconstruction..."
    )

    for _, row in df.iterrows():
        text = str(row["text"])

        gold_drug = row.get("drug_text_primary")
        gold_effect = row.get("effect_text")

        # Only evaluate records with a usable gold
        # drug/effect pair.
        if not gold_drug or not gold_effect:
            skipped_records += 1
            continue

        evaluated_records += 1

        result = pipeline.extract(text)

        events, excluded_findings = builder.build(
            result,
            text,
        )

        matched = False

        for event in events:
            effect_matches = spans_overlap(
                gold_effect,
                event.effect.text,
            )

            drug_matches = any(
                spans_overlap(gold_drug, drug.text)
                for drug in event.drugs
            )

            if effect_matches and drug_matches:
                matched = True
                break

        if matched:
            true_positives += 1
        else:
            false_negatives += 1

        # Count reconstructed events as false positives
        # except for the single event that matched the
        # gold annotation.
        false_positives += len(events) - (
            1 if matched else 0
        )

    precision = (
        true_positives
        / (true_positives + false_positives)
        if true_positives + false_positives > 0
        else 0.0
    )

    recall = (
        true_positives
        / (true_positives + false_negatives)
        if true_positives + false_negatives > 0
        else 0.0
    )

    f1 = (
        2 * (precision * recall) / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    print()
    print("Event Reconstruction Evaluation")
    print("--------------------------------")
    print(f"Evaluated records: {evaluated_records}")
    print(f"Skipped records:   {skipped_records}")
    print(f"True positives:    {true_positives}")
    print(f"False positives:   {false_positives}")
    print(f"False negatives:   {false_negatives}")
    print()
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")


if __name__ == "__main__":
    main()