from typing import List, Dict
import re
import logging
from collections import defaultdict

from data_pipeline.schema.fragment import NarrativeFragment, SceneBlueprint
from data_pipeline.parsers.base_parser import ParsedDocument


logger = logging.getLogger(__name__)


class ScenePatternExtractor:
    def execute(self, documents: List[ParsedDocument], fragments: List[NarrativeFragment]) -> List[SceneBlueprint]:
        blueprints = []

        for doc in documents:
            doc_frags = [f for f in fragments if f.source_book == doc.title]
            grouped = self._group_by_scene(doc_frags)
            for scene_key, scene_frags in grouped.items():
                bp = self._build_blueprint(doc, scene_key, scene_frags)
                if bp:
                    blueprints.append(bp)

        logger.info(f"Extracted {len(blueprints)} scene blueprints")
        return blueprints

    def _group_by_scene(self, fragments: List[NarrativeFragment]) -> Dict[tuple, List[NarrativeFragment]]:
        grouped = defaultdict(list)
        for frag in fragments:
            key = (frag.chapter, frag.scene)
            grouped[key].append(frag)
        return dict(grouped)

    def _build_blueprint(self, doc: ParsedDocument, scene_key: tuple, fragments: List[NarrativeFragment]) -> SceneBlueprint:
        chapter, scene_num = scene_key

        tensions = [f.tension for f in fragments if f.tension]
        emotions = [f.emotion for f in fragments if f.emotion]
        participants = list(set(
            p for f in fragments for p in f.participants
        ))
        genres = list(set(f.genre_hint for f in fragments if f.genre_hint))
        roles = [f.scene_role for f in fragments if f.scene_role]
        locations = list(set(f.location for f in fragments if f.location))

        opening = self._find_opening_pattern(fragments)
        conflict = self._find_conflict_pattern(fragments)
        revelation = self._find_revelation_pattern(fragments)
        climax = self._find_climax_pattern(fragments)
        ending = self._find_ending_pattern(fragments)

        reusable = []
        if opening:
            reusable.append(f"opening:{opening}")
        if conflict:
            reusable.append(f"conflict:{conflict}")
        if revelation:
            reusable.append(f"revelation:{revelation}")

        return SceneBlueprint(
            source_book=doc.title,
            chapter=chapter,
            scene_number=scene_num,
            opening_pattern=opening,
            conflict_pattern=conflict,
            revelation_pattern=revelation,
            climax_pattern=climax,
            ending_pattern=ending,
            tension_curve=tensions,
            emotion_arc=emotions,
            participants=participants,
            location=locations[0] if locations else "",
            genre_hints=genres,
            reusable_patterns=reusable,
        )

    def _find_opening_pattern(self, fragments: List[NarrativeFragment]) -> str:
        for f in fragments:
            if f.scene_role == "opening":
                t = f.text[:150].lower()
                if "once upon" in t or "it was" in t:
                    return "storybook_opening"
                if "the " in t[:20]:
                    return "direct_opening"
                if "when" in t[:30]:
                    return "temporal_opening"
                return "standard_opening"
        return ""

    def _find_conflict_pattern(self, fragments: List[NarrativeFragment]) -> str:
        for f in fragments:
            if f.conflict_type:
                return f.conflict_type
        if any(f.tension and f.tension > 0.6 for f in fragments):
            return "rising_tension"
        return ""

    def _find_revelation_pattern(self, fragments: List[NarrativeFragment]) -> str:
        for f in fragments:
            if f.scene_role == "revelation":
                return "character_revelation"
        for f in fragments:
            if "discover" in f.text.lower() or "realiz" in f.text.lower():
                return "discovery_revelation"
        return ""

    def _find_climax_pattern(self, fragments: List[NarrativeFragment]) -> str:
        for f in fragments:
            if f.scene_role == "climax":
                t = f.text.lower()
                if "fight" in t or "battle" in t:
                    return "combat_climax"
                if "argu" in t or "confront" in t:
                    return "confrontation_climax"
                return "emotional_climax"
        if any(f.tension and f.tension > 0.8 for f in fragments):
            return "high_tension_climax"
        return ""

    def _find_ending_pattern(self, fragments: List[NarrativeFragment]) -> str:
        for f in fragments:
            if f.scene_role in ("resolution", "ending"):
                return "resolution_ending"
        return ""
