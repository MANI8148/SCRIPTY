from __future__ import annotations
import re
import string
from typing import Any

from backend.v2.types import (
    MemoryEntry,
    NarrativePackage,
    SceneObjective,
    WorldConstraints,
)


# ── Category keyword patterns from data pipeline extractors ──────────────

_DIALOGUE_PATTERNS = re.compile(
    r'["\u201c\u201d]|'
    r'\b(?:said|asked|replied|cried|whispered|shouted|murmured|answered|'
    r'exclaimed|called|told|spoke|uttered|demanded|offered)\b',
    re.IGNORECASE,
)

_BODY_LANGUAGE_PATTERNS = re.compile(
    r'\b(?:shook|nodded|shrugged|gestured|recoiled|flinched|trembled|'
    r'clenched|stiffened|relaxed|slumped|straightened|crossed|'
    r'folded|unfolded|bowed|bent|knelt|raised.*(?:hand|arm|eyebrow)|'
    r'glanced|stared|looked.*away|averted|met.*(?:gaze|eye)|'
    r'sigh|grin|frown|scowl|smirk|wince)\b',
    re.IGNORECASE,
)

_ACTION_PATTERNS = re.compile(
    r'\b(?:ran|walked|moved|jumped|pushed|pulled|grabbed|caught|'
    r'threw|struck|hit|kicked|lunged|dove|sprang|rushed|'
    r'advanced|retreated|entered|exited|paced|circled|'
    r'climbed|crawled|slid|ducked|leaped|charged|fled|'
    r'reached|seized|snatched|grasped|hurled|sprinted|vaulted)\b',
    re.IGNORECASE,
)

_REACTION_PATTERNS = re.compile(
    r'\b(?:startled|surprised|shocked|stunned|alarmed|horrified|'
    r'terrified|recoiled|gasped|froze|flinched|jumped.*back|'
    r'drew.*breath|caught.*(?:breath|off.*guard)|'
    r'stepped.*back|backed.*away|reared)\b',
    re.IGNORECASE,
)

_EMOTION_PATTERNS = re.compile(
    r'\b(?:angry|afraid|scared|fearful|joyful|happy|sad|melancholy|'
    r'bitter|guilty|ashamed|proud|hopeful|despair|anxious|nervous|'
    r'calm|peaceful|rage|fury|terror|dread|delight|sorrow|grief|'
    r'envy|jealous|grateful|relieved|lonely|nostalgia|'
    r'felt|feeling|emotion|passion|'
    r'tears|wept|crying|sobbing|weeping|wailed|trembled)\b',
    re.IGNORECASE,
)

_SENSORY_PATTERNS = re.compile(
    r'\b(?:smell|scent|aroma|fragrance|stench|odor|'
    r'heard|sound|noise|silence|echo|creak|rustle|'
    r'saw|seen|glimpse|sight|vision|gaze|'
    r'light|shadow|dark|bright|dim|gloom|'
    r'cold|warm|hot|chill|breeze|wind|'
    r'touch|texture|rough|smooth|soft|hard|'
    r'taste|bitter|sweet|sour|salt)\b',
    re.IGNORECASE,
)

_RELATIONSHIP_PATTERNS = re.compile(
    r'\b(?:friend|enemy|ally|rival|lover|partner|'
    r'brother|sister|mother|father|son|daughter|'
    r'comrade|companion|colleague|associate|'
    r'trusted|betrayed|abandoned|protected|'
    r'together|between|apart|separated|united)\b',
    re.IGNORECASE,
)

_THOUGHT_PATTERNS = re.compile(
    r'\b(?:thought|wondered|reflected|considered|pondered|'
    r'contemplated|mused|speculated|realized|understood|'
    r'believed|doubted|suspected|imagined|supposed|'
    r'decided|concluded|reasoned|remembered|forgot|'
    r'wished|hoped|feared|desired|yearned)\b',
    re.IGNORECASE,
)

_CATEGORY_CLASSIFIERS: list[tuple[str, re.Pattern, float]] = [
    ("dialogue", _DIALOGUE_PATTERNS, 0.07),
    ("thought", _THOUGHT_PATTERNS, 0.06),
    ("reaction", _REACTION_PATTERNS, 0.06),
    ("body_language", _BODY_LANGUAGE_PATTERNS, 0.06),
    ("emotion", _EMOTION_PATTERNS, 0.05),
    ("relationship", _RELATIONSHIP_PATTERNS, 0.06),
    ("sensory", _SENSORY_PATTERNS, 0.05),
    ("action", _ACTION_PATTERNS, 0.06),
]


