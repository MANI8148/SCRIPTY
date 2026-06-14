import json

import pytest

from backend.research.memory_manager import MemoryManager, SemanticFact
from backend.research.narrative_graph import (
    KGEdge,
    KGNode,
    EdgeType,
    GraphPlannerAdapter,
    GraphQueryLayer,
    NarrativeGraph,
    NarrativeNode,
    NodeType,
)
from backend.research.story_bible_graph import StoryBibleGraph


class DummyScene:
    def __init__(self, scene_num: int, content: str) -> None:
        self.scene_num = scene_num
        self.content = content


class DummyChapter:
    chapter_num = 1
    summary = "Asha finds a clue because the archive danger rises."

    def __init__(self) -> None:
        self.scenes = [
            DummyScene(1, "Asha wants the ledger. A secret clue creates danger and a promise."),
            DummyScene(2, "The mystery is revealed and the promise receives payoff."),
        ]


def test_required_schema_and_networkx_backend():
    graph = NarrativeGraph()
    schema = graph.schema()
    assert schema["backend"] == "networkx.MultiDiGraph"
    assert {"character", "location", "item", "event", "faction", "secret"} <= set(schema["node_types"])
    assert {"owns", "knows", "visited", "allied_with", "hostile_to", "discovered", "caused", "located_in", "member_of"} <= set(schema["edge_types"])
    assert graph.validate() == []


def test_add_entities_relations_facts_and_paths():
    graph = NarrativeGraph()
    asha = graph.add_character("Asha", role="protagonist")
    delhi = graph.add_location("Delhi")
    ledger = graph.add_item("Ledger")
    secret = graph.get_or_create_node("Cipher Secret", NodeType.SECRET)
    graph.add_relation(asha.node_id, ledger.node_id, EdgeType.OWNS)
    graph.add_relation(asha.node_id, secret.node_id, EdgeType.KNOWS)
    graph.add_event("Asha visits Delhi", characters=["Asha"], location="Delhi", chapter_num=1, scene_num=1)

    character_facts = graph.get_character_facts("Asha")
    location_facts = graph.get_location_facts(delhi.label)

    assert any(row["relation"] == "owns" and row["entity"] == "Ledger" for row in character_facts["outgoing"])
    assert any(row["relation"] == "visited" and row["entity"] == "Delhi" for row in character_facts["outgoing"])
    assert any(row["relation"] == "located_in" for row in location_facts["incoming"])
    assert graph.who_knows_about("Cipher Secret") == ["Asha"]
    assert graph.path_between("Asha", "Delhi") == ["Asha", "Delhi"]
    assert graph.connectivity_score() == 1.0


def test_serialization_round_trip_preserves_kg(tmp_path):
    graph = NarrativeGraph()
    graph.add_character("Asha")
    graph.add_location("Delhi")
    graph.add_relation("Asha", "Delhi", "visited", chapter_num=2, scene_num=3)
    path = graph.serialize(tmp_path / "graph.json")

    payload = json.loads(path.read_text())
    restored = NarrativeGraph.deserialize(path)

    assert payload["stats"]["node_count"] == 2
    assert restored.get_character_facts("Asha")["outgoing"][0]["entity"] == "Delhi"
    assert restored.stats()["relation_types"]["visited"] == 1


def test_legacy_timeline_api_still_infers_edges():
    graph = NarrativeGraph()
    graph.add_node(NarrativeNode("a", 1, 1, "Asha arrives", ["Asha"], "Delhi"))
    graph.add_node(NarrativeNode("b", 1, 2, "Asha acts because danger rises", ["Asha"], "Delhi"))
    graph.infer_edges_from_timeline()
    assert graph.edges[0].edge_type == "causes"
    assert graph.stats()["relation_types"]["caused"] == 1


def test_story_bible_graph_reads_updates_and_syncs_memory():
    memory = MemoryManager()
    memory.register_character("Asha", "protagonist", ("curious",))
    memory.semantic.store(SemanticFact("Delhi", "setting", "Delhi in 1911", 0))
    bible = StoryBibleGraph(memory_manager=memory)
    bible.attach_memory_manager(memory)

    before = bible.before_chapter(1, protagonist="Asha", antagonist="Sen", location="Delhi")
    bible.update_from_chapter(DummyChapter(), {"protagonist": "Asha", "antagonist": "Sen", "location": "Delhi"})
    after = bible.before_chapter(2, protagonist="Asha", antagonist="Sen", location="Delhi")

    assert "graph_state" in before
    assert after["graph_state"]["location_history"]["previous_visits"]
    assert bible.graph.stats()["story_bible_coverage"] > 0.5
    assert len(memory.episodic) == 2
    assert memory.semantic.retrieve_for_entity("Asha")


