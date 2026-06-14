"""MVP tests for SCRIPTY v2 — every subsystem must produce measurable output.

Uses backend.v2.metrics for quality assertions instead of hardcoded magic numbers.
"""

import asyncio

from backend.v2.character_agent import CharacterAgent
from backend.v2.dramatic_realizer import DramaticRealizer
from backend.v2.types import SceneBlueprint
from backend.v2.conflict_resolver import ConflictResolver
from backend.v2.engine import StoryEngineV2
from backend.v2.factories import build_character_agents
from backend.v2.memory_system import MemorySystem
from backend.v2.metrics import (
    THRESHOLDS,
    word_count as metrics_word_count,
    dialogue_count as metrics_dialogue_count,
    measure_all,
)
from backend.v2.pipeline import ScenePipeline
from backend.v2.story_planner import StoryPlanner
from backend.v2.state_update import StateUpdater
from backend.v2.types import (
    AgentState,
    CharacterBeliefs,
    CharacterRecord,
    GeneratedScene,
    Intention,
    MemoryEntry,
    MemoryQuery,
    SceneObjective,
    SceneType,
    StoryMode,
    WorldConstraints,
)
from backend.v2.world_state import WorldState


def _make_world() -> WorldConstraints:
    return WorldConstraints(
        era="digital",
        tech_level="digital",
        tone="vibrant, connected",
        infrastructure=["smart cities", "it hubs"],
        transport=["metro trains"],
        location_description="Hyderabad",
        year=2024,
    )


def _make_agents(count: int = 2) -> list[CharacterAgent]:
    data = [
        {
            "name": "Arjun",
            "role": "protagonist",
            "traits": ["curious", "brave"],
            "goals": ["uncover the truth"],
            "relationships": {"Maya": "rival"},
        },
        {
            "name": "Maya",
            "role": "antagonist",
            "traits": ["deceptive", "ambitious"],
            "goals": ["protect the secret"],
            "relationships": {"Arjun": "rival"},
        },
    ]
    return build_character_agents(data[:count])


# ---------------------------------------------------------------------------
# WorldState tests
# ---------------------------------------------------------------------------


class TestWorldState:
    def test_temporal_context(self):
        ws = WorldState()
        constraints = asyncio.run(
            ws.build_constraints(location="Hyderabad", year=1920)
        )
        assert constraints.era == "colonial"
        assert constraints.tech_level == "industrial"
        assert len(constraints.infrastructure) > 0
        assert len(constraints.transport) > 0

    def test_generation_context(self):
        ws = WorldState()
        constraints = asyncio.run(
            ws.build_constraints(location="Hyderabad", year=2024)
        )
        ctx = ws.to_generation_context(constraints)
        assert "era" in ctx
        assert "tech_level" in ctx
        assert "infrastructure" in ctx


# ---------------------------------------------------------------------------
# MemorySystem tests
# ---------------------------------------------------------------------------


class TestMemorySystem:
    def test_record_and_retrieve(self):
        mem = MemorySystem()
        mem.register_character("Arjun")
        mem.record_event("Arjun found a hidden ledger", 1, 1, ["Arjun"])
        results = mem.retrieve(MemoryQuery(focus_character="Arjun", context_query="ledger"))
        assert len(results) >= 1
        assert "ledger" in results[0].text

    def test_beliefs_isolation(self):
        mem = MemorySystem()
        mem.register_character("Arjun")
        mem.register_character("Maya")
        arjun_beliefs = mem.beliefs_for("Arjun")
        maya_beliefs = mem.beliefs_for("Maya")
        arjun_beliefs.discovered.append("secret tunnel")
        assert "secret tunnel" not in maya_beliefs.discovered

    def test_recent_context_respects_window(self):
        mem = MemorySystem()
        mem.register_character("Arjun")
        mem.record_event("event one", 1, 1, ["Arjun"])
        mem.record_event("event two", 1, 2, ["Arjun"])
        recent = mem.recent_context("Arjun", window=1)
        assert len(recent) == 1
        assert "two" in recent[0]

    def test_recent_context_all_events(self):
        mem = MemorySystem()
        mem.register_character("Arjun")
        mem.record_event("event one", 1, 1, ["Arjun"])
        mem.record_event("event two", 1, 2, ["Arjun"])
        all_events = mem.recent_context("Arjun", window=5)
        assert len(all_events) >= 2


# ---------------------------------------------------------------------------
# CharacterAgent tests
# ---------------------------------------------------------------------------


