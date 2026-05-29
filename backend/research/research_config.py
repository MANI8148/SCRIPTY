from __future__ import annotations

import os
from dataclasses import asdict, dataclass


def _flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ResearchEngineConfig:
    """Feature flags and defaults for the research-grade narrative subsystems."""

    literary_intelligence_enabled: bool = True
    embedding_memory_enabled: bool = True
    ml_scene_prediction_enabled: bool = True
    backward_compatibility_mode: bool = False
    vector_backend: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    scene_predictor: str = "random_forest"
    memory_top_k: int = 5
    output_dashboard: bool = True

    @classmethod
    def from_env(cls) -> "ResearchEngineConfig":
        backward = _flag("SCRIPTY_BACKWARD_COMPATIBILITY_MODE", False)
        return cls(
            literary_intelligence_enabled=_flag("SCRIPTY_PHASE_A_ENABLED", not backward),
            embedding_memory_enabled=_flag("SCRIPTY_PHASE_B_ENABLED", not backward),
            ml_scene_prediction_enabled=_flag("SCRIPTY_PHASE_C_ENABLED", not backward),
            backward_compatibility_mode=backward,
            vector_backend=os.getenv("SCRIPTY_VECTOR_BACKEND", "local"),
            embedding_model=os.getenv("SCRIPTY_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            scene_predictor=os.getenv("SCRIPTY_SCENE_PREDICTOR", "random_forest"),
            memory_top_k=int(os.getenv("SCRIPTY_MEMORY_TOP_K", "5")),
            output_dashboard=_flag("SCRIPTY_OUTPUT_DASHBOARD", True),
        )

    def disabled_tiers(self) -> set[str]:
        if self.backward_compatibility_mode:
            return {"semantic"}
        return set()

    def to_dict(self) -> dict:
        return asdict(self)
