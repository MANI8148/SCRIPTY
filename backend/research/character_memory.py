"""
Character-specific memory tracking for the research-grade narrative engine.

Provides CharacterGoal, EmotionalState, Relationship, KnowledgeItem,
UnresolvedConflict dataclasses and the CharacterMemory class that tracks
character goals, emotional states, relationships, knowledge, and conflicts
across chapters.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CharacterGoal:
    """A goal that a character is pursuing."""

    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    chapter_introduced: int = 0
    chapter_resolved: Optional[int] = None
    priority: float = 0.5  # [0.0, 1.0] — higher = more important
    status: str = "active"  # "active" | "achieved" | "failed" | "abandoned"


@dataclass
class EmotionalState:
    """A character's emotional state at a specific chapter."""

    chapter_num: int
    primary_emotion: str = "neutral"  # e.g. "hopeful", "fearful", "angry", "content"
    intensity: float = 0.5  # [0.0, 1.0]
    trigger: str = ""  # what caused this emotional state


@dataclass
class Relationship:
    """A relationship between this character and another character."""

    other_character: str
    relationship_type: str = "acquaintance"  # e.g. "ally", "enemy", "family", "romantic"
    strength: float = 0.5  # [0.0, 1.0] — how strong the relationship is
    chapter_established: int = 0
    notes: str = ""


@dataclass
class KnowledgeItem:
    """A piece of knowledge that a character has acquired."""

    knowledge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    chapter_acquired: int = 0
    source: str = ""  # how they learned this (e.g. "overheard", "told by X", "discovered")
    importance: float = 0.5  # [0.0, 1.0]


@dataclass
class UnresolvedConflict:
    """An unresolved conflict involving this character."""

    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    chapter_introduced: int = 0
    chapter_resolved: Optional[int] = None
    opposing_character: Optional[str] = None
    conflict_type: str = "interpersonal"  # e.g. "interpersonal", "internal", "external"


# ---------------------------------------------------------------------------
# CharacterMemory
# ---------------------------------------------------------------------------

