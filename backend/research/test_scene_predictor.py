from backend.research.model_comparison import SceneModelComparator
from backend.research.scene_dataset_generator import SceneDatasetGenerator
from backend.research.scene_predictor_rf import RandomForestScenePredictor
from backend.research.scene_predictor_xgb import XGBoostScenePredictor


def test_random_forest_predictor_distribution_and_serialization(tmp_path):
    examples = SceneDatasetGenerator().generate_synthetic_dataset(book_count=8)
    predictor = RandomForestScenePredictor()
    predictor.train(examples)

    distribution = predictor.rank_scene_candidates(examples[0].features)
    assert round(sum(distribution.values()), 6) == 1.0
    assert predictor.predict_next_scene(examples[0].features) in distribution

    path = predictor.save_model(tmp_path / "scene_rf.model")
    restored = RandomForestScenePredictor()
    restored.load_model(path)
    assert restored.predict_next_scene(examples[0].features) in distribution


def test_xgboost_predictor_uses_same_interface_with_fallback():
    examples = SceneDatasetGenerator().generate_synthetic_dataset(book_count=4)
    predictor = XGBoostScenePredictor()
    predictor.train(examples)
    distribution = predictor.rank_scene_candidates(examples[1].features)

    assert round(sum(distribution.values()), 6) == 1.0
    assert predictor.predict_next_scene(examples[1].features) in distribution


def test_model_comparison_metrics():
    examples = SceneDatasetGenerator().generate_synthetic_dataset(book_count=4)
    predictor = RandomForestScenePredictor()
    predictor.train(examples)

    metrics = SceneModelComparator().evaluate(predictor, examples[:12])

    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["top3_accuracy"] <= 1.0
    assert "confusion_matrix" in metrics
    assert "per_genre_accuracy" in metrics
