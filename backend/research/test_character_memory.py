"""
Unit tests for the CharacterMemory class.

Tests character goal tracking, emotional state management, relationship
recording, knowledge acquisition, and conflict tracking.
"""

import pytest

from backend.research.character_memory import (
    CharacterGoal,
    CharacterMemory,
    EmotionalState,
    KnowledgeItem,
    Relationship,
    UnresolvedConflict,
)


# ---------------------------------------------------------------------------
# Goal tracking tests
# ---------------------------------------------------------------------------

def test_track_goal():
    """Test tracking a new character goal."""
    memory = CharacterMemory("Alice")
    goal_id = memory.track_goal(
        description="Find the lost artifact",
        chapter_introduced=1,
        priority=0.8,
    )

    assert goal_id is not None
    goals = memory.get_active_goals()
    assert len(goals) == 1
    assert goals[0].description == "Find the lost artifact"
    assert goals[0].priority == 0.8
    assert goals[0].status == "active"


def test_track_goal_with_explicit_id():
    """Test tracking a goal with an explicit ID."""
    memory = CharacterMemory("Bob")
    goal_id = memory.track_goal(
        description="Defeat the villain",
        chapter_introduced=2,
        goal_id="goal-123",
    )

    assert goal_id == "goal-123"
    goals = memory.get_all_goals()
    assert len(goals) == 1
    assert goals[0].goal_id == "goal-123"


def test_update_goal_status():
    """Test updating the status of a goal."""
    memory = CharacterMemory("Charlie")
    goal_id = memory.track_goal(
        description="Rescue the princess",
        chapter_introduced=1,
    )

    memory.update_goal_status(goal_id, "achieved", chapter_resolved=5)

    goals = memory.get_all_goals()
    assert len(goals) == 1
    assert goals[0].status == "achieved"
    assert goals[0].chapter_resolved == 5

    # Active goals should be empty now
    active_goals = memory.get_active_goals()
    assert len(active_goals) == 0


def test_update_nonexistent_goal_raises_error():
    """Test that updating a nonexistent goal raises KeyError."""
    memory = CharacterMemory("Diana")

    with pytest.raises(KeyError, match="Goal .* not found"):
        memory.update_goal_status("nonexistent-id", "achieved")


def test_multiple_goals():
    """Test tracking multiple goals."""
    memory = CharacterMemory("Eve")
    goal1 = memory.track_goal("Goal 1", chapter_introduced=1, priority=0.9)
    goal2 = memory.track_goal("Goal 2", chapter_introduced=2, priority=0.5)
    goal3 = memory.track_goal("Goal 3", chapter_introduced=3, priority=0.7)

    active_goals = memory.get_active_goals()
    assert len(active_goals) == 3

    # Resolve one goal
    memory.update_goal_status(goal2, "failed", chapter_resolved=4)

    active_goals = memory.get_active_goals()
    assert len(active_goals) == 2
    assert all(g.goal_id != goal2 for g in active_goals)


# ---------------------------------------------------------------------------
# Emotional state tests
# ---------------------------------------------------------------------------

def test_update_emotional_state():
    """Test recording an emotional state."""
    memory = CharacterMemory("Frank")
    memory.update_emotional_state(
        chapter_num=1,
        primary_emotion="hopeful",
        intensity=0.7,
        trigger="Found a clue",
    )

    state = memory.get_emotional_state(1)
    assert state is not None
    assert state.primary_emotion == "hopeful"
    assert state.intensity == 0.7
    assert state.trigger == "Found a clue"


def test_emotional_state_progression():
    """Test tracking emotional state changes across chapters."""
    memory = CharacterMemory("Grace")
    memory.update_emotional_state(1, "neutral", 0.5, "Starting the journey")
    memory.update_emotional_state(3, "fearful", 0.8, "Encountered danger")
    memory.update_emotional_state(5, "hopeful", 0.6, "Found allies")

    # Query at chapter 2 should return chapter 1 state
    state = memory.get_emotional_state(2)
    assert state is not None
    assert state.chapter_num == 1
    assert state.primary_emotion == "neutral"

    # Query at chapter 4 should return chapter 3 state
    state = memory.get_emotional_state(4)
    assert state is not None
    assert state.chapter_num == 3
    assert state.primary_emotion == "fearful"

    # Query at chapter 6 should return chapter 5 state
    state = memory.get_emotional_state(6)
    assert state is not None
    assert state.chapter_num == 5
    assert state.primary_emotion == "hopeful"


