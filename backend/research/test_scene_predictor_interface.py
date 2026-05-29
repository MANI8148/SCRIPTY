import pytest

from backend.research.scene_dataset_generator import SceneDatasetGenerator
from backend.research.scene_predictor import ScenePredictor
from backend.research.scene_predictor_rf import RandomForestScenePredictor
from backend.research.scene_predictor_xgb import XGBoostScenePredictor


def test_scene_predictor_factory_loads_rf_and_xgb():
    assert isinstance(ScenePredictor.load("random_forest"), RandomForestScenePredictor)
    assert isinstance(ScenePredictor.load("xgboost"), XGBoostScenePredictor)


def test_scene_predictor_factory_rejects_unknown_model():
    with pytest.raises(ValueError):
        ScenePredictor.load("unknown")


def test_scene_predictor_model_path_loading(tmp_path):
    examples = SceneDatasetGenerator().generate_synthetic_dataset(book_count=3)
    predictor = RandomForestScenePredictor()
    predictor.train(examples)
    path = predictor.save_model(tmp_path / "model.json")

    restored = ScenePredictor.load("rf", str(path))
    assert restored.predict_next_scene(examples[0].features)
