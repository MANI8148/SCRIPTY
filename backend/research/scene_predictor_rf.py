from __future__ import annotations

import pickle
from pathlib import Path

from backend.research.scene_dataset_generator import SCENE_TYPES, SceneFeatureExtractor
from backend.research.scene_predictor import FrequencyScenePredictor


class RandomForestScenePredictor(FrequencyScenePredictor):
    def __init__(self) -> None:
        super().__init__()
        self.feature_extractor = SceneFeatureExtractor()
        self._model = None
        self._classes = list(SCENE_TYPES)

    def train(self, examples: list) -> None:
        super().train(examples)
        try:
            from sklearn.ensemble import RandomForestClassifier  # type: ignore

            x_train = [self.feature_extractor.vectorize(example.features) for example in examples]
            y_train = [example.target for example in examples]
            if x_train and len(set(y_train)) > 1:
                model = RandomForestClassifier(n_estimators=32, random_state=7)
                model.fit(x_train, y_train)
                self._model = model
                self._classes = [str(item) for item in model.classes_]
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
        for scene_type, probability in zip(self._classes, probabilities):
            distribution[scene_type] = float(probability)
        return self.normalize_distribution(distribution)

    def save_model(self, path: str | Path) -> Path:
        if self._model is None:
            return super().save_model(path)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump({"model": self._model, "classes": self._classes}, handle)
        return target

    def load_model(self, path: str | Path) -> None:
        target = Path(path)
        try:
            with target.open("rb") as handle:
                data = pickle.load(handle)
            self._model = data["model"]
            self._classes = [str(item) for item in data["classes"]]
            self.model_available = True
        except Exception:
            self._model = None
            self.model_available = False
