from typing import List
import json
import logging
from pathlib import Path

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.config import EXTRACTION_CONFIG as _


logger = logging.getLogger(__name__)


class CorpusBuilder:
    def build(self, fragments: List[NarrativeFragment], output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            for frag in fragments:
                entry = self._build_entry(frag)
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        logger.info(f"RAG corpus saved to {output_path} ({len(fragments)} entries)")

    def _build_entry(self, frag: NarrativeFragment) -> dict:
        retrieval_tags = list(set(frag.retrieval_tags))

        if frag.emotion:
            retrieval_tags.append(f"emotion:{frag.emotion}")
        if frag.genre_hint:
            retrieval_tags.append(f"genre:{frag.genre_hint}")
        if frag.category:
            retrieval_tags.append(f"category:{frag.category}")
        if frag.conflict_type:
            retrieval_tags.append(f"conflict:{frag.conflict_type}")
        if frag.relationship_type:
            retrieval_tags.append(f"relationship:{frag.relationship_type}")
        if frag.scene_role:
            retrieval_tags.append(f"scene_role:{frag.scene_role}")
        if frag.quality_score >= 0.85:
            retrieval_tags.append("quality:elite")

        keywords = list(set(frag.keywords))
        if not keywords:
            import re
            words = re.findall(r'\b[A-Z][a-z]{3,}\b', frag.text)
            keywords = list(set(w.lower() for w in words))[:10]

        return {
            "id": frag.id,
            "text": frag.text,
            "source_book": frag.source_book,
            "author": frag.author,
            "chapter": frag.chapter,
            "scene": frag.scene,
            "category": frag.category,
            "subcategory": frag.subcategory,
            "emotion": frag.emotion,
            "emotion_intensity": frag.emotion_intensity,
            "tension": frag.tension,
            "stakes": frag.stakes,
            "genre_hint": frag.genre_hint,
            "participants": frag.participants,
            "speaker": frag.speaker,
            "target": frag.target,
            "relationship_type": frag.relationship_type,
            "conflict_type": frag.conflict_type,
            "goal": frag.goal,
            "motivation": frag.motivation,
            "location": frag.location,
            "time_period": frag.time_period,
            "scene_role": frag.scene_role,
            "narrative_function": frag.narrative_function,
            "quality_score": frag.quality_score,
            "embedding": frag.embedding,
            "keywords": keywords,
            "emotion_tags": frag.emotion_tags,
            "genre_tags": frag.genre_tags,
            "retrieval_tags": retrieval_tags,
        }
