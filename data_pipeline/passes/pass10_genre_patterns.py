from typing import List
import logging

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category, GENRE_KEYWORDS


logger = logging.getLogger(__name__)


class GenrePatternExtractionPass:
    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            if not frag.genre_hint:
                genre = self._detect_genre(frag.text)
                if genre:
                    frag.genre_hint = genre
                    frag.genre_tags.append(genre)
                    frag.retrieval_tags.append(f"genre:{genre}")

        return fragments

    def _detect_genre(self, text: str) -> str:
        text_lower = text.lower()
        best_genre = None
        best_count = 0

        for genre, keywords in GENRE_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_genre = genre

        if best_count >= 1:
            return best_genre
        return ""
