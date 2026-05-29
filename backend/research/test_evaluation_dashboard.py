from backend.core.data_models import Chapter, Scene, SceneType
import pytest
from backend.research.evaluation_dashboard import EvaluationDashboard
from backend.research.evaluation_pipeline import EvaluationPipeline, EvaluationReport


def test_prediction_and_diversity_metrics():
    pipeline = EvaluationPipeline()
    actual = ["description", "dialogue", "action"]
    predicted = ["description", "action", "action"]

    metrics = pipeline.prediction_metrics(actual, predicted)
    matrix = pipeline.confusion_matrix(actual, predicted)
    diversity = pipeline.scene_diversity_metrics(actual)

    assert metrics["scene_prediction_accuracy"] == pytest.approx(2 / 3)
    assert matrix["dialogue"]["action"] == 1
    assert diversity["scene_type_entropy"] > 0


def test_evaluate_includes_phase_c_metrics():
    chapter = Chapter(
        chapter_num=1,
        title="Chapter 1",
        scenes=[
            Scene(1, SceneType.DESCRIPTION, "Asha found a clue.", 4, 0.2),
            Scene(2, SceneType.DIALOGUE, "Asha said the truth mattered.", 6, 0.5),
        ],
        word_count=10,
        summary="Asha investigates.",
    )

    report = EvaluationPipeline().evaluate([chapter])

    assert "scene_prediction_accuracy" in report.metrics
    assert "scene_type_entropy" in report.metrics
    assert "hybrid_coherence_impact" in report.metrics


def test_dashboard_generation(tmp_path):
    report = EvaluationReport(metrics={"scene_prediction_accuracy": 1.0, "scene_type_entropy": 0.5})
    path = EvaluationDashboard().build([report], tmp_path / "dashboard.html")

    assert path.exists()
    assert "SCRIPTY Evaluation Dashboard" in path.read_text(encoding="utf-8")


def test_pipeline_serializes_dashboard(tmp_path):
    report = EvaluationReport(metrics={"scene_prediction_accuracy": 1.0})
    path = EvaluationPipeline().serialize_dashboard([report], str(tmp_path), "session")

    assert path.name == "evaluation_dashboard.html"
    assert path.exists()
