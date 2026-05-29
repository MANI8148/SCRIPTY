from backend.research.narrative_graph import NarrativeGraph, NarrativeNode


def test_graph_connectivity_and_serialization(tmp_path):
    graph = NarrativeGraph()
    graph.add_node(NarrativeNode("a", 1, 1, "Asha arrives", ["Asha"], "Delhi"))
    graph.add_node(NarrativeNode("b", 1, 2, "Asha acts because danger rises", ["Asha"], "Delhi"))
    graph.infer_edges_from_timeline()
    assert graph.connectivity_score() == 1.0
    assert graph.edges[0].edge_type == "causes"
    assert graph.serialize(tmp_path / "graph.json").exists()

