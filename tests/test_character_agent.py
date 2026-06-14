from backend.research.agent_memory_adapter import AgentMemoryAdapter
from backend.research.agent_planner_adapter import AgentPlannerAdapter
from backend.research.agent_scene_adapter import AgentSceneAdapter
from backend.research.character_agent import CharacterAgent
from backend.research.emotion_model import EmotionState
from backend.research.goal_evaluator import Goal, GoalEvaluator
from backend.research.memory_manager import EpisodicRecord, MemoryManager
from backend.research.narrative_graph import NarrativeGraph
from backend.research.relationship_model import RelationshipState
from backend.research.scene_update_extractor import StructuredSceneUpdateExtractor


def test_different_emotional_states_produce_different_actions():
    calm = CharacterAgent(
        name="Asha",
        goals=[Goal("g1", "find the ledger", 0.8, 0.7, 0.8, 1.0)],
        personality_traits={"cautious"},
        emotional_state=EmotionState(trust=0.6),
    )
    afraid = CharacterAgent(
        name="Asha",
        goals=[Goal("g1", "find the ledger", 0.8, 0.7, 0.8, 1.0)],
        emotional_state=EmotionState(fear=1.0, anger=0.8),
    )

    calm_action = calm.choose_action({"target": "archive"})["planned_action"]
    afraid_action = afraid.choose_action({"target": "archive"})["planned_action"]

    assert calm_action.startswith("gather information")
    assert afraid_action.startswith("confront archive")


def test_different_relationship_states_produce_different_dialogue_context():
    ally_agent = CharacterAgent(name="Asha")
    enemy_agent = CharacterAgent(name="Asha")
    ally_agent.relationships["Sen"] = RelationshipState(trust=0.9, respect=0.8, affection=0.8)
    enemy_agent.relationships["Sen"] = RelationshipState(trust=0.1, fear=0.8, resentment=0.9)

    ally_context = AgentSceneAdapter([ally_agent]).dialogue_context({"Asha": {"intention": "ask", "planned_action": "talk"}})
    enemy_context = AgentSceneAdapter([enemy_agent]).dialogue_context({"Asha": {"intention": "ask", "planned_action": "talk"}})

    assert ally_context["Asha"]["relationships"]["Sen"]["dialogue_stance"] == "open and cooperative"
    assert enemy_context["Asha"]["relationships"]["Sen"]["dialogue_stance"] == "guarded and confrontational"


def test_different_memories_produce_different_decisions():
    memory = MemoryManager()
    memory.register_character("Asha", "protagonist")
    memory.episodic.append(
        EpisodicRecord(
            chapter_num=1,
            scene_num=1,
            event="Asha found evidence about the ledger in the archive.",
            characters_involved=["Asha"],
            location="Delhi",
        )
    )
    adapter = AgentMemoryAdapter(memory, "Asha")
    agent = CharacterAgent(
        name="Asha",
        goals=[Goal("ledger", "use ledger evidence", 0.6, 0.5, 0.6, 1.0)],
        memory_interface=adapter,
    )

    decision = agent.choose_action({"target": "Sen"})

    assert decision["planned_action"].startswith("use remembered evidence")
    assert adapter.retrieve_relevant_memories("ledger evidence")[0].source == "episodic"


def test_goal_scoring_changes_action_selection():
    agent = CharacterAgent(
        name="Asha",
        goals=[
            Goal("low", "wait for permission", 0.2, 0.2, 0.9, 1.0),
            Goal("high", "rescue the witness", 0.9, 0.9, 0.8, 1.0),
        ],
        goal_evaluator=GoalEvaluator(),
    )

    decision = agent.choose_action({"target": "safe house"})

    assert decision["chosen_goal"] == "rescue the witness"
    assert decision["goal_score"] > 0.5


def test_structured_scene_updates_modify_graph_memory_and_agent_state():
    memory = MemoryManager()
    memory.register_character("Asha", "protagonist")
    adapter = AgentMemoryAdapter(memory, "Asha")
    agent = CharacterAgent(name="Asha", memory_interface=adapter)
    graph = NarrativeGraph()
    graph.add_character("Asha")
    graph.add_location("Delhi")
    extractor = StructuredSceneUpdateExtractor()

    update = extractor.extract(
        "Asha discovered a clue. The conflict with Sen became a danger. "
        "Asha promised to protect the witness. The answer fulfilled the promise."
    )
    extractor.apply_updates(
        update,
        graph=graph,
        memory_manager=memory,
        agents=[agent],
        chapter_num=2,
        scene_num=1,
        location="Delhi",
    )

    assert update.discovered_clues
    assert graph.active_nodes("mystery")
    assert graph.stats()["edge_count"] > 0
    assert len(memory.episodic) > 0
    assert agent.beliefs.discovered_information


def test_agent_planner_and_scene_adapter_trace():
    agent = CharacterAgent(
        name="Asha",
        goals=[Goal("g1", "protect the archive", 0.9, 0.8, 0.8, 1.0)],
        emotional_state=EmotionState(anger=0.8),
    )
    planner_context = AgentPlannerAdapter([agent]).enrich_context({"target": "Sen"}, ["Asha"])
    scene_context = AgentSceneAdapter([agent]).build_scene_context(planner_context)

    assert planner_context["agent_preferred_scene_type"] in {"action", "introspection"}
    assert "Asha pursues" in scene_context["agent_scene_guidance"][0]
    assert "protect the archive" in AgentSceneAdapter([agent]).trace("Asha", scene_context)
