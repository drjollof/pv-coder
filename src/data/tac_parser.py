"""
TAC 2017 ADR XML parser.

Converts annotated XML label files into three flat tables:
  - mentions    (Mention elements)
  - relations   (Relation elements)
  - reactions   (Reaction elements — the normalised ADR vocabulary)

Raw files are never modified; all outputs go to the processed directory.

Gold guard
----------
The gold_xml split is the held-out evaluation set. This module refuses to
parse it unless allow_gold=True is passed explicitly. The preprocessing
pipeline (scripts/run_preprocessing.py) always passes allow_gold=False.
Only evaluation scripts should call parse_gold().

Terminology note
----------------
Reaction.str values are TAC-derived normalised ADR strings. They are NOT
MedDRA Preferred Term codes and should not be represented as such.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple

import pandas as pd

_GOLD_GUARD_MESSAGE = (
    "Attempted to parse TAC gold_xml without explicit allow_gold=True. "
    "The gold split is the held-out evaluation set and must remain frozen "
    "until final evaluation. Pass allow_gold=True only in dedicated "
    "evaluation scripts."
)


def _parse_single_xml(
    path: Path, split: str
) -> Tuple[list, list, list]:
    """
    Parse one TAC XML label file into mention, relation, and reaction records.

    Discontinuous spans (comma-separated start/len attributes) are stored
    verbatim in start_raw/len_raw. The is_discontinuous flag and n_spans
    count are derived automatically. The mention_str attribute already
    contains the resolved text string from the annotation tool.

    Returns:
        (mentions, relations, reactions) as lists of dicts.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    drug = root.attrib.get("drug", "UNKNOWN")
    file_name = path.name

    mentions: list[dict] = []
    relations: list[dict] = []
    reactions: list[dict] = []

    mentions_el = root.find("Mentions")
    if mentions_el is not None:
        for m in mentions_el.findall("Mention"):
            start_raw = m.attrib.get("start", "")
            len_raw = m.attrib.get("len", "")
            is_discontinuous = "," in start_raw
            n_spans = len(start_raw.split(",")) if start_raw else 1

            mentions.append({
                "drug": drug,
                "split": split,
                "file": file_name,
                "mention_id": m.attrib.get("id"),
                "section_id": m.attrib.get("section"),
                "mention_type": m.attrib.get("type"),
                "mention_str": m.attrib.get("str"),
                "start_raw": start_raw,
                "len_raw": len_raw,
                "is_discontinuous": is_discontinuous,
                "n_spans": n_spans,
            })

    relations_el = root.find("Relations")
    if relations_el is not None:
        for r in relations_el.findall("Relation"):
            relations.append({
                "drug": drug,
                "split": split,
                "file": file_name,
                "relation_id": r.attrib.get("id"),
                "relation_type": r.attrib.get("type"),
                "arg1": r.attrib.get("arg1"),
                "arg2": r.attrib.get("arg2"),
            })

    reactions_el = root.find("Reactions")
    if reactions_el is not None:
        for rx in reactions_el.findall("Reaction"):
            raw_str = rx.attrib.get("str", "")
            
            # Extract MedDRA normalizations
            meddra_pt = None
            meddra_pt_id = None
            norm = rx.find("Normalization")
            if norm is not None:
                meddra_pt = norm.attrib.get("meddra_pt")
                meddra_pt_id = norm.attrib.get("meddra_pt_id")
                
            reactions.append({
                "drug": drug,
                "split": split,
                "file": file_name,
                "reaction_id": rx.attrib.get("id"),
                "reaction_str": raw_str.lower().strip(),
                "meddra_pt": meddra_pt,
                "meddra_pt_id": meddra_pt_id,
            })

    return mentions, relations, reactions


def parse_directory(
    xml_dir: Path,
    split: str,
    allow_gold: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Parse all XML files in a TAC directory.

    Args:
        xml_dir:    Directory containing the XML files.
        split:      'train' or 'gold'.
        allow_gold: Must be True to parse the gold split. Defaults to False.

    Returns:
        (mentions_df, relations_df, reactions_df)

    Raises:
        PermissionError: if split == 'gold' and allow_gold is False.
        FileNotFoundError: if xml_dir does not exist.
        ValueError: if no XML files are found.
    """
    if split == "gold" and not allow_gold:
        raise PermissionError(_GOLD_GUARD_MESSAGE)

    xml_dir = Path(xml_dir)
    if not xml_dir.exists():
        raise FileNotFoundError(f"TAC XML directory not found: {xml_dir}")

    xml_files = sorted(xml_dir.glob("*.xml"))
    if not xml_files:
        raise ValueError(f"No XML files found in {xml_dir}")

    all_mentions: list[dict] = []
    all_relations: list[dict] = []
    all_reactions: list[dict] = []

    for xf in xml_files:
        m, r, rx = _parse_single_xml(xf, split)
        all_mentions.extend(m)
        all_relations.extend(r)
        all_reactions.extend(rx)

    return (
        pd.DataFrame(all_mentions),
        pd.DataFrame(all_relations),
        pd.DataFrame(all_reactions),
    )


def parse_train(tac_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Parse the train_xml split. Safe for use during development.

    Args:
        tac_dir: Root TAC directory containing train_xml/ and gold_xml/.

    Returns:
        (mentions_df, relations_df, reactions_df) — split == 'train' only.
    """
    return parse_directory(
        Path(tac_dir) / "train_xml",
        split="train",
        allow_gold=False,
    )


def parse_gold(tac_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Parse the gold_xml split.

    This function must only be called from dedicated evaluation scripts,
    after all model development and threshold tuning is complete.

    Args:
        tac_dir: Root TAC directory containing train_xml/ and gold_xml/.

    Returns:
        (mentions_df, relations_df, reactions_df) — split == 'gold' only.
    """
    return parse_directory(
        Path(tac_dir) / "gold_xml",
        split="gold",
        allow_gold=True,
    )
