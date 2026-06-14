from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from backend.research.scene_dataset_generator import SCENE_TYPES


class ScenePredictor(ABC):
    scene_types = tuple(SCENE_TYPES)

    @abstractmethod
    def predict_next_scene(self, features: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def rank_scene_candidates(self, features: dict) -> dict[str, float]:
        raise NotImplementedError

    @classmethod
    def load(cls, model_type: str = "random_forest", model_path: str | None = None) -> "ScenePredictor":
        if model_type in {"random_forest", "rf"}:
            from backend.research.scene_predictor_rf import RandomForestScenePredictor

            predictor = RandomForestScenePredictor()
        elif model_type in {"xgboost", "xgb"}:
            from backend.research.scene_predictor_xgb import XGBoostScenePredictor

            predictor = XGBoostScenePredictor()
        else:
            raise ValueError(f"unknown scene predictor type: {model_type}")
        if model_path:
            predictor.load_model(model_path)
        return predictor

    @classmethod
    def from_default(cls, model_dir: str | None = None) -> "ScenePredictor":
        """Load best available predictor: RF > XGB > frequency fallback."""
        if model_dir is None:
            model_dir = str(Path(__file__).resolve().parent / "models")
        rf_path = str(Path(model_dir) / "scene_predictor_rf.json")
        xgb_path = str(Path(model_dir) / "scene_predictor_xgb.json")
        # 1. Try RF
        try:
            from backend.research.scene_predictor_rf import RandomForestScenePredictor
            rf = RandomForestScenePredictor()
            rf.load_model(rf_path)
            if rf.model_available:
                return rf
        except Exception:
            pass
        # 2. Try XGB
        try:
            from backend.research.scene_predictor_xgb import XGBoostScenePredictor
            xgb = XGBoostScenePredictor()
            xgb.load_model(xgb_path)
            if xgb.model_available:
                return xgb
        except Exception:
            pass
        # 3. Frequency fallback
        freq = FrequencyScenePredictor()
        try:
            freq.load_model(xgb_path)
        except Exception:
            pass
        return freq

    @staticmethod
    def normalize_distribution(distribution: dict[str, float]) -> dict[str, float]:
        cleaned = {scene_type: max(0.0, float(distribution.get(scene_type, 0.0))) for scene_type in SCENE_TYPES}
        total = sum(cleaned.values())
        if total <= 0:
            return {scene_type: 1.0 / len(SCENE_TYPES) for scene_type in SCENE_TYPES}
        return {scene_type: value / total for scene_type, value in cleaned.items()}


class FrequencyScenePredictor(ScenePredictor):
    """Dependency-free fallback predictor using learned target frequencies and rules."""

    def __init__(self) -> None:
        self.target_counts = {scene_type: 1.0 for scene_type in SCENE_TYPES}
        self.transition_counts: dict[str, dict[str, float]] = {}
        self.model_available = False

    def train(self, examples: list) -> None:
        for example in examples:
            previous = str(example.features.get("previous_scene_type", "description"))
            target = str(example.target)
            self.target_counts[target] = self.target_counts.get(target, 0.0) + 1.0
            self.transition_counts.setdefault(previous, {scene_type: 1.0 for scene_type in SCENE_TYPES})
            self.transition_counts[previous][target] = self.transition_counts[previous].get(target, 0.0) + 1.0

    def predict_next_scene(self, features: dict) -> str:
        distribution = self.rank_scene_candidates(features)
        return max(distribution, key=distribution.__getitem__)

    def rank_scene_candidates(self, features: dict) -> dict[str, float]:
        previous = str(features.get("previous_scene_type", "description"))
        if previous in self.transition_counts:
            distribution = dict(self.transition_counts[previous])
        else:
            distribution = dict(self.target_counts)
        tension = float(features.get("tension", features.get("target_tension", 0.0)))
        if tension >= 0.65:
            distribution["action"] = distribution.get("action", 0.0) + 2.0
        elif tension >= 0.45:
            distribution["dialogue"] = distribution.get("dialogue", 0.0) + 1.5
        elif tension <= 0.25:
            distribution["description"] = distribution.get("description", 0.0) + 1.5
        return self.normalize_distribution(distribution)

    def save_model(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"target_counts": self.target_counts, "transition_counts": self.transition_counts}, sort_keys=True),
            encoding="utf-8",
        )
        return target

    def load_model(self, path: str | Path) -> None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return  # Binary or non-JSON file; stay with defaults
        self.target_counts = {str(k): float(v) for k, v in data.get("target_counts", {}).items()}
        self.transition_counts = {
            str(prev): {str(k): float(v) for k, v in counts.items()}
            for prev, counts in data.get("transition_counts", {}).items()
        }
