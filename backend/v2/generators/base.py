"""
SCRIPTY v2 — TextGenerator Abstract Base Class
Defines the interface for all text generators.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.v2.types import SceneBlueprint, GeneratedScene


class TextGenerator(ABC):
    """Abstract base class for all text generators."""

    @abstractmethod
    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        """Produce a complete scene from the blueprint."""
        ...

    def set_agents(self, agents: list[Any]) -> None:
        """Optional: set agent references for voice adaptation."""
        pass