def test_emotional_state_before_any_recorded():
    """Test querying emotional state before any have been recorded."""
    memory = CharacterMemory("Henry")
    state = memory.get_emotional_state(1)
    assert state is None


def test_emotional_history():
    """Test retrieving full emotional history."""
    memory = CharacterMemory("Iris")
    memory.update_emotional_state(3, "angry", 0.9, "Betrayed")
    memory.update_emotional_state(1, "neutral", 0.5, "Beginning")
    memory.update_emotional_state(5, "content", 0.4, "Resolution")

    history = memory.get_emotional_history()
    assert len(history) == 3
    # Should be sorted by chapter_num
    assert history[0].chapter_num == 1
    assert history[1].chapter_num == 3
    assert history[2].chapter_num == 5


# ---------------------------------------------------------------------------
# Relationship tests
# ---------------------------------------------------------------------------

def test_record_relationship():
    """Test recording a relationship."""
    memory = CharacterMemory("Jack")
    memory.record_relationship(
        other_character="Jill",
        relationship_type="ally",
        strength=0.8,
        chapter_established=2,
        notes="Met during the quest",
    )

    relationship = memory.get_relationship("Jill")
    assert relationship is not None
    assert relationship.other_character == "Jill"
    assert relationship.relationship_type == "ally"
    assert relationship.strength == 0.8
    assert relationship.notes == "Met during the quest"


def test_update_relationship():
    """Test updating an existing relationship."""
    memory = CharacterMemory("Kate")
    memory.record_relationship("Leo", "acquaintance", 0.3, 1)

    # Update the relationship
    memory.record_relationship("Leo", "ally", 0.7, 3, "Fought together")

    relationship = memory.get_relationship("Leo")
    assert relationship is not None
    assert relationship.relationship_type == "ally"
    assert relationship.strength == 0.7
    assert relationship.chapter_established == 3


def test_multiple_relationships():
    """Test tracking multiple relationships."""
    memory = CharacterMemory("Mike")
    memory.record_relationship("Nancy", "ally", 0.8, 1)
    memory.record_relationship("Oscar", "enemy", 0.9, 2)
    memory.record_relationship("Paula", "family", 1.0, 0)

    relationships = memory.get_all_relationships()
    assert len(relationships) == 3

    # Check specific relationships
    assert memory.get_relationship("Nancy").relationship_type == "ally"
    assert memory.get_relationship("Oscar").relationship_type == "enemy"
    assert memory.get_relationship("Paula").relationship_type == "family"


def test_get_nonexistent_relationship():
    """Test querying a relationship that doesn't exist."""
    memory = CharacterMemory("Quinn")
    relationship = memory.get_relationship("Unknown")
    assert relationship is None


# ---------------------------------------------------------------------------
# Knowledge tests
# ---------------------------------------------------------------------------

def test_add_knowledge():
    """Test adding a knowledge item."""
    memory = CharacterMemory("Rachel")
    knowledge_id = memory.add_knowledge(
        content="The artifact is hidden in the temple",
        chapter_acquired=3,
        source="overheard",
        importance=0.9,
    )

    assert knowledge_id is not None
    knowledge = memory.get_all_knowledge()
    assert len(knowledge) == 1
    assert knowledge[0].content == "The artifact is hidden in the temple"
    assert knowledge[0].importance == 0.9


def test_add_knowledge_with_explicit_id():
    """Test adding knowledge with an explicit ID."""
    memory = CharacterMemory("Sam")
    knowledge_id = memory.add_knowledge(
        content="Secret passage exists",
        chapter_acquired=2,
        knowledge_id="knowledge-456",
    )

    assert knowledge_id == "knowledge-456"
    knowledge = memory.get_all_knowledge()
    assert len(knowledge) == 1
    assert knowledge[0].knowledge_id == "knowledge-456"


