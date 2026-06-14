from typing import List, Dict
import re
import logging
from collections import defaultdict

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category, SCENE_ROLES
from data_pipeline.config import EXTRACTION_CONFIG


logger = logging.getLogger(__name__)


class ScenePatternExtractionPass:
    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            if not frag.scene_role:
                role = self._detect_scene_role(frag.text, frag)
                if role:
                    frag.scene_role = role
                    frag.retrieval_tags.append(f"scene_role:{role}")

        return fragments

    def _detect_scene_role(self, text: str, frag: NarrativeFragment) -> str:
        t = text.lower()

        if any(w in t for w in ["suddenly", "without warning", "all at once",
                                 "out of nowhere", "in that instant"]):
            return "turning_point"

        if any(w in t for w in ["finally", "at last", "in the end",
                                "and so", "thus it was"]):
            if any(w in t for w in ["but", "however", "yet", "though"]):
                return "climax"
            return "resolution"

        if any(w in t for w in ["meanwhile", "later", "the next",
                                "after that", "then"]):
            return "rising_action"

        if frag.tension and frag.tension > 0.7:
            return "climax"

        if any(w in t for w in ["if only", "had he known", "little did",
                                 "what he didn't know"]):
            return "setup"

        first_100 = t[:100]
        if any(first_100.startswith(w) for w in ["the ", "it was", "there was",
                                                  "once ", "in the", "a "]):
            return "opening"

        if any(w in t for w in ["?", "!"]) and any(w in t for w in ["reveal", "discover",
                                                                     "find out", "truth"]):
            return "revelation"

        if any(w in t for w in ["to be continued", "cliffhanger", "what would",
                                 "little did they know", "would they"]):
            return "cliffhanger"

        return ""
