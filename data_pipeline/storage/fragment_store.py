from typing import List, Optional, Dict, Any
import json
import logging
from pathlib import Path

from data_pipeline.schema.fragment import NarrativeFragment
from .jsonl_store import JsonlStore


logger = logging.getLogger(__name__)


class FragmentStore:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.fragment_store: JsonlStore[NarrativeFragment] = JsonlStore.for_fragments(
            str(self.base_path / "fragments.jsonl")
        )
        self.elite_store: JsonlStore[NarrativeFragment] = JsonlStore.for_fragments(
            str(self.base_path / "elite_fragments.jsonl")
        )

    def save_fragments(self, fragments: List[NarrativeFragment]) -> None:
        self.fragment_store.append_batch(fragments)
        elite = [f for f in fragments if f.is_elite()]
        if elite:
            self.elite_store.append_batch(elite)
        logger.info(f"Saved {len(fragments)} fragments ({len(elite)} elite)")

    def load_fragments(self) -> List[NarrativeFragment]:
        return self.fragment_store.read_all()

    def load_elite(self) -> List[NarrativeFragment]:
        return self.elite_store.read_all()

    def get_statistics(self) -> Dict[str, Any]:
        fragments = self.load_fragments()
        if not fragments:
            return {"total": 0}

        from collections import Counter, defaultdict
        stats = {
            "total": len(fragments),
            "elite": sum(1 for f in fragments if f.is_elite()),
            "by_category": Counter(f.category for f in fragments),
            "by_emotion": Counter(f.emotion for f in fragments if f.emotion),
            "by_genre": Counter(f.genre_hint for f in fragments if f.genre_hint),
            "by_relationship": Counter(f.relationship_type for f in fragments if f.relationship_type),
            "by_conflict": Counter(f.conflict_type for f in fragments if f.conflict_type),
            "by_scene_role": Counter(f.scene_role for f in fragments if f.scene_role),
            "by_book": Counter(f.source_book for f in fragments),
            "avg_quality": sum(f.quality_score for f in fragments) / len(fragments),
            "avg_tension": sum(f.tension for f in fragments if f.tension) / max(1, sum(1 for f in fragments if f.tension)),
            "avg_stakes": sum(f.stakes for f in fragments if f.stakes) / max(1, sum(1 for f in fragments if f.stakes)),
            "unique_books": len(set(f.source_book for f in fragments)),
            "unique_characters": len(set(p for f in fragments for p in f.participants)),
        }
        return stats

    def count(self) -> int:
        return self.fragment_store.count()

    def clear(self) -> None:
        self.fragment_store.clear()
        self.elite_store.clear()
