from typing import List, Optional
import logging

from data_pipeline.parsers.base_parser import ParsedDocument, ParsedChapter, ParsedScene
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category, get_group
from data_pipeline.extractors import (
    DialogueExtractor,
    BodyLanguageExtractor,
    ActionExtractor,
    ReactionExtractor,
    MemoryExtractor,
    SensoryExtractor,
    ThoughtExtractor,
    EmotionExtractor,
    RelationshipExtractor,
)
from data_pipeline.config import EXTRACTION_CONFIG


logger = logging.getLogger(__name__)


class NarrativeFragmentExtractionPass:
    def __init__(self):
        self.dialogue = DialogueExtractor()
        self.body_language = BodyLanguageExtractor()
        self.actions = ActionExtractor()
        self.reactions = ReactionExtractor()
        self.memories = MemoryExtractor()
        self.sensory = SensoryExtractor()
        self.thoughts = ThoughtExtractor()
        self.emotions = EmotionExtractor()
        self.relationships = RelationshipExtractor()

    def execute(self, documents: List[ParsedDocument]) -> List[NarrativeFragment]:
        all_fragments = []
        for doc in documents:
            fragments = self._process_document(doc)
            all_fragments.extend(fragments)
            logger.info(f"Extracted {len(fragments)} fragments from {doc.title}")
        return all_fragments

    def _process_document(self, doc: ParsedDocument) -> List[NarrativeFragment]:
        fragments = []
        fragment_id = 0

        for chapter in doc.chapters:
            for scene in chapter.scenes:
                for pi, para in enumerate(scene.paragraphs):
                    if len(para) < EXTRACTION_CONFIG["min_paragraph_length"]:
                        continue
                    if len(para) > EXTRACTION_CONFIG["max_paragraph_length"]:
                        continue

                    extracted = self._extract_from_paragraph(para, doc, chapter, scene, pi)
                    for ext in extracted:
                        ext.id = f"frag_{doc.title}_{chapter.number}_{scene.number}_{pi}_{fragment_id}"
                        fragment_id += 1
                        fragments.append(ext)

        return fragments

    def _extract_from_paragraph(
        self, text: str, doc: ParsedDocument,
        chapter: ParsedChapter, scene: ParsedScene, para_idx: int
    ) -> List[NarrativeFragment]:
        results = []

        all_extractions = []
        all_extractions.extend(self.dialogue.extract(text, para_idx))
        all_extractions.extend(self.body_language.extract(text, para_idx))
        all_extractions.extend(self.actions.extract(text, para_idx))
        all_extractions.extend(self.reactions.extract(text, para_idx))
        all_extractions.extend(self.memories.extract(text, para_idx))
        all_extractions.extend(self.sensory.extract(text, para_idx))
        all_extractions.extend(self.thoughts.extract(text, para_idx))
        all_extractions.extend(self.emotions.extract(text, para_idx))
        all_extractions.extend(self.relationships.extract(text, para_idx))

        if not all_extractions:
            frag = self._make_fragment(
                text, doc, chapter, scene, para_idx,
                category=Category.ACTIONS.value,
                subcategory=Category.PHYSICAL_ACTIONS.value,
            )
            results.append(frag)
            return results

        for ext in all_extractions:
            emotion_info = self._get_primary_emotion(ext)
            frag = self._make_fragment(
                text, doc, chapter, scene, para_idx,
                category=ext.get("category", Category.ACTIONS.value),
                subcategory=ext.get("subcategory", ""),
                emotion=emotion_info.get("emotion", ""),
                emotion_intensity=emotion_info.get("intensity", 0.0),
                participants=ext.get("participants", []),
                speaker=ext.get("speaker", ""),
                target=ext.get("target", ""),
                relationship_type=ext.get("relationship_type", ""),
            )
            frag.metadata["extractor_confidence"] = ext.get("confidence", 0.5)
            frag.tension = self.emotions.estimate_tension(text)
            frag.stakes = self.emotions.estimate_stakes(text)
            results.append(frag)

        if len(results) > 8:
            results.sort(key=lambda x: x.metadata.get("extractor_confidence", 0), reverse=True)
            results = results[:8]

        return results

    def _make_fragment(
        self, text: str, doc: ParsedDocument,
        chapter: ParsedChapter, scene: ParsedScene, para_idx: int,
        category: str = "", subcategory: str = "",
        emotion: str = "", emotion_intensity: float = 0.0,
        participants: Optional[List[str]] = None,
        speaker: str = "", target: str = "",
        relationship_type: str = "",
    ) -> NarrativeFragment:
        return NarrativeFragment(
            source_book=doc.title,
            author=doc.author,
            chapter=chapter.number,
            scene=scene.number,
            paragraph=para_idx,
            text=text,
            category=category,
            subcategory=subcategory,
            emotion=emotion,
            emotion_intensity=emotion_intensity,
            participants=participants or [],
            speaker=speaker,
            target=target,
            relationship_type=relationship_type,
            scene_role=self._detect_scene_role(text),
            narrative_function=self._detect_narrative_function(text),
        )

    def _detect_scene_role(self, text: str) -> str:
        t = text[:100].lower()
        openers = ["the ", "it was", "there was", "once", "when", "as"]
        if any(t.startswith(o) for o in openers):
            return "opening"
        if any(w in t for w in ["suddenly", "abruptly", "without warning"]):
            return "climax"
        if any(w in t for w in ["finally", "at last", "in the end"]):
            return "resolution"
        if any(w in t for w in ["meanwhile", "later", "after"]):
            return "rising_action"
        return ""

    def _detect_narrative_function(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ["explain", "describe", "told about", "history"]):
            return "exposition"
        if any(w in t for w in ["argu", "conflict", "fight", "disagree"]):
            return "conflict_escalation"
        if any(w in t for w in ["realiz", "understand", "suddenly knew"]):
            return "revelation"
        if any(w in t for w in ["city", "town", "building", "street", "landscape"]):
            return "worldbuilding"
        if any(w in t for w in ["remember", "thought back", "recall"]):
            return "character_development"
        return "plot_advancement"

    def _get_primary_emotion(self, ext: dict) -> dict:
        emotion = ext.get("emotion", "")
        intensity = ext.get("emotion_intensity", 0.0)
        if emotion:
            return {"emotion": emotion, "intensity": intensity}

        text = ext.get("text", "")
        for emotion_type, keywords in EXTRACTION_CONFIG["emotion_indicators"].items():
            for kw in keywords:
                if kw in text.lower():
                    return {"emotion": emotion_type, "intensity": 0.6}
        return {"emotion": "", "intensity": 0.0}
