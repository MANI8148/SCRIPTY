from __future__ import annotations

from abc import ABC, abstractmethod

from backend.v2.types import GeneratedScene, SceneBlueprint


class TextGenerator(ABC):
    @abstractmethod
    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        ...

    def set_agents(self, agents: list) -> None:
        """Register agents for voice-aware generation. Optional override."""
        pass
