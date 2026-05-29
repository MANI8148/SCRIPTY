from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class NarrativeNode:
    node_id: str
    chapter_num: int
    scene_num: int
    event: str
    characters: list[str]
    location: str


@dataclass(frozen=True)
class NarrativeEdge:
    source_id: str
    target_id: str
    edge_type: str


class NarrativeGraph:
    def __init__(self) -> None:
        self.nodes: list[NarrativeNode] = []
        self.edges: list[NarrativeEdge] = []

    def add_node(self, node: NarrativeNode) -> None:
        self.nodes.append(node)

    def infer_edges_from_timeline(self) -> None:
        existing = {(e.source_id, e.target_id) for e in self.edges}
        causal_words = {"because", "therefore", "so", "forced", "caused"}
        for left, right in zip(self.nodes, self.nodes[1:]):
            shared = set(left.characters) & set(right.characters) or left.location == right.location
            if not shared:
                continue
            edge_type = "causes" if causal_words & set(right.event.lower().split()) else "follows"
            if (left.node_id, right.node_id) not in existing:
                self.edges.append(NarrativeEdge(left.node_id, right.node_id, edge_type))

    def connectivity_score(self) -> float:
        if not self.nodes:
            return 0.0
        connected = {edge.source_id for edge in self.edges} | {edge.target_id for edge in self.edges}
        return len(connected) / len(self.nodes)

    def serialize(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"nodes": [asdict(n) for n in self.nodes], "edges": [asdict(e) for e in self.edges]}, indent=2, sort_keys=True), encoding="utf-8")
        return target
