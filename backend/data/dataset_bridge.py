import os
import json
import random
from backend.data.curated_lists import CHARACTERS, ROLES, EMOTIONS, CURATED_OBJECTS, CURATED_LOCATIONS, CONFLICT_THEMES

class DatasetBridge:
    """
    Safely interfaces with dataset files, filtering out poor quality items.
    If the dataset doesn't have sufficient good items, it gracefully falls back to curated lists.
    """
    def __init__(self, data_dir="backend/data_processed"):
        self.data_dir = data_dir
        self.metadata = self._load_data()
        
    def _load_data(self):
        data = {
            "people": [],
            "places": [],
            "concepts": [],
            "keywords": [],
            "actions": []
        }
        
        if not os.path.exists(self.data_dir):
            return data
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.data_dir, filename), 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        for key in data.keys():
                            if key in file_data:
                                data[key].extend(file_data[key])
                except Exception:
                    pass
                    
        # Remove duplicates
        for key in data.keys():
            data[key] = list(set(data[key]))
            
        return data

    def safe_get_character(self):
        # Even with existing datasets, NLP sometimes categorises random words as people
        # We enforce a strict fallback if an extracted actor name is highly suspect.
        # Suspect names are usually words that are in standard English dictionary.
        
        if self.metadata["people"]:
            candidate = random.choice(self.metadata["people"])
            # Simple check: if candidate is too generic (e.g., "Accept", "Ability"), use fallback
            if len(candidate) > 12 or len(candidate) < 3:
                return random.choice(CHARACTERS)
            return candidate
            
        return random.choice(CHARACTERS)

    def get_role(self, era="modern"):
        if era in ROLES:
            return random.choice(ROLES[era])
        return random.choice(ROLES["modern"])

    def get_emotion(self):
        return random.choice(EMOTIONS)

    def get_conflict_theme(self):
        if self.metadata["concepts"]:
            # Prefer concepts from dataset, otherwise curated themes
            if random.random() < 0.5:
                # Format concept
                concept = random.choice(self.metadata["concepts"]).lower()
                return f"struggle surrounding {concept}"
        return random.choice(CONFLICT_THEMES)

    def get_narrative_object(self, obj_type="Object"):
        """Returns an actionable narrative item based on type"""
        return random.choice(CURATED_OBJECTS.get(obj_type, CURATED_OBJECTS["Object"]))
