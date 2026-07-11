"""World tech builder — tech levels and available tools."""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints, GenerationRequest


class TechBuilder:
    """Builds technology profile (level, tools, communication) for a world."""

    _TOOLS_BY_LEVEL = {
        "pre-industrial": ["plow", "hand loom", "oil lamp"],
        "industrial": ["steam engine", "telegraph", "railway"],
        "digital": ["smartphone", "computer", "internet"],
    }

    def build(self, base: WorldConstraints, request: GenerationRequest) -> dict[str, Any]:
        level = base.tech_level or "pre-industrial"
        tools = self._TOOLS_BY_LEVEL.get(level, ["basic tools"])
        return {
            "tech_level": level,
            "available_tools": tools,
            "communication": "printed word" if level != "digital" else "instant messaging",
            "transport": list(base.transport or []),
        }
