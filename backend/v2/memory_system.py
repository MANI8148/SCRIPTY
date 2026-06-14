from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from backend.v2.memory_callback import CallbackScheduler
from backend.v2.memory_consequence import ConsequenceEngine, ConsequenceEntry, ConsequenceStore
from backend.v2.memory_emotional import EmotionalRetrievalEngine
from backend.v2.memory_interpretation import InterpretationEngine, InterpretationEntry, InterpretationStore
from backend.v2.memory_relationship import RelationshipDelta, RelationshipDeltaStore, RelationshipDeltaTracker
from backend.v2.rag_bridge import RAGBridge
from backend.v2.types import (
    CharacterBeliefs,
    ConsequenceEntry,
    InterpretationEntry,
    MemoryEntry,
    MemoryQuery,
    RelationKind,
    RelationshipDelta,
    ScheduledCallback,
)


@dataclass
class EpisodicStore:
    records: list[MemoryEntry] = field(default_factory=list)

    def add(self, entry: MemoryEntry) -> None:
        self.records.append(entry)

    def query(self, character: str, top_k: int = 5) -> list[MemoryEntry]:
        relevant = [r for r in self.records if character in r.characters]
        relevant.sort(key=lambda r: r.relevance_score, reverse=True)
        return relevant[:top_k]


@dataclass
class SemanticStore:
    facts: list[MemoryEntry] = field(default_factory=list)

    def add(self, entry: MemoryEntry) -> None:
        self.facts.append(entry)

    def query(self, entity: str) -> list[MemoryEntry]:
        return [f for f in self.facts if entity.lower() in f.text.lower()]