class CharacterMemory:
    """
    Tracks character-specific state across chapters including goals, emotional
    states, relationships, knowledge, and unresolved conflicts.

    This class provides a comprehensive view of a character's narrative arc
    and internal state, enabling character-driven narrative generation.
    """

    def __init__(self, character_name: str) -> None:
        """
        Initialize character memory for a specific character.

        Parameters
        ----------
        character_name:
            The name of the character this memory tracks.
        """
        self.character_name = character_name
        self._goals: dict[str, CharacterGoal] = {}
        self._emotional_states: list[EmotionalState] = []
        self._relationships: dict[str, Relationship] = {}
        self._knowledge: dict[str, KnowledgeItem] = {}
        self._conflicts: dict[str, UnresolvedConflict] = {}

    # ------------------------------------------------------------------
    # Goal tracking
    # ------------------------------------------------------------------

    def track_goal(
        self,
        description: str,
        chapter_introduced: int,
        priority: float = 0.5,
        goal_id: Optional[str] = None,
    ) -> str:
        """
        Track a new goal for this character.

        Parameters
        ----------
        description:
            Description of the goal.
        chapter_introduced:
            Chapter number where the goal was introduced.
        priority:
            Priority of the goal (0.0-1.0), default 0.5.
        goal_id:
            Optional explicit goal ID; if None, generates a UUID.

        Returns
        -------
        str
            The goal ID.
        """
        if goal_id is None:
            goal_id = str(uuid.uuid4())

        goal = CharacterGoal(
            goal_id=goal_id,
            description=description,
            chapter_introduced=chapter_introduced,
            priority=priority,
            status="active",
        )
        self._goals[goal_id] = goal
        return goal_id

    def update_goal_status(
        self,
        goal_id: str,
        status: str,
        chapter_resolved: Optional[int] = None,
    ) -> None:
        """
        Update the status of an existing goal.

        Parameters
        ----------
        goal_id:
            The ID of the goal to update.
        status:
            New status: "active", "achieved", "failed", or "abandoned".
        chapter_resolved:
            Chapter number where the goal was resolved (if applicable).
        """
        if goal_id not in self._goals:
            raise KeyError(f"Goal {goal_id} not found for character {self.character_name}")

        self._goals[goal_id].status = status
        if chapter_resolved is not None:
            self._goals[goal_id].chapter_resolved = chapter_resolved

    def get_active_goals(self) -> list[CharacterGoal]:
        """Return all active goals for this character."""
        return [g for g in self._goals.values() if g.status == "active"]

    def get_all_goals(self) -> list[CharacterGoal]:
        """Return all goals (active and resolved) for this character."""
        return list(self._goals.values())

    # ------------------------------------------------------------------
    # Emotional state tracking
    # ------------------------------------------------------------------

    def update_emotional_state(
        self,
        chapter_num: int,
        primary_emotion: str,
        intensity: float = 0.5,
        trigger: str = "",
    ) -> None:
        """
        Record a new emotional state for this character.

        Parameters
        ----------
        chapter_num:
            Chapter number where this emotional state occurs.
        primary_emotion:
            The primary emotion (e.g., "hopeful", "fearful", "angry").
        intensity:
            Intensity of the emotion (0.0-1.0), default 0.5.
        trigger:
            What caused this emotional state.
        """
        state = EmotionalState(
            chapter_num=chapter_num,
            primary_emotion=primary_emotion,
            intensity=intensity,
            trigger=trigger,
        )
        self._emotional_states.append(state)

    def get_emotional_state(self, chapter_num: int) -> Optional[EmotionalState]:
        """
        Get the most recent emotional state at or before the given chapter.

        Parameters
        ----------
        chapter_num:
            Chapter number to query.

        Returns
        -------
        Optional[EmotionalState]
            The most recent emotional state, or None if no states recorded.
        """
        relevant_states = [
            s for s in self._emotional_states if s.chapter_num <= chapter_num
        ]
        if not relevant_states:
            return None
        return max(relevant_states, key=lambda s: s.chapter_num)

    def get_emotional_history(self) -> list[EmotionalState]:
        """Return all emotional states in chronological order."""
        return sorted(self._emotional_states, key=lambda s: s.chapter_num)

    # ------------------------------------------------------------------
    # Relationship tracking
    # ------------------------------------------------------------------

    def record_relationship(
        self,
        other_character: str,
        relationship_type: str,
        strength: float = 0.5,
        chapter_established: int = 0,
        notes: str = "",
    ) -> None:
        """
        Record or update a relationship with another character.

        Parameters
        ----------
        other_character:
            Name of the other character.
        relationship_type:
            Type of relationship (e.g., "ally", "enemy", "family").
        strength:
            Strength of the relationship (0.0-1.0), default 0.5.
        chapter_established:
            Chapter where the relationship was established.
        notes:
            Additional notes about the relationship.
        """
        relationship = Relationship(
            other_character=other_character,
            relationship_type=relationship_type,
            strength=strength,
            chapter_established=chapter_established,
            notes=notes,
        )
        self._relationships[other_character] = relationship

    def get_relationship(self, other_character: str) -> Optional[Relationship]:
        """
        Get the relationship with another character.

        Parameters
        ----------
        other_character:
            Name of the other character.

        Returns
        -------
        Optional[Relationship]
            The relationship, or None if no relationship recorded.
        """
        return self._relationships.get(other_character)

    def get_all_relationships(self) -> list[Relationship]:
        """Return all relationships for this character."""
        return list(self._relationships.values())

    # ------------------------------------------------------------------
    # Knowledge tracking
    # ------------------------------------------------------------------

    def add_knowledge(
        self,
        content: str,
        chapter_acquired: int,
        source: str = "",
        importance: float = 0.5,
        knowledge_id: Optional[str] = None,
    ) -> str:
        """
        Add a piece of knowledge that this character has acquired.

        Parameters
        ----------
        content:
            The knowledge content.
        chapter_acquired:
            Chapter where the knowledge was acquired.
        source:
            How the character learned this.
        importance:
            Importance of the knowledge (0.0-1.0), default 0.5.
        knowledge_id:
            Optional explicit knowledge ID; if None, generates a UUID.

        Returns
        -------
        str
            The knowledge ID.
        """
        if knowledge_id is None:
            knowledge_id = str(uuid.uuid4())

        knowledge = KnowledgeItem(
            knowledge_id=knowledge_id,
            content=content,
            chapter_acquired=chapter_acquired,
            source=source,
            importance=importance,
        )
        self._knowledge[knowledge_id] = knowledge
        return knowledge_id

    def get_knowledge_by_chapter(self, chapter_num: int) -> list[KnowledgeItem]:
        """
        Get all knowledge acquired at or before the given chapter.

        Parameters
        ----------
        chapter_num:
            Chapter number to query.

        Returns
        -------
        list[KnowledgeItem]
            All knowledge items acquired by this chapter.
        """
        return [
            k for k in self._knowledge.values()
            if k.chapter_acquired <= chapter_num
        ]

    def get_all_knowledge(self) -> list[KnowledgeItem]:
        """Return all knowledge items for this character."""
        return list(self._knowledge.values())

    # ------------------------------------------------------------------
    # Conflict tracking
    # ------------------------------------------------------------------

    def add_conflict(
        self,
        description: str,
        chapter_introduced: int,
        opposing_character: Optional[str] = None,
        conflict_type: str = "interpersonal",
        conflict_id: Optional[str] = None,
    ) -> str:
        """
        Add an unresolved conflict involving this character.

        Parameters
        ----------
        description:
            Description of the conflict.
        chapter_introduced:
            Chapter where the conflict was introduced.
        opposing_character:
            Name of the opposing character (if applicable).
        conflict_type:
            Type of conflict: "interpersonal", "internal", or "external".
        conflict_id:
            Optional explicit conflict ID; if None, generates a UUID.

        Returns
        -------
        str
            The conflict ID.
        """
        if conflict_id is None:
            conflict_id = str(uuid.uuid4())

        conflict = UnresolvedConflict(
            conflict_id=conflict_id,
            description=description,
            chapter_introduced=chapter_introduced,
            opposing_character=opposing_character,
            conflict_type=conflict_type,
        )
        self._conflicts[conflict_id] = conflict
        return conflict_id

    def resolve_conflict(self, conflict_id: str, chapter_resolved: int) -> None:
        """
        Mark a conflict as resolved.

        Parameters
        ----------
        conflict_id:
            The ID of the conflict to resolve.
        chapter_resolved:
            Chapter number where the conflict was resolved.
        """
        if conflict_id not in self._conflicts:
            raise KeyError(
                f"Conflict {conflict_id} not found for character {self.character_name}"
            )

        self._conflicts[conflict_id].chapter_resolved = chapter_resolved

    def get_unresolved_conflicts(self) -> list[UnresolvedConflict]:
        """Return all unresolved conflicts for this character."""
        return [c for c in self._conflicts.values() if c.chapter_resolved is None]

    def get_all_conflicts(self) -> list[UnresolvedConflict]:
        """Return all conflicts (resolved and unresolved) for this character."""
        return list(self._conflicts.values())

    # ------------------------------------------------------------------
    # Character state snapshot
    # ------------------------------------------------------------------

    def get_character_state(self, chapter_num: int) -> dict:
        """
        Return a complete snapshot of the character's state at a given chapter.

        Parameters
        ----------
        chapter_num:
            Chapter number to query.

        Returns
        -------
        dict
            A dictionary containing:
            - character_name: str
            - active_goals: list of CharacterGoal dicts
            - emotional_state: EmotionalState dict or None
            - relationships: list of Relationship dicts
            - knowledge: list of KnowledgeItem dicts
            - unresolved_conflicts: list of UnresolvedConflict dicts
        """
        # Get active goals at this chapter
        active_goals = [
            g for g in self._goals.values()
            if g.chapter_introduced <= chapter_num
            and (g.chapter_resolved is None or g.chapter_resolved > chapter_num)
            and g.status == "active"
        ]

        # Get emotional state at this chapter
        emotional_state = self.get_emotional_state(chapter_num)

        # Get relationships established by this chapter
        relationships = [
            r for r in self._relationships.values()
            if r.chapter_established <= chapter_num
        ]

        # Get knowledge acquired by this chapter
        knowledge = self.get_knowledge_by_chapter(chapter_num)

        # Get unresolved conflicts at this chapter
        unresolved_conflicts = [
            c for c in self._conflicts.values()
            if c.chapter_introduced <= chapter_num
            and (c.chapter_resolved is None or c.chapter_resolved > chapter_num)
        ]

        return {
            "character_name": self.character_name,
            "active_goals": [
                {
                    "goal_id": g.goal_id,
                    "description": g.description,
                    "priority": g.priority,
                    "chapter_introduced": g.chapter_introduced,
                }
                for g in active_goals
            ],
            "emotional_state": (
                {
                    "chapter_num": emotional_state.chapter_num,
                    "primary_emotion": emotional_state.primary_emotion,
                    "intensity": emotional_state.intensity,
                    "trigger": emotional_state.trigger,
                }
                if emotional_state
                else None
            ),
            "relationships": [
                {
                    "other_character": r.other_character,
                    "relationship_type": r.relationship_type,
                    "strength": r.strength,
                    "notes": r.notes,
                }
                for r in relationships
            ],
            "knowledge": [
                {
                    "knowledge_id": k.knowledge_id,
                    "content": k.content,
                    "source": k.source,
                    "importance": k.importance,
                }
                for k in knowledge
            ],
            "unresolved_conflicts": [
                {
                    "conflict_id": c.conflict_id,
                    "description": c.description,
                    "opposing_character": c.opposing_character,
                    "conflict_type": c.conflict_type,
                }
                for c in unresolved_conflicts
            ],
        }
