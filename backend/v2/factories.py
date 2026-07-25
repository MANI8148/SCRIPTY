from __future__ import annotations

from backend.v2.character_agent import CharacterAgent
from backend.v2.types import CharacterRecord, RelationKind

# Trait → OCEAN (Big-Five) nudges. Each trait pushes the relevant dimension
# up or down from the 0.5 neutral baseline. Used to give characters a
# distinct voice fingerprint even without an explicit `ocean` field.
_TRAIT_OCEAN: dict[str, tuple[str, float]] = {
    "pious": ("conscientiousness", +0.3),
    "spiritual": ("openness", +0.2),
    "wise": ("openness", +0.2),
    "learned": ("openness", +0.3),
    "curious": ("openness", +0.3),
    "cautious": ("neuroticism", +0.2),
    "anxious": ("neuroticism", +0.4),
    "reckless": ("conscientiousness", -0.3),
    "brash": ("agreeableness", -0.3),
    "rude": ("agreeableness", -0.4),
    "kind": ("agreeableness", +0.3),
    "gentle": ("agreeableness", +0.3),
    "compassionate": ("agreeableness", +0.4),
    "deceptive": ("agreeableness", -0.3),
    "cunning": ("conscientiousness", +0.2),
    "sly": ("conscientiousness", +0.1),
    "proud": ("extraversion", +0.2),
    "ambitious": ("extraversion", +0.3),
    "arrogant": ("agreeableness", -0.3),
    "loyal": ("agreeableness", +0.2),
    "brave": ("extraversion", +0.2),
    "mysterious": ("openness", +0.2),
    "melancholic": ("neuroticism", +0.3),
}


def _derive_ocean(traits: list[str]) -> dict[str, float]:
    ocean = {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    }
    for t in traits:
        nudges = _TRAIT_OCEAN.get(t.lower())
        if nudges:
            dim, delta = nudges
            ocean[dim] = min(1.0, max(0.0, ocean[dim] + delta))
    return ocean


def build_character_agents(
    character_data: list[dict],
) -> list[CharacterAgent]:
    agents: list[CharacterAgent] = []
    for data in character_data:
        traits = data.get("traits", ["curious"])
        record = CharacterRecord(
            name=data.get("name", "Unknown"),
            role=data.get("role", "bystander"),
            traits=traits,
            goals=data.get("goals", [data.get("goal", "survive")]),
            relationships=_build_relationships(data.get("relationships", {})),
            ocean=data.get("ocean", _derive_ocean(traits)),
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