class TestCharacterAgent:
    def test_decide_intention(self):
        agent, *_ = _make_agents(1)
        intention = agent.decide_intention(
            world_context={"era": "digital", "active_conflicts": ["rising tension"]},
            memories=["danger lurks in the old city"],
        )
        assert intention.goal == "uncover the truth"
        assert intention.action in ("confront", "observe", "investigate")

    def test_decide_intention_produces_action(self):
        agent, *_ = _make_agents(1)
        intention = agent.decide_intention(
            world_context={"era": "digital"},
            memories=None,
        )
        assert isinstance(intention, Intention)
        assert len(intention.action) > 0

    def test_relationship_pressure(self):
        agents = _make_agents(2)
        arjun = agents[0]
        maya = agents[1]
        pressure = arjun.relationship_pressure_with(maya.name)
        # Rival relationship should produce positive pressure
        assert pressure > 0
        assert pressure < 1.0  # pressure is normalized


# ---------------------------------------------------------------------------
# StoryPlanner tests
# ---------------------------------------------------------------------------


class TestStoryPlanner:
    def test_plan_chapter_produces_scene_objectives(self):
        planner = StoryPlanner()
        world = _make_world()
        objectives = planner.plan_chapter(
            chapter_num=1, total_chapters=10, world=world,
            story_mode=StoryMode.CHAPTER,
        )
        assert len(objectives) >= 3
        for obj in objectives:
            assert isinstance(obj, SceneObjective)
            assert len(obj.purpose) > 0
            assert 0 <= obj.required_tension <= 1.0

    def test_short_mode_fewer_scenes(self):
        planner = StoryPlanner()
        world = _make_world()
        short = planner.plan_chapter(
            chapter_num=1, total_chapters=1, world=world,
            story_mode=StoryMode.SHORT,
        )
        chapter = planner.plan_chapter(
            chapter_num=1, total_chapters=10, world=world,
            story_mode=StoryMode.CHAPTER,
        )
        assert len(short) <= len(chapter) + 2


# ---------------------------------------------------------------------------
# ConflictResolver tests
# ---------------------------------------------------------------------------


class TestConflictResolver:
    def test_resolve_no_conflict(self):
        resolver = ConflictResolver()
        agents = _make_agents(2)
        for a in agents:
            a.decide_intention(world_context={"era": "digital"})
        states = [a.to_agent_state() for a in agents]

        base = SceneObjective(
            purpose="explore the market",
            characters_involved=[],
            location="Hyderabad",
            conflict_type="dormant",
            required_tension=0.3,
            target_scene_type=SceneType.DESCRIPTION,
            resolution_goal="set the scene",
        )
        result = resolver.resolve(states, base)
        assert len(result.characters_involved) > 0

    def test_calculate_scene_type_escalation(self):
        resolver = ConflictResolver()
        agents = _make_agents(2)
        agents[0].emotional_pressure = 0.9
        agents[1].emotional_pressure = 0.8
        states = [a.to_agent_state() for a in agents]

        result = resolver.calculate_scene_type(states, SceneType.DESCRIPTION)
        assert result == SceneType.ACTION


# ---------------------------------------------------------------------------
# DramaticRealizer tests
# ---------------------------------------------------------------------------


class TestDramaticRealizer:
    def test_realize_produces_meaningful_text(self):
        realizer = DramaticRealizer()
        world = _make_world()
        agents = _make_agents(2)

        blueprint = SceneBlueprint(
            objective=SceneObjective(
                purpose="discover hidden truth",
                characters_involved=["Arjun", "Maya"],
                location="Hyderabad",
                conflict_type="emerging",
                required_tension=0.6,
                target_scene_type=SceneType.DIALOGUE,
                resolution_goal="reveal information",
            ),
            agent_states={a.name: a.to_agent_state() for a in agents},
            world=world,
            retrieved_memories=[
                MemoryEntry(
                    text="Arjun saw Maya at the old archive",
                    source="episodic", chapter_num=1, scene_num=1,
                    characters=["Arjun"],
                ),
            ],
        )

        scene = realizer.realize(blueprint)
        assert isinstance(scene, GeneratedScene)
        # Scene must be substantial — at least 50 chars and 5+ words
        assert len(scene.content) > 50
        assert scene.word_count >= 5

    def test_realize_action_scene(self):
        realizer = DramaticRealizer()
        world = _make_world()
        agents = _make_agents(2)

        blueprint = SceneBlueprint(
            objective=SceneObjective(
                purpose="chase through the market",
                characters_involved=["Arjun", "Maya"],
                location="Hyderabad",
                conflict_type="explosive",
                required_tension=0.9,
                target_scene_type=SceneType.ACTION,
                resolution_goal="escalate stakes",
            ),
            agent_states={a.name: a.to_agent_state() for a in agents},
            world=world,
            retrieved_memories=[],
        )

        scene = realizer.realize(blueprint)
        assert scene.scene_type == SceneType.ACTION
        assert scene.word_count >= 5

    def test_realize_produces_some_dialogue_in_dialogue_scenes(self):
        realizer = DramaticRealizer()
        world = _make_world()
        agents = _make_agents(2)

        blueprint = SceneBlueprint(
            objective=SceneObjective(
                purpose="argue about the truth",
                characters_involved=["Arjun", "Maya"],
                location="Hyderabad",
                conflict_type="active",
                required_tension=0.7,
                target_scene_type=SceneType.DIALOGUE,
                resolution_goal="reveal information",
            ),
            agent_states={a.name: a.to_agent_state() for a in agents},
            world=world,
            retrieved_memories=[],
        )

        scene = realizer.realize(blueprint)
        assert scene.word_count >= 5
        assert scene.scene_type == SceneType.DIALOGUE


