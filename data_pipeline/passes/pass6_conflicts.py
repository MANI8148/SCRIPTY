from typing import List
import logging
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category
from data_pipeline.config import EXTRACTION_CONFIG


logger = logging.getLogger(__name__)


class ConflictExtractionPass:
    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            if not frag.conflict_type:
                conflict = self._detect_conflict(frag.text)
                if conflict:
                    frag.conflict_type = conflict["type"]
                    frag.category = Category.CONFLICTS.value
                    frag.subcategory = conflict["subcategory"]
                    frag.retrieval_tags.append(f"conflict:{conflict['type']}")

        return fragments

    def _detect_conflict(self, text: str) -> dict:
        text_lower = text.lower()
        best_type = None
        best_sub = None
        best_count = 0

        for conflict_type, indicators in EXTRACTION_CONFIG["conflict_indicators"].items():
            count = sum(1 for ind in indicators if ind in text_lower)
            if count > best_count:
                best_count = count
                best_type = conflict_type

        if best_count > 0:
            sub_map = {
                "internal": Category.INTERNAL_CONFLICTS,
                "interpersonal": Category.INTERPERSONAL_CONFLICTS,
                "group": Category.GROUP_CONFLICTS,
                "institutional": Category.INSTITUTIONAL_CONFLICTS,
                "moral": Category.MORAL_CONFLICTS,
            }
            return {
                "type": best_type,
                "subcategory": sub_map.get(best_type, Category.INTERNAL_CONFLICTS).value,
            }

        return {}
