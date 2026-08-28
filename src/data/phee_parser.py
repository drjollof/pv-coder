"""
PHEE parquet parser.

Converts raw train/dev/test parquet files into a flat, analysis-ready event table.
Raw data files are never modified; all outputs go to the processed directory.

Output schema is documented in docs/data_schema.md.
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd


def _extract_text_from_span(span_value) -> Optional[str]:
    """
    Collapse the list-of-lists span format [[text, ...], ...] to the first text token.

    PHEE stores text as [[token]] for single spans and [[t1], [t2]] for discontinuous.
    We extract only the first span here; full offsets are preserved in raw_event_data.
    """
    if not span_value:
        return None
    try:
        inner = span_value[0]
        if isinstance(inner, list):
            return str(inner[0]) if inner else None
        return str(inner) if inner is not None else None
    except (IndexError, TypeError):
        return None


def _extract_all_drug_texts(treatment: dict) -> list[str]:
    """
    Extract every drug text mention from Treatment.Drug.text.

    Drug.text is a list of span groups: [[drug_a], [drug_b], ...].
    We flatten to a deduplicated ordered list of drug strings.
    """
    drug = treatment.get("Drug")
    if not drug or not isinstance(drug, dict):
        return []

    text_val = drug.get("text", [])
    if not isinstance(text_val, list):
        return []

    seen: dict[str, None] = {}
    for span_group in text_val:
        if isinstance(span_group, list):
            for item in span_group:
                if item is not None:
                    s = str(item).strip()
                    if s:
                        seen[s] = None
        elif span_group is not None:
            s = str(span_group).strip()
            if s:
                seen[s] = None

    return list(seen.keys())


def _flatten_event(
    ev_row: dict,
    row_id: str,
    row_text: str,
    split: str,
    is_mult_event: bool,
) -> dict:
    """
    Convert one event row (event_id, event_type, event_data) into a flat record.

    event_data is a JSON-encoded string and must be parsed. Missing arguments
    produce None, not empty strings, so callers can distinguish absent from empty.
    """
    raw_event_data: str = ev_row.get("event_data", "{}")
    try:
        ed: dict = json.loads(raw_event_data)
    except (json.JSONDecodeError, TypeError):
        ed = {}

    trigger = ed.get("Trigger") or {}
    effect = ed.get("Effect") or {}
    treatment = ed.get("Treatment") or {}
    subject = ed.get("Subject") or {}
    severity = ed.get("Severity") or {}
    speculated = ed.get("Speculated") or {}

    drug_texts = _extract_all_drug_texts(treatment)

    return {
        "id": row_id,
        "split": split,
        "text": row_text,
        "is_mult_event": is_mult_event,
        "event_id": ev_row.get("event_id", ""),
        "event_type": ev_row.get("event_type", ""),
        "trigger_text": _extract_text_from_span(trigger.get("text")),
        "effect_text": _extract_text_from_span(effect.get("text")),
        "drug_text_primary": drug_texts[0] if drug_texts else None,
        "drug_texts": json.dumps(drug_texts),
        "disorder_text": _extract_text_from_span(
            (treatment.get("Disorder") or {}).get("text")
        ),
        "subject_text": _extract_text_from_span(subject.get("text")),
        "age_text": _extract_text_from_span(
            (subject.get("Age") or {}).get("text")
        ),
        "sex_text": _extract_text_from_span(
            (subject.get("Gender") or {}).get("text")
        ),
        "route_text": _extract_text_from_span(
            (treatment.get("Route") or {}).get("text")
        ),
        "dosage_text": _extract_text_from_span(
            (treatment.get("Dosage") or {}).get("text")
        ),
        "frequency_text": _extract_text_from_span(
            (treatment.get("Freq") or {}).get("text")
        ),
        "duration_text": _extract_text_from_span(
            (treatment.get("Duration") or {}).get("text")
        ),
        "severity": severity.get("value") if isinstance(severity, dict) else None,
        "speculated": bool(speculated.get("value", False))
        if isinstance(speculated, dict)
        else False,
        "is_combination": bool(treatment.get("Combination")),
        "raw_event_data": raw_event_data,
    }


def parse_split(parquet_path: Path, split: str) -> pd.DataFrame:
    """
    Parse a single PHEE parquet file and return a flat event DataFrame.

    Args:
        parquet_path: Absolute path to the parquet file (read-only).
        split: 'train', 'dev', or 'test'.

    Returns:
        DataFrame with one row per annotated event.
    """
    if not parquet_path.exists():
        raise FileNotFoundError(f"PHEE parquet not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    records = []
    for _, row in df.iterrows():
        row_id = str(row["id"])
        row_text = str(row["context"])
        is_mult_event = bool(row["is_mult_event"])
        annotations = row["annotations"]

        if not annotations:
            continue

        for ann_block in annotations:
            if not isinstance(ann_block, dict):
                continue
            events = ann_block.get("events", [])
            for ev_row in events:
                if not isinstance(ev_row, dict):
                    continue
                records.append(
                    _flatten_event(ev_row, row_id, row_text, split, is_mult_event)
                )

    return pd.DataFrame(records)


def parse_all(phee_dir: Path) -> pd.DataFrame:
    """
    Parse train, dev, and test splits and return a concatenated DataFrame.

    Args:
        phee_dir: Directory containing train.parquet, dev.parquet, test.parquet.

    Returns:
        Concatenated DataFrame with a 'split' column identifying the source.
    """
    phee_dir = Path(phee_dir)
    frames = []
    for split in ("train", "dev", "test"):
        path = phee_dir / f"{split}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"PHEE split not found: {path}")
        frame = parse_split(path, split)
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)
