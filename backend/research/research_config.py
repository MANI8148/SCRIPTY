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

    # Phase 11 — Architecture Improvement & Interference Reduction flags
    predictor_aware_retrieval_enabled: bool = False
    structured_memory_enabled: bool = False
    memory_compression_enabled: bool = False
    context_gateway_enabled: bool = False
    token_budget_controller_enabled: bool = False
    character_state_engine_enabled: bool = False
    narrative_thread_tracker_enabled: bool = False
    advanced_evaluation_enabled: bool = False

    # Token budget targets (percentages)
    budget_chapter_context: float = 35.0
    budget_story_bible: float = 25.0
    budget_character_agents: float = 20.0
    budget_memory: float = 15.0
    budget_predictor: float = 5.0

    # Phase 12 — Influence Verification & Control Analysis flags
    influence_tracing_enabled: bool = False
    counterfactual_testing_enabled: bool = False
    thread_verification_enabled: bool = False
    retrieval_usefulness_enabled: bool = False
    context_ablation_enabled: bool = False
    generation_attribution_enabled: bool = False
    statistical_analysis_enabled: bool = False

    # Phase 13 — Control Optimization & Architecture Consolidation flags
    character_state_enforcement_enabled: bool = False
    thread_objective_conversion_enabled: bool = False
    prompt_budget_optimization_enabled: bool = False
    event_centric_retrieval_enabled: bool = False
    memory_importance_decay_enabled: bool = False
    control_efficiency_analysis_enabled: bool = False
    architecture_reduction_enabled: bool = False
    optimized_architecture_mode: bool = False
    reduced_architecture_mode: bool = False

    # Phase 13 — Budget overrides (populated by optimizer)
    budget_override_predictor: float | None = None
    budget_override_literary: float | None = None
    budget_override_memory: float | None = None
    budget_override_character: float | None = None
    budget_override_threads: float | None = None
    budget_override_bible: float | None = None

    # Phase 13 — Importance decay parameters
    importance_decay_rate: float = 0.05
    importance_critical_multiplier: float = 2.0

    # Phase 14 — External Validation & Scientific Evaluation flags
    baseline_comparison_enabled: bool = False
    human_evaluation_enabled: bool = False
    automated_judge_enabled: bool = False
    significance_analysis_enabled: bool = False
    long_horizon_validation_enabled: bool = False
    failure_analysis_enabled: bool = False
    cost_performance_enabled: bool = False
    generalization_benchmark_enabled: bool = False
    research_figures_enabled: bool = False

    # Phase 15 — Productionization & Generalization flags
    multi_llm_validation_enabled: bool = False
    human_evaluation_mode: bool = False
    studio_mode: bool = False
    api_mode: bool = False
    regression_testing_enabled: bool = False
    failure_reduction_enabled: bool = False

    # Retrieval tuning
    retrieval_confidence_threshold: float = 0.3
    retrieval_max_memories: int = 5
    retrieval_deduplication_enabled: bool = True

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