def test_get_knowledge_by_chapter():
    """Test retrieving knowledge by chapter."""
    memory = CharacterMemory("Tina")
    memory.add_knowledge("Knowledge 1", chapter_acquired=1, importance=0.5)
    memory.add_knowledge("Knowledge 2", chapter_acquired=3, importance=0.7)
    memory.add_knowledge("Knowledge 3", chapter_acquired=5, importance=0.9)

    # At chapter 2, should have only knowledge 1
    knowledge = memory.get_knowledge_by_chapter(2)
    assert len(knowledge) == 1
    assert knowledge[0].content == "Knowledge 1"

    # At chapter 4, should have knowledge 1 and 2
    knowledge = memory.get_knowledge_by_chapter(4)
    assert len(knowledge) == 2

    # At chapter 6, should have all knowledge
    knowledge = memory.get_knowledge_by_chapter(6)
    assert len(knowledge) == 3


def test_multiple_knowledge_items():
    """Test tracking multiple knowledge items."""
    memory = CharacterMemory("Uma")
    k1 = memory.add_knowledge("Fact 1", 1, "discovered", 0.8)
    k2 = memory.add_knowledge("Fact 2", 2, "told by ally", 0.6)
    k3 = memory.add_knowledge("Fact 3", 3, "read in book", 0.4)

    all_knowledge = memory.get_all_knowledge()
    assert len(all_knowledge) == 3
    assert {k.knowledge_id for k in all_knowledge} == {k1, k2, k3}


# ---------------------------------------------------------------------------
# Conflict tests
# ---------------------------------------------------------------------------

def test_add_conflict():
    """Test adding an unresolved conflict."""
    memory = CharacterMemory("Victor")
    conflict_id = memory.add_conflict(
        description="Must defeat the dragon",
        chapter_introduced=2,
        opposing_character="Dragon",
        conflict_type="external",
    )

    assert conflict_id is not None
    conflicts = memory.get_unresolved_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].description == "Must defeat the dragon"
    assert conflicts[0].opposing_character == "Dragon"


def test_add_conflict_with_explicit_id():
    """Test adding a conflict with an explicit ID."""
    memory = CharacterMemory("Wendy")
    conflict_id = memory.add_conflict(
        description="Internal struggle",
        chapter_introduced=1,
        conflict_type="internal",
        conflict_id="conflict-789",
    )

    assert conflict_id == "conflict-789"
    conflicts = memory.get_all_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].conflict_id == "conflict-789"


def test_resolve_conflict():
    """Test resolving a conflict."""
    memory = CharacterMemory("Xavier")
    conflict_id = memory.add_conflict(
        description="Rivalry with antagonist",
        chapter_introduced=1,
        opposing_character="Antagonist",
    )

    memory.resolve_conflict(conflict_id, chapter_resolved=5)

    # Should not be in unresolved conflicts
    unresolved = memory.get_unresolved_conflicts()
    assert len(unresolved) == 0

    # Should still be in all conflicts
    all_conflicts = memory.get_all_conflicts()
    assert len(all_conflicts) == 1
    assert all_conflicts[0].chapter_resolved == 5


def test_resolve_nonexistent_conflict_raises_error():
    """Test that resolving a nonexistent conflict raises KeyError."""
    memory = CharacterMemory("Yara")

    with pytest.raises(KeyError, match="Conflict .* not found"):
        memory.resolve_conflict("nonexistent-id", 5)


def test_multiple_conflicts():
    """Test tracking multiple conflicts."""
    memory = CharacterMemory("Zane")
    c1 = memory.add_conflict("Conflict 1", 1, "Enemy1", "interpersonal")
    c2 = memory.add_conflict("Conflict 2", 2, None, "internal")
    c3 = memory.add_conflict("Conflict 3", 3, "Enemy2", "external")

    unresolved = memory.get_unresolved_conflicts()
    assert len(unresolved) == 3

    # Resolve one conflict
    memory.resolve_conflict(c2, 4)

    unresolved = memory.get_unresolved_conflicts()
    assert len(unresolved) == 2
    assert all(c.conflict_id != c2 for c in unresolved)


# ---------------------------------------------------------------------------
# Character state snapshot tests
# ---------------------------------------------------------------------------