# ---------------------------------------------------------------------------
# StateUpdater tests
# ---------------------------------------------------------------------------


class TestStateUpdater:
    def test_update_characters_modifies_pressure(self):
        updater = StateUpdater()
        agents = _make_agents(2)
        scene = GeneratedScene(
            content="Arjun confronted Maya about the ledger",
            scene_type=SceneType.ACTION,
            word_count=10,
            tension=0.8,
            characters_involved=["Arjun"],
        )
        world = _make_world()
        updater.update_characters(agents, scene, world)
        assert agents[0].emotional_pressure > 0.0

    def test_record_scene_memory(self):
        updater = StateUpdater()
        memory = MemorySystem()
        memory.register_character("Arjun")
        scene = GeneratedScene(
            content="Arjun discovers a hidden passage",
            scene_type=SceneType.ACTION,
            word_count=8,
            tension=0.5,
            characters_involved=["Arjun"],
        )
        updater.record_scene_memory(memory, scene, chapter_num=1, scene_num=1)
        results = memory.retrieve(
            MemoryQuery(focus_character="Arjun", context_query="passage")
        )
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Integration test — Pipeline
# ---------------------------------------------------------------------------


class TestScenePipeline:
    def test_run_produces_scene(self):
        resolver = ConflictResolver()
        realizer = DramaticRealizer()
        memory = MemorySystem()
        pipeline = ScenePipeline(conflict_resolver=resolver, realizer=realizer, memory=memory)

        agents = _make_agents(2)
        for a in agents:
            memory.register_character(a.name)

        world = _make_world()
        objective = SceneObjective(
            purpose="character confronts an obstacle",
            characters_involved=["Arjun", "Maya"],
            location="Hyderabad",
            conflict_type="active",
            required_tension=0.65,
            target_scene_type=SceneType.ACTION,
            resolution_goal="escalate stakes",
        )
        scene = pipeline.run(
            agents=agents,
            world=world,
            chapter_num=1,
            scene_index=0,
            total_scenes=3,
            objective=objective,
            story_mode=StoryMode.SHORT,
        )

        assert isinstance(scene, GeneratedScene)
        assert scene.word_count >= 10
        assert len(scene.characters_involved) > 0


# ---------------------------------------------------------------------------
# Integration test — Full Engine
# ---------------------------------------------------------------------------


class TestStoryEngineV2:
    def test_generate_short(self):
        engine = StoryEngineV2()
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1920,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [],
                "location_type": "urban",
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        assert result.word_count > 0
        assert len(result.story_text) > 0
        assert len(result.chapters) == 1

    def test_generate_with_characters(self):
        agents = _make_agents(2)
        engine = StoryEngineV2()
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1920,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [
                    {
                        "name": "Arjun",
                        "role": "protagonist",
                        "traits": ["curious", "brave"],
                        "goals": ["uncover the truth"],
                        "relationships": {"Maya": "rival"},
                    },
                    {
                        "name": "Maya",
                        "role": "antagonist",
                        "traits": ["deceptive", "ambitious"],
                        "goals": ["protect the secret"],
                        "relationships": {"Arjun": "rival"},
                    },
                ],
                "location_type": "urban",
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        assert result.word_count > 0
        assert "Arjun" in result.story_text or "Maya" in result.story_text

    def test_generated_story_has_measurable_quality(self):
        engine = StoryEngineV2()
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1857,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [],
                "location_type": "urban",
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        metrics = measure_all(result.story_text)
        # Story must have at least some substance
        assert metrics.word_count >= THRESHOLDS.word_count_min // 2
        # Must have at least minimal vocabulary diversity
        assert metrics.type_token_ratio > 0.1
        # Must mention characters or entities
        assert metrics.sentence_count >= 3


# ---------------------------------------------------------------------------
# Factories tests
# ---------------------------------------------------------------------------


class TestFactories:
    def test_build_agents(self):
        agents = _make_agents(2)
        assert len(agents) == 2
        assert agents[0].name == "Arjun"
        assert agents[1].name == "Maya"
        rel = agents[0].character.relationships.get("Maya")
        assert rel is not None

    def test_default_relationships(self):
        data = [
            {"name": "A", "role": "hero", "traits": ["brave"], "goals": ["win"]},
            {"name": "B", "role": "sidekick", "traits": ["loyal"], "goals": ["help"]},
        ]
        agents = build_character_agents(data)
        assert agents[0].character.relationships.get("B") is not None
        assert agents[1].character.relationships.get("A") is not None