def test_graph_query_layer_location_and_mystery_context():
    graph = NarrativeGraph()
    graph.add_character("Asha")
    graph.add_character("Sen")
    graph.add_location("Delhi")
    graph.add_relation("Asha", "Delhi", "visited", chapter_num=1, scene_num=1)
    graph.add_relation("Asha", "Sen", "hostile_to")
    graph.add_relation("Sen", "Delhi", "visited", chapter_num=1, scene_num=2)
    mystery = graph.add_story_fact("Asha", "mystery", "missing ledger", chapter_num=1)
    graph.add_relation("Asha", mystery.node_id, "discovered")

    query = GraphQueryLayer(graph)
    location_context = query.context_for_location("Asha", "Delhi")
    mystery_context = query.context_for_mystery(mystery.label)

    assert location_context["known_enemies_there"] == ["Sen"]
    assert mystery_context["related_clues"][0]["entity"] == "Asha"


def test_graph_planner_adapter_and_metrics():
    graph = NarrativeGraph()
    graph.add_character("Asha")
    goal = graph.add_story_fact("Asha", "goal", "protect the ledger", chapter_num=1)
    conflict = graph.add_story_fact("Asha", "conflict", "Sen blocks the archive", chapter_num=1)
    mystery = graph.add_story_fact("Asha", "mystery", "who forged the warrant", chapter_num=1)
    setup = graph.add_story_fact("Asha", "foreshadow", "cracked seal", chapter_num=1)
    event = graph.add_event("The seal matters", characters=["Asha"], location="Delhi", chapter_num=2, scene_num=1)
    graph.update_status(goal.node_id, "progressed", chapter_num=2)
    graph.update_status(conflict.node_id, "resolved", chapter_num=2)
    graph.update_status(mystery.node_id, "revealed", chapter_num=2)
    graph.add_relation(setup.node_id, event.node_id, "pays_off")

    guidance = GraphPlannerAdapter(graph).chapter_guidance(2, "Asha")
    stats = graph.stats()

    assert guidance["suggested_threads"]
    assert stats["goal_progress_rate"] == 1.0
    assert stats["conflict_resolution_rate"] == 1.0
    assert stats["mystery_completion_rate"] == 1.0
    assert stats["foreshadow_payoff_rate"] == 1.0
    assert stats["graph_utilization_rate"] == 0.0


def test_validation_and_error_paths():
    graph = NarrativeGraph()
    graph.add_character("Asha")
    graph.add_location("Delhi")
    with pytest.raises(KeyError):
        graph.add_relation("Asha", "Missing", "knows")
    with pytest.raises(ValueError):
        graph.get_character_facts("Delhi")
    assert graph.path_between("Asha", "Missing") == []
    assert graph.who_knows_about("Missing") == []


def test_low_level_branches_and_query_edges(tmp_path):
    graph = NarrativeGraph()
    node = KGNode("x", "character", "Asha")
    assert hash(node) == hash("x")
    graph.add_kg_node(node)
    graph.add_kg_node(KGNode("x2", "character", "Asha", attributes={"role": "lead"}))
    assert graph.get_character_facts("Asha")["entity"]["attributes"]["role"] == "lead"
    with pytest.raises(ValueError):
        graph.add_kg_node(KGNode("bad", "unsupported", "Bad"))
    with pytest.raises(ValueError):
        graph.add_kg_edge(KGEdge("x", "x", "unsupported"))
    with pytest.raises(KeyError):
        graph.add_kg_edge(KGEdge("x", "missing", "knows"))

    graph.add_location("Delhi")
    first = graph.add_relation("Asha", "Delhi", "visited", weight=0.2, notes="first")
    second = graph.add_relation("Asha", "Delhi", "visited", weight=0.9, notes="stronger", attributes={"seen": True})
    assert first.edge_id == second.edge_id
    assert second.weight == 0.9
    assert graph.previous_visits("Missing", "Delhi") == []
    assert graph.path_between("Asha", "Delhi", max_depth=0) == []
    assert graph.path_between("Asha", "Asha") == ["Asha"]

    graph.graph.nodes["x"]["entity_type"] = "invalid"
    graph.graph.nodes["x"]["label"] = ""
    graph.graph.edges[first.source_id, first.target_id, first.edge_id]["relation"] = "invalid"
    issues = graph.validate()
    assert any("invalid node type" in issue for issue in issues)
    assert any("missing label" in issue for issue in issues)
    assert any("invalid edge type" in issue for issue in issues)

    assert graph.serialize(tmp_path / "invalid.json").exists()


