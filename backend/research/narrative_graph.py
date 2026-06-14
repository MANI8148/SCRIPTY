"""
NetworkX-backed narrative knowledge graph for SCRIPTY.

The graph is intentionally both a story-bible store and a generation input:
chapter context can be read from it before generation, and generated scenes
can update it afterward. The legacy ``NarrativeGraph`` and ``NarrativeNode``
API is preserved for older engine and metric callers.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional

import networkx as nx

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    OBJECT = "object"
    EVENT = "event"
    FACTION = "faction"
    SECRET = "secret"
    GOAL = "goal"
    CONFLICT = "conflict"
    MYSTERY = "mystery"
    PROMISE = "promise"
    FORESHADOW = "foreshadow"


class EdgeType(str, Enum):
    OWNS = "owns"
    KNOWS = "knows"
    KNOWS_ABOUT = "knows_about"
    VISITED = "visited"
    ALLIED_WITH = "allied_with"
    HOSTILE_TO = "hostile_to"
    DISCOVERED = "discovered"
    CAUSED = "caused"
    CAUSES = "causes"
    LOCATED_IN = "located_in"
    LOCATED_AT = "located_at"
    MEMBER_OF = "member_of"
    PARTICIPATED_IN = "participated_in"
    PRECEDED_BY = "preceded_by"
    FOLLOWS = "follows"
    WANTS = "wants"
    FEARS = "fears"
    ALLY_OF = "ally_of"
    ENEMY_OF = "enemy_of"
    PREVENTED = "prevented"
    PROMISED = "promised"
    FORESHADOWS = "foreshadows"
    PAYS_OFF = "pays_off"
    REMEMBERS = "remembers"
    LOST = "lost"
    FOUND = "found"
    RELATED = "related"


# Backward-compatible names used by existing imports.
EntityType = NodeType
RelationType = EdgeType

REQUIRED_NODE_TYPES = {
    NodeType.CHARACTER.value,
    NodeType.LOCATION.value,
    NodeType.ITEM.value,
    NodeType.EVENT.value,
    NodeType.FACTION.value,
    NodeType.SECRET.value,
}

REQUIRED_EDGE_TYPES = {
    EdgeType.OWNS.value,
    EdgeType.KNOWS.value,
    EdgeType.VISITED.value,
    EdgeType.ALLIED_WITH.value,
    EdgeType.HOSTILE_TO.value,
    EdgeType.DISCOVERED.value,
    EdgeType.CAUSED.value,
    EdgeType.LOCATED_IN.value,
    EdgeType.MEMBER_OF.value,
}


@dataclass
class KGNode:
    node_id: str
    entity_type: str
    label: str
    chapter_num: int = 0
    scene_num: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.node_id)


@dataclass
class KGEdge:
    source_id: str
    target_id: str
    relation: str
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chapter_num: int = 0
    scene_num: int = 0
    weight: float = 1.0
    notes: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


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


_CAUSAL_WORDS = {"because", "therefore", "so", "forced", "caused", "led", "resulted"}
_NODE_ALIASES = {"object": "item"}
_EDGE_ALIASES = {
    "knows_about": EdgeType.KNOWS.value,
    "causes": EdgeType.CAUSED.value,
    "located_at": EdgeType.LOCATED_IN.value,
    "ally_of": EdgeType.ALLIED_WITH.value,
    "enemy_of": EdgeType.HOSTILE_TO.value,
}


def _normalize_node_type(value: str | NodeType) -> str:
    raw = value.value if isinstance(value, NodeType) else str(value).lower()
    return _NODE_ALIASES.get(raw, raw)


def _normalize_edge_type(value: str | EdgeType) -> str:
    raw = value.value if isinstance(value, EdgeType) else str(value).lower()
    return _EDGE_ALIASES.get(raw, raw)


class NarrativeKnowledgeGraph:
    """Production narrative graph backed by ``networkx.MultiDiGraph``."""

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._label_index: dict[str, str] = {}
        self.nodes: list[NarrativeNode] = []
        self.edges: list[NarrativeEdge] = []
        self._graph_context_reads = 0
        self._graph_context_uses = 0

    @property
    def _nodes(self) -> dict[str, KGNode]:
        return {
            node_id: KGNode(
                node_id=node_id,
                entity_type=data["entity_type"],
                label=data["label"],
                chapter_num=data.get("chapter_num", 0),
                scene_num=data.get("scene_num", 0),
                attributes=dict(data.get("attributes", {})),
            )
            for node_id, data in self.graph.nodes(data=True)
        }

    @property
    def _edges(self) -> list[KGEdge]:
        return [
            KGEdge(
                edge_id=key,
                source_id=source,
                target_id=target,
                relation=data["relation"],
                chapter_num=data.get("chapter_num", 0),
                scene_num=data.get("scene_num", 0),
                weight=data.get("weight", 1.0),
                notes=data.get("notes", ""),
                attributes=dict(data.get("attributes", {})),
            )
            for source, target, key, data in self.graph.edges(keys=True, data=True)
        ]

    # ------------------------------------------------------------------
    # Schema and validation
    # ------------------------------------------------------------------

    def schema(self) -> dict[str, Any]:
        return {
            "node_types": [node_type.value for node_type in NodeType],
            "edge_types": [edge_type.value for edge_type in EdgeType],
            "required_node_types": sorted(REQUIRED_NODE_TYPES),
            "required_edge_types": sorted(REQUIRED_EDGE_TYPES),
            "backend": "networkx.MultiDiGraph",
            "update_rules": [
                "Every generated scene creates an event node.",
                "Scene participants are linked to events with participated_in.",
                "Scene locations are linked with located_in and visited.",
                "Conflicts, goals, mysteries, promises, and foreshadowing remain active until status changes.",
                "Payoff edges connect promise or foreshadow nodes to resolving events.",
            ],
            "validation_rules": [
                "Node and edge types must be declared in the schema.",
                "Relations require existing source and target nodes.",
                "Duplicate source-target-relation edges are merged by default.",
                "Character facts and location facts are derived only from typed graph relations.",
            ],
        }

    def validate(self) -> list[str]:
        issues: list[str] = []
        valid_nodes = {node_type.value for node_type in NodeType}
        valid_edges = {edge_type.value for edge_type in EdgeType}
        for node_id, data in self.graph.nodes(data=True):
            if data.get("entity_type") not in valid_nodes:
                issues.append(f"invalid node type for {node_id}: {data.get('entity_type')}")
            if not data.get("label"):
                issues.append(f"missing label for {node_id}")
        for source, target, _key, data in self.graph.edges(keys=True, data=True):
            if source not in self.graph or target not in self.graph:  # pragma: no cover - NetworkX removes dangling edges.
                issues.append(f"dangling edge {source}->{target}")
            if data.get("relation") not in valid_edges:
                issues.append(f"invalid edge type for {source}->{target}: {data.get('relation')}")
        return issues

    # ------------------------------------------------------------------
    # Core node and relation APIs
    # ------------------------------------------------------------------

    def add_kg_node(self, node: KGNode) -> KGNode:
        entity_type = _normalize_node_type(node.entity_type)
        if entity_type not in {node_type.value for node_type in NodeType}:
            raise ValueError(f"Unsupported node type: {node.entity_type}")
        existing_id = self._label_index.get(node.label.lower())
        allow_repeated_label = entity_type == NodeType.EVENT.value
        if existing_id and not allow_repeated_label:
            data = self.graph.nodes[existing_id]
            data["attributes"].update(node.attributes)
            return self._node_from_id(existing_id)
        self.graph.add_node(
            node.node_id,
            entity_type=entity_type,
            label=node.label,
            chapter_num=node.chapter_num,
            scene_num=node.scene_num,
            attributes=dict(node.attributes),
        )
        self._label_index.setdefault(node.label.lower(), node.node_id)
        logger.debug("narrative_graph_node_added", extra={"node_id": node.node_id, "type": entity_type})
        return self._node_from_id(node.node_id)

    def add_kg_edge(self, edge: KGEdge, *, merge_duplicate: bool = True) -> KGEdge:
        relation = _normalize_edge_type(edge.relation)
        if relation not in {edge_type.value for edge_type in EdgeType}:
            raise ValueError(f"Unsupported edge type: {edge.relation}")
        if edge.source_id not in self.graph or edge.target_id not in self.graph:
            raise KeyError(f"Both relation endpoints must exist: {edge.source_id}, {edge.target_id}")
        if merge_duplicate:
            for _source, target, key, data in self.graph.out_edges(edge.source_id, keys=True, data=True):
                if target == edge.target_id and data.get("relation") == relation:
                    data["weight"] = max(float(data.get("weight", 1.0)), edge.weight)
                    data["notes"] = edge.notes or data.get("notes", "")
                    data.setdefault("attributes", {}).update(edge.attributes)
                    return self._edge_from_key(edge.source_id, edge.target_id, key)
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            key=edge.edge_id,
            relation=relation,
            chapter_num=edge.chapter_num,
            scene_num=edge.scene_num,
            weight=edge.weight,
            notes=edge.notes,
            attributes=dict(edge.attributes),
        )
        logger.debug(
            "narrative_graph_edge_added",
            extra={"source": edge.source_id, "target": edge.target_id, "relation": relation},
        )
        return self._edge_from_key(edge.source_id, edge.target_id, edge.edge_id)

    def get_or_create_node(
        self,
        label: str,
        entity_type: str | NodeType = NodeType.CHARACTER,
        chapter_num: int = 0,
        scene_num: int = 0,
        attributes: Optional[dict[str, Any]] = None,
    ) -> KGNode:
        key = label.lower()
        if key in self._label_index:
            node = self._node_from_id(self._label_index[key])
            if attributes:
                self.graph.nodes[node.node_id].setdefault("attributes", {}).update(attributes)
                node.attributes.update(attributes)
            return node
        stable = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip().lower()).strip("_") or str(uuid.uuid4())
        node_id = f"{_normalize_node_type(entity_type)}:{stable}"
        if node_id in self.graph:
            node_id = f"{node_id}:{uuid.uuid4()}"
        return self.add_kg_node(KGNode(node_id, _normalize_node_type(entity_type), label, chapter_num, scene_num, attributes or {}))

    def add_character(self, name: str, **attributes: Any) -> KGNode:
        return self.get_or_create_node(name, NodeType.CHARACTER, attributes=attributes)

    def add_location(self, name: str, **attributes: Any) -> KGNode:
        return self.get_or_create_node(name, NodeType.LOCATION, attributes=attributes)

    def add_item(self, name: str, **attributes: Any) -> KGNode:
        return self.get_or_create_node(name, NodeType.ITEM, attributes=attributes)

    def add_event(
        self,
        description: str,
        *,
        characters: Optional[list[str]] = None,
        location: str = "",
        chapter_num: int = 0,
        scene_num: int = 0,
        **attributes: Any,
    ) -> KGNode:
        event_id = attributes.pop("event_id", f"event:{chapter_num}:{scene_num}:{len(self.graph.nodes)}")
        node = self.add_kg_node(
            KGNode(
                node_id=event_id,
                entity_type=NodeType.EVENT.value,
                label=description[:120],
                chapter_num=chapter_num,
                scene_num=scene_num,
                attributes={"description": description, "characters": characters or [], "location": location, **attributes},
            )
        )
        for character in characters or []:
            char_node = self.add_character(character)
            self.add_relation(char_node.node_id, node.node_id, EdgeType.PARTICIPATED_IN, chapter_num=chapter_num, scene_num=scene_num)
        if location:
            loc_node = self.add_location(location)
            self.add_relation(node.node_id, loc_node.node_id, EdgeType.LOCATED_IN, chapter_num=chapter_num, scene_num=scene_num)
            for character in characters or []:
                char_node = self.add_character(character)
                self.add_relation(char_node.node_id, loc_node.node_id, EdgeType.VISITED, chapter_num=chapter_num, scene_num=scene_num)
        return node

    def add_relation(
        self,
        source: str,
        target: str,
        relation: str | EdgeType,
        *,
        chapter_num: int = 0,
        scene_num: int = 0,
        weight: float = 1.0,
        notes: str = "",
        attributes: Optional[dict[str, Any]] = None,
    ) -> KGEdge:
        source_id = self._resolve_node_id(source)
        target_id = self._resolve_node_id(target)
        return self.add_kg_edge(
            KGEdge(
                source_id=source_id,
                target_id=target_id,
                relation=_normalize_edge_type(relation),
                chapter_num=chapter_num,
                scene_num=scene_num,
                weight=weight,
                notes=notes,
                attributes=attributes or {},
            )
        )

    # Backward-compatible helper names.
    record_character = add_character
    record_location = add_location

    def record_event(
        self,
        description: str,
        characters: list[str],
        location: str,
        chapter_num: int,
        scene_num: int,
    ) -> KGNode:
        return self.add_event(description, characters=characters, location=location, chapter_num=chapter_num, scene_num=scene_num)

    def record_relation(self, label_a: str, relation: str, label_b: str, chapter_num: int = 0, scene_num: int = 0, notes: str = "") -> KGEdge:
        if label_a.lower() not in self._label_index:
            self.get_or_create_node(label_a)
        if label_b.lower() not in self._label_index:
            self.get_or_create_node(label_b)
        return self.add_relation(label_a, label_b, relation, chapter_num=chapter_num, scene_num=scene_num, notes=notes)

    # ------------------------------------------------------------------
    # Story-bible mutation helpers
    # ------------------------------------------------------------------

    def add_story_fact(self, entity: str, fact_type: str, value: str, *, chapter_num: int = 0, status: str = "active") -> KGNode:
        owner = self.get_or_create_node(entity)
        fact_node = self.get_or_create_node(
            f"{entity}:{fact_type}:{value}",
            self._node_type_for_fact(fact_type),
            chapter_num=chapter_num,
            attributes={"fact_type": fact_type, "value": value, "status": status},
        )
        relation = EdgeType.WANTS if fact_type == "goal" else EdgeType.RELATED
        self.add_relation(owner.node_id, fact_node.node_id, relation, chapter_num=chapter_num)
        return fact_node

    def update_status(self, label_or_id: str, status: str, *, chapter_num: int = 0) -> None:
        node_id = self._resolve_node_id(label_or_id)
        self.graph.nodes[node_id].setdefault("attributes", {})["status"] = status
        self.graph.nodes[node_id].setdefault("attributes", {})["status_chapter"] = chapter_num

    def mark_graph_context_read(self) -> None:
        self._graph_context_reads += 1

    def mark_graph_context_used(self) -> None:
        self._graph_context_uses += 1

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_entity(self, label: str) -> Optional[KGNode]:
        node_id = self._label_index.get(label.lower())
        return self._node_from_id(node_id) if node_id else None

    def relations_of(self, node_id_or_label: str) -> list[KGEdge]:
        node_id = self._resolve_node_id(node_id_or_label)
        edges: list[KGEdge] = []
        for source, target, key in self.graph.in_edges(node_id, keys=True):
            edges.append(self._edge_from_key(source, target, key))
        for source, target, key in self.graph.out_edges(node_id, keys=True):
            edges.append(self._edge_from_key(source, target, key))
        return edges

    def get_character_facts(self, character: str) -> dict[str, Any]:
        return self._entity_facts(character, expected_type=NodeType.CHARACTER.value)

    def get_location_facts(self, location: str) -> dict[str, Any]:
        return self._entity_facts(location, expected_type=NodeType.LOCATION.value)

    def who_knows_about(self, entity_label: str) -> list[str]:
        try:
            target_id = self._resolve_node_id(entity_label)
        except KeyError:
            return []
        knowers: list[str] = []
        for source, target, data in self.graph.in_edges(target_id, data=True):
            if data.get("relation") in {EdgeType.KNOWS.value, EdgeType.DISCOVERED.value, EdgeType.KNOWS_ABOUT.value}:
                source_data = self.graph.nodes[source]
                if source_data.get("entity_type") == NodeType.CHARACTER.value:
                    knowers.append(source_data["label"])
        return sorted(dict.fromkeys(knowers))

    def path_between(self, label_a: str, label_b: str, max_depth: int = 8) -> list[str]:
        try:
            source = self._resolve_node_id(label_a)
            target = self._resolve_node_id(label_b)
        except KeyError:
            return []
        if source == target:
            return [self.graph.nodes[source]["label"]]
        undirected = self.graph.to_undirected(as_view=True)
        try:
            path = nx.shortest_path(undirected, source=source, target=target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        if len(path) - 1 > max_depth:
            return []
        return [self.graph.nodes[node_id]["label"] for node_id in path]

    def active_nodes(self, node_type: str | NodeType) -> list[KGNode]:
        normalized = _normalize_node_type(node_type)
        return [
            self._node_from_id(node_id)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("entity_type") == normalized and data.get("attributes", {}).get("status", "active") == "active"
        ]

    def previous_visits(self, character: str, location: str) -> list[dict[str, Any]]:
        try:
            char_id = self._resolve_node_id(character)
            loc_id = self._resolve_node_id(location)
        except KeyError:
            return []
        visits = []
        for _source, target, data in self.graph.out_edges(char_id, data=True):
            if target == loc_id and data.get("relation") == EdgeType.VISITED.value:
                visits.append({"chapter_num": data.get("chapter_num", 0), "scene_num": data.get("scene_num", 0), "location": location})
        return sorted(visits, key=lambda row: (row["chapter_num"], row["scene_num"]))

    def events_in_chapter(self, chapter_num: int) -> list[KGNode]:
        return [
            self._node_from_id(node_id)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("entity_type") == NodeType.EVENT.value and data.get("chapter_num") == chapter_num
        ]

    def characters_in_scene(self, chapter_num: int, scene_num: int) -> list[str]:
        result: list[str] = []
        for event in self.events_in_chapter(chapter_num):
            if event.scene_num != scene_num:
                continue
            result.extend(str(name) for name in event.attributes.get("characters", []))
        return list(dict.fromkeys(result))

    def contradicts(self, event_label: str) -> list[str]:
        event = self.get_entity(event_label)
        if not event:
            return []
        issues: list[str] = []
        for character in event.attributes.get("characters", []):
            char_node = self.get_entity(character)
            if char_node and char_node.attributes.get("death_chapter", 10**9) < event.chapter_num:
                issues.append(f"{character} appears after death in chapter {event.chapter_num}.")
        return issues

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def connectivity_score(self) -> float:
        if self.graph.number_of_nodes() == 0:
            return 0.0
        connected: set[str] = set()
        for source, target in self.graph.edges():
            connected.add(source)
            connected.add(target)
        return round(len(connected) / self.graph.number_of_nodes(), 6)

    def goal_progress_rate(self) -> float:
        goals = self._nodes_by_type(NodeType.GOAL)
        progressed = [n for n in goals if n.attributes.get("status") in {"progressed", "completed", "resolved"}]
        return self._ratio(progressed, goals)

    def conflict_resolution_rate(self) -> float:
        conflicts = self._nodes_by_type(NodeType.CONFLICT)
        resolved = [n for n in conflicts if n.attributes.get("status") in {"resolved", "completed"}]
        return self._ratio(resolved, conflicts)

    def mystery_completion_rate(self) -> float:
        mysteries = self._nodes_by_type(NodeType.MYSTERY)
        completed = [n for n in mysteries if n.attributes.get("status") in {"revealed", "resolved", "completed"}]
        return self._ratio(completed, mysteries)

    def relationship_consistency(self) -> float:
        pairs: dict[frozenset[str], set[str]] = {}
        for edge in self._edges:
            if edge.relation in {EdgeType.ALLIED_WITH.value, EdgeType.HOSTILE_TO.value, EdgeType.ALLY_OF.value, EdgeType.ENEMY_OF.value}:
                pairs.setdefault(frozenset({edge.source_id, edge.target_id}), set()).add(edge.relation)
        contradictory = sum(1 for values in pairs.values() if EdgeType.ALLIED_WITH.value in values and EdgeType.HOSTILE_TO.value in values)
        return round(1.0 - (contradictory / max(1, len(pairs))), 6)

    def entity_consistency(self) -> float:
        return 1.0 if not self.validate() else 0.0

    def causal_chain_depth(self) -> float:
        causal = nx.DiGraph()
        causal.add_nodes_from(self.graph.nodes)
        causal.add_edges_from((e.source_id, e.target_id) for e in self._edges if e.relation in {EdgeType.CAUSED.value, EdgeType.CAUSES.value})
        if causal.number_of_edges() == 0:
            return 0.0
        if not nx.is_directed_acyclic_graph(causal):
            return float(len(max(nx.simple_cycles(causal), key=len, default=[])))
        depths: dict[str, int] = {}
        for node in nx.topological_sort(causal):
            predecessors = list(causal.predecessors(node))
            depths[node] = 0 if not predecessors else max(depths[pred] + 1 for pred in predecessors)
        return float(max(depths.values(), default=0))

    def foreshadow_payoff_rate(self) -> float:
        setups = self._nodes_by_type(NodeType.FORESHADOW)
        paid = {edge.source_id for edge in self._edges if edge.relation == EdgeType.PAYS_OFF.value}
        return self._ratio([node for node in setups if node.node_id in paid or node.attributes.get("status") == "paid_off"], setups)

    def graph_utilization_rate(self) -> float:
        return round(self._graph_context_uses / max(1, self._graph_context_reads), 6)

    def story_bible_coverage(self) -> float:
        present = {data.get("entity_type") for _node, data in self.graph.nodes(data=True)}
        expected = {NodeType.CHARACTER.value, NodeType.LOCATION.value, NodeType.EVENT.value, NodeType.GOAL.value, NodeType.CONFLICT.value, NodeType.MYSTERY.value}
        return round(len(present & expected) / len(expected), 6)

    def long_term_memory_usage(self) -> float:
        remembered = [edge for edge in self._edges if edge.relation in {EdgeType.REMEMBERS.value, EdgeType.KNOWS.value, EdgeType.DISCOVERED.value}]
        return round(len(remembered) / max(1, self.graph.number_of_edges()), 6)

    def stats(self) -> dict[str, Any]:
        entity_counts = Counter(data.get("entity_type") for _node, data in self.graph.nodes(data=True))
        relation_counts = Counter(data.get("relation") for *_rest, data in self.graph.edges(keys=True, data=True))
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "entity_types": dict(entity_counts),
            "relation_types": dict(relation_counts),
            "connectivity_score": self.connectivity_score(),
            "goal_progress_rate": self.goal_progress_rate(),
            "conflict_resolution_rate": self.conflict_resolution_rate(),
            "mystery_completion_rate": self.mystery_completion_rate(),
            "relationship_consistency": self.relationship_consistency(),
            "entity_consistency": self.entity_consistency(),
            "causal_chain_depth": self.causal_chain_depth(),
            "foreshadow_payoff_rate": self.foreshadow_payoff_rate(),
            "graph_utilization_rate": self.graph_utilization_rate(),
            "story_bible_coverage": self.story_bible_coverage(),
            "long_term_memory_usage": self.long_term_memory_usage(),
        }

    # ------------------------------------------------------------------
    # Legacy timeline API
    # ------------------------------------------------------------------

    def add_node(self, node: NarrativeNode) -> None:
        self.nodes.append(node)
        self.add_event(
            node.event,
            characters=list(node.characters),
            location=node.location,
            chapter_num=node.chapter_num,
            scene_num=node.scene_num,
            event_id=node.node_id,
        )

    def infer_edges_from_timeline(self) -> None:
        existing = {(edge.source_id, edge.target_id) for edge in self.edges}
        for left, right in zip(self.nodes, self.nodes[1:]):
            if not (set(left.characters) & set(right.characters) or left.location == right.location):
                continue
            causal = bool(_CAUSAL_WORDS & set(right.event.lower().split()))
            legacy_type = "causes" if causal else "follows"
            if (left.node_id, right.node_id) not in existing:
                self.edges.append(NarrativeEdge(left.node_id, right.node_id, legacy_type))
            self.add_relation(left.node_id, right.node_id, EdgeType.CAUSED if causal else EdgeType.FOLLOWS, chapter_num=right.chapter_num, scene_num=right.scene_num)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema(),
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "kg_nodes": [
                {"node_id": node_id, **data}
                for node_id, data in self.graph.nodes(data=True)
            ],
            "kg_edges": [
                {"edge_id": key, "source_id": source, "target_id": target, **data}
                for source, target, key, data in self.graph.edges(keys=True, data=True)
            ],
            "stats": self.stats(),
        }

    def serialize(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def deserialize(cls, path: str | Path) -> "NarrativeKnowledgeGraph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        graph = cls()
        for node_data in data.get("kg_nodes", []):
            graph.add_kg_node(
                KGNode(
                    node_id=node_data["node_id"],
                    entity_type=node_data["entity_type"],
                    label=node_data["label"],
                    chapter_num=node_data.get("chapter_num", 0),
                    scene_num=node_data.get("scene_num", 0),
                    attributes=node_data.get("attributes", {}),
                )
            )
        for edge_data in data.get("kg_edges", []):
            graph.add_kg_edge(
                KGEdge(
                    edge_id=edge_data.get("edge_id", str(uuid.uuid4())),
                    source_id=edge_data["source_id"],
                    target_id=edge_data["target_id"],
                    relation=edge_data["relation"],
                    chapter_num=edge_data.get("chapter_num", 0),
                    scene_num=edge_data.get("scene_num", 0),
                    weight=edge_data.get("weight", 1.0),
                    notes=edge_data.get("notes", ""),
                    attributes=edge_data.get("attributes", {}),
                ),
                merge_duplicate=False,
            )
        for node in data.get("nodes", []):
            graph.nodes.append(NarrativeNode(**node))
        for edge in data.get("edges", []):
            graph.edges.append(NarrativeEdge(**edge))
        return graph

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_node_id(self, node_id_or_label: str) -> str:
        if node_id_or_label in self.graph:
            return node_id_or_label
        key = node_id_or_label.lower()
        if key in self._label_index:
            return self._label_index[key]
        raise KeyError(f"Unknown graph node: {node_id_or_label}")

    def _node_from_id(self, node_id: str) -> KGNode:
        data = self.graph.nodes[node_id]
        return KGNode(
            node_id=node_id,
            entity_type=data["entity_type"],
            label=data["label"],
            chapter_num=data.get("chapter_num", 0),
            scene_num=data.get("scene_num", 0),
            attributes=dict(data.get("attributes", {})),
        )

    def _edge_from_key(self, source: str, target: str, key: str) -> KGEdge:
        data = self.graph.edges[source, target, key]
        return KGEdge(
            edge_id=key,
            source_id=source,
            target_id=target,
            relation=data["relation"],
            chapter_num=data.get("chapter_num", 0),
            scene_num=data.get("scene_num", 0),
            weight=data.get("weight", 1.0),
            notes=data.get("notes", ""),
            attributes=dict(data.get("attributes", {})),
        )

    def _entity_facts(self, label: str, *, expected_type: str) -> dict[str, Any]:
        node_id = self._resolve_node_id(label)
        node = self._node_from_id(node_id)
        if node.entity_type != expected_type:
            raise ValueError(f"{label} is {node.entity_type}, expected {expected_type}")
        outgoing = []
        incoming = []
        for edge in self.relations_of(node_id):
            other_id = edge.target_id if edge.source_id == node_id else edge.source_id
            other = self._node_from_id(other_id)
            row = {
                "relation": edge.relation,
                "entity": other.label,
                "entity_type": other.entity_type,
                "chapter_num": edge.chapter_num,
                "scene_num": edge.scene_num,
                "notes": edge.notes,
            }
            if edge.source_id == node_id:
                outgoing.append(row)
            else:
                incoming.append(row)
        return {"entity": asdict(node), "outgoing": outgoing, "incoming": incoming}

    def _nodes_by_type(self, node_type: NodeType) -> list[KGNode]:
        return [self._node_from_id(node_id) for node_id, data in self.graph.nodes(data=True) if data.get("entity_type") == node_type.value]

    def _node_type_for_fact(self, fact_type: str) -> NodeType:
        mapping = {
            "goal": NodeType.GOAL,
            "conflict": NodeType.CONFLICT,
            "mystery": NodeType.MYSTERY,
            "promise": NodeType.PROMISE,
            "foreshadow": NodeType.FORESHADOW,
            "secret": NodeType.SECRET,
        }
        return mapping.get(fact_type, NodeType.SECRET)

    @staticmethod
    def _ratio(numerator: Iterable[Any], denominator: Iterable[Any]) -> float:
        den = list(denominator)
        if not den:
            return 0.0
        return round(len(list(numerator)) / len(den), 6)


class GraphQueryLayer:
    """Retrieval-oriented graph queries for chapter context assembly."""

    def __init__(self, graph: NarrativeKnowledgeGraph) -> None:
        self.graph = graph

    def context_for_location(self, protagonist: str, location: str) -> dict[str, Any]:
        visits = self.graph.previous_visits(protagonist, location)
        conflicts = [
            asdict(node) for node in self.graph.active_nodes(NodeType.CONFLICT)
            if location.lower() in json.dumps(node.attributes).lower() or location.lower() in node.label.lower()
        ]
        enemies = []
        try:
            protagonist_id = self.graph._resolve_node_id(protagonist)
            location_id = self.graph._resolve_node_id(location)
        except KeyError:
            return {"previous_visits": visits, "unresolved_conflicts": conflicts, "known_enemies_there": []}
        for _source, target, data in self.graph.graph.out_edges(protagonist_id, data=True):
            if data.get("relation") != EdgeType.HOSTILE_TO.value:
                continue
            for _enemy, enemy_target, enemy_data in self.graph.graph.out_edges(target, data=True):
                if enemy_target == location_id and enemy_data.get("relation") in {EdgeType.VISITED.value, EdgeType.LOCATED_IN.value}:
                    enemies.append(self.graph.graph.nodes[target]["label"])
        return {"previous_visits": visits, "unresolved_conflicts": conflicts, "known_enemies_there": sorted(set(enemies))}

    def context_for_mystery(self, mystery: str) -> dict[str, Any]:
        node = self.graph.get_entity(mystery)
        if not node:
            return {"related_clues": [], "prior_mentions": [], "pending_payoffs": []}
        clues = []
        mentions = []
        payoffs = []
        for edge in self.graph.relations_of(node.node_id):
            other_id = edge.target_id if edge.source_id == node.node_id else edge.source_id
            other = self.graph._node_from_id(other_id)
            row = {"relation": edge.relation, "entity": other.label, "chapter_num": edge.chapter_num}
            if edge.relation in {EdgeType.DISCOVERED.value, EdgeType.KNOWS.value}:
                clues.append(row)
            elif edge.relation == EdgeType.PAYS_OFF.value:
                payoffs.append(row)
            else:
                mentions.append(row)
        return {"related_clues": clues, "prior_mentions": mentions, "pending_payoffs": payoffs}

    def retrieve(self, *, protagonist: str = "", location: str = "", mystery: str = "") -> dict[str, Any]:
        context: dict[str, Any] = {}
        if protagonist and location:
            context["location_context"] = self.context_for_location(protagonist, location)
        if mystery:
            context["mystery_context"] = self.context_for_mystery(mystery)
        return context


class GraphPlannerAdapter:
    """Turns graph state into planner constraints and opportunities."""

    def __init__(self, graph: NarrativeKnowledgeGraph) -> None:
        self.graph = graph

    def chapter_guidance(self, chapter_num: int, protagonist: str = "") -> dict[str, Any]:
        conflicts = [asdict(node) for node in self.graph.active_nodes(NodeType.CONFLICT)]
        mysteries = [asdict(node) for node in self.graph.active_nodes(NodeType.MYSTERY)]
        goals = [asdict(node) for node in self.graph.active_nodes(NodeType.GOAL)]
        promises = [asdict(node) for node in self.graph.active_nodes(NodeType.PROMISE)]
        foreshadows = [asdict(node) for node in self.graph.active_nodes(NodeType.FORESHADOW)]
        guidance = {
            "conflict_continuations": conflicts[:3],
            "mystery_progression": mysteries[:3],
            "goal_progression": goals[:3],
            "payoff_opportunities": (promises + foreshadows)[:3],
            "suggested_threads": [],
        }
        for node in conflicts[:2]:
            guidance["suggested_threads"].append(f"Continue unresolved conflict: {node['label']}")
        for node in mysteries[:2]:
            guidance["suggested_threads"].append(f"Advance mystery: {node['label']}")
        for node in goals[:2]:
            guidance["suggested_threads"].append(f"Pressure active goal: {node['label']}")
        for node in guidance["payoff_opportunities"][:2]:
            guidance["suggested_threads"].append(f"Look for payoff opportunity: {node['label']}")
        self.graph.mark_graph_context_read()
        logger.debug("graph_planner_guidance", extra={"chapter_num": chapter_num, "thread_count": len(guidance["suggested_threads"])})
        return guidance

    def graph_decision(self, chapter_num: int) -> dict[str, Any]:
        """Return graph-level scene constraints as a structured decision."""
        from backend.core.data_models import GraphDecision
        conflicts = self.graph.active_nodes(NodeType.CONFLICT)
        blocked: list[tuple[str, str]] = []
        forced: str | None = None
        valid = ["action", "dialogue", "introspection", "description", "transition"]
        if any("climax" in c.label.lower() or "final" in c.label.lower() for c in conflicts):
            forced = "action"
            blocked.append(("description", "transition"))
        elif len(self.graph.nodes) > 10 and len(self.graph.nodes) % 5 == 0:
            valid = [t for t in valid if t != "description"]
            blocked.append(("description", "introspection"))
        return asdict(GraphDecision(
            valid_scene_types=list(dict.fromkeys(valid)),
            blocked_pairs=blocked,
            forced_scene_type=forced,
        ))


NarrativeGraph = NarrativeKnowledgeGraph
