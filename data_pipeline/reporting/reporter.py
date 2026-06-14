from typing import List, Dict, Any
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

from data_pipeline.schema.fragment import NarrativeFragment, ForeshadowingLink, SceneBlueprint, CharacterMemoryFragment
from data_pipeline.config import DEFAULT_PIPELINE_CONFIG


logger = logging.getLogger(__name__)


class Reporter:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or DEFAULT_PIPELINE_CONFIG["report_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_reports(
        self,
        fragments: List[NarrativeFragment],
        foreshadowing_links: List[ForeshadowingLink],
        scene_blueprints: List[SceneBlueprint],
        character_memories: List[CharacterMemoryFragment],
    ) -> Dict[str, str]:
        reports = {}

        report_generators = [
            ("corpus_statistics.json", self._corpus_statistics),
            ("emotion_statistics.json", self._emotion_statistics),
            ("genre_statistics.json", self._genre_statistics),
            ("dialogue_statistics.json", self._dialogue_statistics),
            ("relationship_statistics.json", self._relationship_statistics),
            ("conflict_statistics.json", self._conflict_statistics),
            ("narrative_device_statistics.json", self._narrative_device_statistics),
            ("scene_pattern_statistics.json", self._scene_pattern_statistics),
            ("quality_distribution.json", self._quality_distribution),
        ]

        for filename, generator in report_generators:
            try:
                data = generator(fragments)
                path = self.output_dir / filename
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                reports[filename] = str(path)
                logger.info(f"Report generated: {path}")
            except Exception as e:
                logger.warning(f"Failed to generate {filename}: {e}")

        if foreshadowing_links:
            path = self.output_dir / "foreshadowing_report.json"
            with open(path, 'w') as f:
                json.dump(self._foreshadowing_report(foreshadowing_links), f, indent=2)
            reports["foreshadowing_report.json"] = str(path)

        if character_memories:
            path = self.output_dir / "character_memory_report.json"
            with open(path, 'w') as f:
                json.dump(self._character_memory_report(character_memories), f, indent=2)
            reports["character_memory_report.json"] = str(path)

        summary = self._generate_summary(reports, fragments)
        path = self.output_dir / "pipeline_summary.json"
        with open(path, 'w') as f:
            json.dump(summary, f, indent=2)
        reports["pipeline_summary.json"] = str(path)

        return reports

    def _corpus_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        return {
            "total_fragments": len(fragments),
            "elite_fragments": sum(1 for f in fragments if f.is_elite()),
            "unique_books": len(set(f.source_book for f in fragments)),
            "unique_authors": len(set(f.author for f in fragments if f.author)),
            "fragments_per_book": dict(Counter(f.source_book for f in fragments).most_common(20)),
            "category_distribution": dict(Counter(f.category for f in fragments).most_common()),
            "subcategory_distribution": dict(Counter(f.subcategory for f in fragments if f.subcategory).most_common(30)),
            "avg_quality": round(sum(f.quality_score for f in fragments) / len(fragments), 3),
            "avg_tension": round(sum(f.tension for f in fragments if f.tension) / max(1, sum(1 for f in fragments if f.tension)), 3),
            "avg_stakes": round(sum(f.stakes for f in fragments if f.stakes) / max(1, sum(1 for f in fragments if f.stakes)), 3),
        }

    def _emotion_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        emotions = [f.emotion for f in fragments if f.emotion]
        return {
            "total_emotional_fragments": len(emotions),
            "emotion_distribution": dict(Counter(emotions).most_common()),
            "avg_intensity_by_emotion": {
                e: round(sum(f.emotion_intensity for f in fragments if f.emotion == e) / max(1, sum(1 for f in fragments if f.emotion == e)), 3)
                for e in set(emotions)
            },
        }

    def _genre_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        genres = [f.genre_hint for f in fragments if f.genre_hint]
        genre_by_book = {}
        for book in set(f.source_book for f in fragments):
            book_genres = [f.genre_hint for f in fragments if f.source_book == book and f.genre_hint]
            if book_genres:
                genre_by_book[book] = dict(Counter(book_genres).most_common())
        return {
            "total_genre_tagged": len(genres),
            "genre_distribution": dict(Counter(genres).most_common()),
            "genre_by_book": genre_by_book,
        }

    def _dialogue_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        dialogue_frags = [f for f in fragments if "dialogue" in f.category]
        return {
            "total_dialogue_fragments": len(dialogue_frags),
            "dialogue_subcategory_distribution": dict(Counter(f.subcategory for f in dialogue_frags).most_common()),
            "unique_speakers": len(set(f.speaker for f in dialogue_frags if f.speaker)),
            "most_frequent_speakers": dict(Counter(f.speaker for f in dialogue_frags if f.speaker).most_common(20)),
        }

    def _relationship_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        rel_frags = [f for f in fragments if f.relationship_type]
        return {
            "total_relationship_fragments": len(rel_frags),
            "relationship_type_distribution": dict(Counter(f.relationship_type for f in rel_frags).most_common()),
            "books_with_relationships": len(set(f.source_book for f in rel_frags)),
        }

    def _conflict_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        conflict_frags = [f for f in fragments if f.conflict_type]
        return {
            "total_conflict_fragments": len(conflict_frags),
            "conflict_type_distribution": dict(Counter(f.conflict_type for f in conflict_frags).most_common()),
            "conflict_by_book": {
                b: dict(Counter(f.conflict_type for f in fragments if f.source_book == b and f.conflict_type).most_common())
                for b in set(f.source_book for f in conflict_frags)
            },
        }

    def _narrative_device_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        device_frags = [f for f in fragments if f.metadata.get("narrative_device")]
        return {
            "total_device_fragments": len(device_frags),
            "device_distribution": dict(Counter(f.metadata["narrative_device"] for f in device_frags).most_common()),
        }

    def _scene_pattern_statistics(self, fragments: List[NarrativeFragment]) -> dict:
        scene_frags = [f for f in fragments if f.scene_role]
        return {
            "total_scene_role_tagged": len(scene_frags),
            "scene_role_distribution": dict(Counter(f.scene_role for f in scene_frags).most_common()),
            "narrative_function_distribution": dict(Counter(f.narrative_function for f in fragments if f.narrative_function).most_common()),
        }

    def _quality_distribution(self, fragments: List[NarrativeFragment]) -> dict:
        quality_scores = [f.quality_score for f in fragments]
        return {
            "min": round(min(quality_scores), 3),
            "max": round(max(quality_scores), 3),
            "mean": round(sum(quality_scores) / len(quality_scores), 3),
            "median": round(sorted(quality_scores)[len(quality_scores) // 2], 3),
            "elite_count": sum(1 for f in fragments if f.is_elite()),
            "acceptable_count": sum(1 for f in fragments if 0.60 <= f.quality_score < 0.85),
            "distribution_deciles": {
                f"p{(i+1)*10}": round(np.percentile(quality_scores, (i+1)*10), 3)
                for i in range(10)
            } if quality_scores else {},
        }

    def _foreshadowing_report(self, links: List[ForeshadowingLink]) -> dict:
        return {
            "total_links": len(links),
            "avg_distance": round(sum(l.distance for l in links) / len(links), 1) if links else 0,
            "links_per_book": dict(Counter(l.source_book for l in links).most_common()),
            "high_confidence_links": sum(1 for l in links if l.confidence >= 0.7),
        }

    def _character_memory_report(self, memories: List[CharacterMemoryFragment]) -> dict:
        return {
            "total_memories": len(memories),
            "memory_type_distribution": dict(Counter(m.memory_type for m in memories if m.memory_type).most_common()),
            "unique_characters": len(set(m.character for m in memories if m.character)),
            "changes_distribution": {
                "belief_changes": sum(len(m.belief_changes) for m in memories),
                "goal_changes": sum(len(m.goal_changes) for m in memories),
                "relationship_changes": sum(len(m.relationship_changes) for m in memories),
                "knowledge_changes": sum(len(m.knowledge_changes) for m in memories),
            },
        }

    def _generate_summary(self, reports: Dict[str, str], fragments: List[NarrativeFragment]) -> dict:
        return {
            "pipeline_run": datetime.utcnow().isoformat(),
            "total_fragments": len(fragments),
            "reports_generated": list(reports.keys()),
            "output_directory": str(self.output_dir),
            "status": "completed",
        }


try:
    import numpy as np
except ImportError:
    import statistics as _s
    np = None
    def _percentile(data, p):
        data = sorted(data)
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= len(data):
            return data[-1]
        return data[f] * (c - k) + data[c] * (k - f)
