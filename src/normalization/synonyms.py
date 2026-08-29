import json
from pathlib import Path
from typing import Dict, Optional

class SynonymNormalizer:
    def __init__(self, dict_path: str = "data/custom_synonyms.json"):
        self.dict_path = Path(dict_path)
        self.dictionary: Dict[str, str] = {}
        self.load_dictionary()

    def load_dictionary(self):
        if self.dict_path.exists():
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
        else:
            print(f"Warning: Synonym dictionary not found at {self.dict_path}")

    def normalize(self, surface_form: str) -> str:
        """
        Returns the expanded synonym if it exists, otherwise returns the surface_form.
        """
        key = surface_form.lower().strip()
        return self.dictionary.get(key, surface_form)