def _classify_memory(mem: MemoryEntry) -> str:
    """Classify a memory entry into one of the 8 NarrativePackage categories.

    Strategy:
    1. Use explicit `mem.category` if set (from RAGBridge corpus metadata).
    2. Check for quoted speech (strongest signal for dialogue).
    3. Use keyword pattern matching with match-count thresholds.
    4. Fall back to `` (unclassified) for graceful degradation.
    """
    if mem.category:
        return mem.category

    text = mem.text.strip()
    if not text:
        return ""

    word_count = len(text.split())

    # Strongest signal: quoted speech → dialogue (only for meaningful texts)
    if ('"' in text or '\u201c' in text or '\u201d' in text) and word_count >= 3:
        return "dialogue"

    best_slot = ""
    best_density = 0.0
    for slot_name, pattern, min_density in _CATEGORY_CLASSIFIERS:
        matches = pattern.findall(text)
        match_count = len(matches)
        density = match_count / max(word_count, 1)
        if density >= min_density and density > best_density:
            best_density = density
            best_slot = slot_name

    if best_slot:
        return best_slot

    # If no classifier matched but emotion_tags exist and text is long enough
    if mem.emotion_tags and word_count >= 3:
        return "emotion"

    return ""


class NarrativeRetriever:
    """Transforms flat MemoryEntry lists into category-aware NarrativePackages.

    Each entry is classified and routed to the appropriate slot in a
    NarrativePackage, enabling the DramaticRealizer to pull content
    by narrative function (dialogue, action, body language, etc.).

    No new FAISS indexes are created — classification is purely
    post-retrieval using keyword patterns aligned with the data
    pipeline extractors.
    """

    def __init__(
        self,
        memory_system: Any | None = None,
    ) -> None:
        self._memory = memory_system

    def retrieve(
        self,
        objective: SceneObjective,
        world: WorldConstraints,
        memories: list[MemoryEntry],
    ) -> NarrativePackage:
        """Classify a list of memories into a structured NarrativePackage.

        Args:
            objective: Current scene objective (purpose, characters, tension).
            world: World constraints for context.
            memories: Flat list of retrieved MemoryEntry objects.

        Returns:
            NarrativePackage with memories routed to their most likely slot.
        """
        package = NarrativePackage()
        slot_map = {
            "dialogue": package.dialogue_examples,
            "action": package.action_examples,
            "body_language": package.body_language_examples,
            "reaction": package.reaction_examples,
            "sensory": package.sensory_examples,
            "emotion": package.emotion_examples,
            "relationship": package.relationship_examples,
            "thought": package.thought_examples,
        }

        for mem in memories:
            slot = _classify_memory(mem)
            if slot in slot_map:
                slot_map[slot].append(mem)
            else:
                # Unclassified — route based on emotion_tags or put in emotion slot
                if mem.emotion_tags:
                    package.emotion_examples.append(mem)
                else:
                    # If truly unclassifiable and high relevance, put in emotion slot
                    if mem.relevance_score >= 0.4:
                        package.emotion_examples.append(mem)

        # Deduplicate within each slot (by text overlap)
        for slot_name, slot_list in slot_map.items():
            package = self._deduplicate_slot(package, slot_name, slot_list)

        return package

    def _deduplicate_slot(
        self,
        package: NarrativePackage,
        slot_name: str,
        entries: list[MemoryEntry],
    ) -> NarrativePackage:
        """Remove near-duplicate entries from a single slot."""
        if not entries:
            return package
        unique: list[MemoryEntry] = []
        slot_map = {
            "dialogue": "dialogue_examples",
            "action": "action_examples",
            "body_language": "body_language_examples",
            "reaction": "reaction_examples",
            "sensory": "sensory_examples",
            "emotion": "emotion_examples",
            "relationship": "relationship_examples",
            "thought": "thought_examples",
        }
        attr = slot_map[slot_name]
        seen: set[str] = set()
        for e in entries:
            sig = " ".join(e.text.lower().split()[:15])
            if sig not in seen:
                seen.add(sig)
                unique.append(e)
        setattr(package, attr, unique)
        return package

    @staticmethod
    def build_minimal_package(memories: list[MemoryEntry]) -> NarrativePackage:
        """Build a minimal NarrativePackage from a flat memory list.

        Used as a fallback when no NarrativeRetriever is configured.
        Classifies memories and fills all 8 slots.
        """
        retriever = NarrativeRetriever()
        from backend.v2.types import SceneType
        dummy_obj = SceneObjective(
            purpose="",
            characters_involved=[],
            location="",
            conflict_type="",
            required_tension=0.5,
            target_scene_type=SceneType.DESCRIPTION,
            resolution_goal="",
        )
        dummy_world = WorldConstraints(
            era="modern",
            tech_level="modern",
            tone="neutral",
            infrastructure=[],
            transport=[],
        )
        return retriever.retrieve(dummy_obj, dummy_world, memories)

    def get(
        self,
        package: NarrativePackage,
        slot: str,
        index: int = 0,
    ) -> MemoryEntry | None:
        """Safely access a MemoryEntry from a NarrativePackage slot."""
        return getattr(package, slot, [None])[index] if hasattr(package, slot) else None
