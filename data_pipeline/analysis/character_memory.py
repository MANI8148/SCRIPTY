from typing import List, Dict
import re
import logging
from collections import defaultdict

from data_pipeline.schema.fragment import NarrativeFragment, CharacterMemoryFragment
from data_pipeline.parsers.base_parser import ParsedDocument


logger = logging.getLogger(__name__)


BELIEF_CHANGE_INDICATORS = [
    "realized", "understood", "came to believe", "changed his mind",
    "changed her mind", "no longer believed", "now saw",
    "began to think", "started to see", "shifted",
]

GOAL_CHANGE_INDICATORS = [
    "changed his goal", "changed her goal", "new goal",
    "shifted focus", "different path", "changed course",
    "abandoned", "gave up", "pursued a new",
]

RELATIONSHIP_CHANGE_INDICATORS = [
    "grew closer", "drifted apart", "became friends", "became enemies",
    "fell in love", "fell out of love", "lost trust", "gained trust",
    "betrayed", "reconciled", "forgave",
]

KNOWLEDGE_CHANGE_INDICATORS = [
    "learned", "discovered", "found out", "uncovered",
    "revealed to", "taught", "informed",
]


class CharacterMemoryExtractor:
    def execute(self, documents: List[ParsedDocument], fragments: List[NarrativeFragment]) -> List[CharacterMemoryFragment]:
        memories = []
        for doc in documents:
            doc_frags = [f for f in fragments if f.source_book == doc.title]
            doc_memories = self._extract_memories_for_document(doc, doc_frags)
            memories.extend(doc_memories)
        logger.info(f"Extracted {len(memories)} character memory fragments")
        return memories

    def _extract_memories_for_document(self, doc: ParsedDocument, fragments: List[NarrativeFragment]) -> List[CharacterMemoryFragment]:
        memories = []
        for frag in fragments:
            memory = self._extract_memory_from_fragment(frag)
            if memory:
                memories.append(memory)
        return memories

    def _extract_memory_from_fragment(self, frag: NarrativeFragment) -> CharacterMemoryFragment:
        text_lower = frag.text.lower()

        belief_changes = self._find_matches(text_lower, BELIEF_CHANGE_INDICATORS)
        goal_changes = self._find_matches(text_lower, GOAL_CHANGE_INDICATORS)
        relationship_changes = self._find_matches(text_lower, RELATIONSHIP_CHANGE_INDICATORS)
        knowledge_changes = self._find_matches(text_lower, KNOWLEDGE_CHANGE_INDICATORS)

        if not any([belief_changes, goal_changes, relationship_changes, knowledge_changes]):
            return None

        memory_type = self._classify_memory(text_lower)

        return CharacterMemoryFragment(
            source_book=frag.source_book,
            author=frag.author,
            chapter=frag.chapter,
            character=frag.participants[0] if frag.participants else "",
            memory_type=memory_type,
            belief_changes=belief_changes,
            goal_changes=goal_changes,
            relationship_changes=relationship_changes,
            knowledge_changes=knowledge_changes,
            trigger_text=frag.text,
            trigger_category=frag.category,
            emotion=frag.emotion,
            intensity=frag.emotion_intensity,
        )

    def _find_matches(self, text: str, indicators: List[str]) -> List[str]:
        return [ind for ind in indicators if ind in text]

    def _classify_memory(self, text: str) -> str:
        if any(w in text for w in ["remember", "memory", "recall", "flashback"]):
            return "memory_recall"
        if any(w in text for w in ["realiz", "understand", "comprehend"]):
            return "realization"
        if any(w in text for w in ["learn", "discover", "find out"]):
            return "knowledge_gain"
        if any(w in text for w in ["change", "shift", "transform", "evolve"]):
            return "transformation"
        return "observation"
