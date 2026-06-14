from __future__ import annotations

import pickle
from pathlib import Path

from backend.research.scene_dataset_generator import SCENE_TYPES, SceneFeatureExtractor
from backend.research.scene_predictor import FrequencyScenePredictor


class XGBoostScenePredictor(FrequencyScenePredictor):
    """XGBoost predictor with a dependency-free frequency fallback."""

    def __init__(self) -> None:
        super().__init__()
        self.feature_extractor = SceneFeatureExtractor()
        self._model = None
        self._label_to_index = {label: index for index, label in enumerate(SCENE_TYPES)}
        self._index_to_label = {index: label for label, index in self._label_to_index.items()}

    def train(self, examples: list) -> None:
        super().train(examples)
        try:
            from xgboost import XGBClassifier  # type: ignore

            x_train = [self.feature_extractor.vectorize(example.features) for example in examples]
            y_train = [self._label_to_index[example.target] for example in examples]
            if x_train and len(set(y_train)) > 1:
                model = XGBClassifier(
                    n_estimators=24,
                    max_depth=3,
                    learning_rate=0.2,
                    eval_metric="mlogloss",
                    random_state=7,
                )
                model.fit(x_train, y_train)
                self._model = model
                self.model_available = True
        except Exception:
            self._model = None
            self.model_available = False

    def rank_scene_candidates(self, features: dict) -> dict[str, float]:
        if self._model is None:
            return super().rank_scene_candidates(features)
        vector = [self.feature_extractor.vectorize(features)]
        probabilities = self._model.predict_proba(vector)[0]
        distribution = {scene_type: 0.0 for scene_type in SCENE_TYPES}
        for index, probability in enumerate(probabilities):
            label = self._index_to_label.get(index)
            if label:
                distribution[label] = float(probability)
        return self.normalize_distribution(distribution)

    def save_model(self, path: str | Path) -> Path:
        if self._model is None:
            return super().save_model(path)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump({
                "model": self._model,
                "label_to_index": self._label_to_index,
                "index_to_label": self._index_to_label,
            }, handle)
        return target

    def load_model(self, path: str | Path) -> None:
        target = Path(path)
        try:
            with target.open("rb") as handle:
                data = pickle.load(handle)
            self._model = data["model"]
            self._label_to_index = data["label_to_index"]
            self._index_to_label = data["index_to_label"]
            self.model_available = True
        except Exception:
            self._model = None
            self.model_available = False
