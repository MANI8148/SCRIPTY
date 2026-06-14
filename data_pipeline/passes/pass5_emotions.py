from typing import List, Dict
from collections import defaultdict
import logging

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category, EMOTION_KEYWORDS, CATEGORY_META
from data_pipeline.extractors.emotion_extractor import EmotionExtractor


logger = logging.getLogger(__name__)


class EmotionExtractionPass:
    def __init__(self):
        self.extractor = EmotionExtractor()

    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            if not frag.emotion:
                emotion_info = self._get_emotion_info(frag.text)
                if emotion_info:
                    frag.emotion = emotion_info["emotion"]
                    frag.emotion_intensity = emotion_info["intensity"]
                    frag.emotion_tags.append(emotion_info["emotion"])
                    if emotion_info["emotion"] in [e.value for e in [
                        Category.ANGER, Category.FEAR, Category.JOY, Category.SADNESS,
                        Category.GUILT, Category.SHAME, Category.JEALOUSY, Category.HOPE,
                        Category.DESPERATION,
                    ]]:
                        frag.category = Category.EMOTIONS.value
                        frag.subcategory = emotion_info["emotion"]

            if not frag.tension:
                frag.tension = self.extractor.estimate_tension(frag.text)
            if not frag.stakes:
                frag.stakes = self.extractor.estimate_stakes(frag.text)

        return fragments

    def _get_emotion_info(self, text: str) -> dict:
        text_lower = text.lower()
        best_emotion = None
        best_count = 0

        for emotion, keywords in EMOTION_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_emotion = emotion

        if best_emotion:
            intensity = min(1.0, 0.3 + (best_count * 0.15))
            return {"emotion": best_emotion, "intensity": intensity}

        return {}