def test_event_queries_contradictions_cycles_and_retrieval():
    graph = NarrativeGraph()
    graph.add_character("Asha", death_chapter=1)
    graph.add_location("Delhi")
    graph.add_event("Asha returns", characters=["Asha"], location="Delhi", chapter_num=2, scene_num=1)
    graph.add_event("Asha waits", characters=["Asha"], location="Delhi", chapter_num=2, scene_num=2)
    assert graph.events_in_chapter(2)
    assert graph.characters_in_scene(2, 1) == ["Asha"]
    assert graph.characters_in_scene(2, 99) == []
    assert graph.contradicts("Asha returns")
    assert graph.contradicts("Missing") == []

    graph.add_event("First cause", event_id="cause:a")
    graph.add_event("Second cause", event_id="cause:b")
    graph.add_relation("cause:a", "cause:b", "caused")
    assert graph.causal_chain_depth() >= 1.0
    graph.add_relation("cause:b", "cause:a", "caused")
    assert graph.causal_chain_depth() >= 2.0

    query = GraphQueryLayer(graph)
    assert query.context_for_location("Missing", "Delhi")["known_enemies_there"] == []
    assert query.context_for_mystery("Missing") == {"related_clues": [], "prior_mentions": [], "pending_payoffs": []}
    assert query.retrieve(protagonist="Asha", location="Delhi")
    assert query.retrieve(mystery="Missing")["mystery_context"]["related_clues"] == []


def test_story_bible_optional_paths():
    bible = StoryBibleGraph(sync_to_memory=False)
    bible.graph.add_character("Asha")
    assert bible.before_chapter(1)["graph_state"]["relationship_evolution"] == []
    bible.update_from_chapter(DummyChapter(), {"protagonist": "Asha", "location": "Delhi"})
    assert len(bible.graph.events_in_chapter(1)) == 2
    assert bible._relationship_evolution("", "") == []
    assert bible._relationship_evolution("Asha", "Missing") == []


def test_remaining_graph_branches(tmp_path):
    graph = NarrativeGraph()
    assert graph.connectivity_score() == 0.0
    graph.add_character("Asha")
    graph.get_or_create_node("Asha", attributes={"role": "lead"})
    graph.add_character("Asha!")
    graph.add_character("Asha?")
    assert len(graph._nodes) >= 3

    graph.record_event("Recorded event", ["Asha"], "Delhi", 3, 1)
    graph.record_relation("New A", "knows", "New B")
    graph.add_location("Cairo")
    assert graph.path_between("Asha", "Cairo") == []

    graph.add_node(NarrativeNode("left", 1, 1, "Left", ["Asha"], "Delhi"))
    graph.add_node(NarrativeNode("right", 1, 2, "Right", ["Sen"], "Cairo"))
    graph.infer_edges_from_timeline()
    assert all(edge.source_id != "left" or edge.target_id != "right" for edge in graph.edges)

    payload = {
        "kg_nodes": [],
        "kg_edges": [],
        "nodes": [asdict_node("legacy", 1, 1, "Legacy", ["Asha"], "Delhi")],
        "edges": [{"source_id": "legacy", "target_id": "legacy2", "edge_type": "follows"}],
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    restored = NarrativeGraph.deserialize(path)
    assert restored.nodes[0].node_id == "legacy"
    assert restored.edges[0].edge_type == "follows"


def test_remaining_adapter_and_story_bible_branches():
    graph = NarrativeGraph()
    graph.add_character("Asha")
    conflict = graph.add_story_fact("Asha", "conflict", "unresolved duel", chapter_num=1)
    promise = graph.add_story_fact("Asha", "promise", "return the seal", chapter_num=1)
    event = graph.add_event("Promise paid", characters=["Asha"], location="Delhi", chapter_num=2, scene_num=1)
    graph.add_relation(promise.node_id, event.node_id, "pays_off")
    mystery = graph.add_story_fact("Asha", "mystery", "missing seal", chapter_num=1)
    graph.add_relation(mystery.node_id, event.node_id, "pays_off")

    guidance = GraphPlannerAdapter(graph).chapter_guidance(2, "Asha")
    assert any("Continue unresolved conflict" in item for item in guidance["suggested_threads"])
    context = GraphQueryLayer(graph).context_for_mystery(mystery.label)
    assert context["pending_payoffs"]

    bible = StoryBibleGraph(graph=NarrativeGraph())
    bible.graph.add_character("Asha")
    bible.graph.add_location("Delhi")
    bible_event = bible.graph.add_event("Omen appears", characters=["Asha"], location="Delhi", chapter_num=1, scene_num=1)
    bible._extract_story_bible_facts(
        "An omen and hint foreshadow the final answer.",
        bible_event.node_id,
        1,
        1,
        ["Asha"],
        "Delhi",
    )
    assert bible.graph.active_nodes(NodeType.FORESHADOW)


def asdict_node(node_id, chapter_num, scene_num, event, characters, location):
    return {
        "node_id": node_id,
        "chapter_num": chapter_num,
        "scene_num": scene_num,
        "event": event,
        "characters": characters,
        "location": location,
    }
