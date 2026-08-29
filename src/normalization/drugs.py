import json
from pathlib import Path
from typing import Dict, Any, Optional

class DrugNormalizer:
    def __init__(self, dict_path: str = "data/drug_dictionary.json"):
        self.dict_path = Path(dict_path)
        self.dictionary: Dict[str, Dict[str, Any]] = {}
        self.load_dictionary()

    def load_dictionary(self):
        if self.dict_path.exists():
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
        else:
            print(f"Warning: Drug dictionary not found at {self.dict_path}")

    def normalize(self, raw_drug: str) -> Optional[Dict[str, Any]]:
        # Normalise to lowercase for matching
        key = raw_drug.lower().strip()
        if key in self.dictionary:
            return self.dictionary[key]
        return None
