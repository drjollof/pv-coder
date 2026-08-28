#!/usr/bin/env python3
"""
Preprocessing Script.

Reads raw PHEE and TAC train data and writes parquet files to data/processed/.
"""

import argparse
from pathlib import Path
import pandas as pd

from src.data.phee_parser import parse_all
from src.data.tac_parser import parse_train

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phee-dir", default="data/PHEE", help="PHEE data directory")
    parser.add_argument("--tac-dir", default="data/TAC2017", help="TAC 2017 data directory")
    parser.add_argument("--out-dir", default="data/processed", help="Output directory")
    args = parser.parse_args()

    phee_dir = Path(args.phee_dir)
    tac_dir = Path(args.tac_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Parsing PHEE dataset...")
    phee_df = parse_all(phee_dir)
    phee_path = out_dir / "phee_events.parquet"
    phee_df.to_parquet(phee_path, index=False)
    print(f"Saved {len(phee_df)} PHEE events to {phee_path}")

    print("Parsing TAC 2017 dataset...")
    mentions, relations, reactions = parse_train(tac_dir)
    
    mentions_path = out_dir / "tac_mentions.parquet"
    mentions.to_parquet(mentions_path, index=False)
    print(f"Saved {len(mentions)} TAC mentions to {mentions_path}")

    relations_path = out_dir / "tac_relations.parquet"
    relations.to_parquet(relations_path, index=False)
    print(f"Saved {len(relations)} TAC relations to {relations_path}")

    reactions_path = out_dir / "tac_reactions.parquet"
    reactions.to_parquet(reactions_path, index=False)
    print(f"Saved {len(reactions)} TAC reactions to {reactions_path}")

    print("Extracting MedDRA dictionary...")
    meddra_dict = reactions[["reaction_str", "meddra_pt", "meddra_pt_id"]].dropna().drop_duplicates(subset=["meddra_pt_id"])
    dict_path = out_dir / "tac_meddra_dict.parquet"
    meddra_dict.to_parquet(dict_path, index=False)
    print(f"Saved {len(meddra_dict)} unique MedDRA terms to {dict_path}")

if __name__ == "__main__":
    main()
