from __future__ import annotations

from backend.v2.character_agent import CharacterAgent
from backend.v2.types import CharacterRecord, RelationKind


def build_character_agents(
    character_data: list[dict],
) -> list[CharacterAgent]:
    agents: list[CharacterAgent] = []
    for data in character_data:
        record = CharacterRecord(
            name=data.get("name", "Unknown"),
            role=data.get("role", "bystander"),
            traits=data.get("traits", ["curious"]),
            goals=data.get("goals", [data.get("goal", "survive")]),
            relationships=_build_relationships(data.get("relationships", {})),
        )
        agents.append(CharacterAgent(character=record))

    for agent in agents:
        for other in agents:
            if other.name != agent.name:
                existing = agent.character.relationships.get(other.name)
                if existing is None:
                    agent.character.relationships[other.name] = RelationKind.NEUTRAL

    return agents


def _build_relationships(rel_data: dict[str, str]) -> dict[str, RelationKind]:
    mapping: dict[str, RelationKind] = {}
    kind_map = {
        "ally": RelationKind.ALLY,
        "rival": RelationKind.RIVAL,
        "enemy": RelationKind.ENEMY,
        "neutral": RelationKind.NEUTRAL,
        "family": RelationKind.FAMILY,
        "mentor": RelationKind.MENTOR,
        "subordinate": RelationKind.SUBORDINATE,
    }
    for name, kind_str in rel_data.items():
        kind = kind_map.get(kind_str.lower(), RelationKind.NEUTRAL)
        mapping[name] = kind
    return mapping