class MemorySystem:
    """Subjective character knowledge.

    Only the MemorySystem holds what characters know.
    WorldState holds objective truth — there is no cross-sync.

    Extended with advanced memory modules:
      - InterpretationMemory: how characters interpret events
      - ConsequenceMemory: outcomes of character actions
      - EmotionalRetrieval: emotion-based memory recall
      - RelationshipDeltaTracker: relationship change history
      - CallbackScheduler: dramatic timing for memory resurfacing
    """

    def __init__(
        self,
        rag_bridge: RAGBridge | None = None,
        fragments_path: str | None = None,
    ) -> None:
        self.episodic = EpisodicStore()
        self.semantic = SemanticStore()
        self._character_beliefs: dict[str, CharacterBeliefs] = {}

        # Advanced memory modules
        self.interpretation_engine = InterpretationEngine()
        self.consequence_engine = ConsequenceEngine()
        self.emotional_retrieval = EmotionalRetrievalEngine()
        self.relationship_deltas = RelationshipDeltaTracker()
        self.callback_scheduler = CallbackScheduler()

        # RAG bridge — single source for all corpus data
        self.rag_bridge = rag_bridge
        if self.rag_bridge is not None:
            self.rag_bridge.load()
            # Pre-seed episodic memories from corpus fragments via RAGBridge
            self._seed_from_rag_bridge()
        elif fragments_path is not None:
            # Fallback: direct file read (deprecated path)
            self._load_fragments(fragments_path)

    # ------------------------------------------------------------------ #
    # Fragment seeding from data pipeline output
    # ------------------------------------------------------------------ #

    def _seed_from_rag_bridge(self) -> None:
        """Seed episodic memories from RAGBridge fragments (all characters)."""
        if self.rag_bridge is None or not self.rag_bridge.is_loaded:
            return
        fragments = self.rag_bridge.retrieve_fragments(top_k=100)
        for entry in fragments:
            self.episodic.add(entry)
            self.emotional_retrieval.episodic_records.append(entry)

    def _load_fragments(self, path: str) -> None:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    entry = MemoryEntry(
                        text=data.get("trigger_text", ""),
                        source="corpus_fragment",
                        chapter_num=data.get("chapter", 0),
                        scene_num=data.get("scene", 0),
                        characters=[data.get("character", "")],
                        relevance_score=0.6,
                        emotion_tags=[data.get("emotion", "")] if data.get("emotion") else [],
                    )
                    self.episodic.add(entry)
                    self.emotional_retrieval.episodic_records.append(entry)
        except (FileNotFoundError, json.JSONDecodeError, IsADirectoryError):
            pass

    # ------------------------------------------------------------------ #
    # Basic character management
    # ------------------------------------------------------------------ #

    def register_character(self, name: str) -> None:
        if name not in self._character_beliefs:
            self._character_beliefs[name] = CharacterBeliefs()

    def beliefs_for(self, character: str) -> CharacterBeliefs:
        return self._character_beliefs.setdefault(character, CharacterBeliefs())

    # ------------------------------------------------------------------ #
    # Basic record/store/retrieve (backward compatible)
    # ------------------------------------------------------------------ #

    def record_event(
        self,
        text: str,
        chapter_num: int,
        scene_num: int,
        characters: list[str],
        relevance_score: float = 0.5,
        emotion_tags: list[str] | None = None,
    ) -> None:
        entry = MemoryEntry(
            text=text,
            source="generated",
            chapter_num=chapter_num,
            scene_num=scene_num,
            characters=characters,
            relevance_score=relevance_score,
            emotion_tags=emotion_tags or [],
        )
        self.episodic.add(entry)
        # Also keep emotional retrieval in sync
        self.emotional_retrieval.episodic_records.append(entry)

    def record_fact(
        self,
        text: str,
        chapter_num: int,
        scene_num: int,
        characters: list[str],
    ) -> None:
        entry = MemoryEntry(
            text=text,
            source="semantic",
            chapter_num=chapter_num,
            scene_num=scene_num,
            characters=characters,
            relevance_score=1.0,
        )
        self.semantic.add(entry)

    def store(self, entry: MemoryEntry) -> None:
        if entry.source == "semantic":
            self.semantic.add(entry)
        else:
            self.episodic.add(entry)
            # Keep emotional retrieval in sync
            self.emotional_retrieval.episodic_records = self.episodic.records

    def retrieve(self, query: MemoryQuery, story_mode: str | None = None) -> list[MemoryEntry]:
        """Retrieve memories for a given query.

        In SHORT mode (story_mode='short'), no chapter filter is applied
        because all events for a single-chapter story are stored with
        chapter_num=1 and there is no cross-chapter filtering needed.
        The EpisodicStore.query() already does not filter by chapter_num,
        so retrieval works correctly for all modes.
        """
        results = self.episodic.query(query.focus_character, query.top_k)
        entity_facts = self.semantic.query(query.focus_character)
        seen = {r.text for r in results}
        for f in entity_facts:
            if f.text not in seen:
                results.append(f)
                seen.add(f.text)

        # Emotion-based retrieval (Change 2)
        if query.emotion_filter:
            emotion_memories = self.emotional_retrieval.retrieve_by_emotion(
                query.emotion_filter, top_k=3
            )
            for mem in emotion_memories:
                if mem.text not in seen:
                    results.append(mem)
                    seen.add(mem.text)

        # Interpretation-based boosting (Change 6)
        interpretations = self.interpretation_engine.query(
            query.focus_character, top_k=5
        )
        for interp in interpretations:
            if interp.confidence > 0.7:
                for r in results:
                    if interp.source_event_text in r.text or r.text in interp.source_event_text:
                        r.relevance_score = min(1.0, r.relevance_score * 1.25)

        # RAG bridge retrieval from pre-built corpus
        if self.rag_bridge is not None and self.rag_bridge.is_loaded:
            rag_results = self.rag_bridge.retrieve(query)
            for mem in rag_results:
                if mem.text not in seen:
                    results.append(mem)
                    seen.add(mem.text)

        results = results[: query.top_k]
        filtered = []
        for mem in results:
            is_dup = False
            mem_words = set(mem.text.lower().split())
            if not mem_words:
                filtered.append(mem)
                continue
            for existing in filtered:
                existing_words = set(existing.text.lower().split())
                if not existing_words:
                    continue
                jaccard = len(mem_words & existing_words) / len(mem_words | existing_words)
                if jaccard > 0.8:
                    is_dup = True
                    break
            if not is_dup:
                filtered.append(mem)
        return filtered

    def recent_context(self, character: str, window: int = 3) -> list[str]:
        recs = [r for r in self.episodic.records if character in r.characters]
        return [r.text for r in recs[-window:]]

    # ------------------------------------------------------------------ #
    # Interpretation Memory integration
    # ------------------------------------------------------------------ #

    @property
    def interpretation_store(self) -> InterpretationStore:
        return self.interpretation_engine.store

    def record_interpretation(
        self,
        character: str,
        source_event: str,
        interpretation: str,
        emotion_impact: str,
        confidence: float = 0.5,
        chapter_num: int = 0,
        scene_num: int = 0,
    ) -> InterpretationEntry:
        return self.interpretation_engine.add_interpretation(
            character=character,
            source_event=source_event,
            interpretation=interpretation,
            emotion_impact=emotion_impact,
            confidence=confidence,
            chapter_num=chapter_num,
            scene_num=scene_num,
        )

    def interpret_event(
        self,
        event_text: str,
        character_name: str,
        character_traits: list[str],
        chapter_num: int = 0,
        scene_num: int = 0,
    ) -> InterpretationEntry:
        return self.interpretation_engine.interpret_event(
            event_text=event_text,
            character_name=character_name,
            character_traits=character_traits,
            chapter_num=chapter_num,
            scene_num=scene_num,
        )

    def query_interpretations(
        self,
        character: str,
        emotion_filter: str | None = None,
        top_k: int = 5,
    ) -> list[InterpretationEntry]:
        return self.interpretation_engine.query(character, emotion_filter, top_k)

    # ------------------------------------------------------------------ #
    # Consequence Memory integration
    # ------------------------------------------------------------------ #

    @property
    def consequence_store(self) -> ConsequenceStore:
        return self.consequence_engine.store

    def record_consequence(
        self,
        character: str,
        action: str,
        consequence: str,
        success: bool,
        impact: float = 0.5,
        chapter_num: int = 0,
        scene_num: int = 0,
    ) -> ConsequenceEntry:
        return self.consequence_engine.add_consequence(
            character=character,
            action=action,
            consequence=consequence,
            success=success,
            impact=impact,
            chapter_num=chapter_num,
            scene_num=scene_num,
        )

    def query_consequences(
        self, character: str, min_impact: float = 0.3
    ) -> list[ConsequenceEntry]:
        return self.consequence_engine.query(character, min_impact)

    def consequences_for_action(self, action_keyword: str) -> list[ConsequenceEntry]:
        return self.consequence_engine.consequences_for_action(action_keyword)

    # ------------------------------------------------------------------ #
    # Emotional Retrieval integration
    # ------------------------------------------------------------------ #

    def retrieve_by_emotion(
        self, query_emotion: str, top_k: int = 5
    ) -> list[MemoryEntry]:
        return self.emotional_retrieval.retrieve_by_emotion(query_emotion, top_k)

    def retrieve_emotional_context(
        self, character: str, current_emotion: str
    ) -> dict[str, list[MemoryEntry]]:
        return self.emotional_retrieval.retrieve_emotional_context(
            character, current_emotion
        )

    def emotional_timeline(self, character: str) -> list[dict]:
        return self.emotional_retrieval.emotional_timeline(character)

    # ------------------------------------------------------------------ #
    # Relationship Delta integration
    # ------------------------------------------------------------------ #

    @property
    def relationship_delta_store(self) -> RelationshipDeltaStore:
        return self.relationship_deltas.store

    def record_relationship_delta(
        self,
        a: str,
        b: str,
        old_rel: RelationKind,
        new_rel: RelationKind,
        trigger: str,
        chapter_num: int = 0,
    ) -> RelationshipDelta:
        return self.relationship_deltas.record_delta(
            a=a,
            b=b,
            old_rel=old_rel,
            new_rel=new_rel,
            trigger=trigger,
            chapter_num=chapter_num,
        )

    def recent_relationship_changes(
        self, character: str, window: int = 5
    ) -> list[RelationshipDelta]:
        return self.relationship_deltas.recent_changes(character, window)

    def relationship_timeline(self, a: str, b: str) -> list[RelationshipDelta]:
        return self.relationship_deltas.relationship_timeline(a, b)

    def current_relationship_sentiment(self, a: str, b: str) -> float:
        return self.relationship_deltas.current_sentiment(a, b)

    # ------------------------------------------------------------------ #
    # Callback Scheduler integration
    # ------------------------------------------------------------------ #

    def schedule_callback(
        self,
        memory_id: str,
        trigger_chapter: int,
        callback_data: dict[str, Any] | None = None,
    ) -> str:
        return self.callback_scheduler.schedule_memory_callback(
            memory_id=memory_id,
            trigger_chapter=trigger_chapter,
            callback_data=callback_data,
        )

    def check_callbacks(self, current_chapter: int) -> list[ScheduledCallback]:
        return self.callback_scheduler.check_callbacks(current_chapter)

    def mark_callback_fired(self, callback_id: str) -> bool:
        return self.callback_scheduler.mark_fired(callback_id)

    def pending_callbacks(
        self, chapter: int | None = None
    ) -> list[ScheduledCallback]:
        return self.callback_scheduler.pending_callbacks(chapter)

    def clear_fired_callbacks(self) -> int:
        return self.callback_scheduler.clear_fired()

    # ------------------------------------------------------------------ #
    # Bulk operations
    # ------------------------------------------------------------------ #

    def prune(self, keep_top_k: int = 100, min_relevance: float = 0.2) -> int:
        """Prune low-importance memories to prevent unbounded growth.

        For SHORT/CHAPTER stories, keeps only entries with
        relevance_score above min_relevance. For BOOK mode,
        keeps the top-K most relevant entries and prunes the rest.

        Also prunes interpretations and consequences below confidence/impact thresholds.
        Returns total number of entries removed across all stores.
        """
        removed = 0

        # Prune episodic records
        if len(self.episodic.records) > keep_top_k:
            self.episodic.records.sort(key=lambda r: r.relevance_score, reverse=True)
            before = len(self.episodic.records)
            self.episodic.records = [
                r for r in self.episodic.records
                if r.relevance_score >= min_relevance
            ][:keep_top_k]
            removed += before - len(self.episodic.records)

        # Prune emotional retrieval sync
        self.emotional_retrieval.episodic_records = self.episodic.records

        # Prune low-confidence interpretations
        interp_store = self.interpretation_engine.store
        if hasattr(interp_store, 'entries'):
            before = len(interp_store.entries)
            interp_store.entries = [
                e for e in interp_store.entries
                if e.confidence >= 0.3
            ]
            removed += before - len(interp_store.entries)

        # Prune low-impact consequences
        conseq_store = self.consequence_engine.store
        if hasattr(conseq_store, 'entries'):
            before = len(conseq_store.entries)
            conseq_store.entries = [
                e for e in conseq_store.entries
                if e.impact_level >= 0.3
            ]
            removed += before - len(conseq_store.entries)

        # Clear fired callbacks
        removed += self.callback_scheduler.clear_fired()

        return removed

    def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of all memory state for serialization."""
        return {
            "episodic_count": len(self.episodic.records),
            "semantic_count": len(self.semantic.facts),
            "interpretation_count": len(self.interpretation_store.entries),
            "consequence_count": len(self.consequence_store.entries),
            "relationship_delta_count": len(self.relationship_delta_store.deltas),
            "pending_callbacks": len(self.callback_scheduler.pending_callbacks()),
            "registered_characters": list(self._character_beliefs.keys()),
        }