def test_get_character_state_empty():
    """Test getting character state when no data has been recorded."""
    memory = CharacterMemory("Alice")
    state = memory.get_character_state(1)

    assert state["character_name"] == "Alice"
    assert state["active_goals"] == []
    assert state["emotional_state"] is None
    assert state["relationships"] == []
    assert state["knowledge"] == []
    assert state["unresolved_conflicts"] == []


def test_get_character_state_full():
    """Test getting a complete character state snapshot."""
    memory = CharacterMemory("Bob")

    # Add various data
    memory.track_goal("Find treasure", 1, priority=0.8)
    memory.update_emotional_state(2, "excited", 0.7, "Found a clue")
    memory.record_relationship("Charlie", "ally", 0.9, 1)
    memory.add_knowledge("Map location", 2, "discovered", 0.8)
    memory.add_conflict("Rival treasure hunter", 1, "Rival", "interpersonal")

    state = memory.get_character_state(3)

    assert state["character_name"] == "Bob"
    assert len(state["active_goals"]) == 1
    assert state["active_goals"][0]["description"] == "Find treasure"
    assert state["emotional_state"]["primary_emotion"] == "excited"
    assert len(state["relationships"]) == 1
    assert state["relationships"][0]["other_character"] == "Charlie"
    assert len(state["knowledge"]) == 1
    assert state["knowledge"][0]["content"] == "Map location"
    assert len(state["unresolved_conflicts"]) == 1
    assert state["unresolved_conflicts"][0]["description"] == "Rival treasure hunter"


def test_get_character_state_temporal_filtering():
    """Test that character state correctly filters by chapter number."""
    memory = CharacterMemory("Diana")

    # Add data across multiple chapters
    goal1 = memory.track_goal("Early goal", 1)
    goal2 = memory.track_goal("Late goal", 5)
    memory.update_emotional_state(1, "neutral", 0.5)
    memory.update_emotional_state(4, "determined", 0.8)
    memory.add_knowledge("Early knowledge", 2)
    memory.add_knowledge("Late knowledge", 6)
    memory.add_conflict("Early conflict", 1)
    memory.add_conflict("Late conflict", 5)

    # Query at chapter 3
    state = memory.get_character_state(3)

    # Should have early goal but not late goal
    assert len(state["active_goals"]) == 1
    assert state["active_goals"][0]["description"] == "Early goal"

    # Should have chapter 1 emotional state
    assert state["emotional_state"]["chapter_num"] == 1

    # Should have early knowledge but not late knowledge
    assert len(state["knowledge"]) == 1
    assert state["knowledge"][0]["content"] == "Early knowledge"

    # Should have early conflict but not late conflict
    assert len(state["unresolved_conflicts"]) == 1
    assert state["unresolved_conflicts"][0]["description"] == "Early conflict"


def test_get_character_state_resolved_items_excluded():
    """Test that resolved goals and conflicts are excluded from state."""
    memory = CharacterMemory("Eve")

    goal1 = memory.track_goal("Active goal", 1)
    goal2 = memory.track_goal("Resolved goal", 1)
    memory.update_goal_status(goal2, "achieved", chapter_resolved=3)

    conflict1 = memory.add_conflict("Active conflict", 1)
    conflict2 = memory.add_conflict("Resolved conflict", 1)
    memory.resolve_conflict(conflict2, chapter_resolved=3)

    # Query at chapter 5 (after resolution)
    state = memory.get_character_state(5)

    # Should only have active goal
    assert len(state["active_goals"]) == 1
    assert state["active_goals"][0]["description"] == "Active goal"

    # Should only have active conflict
    assert len(state["unresolved_conflicts"]) == 1
    assert state["unresolved_conflicts"][0]["description"] == "Active conflict"


def test_character_state_relationships_temporal():
    """Test that relationships are filtered by chapter established."""
    memory = CharacterMemory("Frank")

    memory.record_relationship("Early friend", "ally", 0.8, chapter_established=1)
    memory.record_relationship("Late friend", "ally", 0.7, chapter_established=5)

    # Query at chapter 3
    state = memory.get_character_state(3)

    # Should only have early friend
    assert len(state["relationships"]) == 1
    assert state["relationships"][0]["other_character"] == "Early friend"

    # Query at chapter 6
    state = memory.get_character_state(6)

    # Should have both friends
    assert len(state["relationships"]) == 2
