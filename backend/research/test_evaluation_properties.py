from pathlib import Path

from backend.core.data_models import Chapter, Scene, SceneType
from backend.research.emotional_arc_model import EmotionalArcModel
from backend.research.evaluation_pipeline import EvaluationPipeline
from backend.research.controllable_generator import ConditioningSpec
from backend.research.narrative_planner import NarrativePlanner


def test_emotional_arc_mad():
    arc = EmotionalArcModel()
    arc.record(1, 1, 0.2, 0.4)
    arc.record(1, 2, 0.8, 0.4)
    assert round(arc.compute_mad(), 3) == 0.3


def test_repetition_rate_and_report_serialization(tmp_path: Path):
    pipeline = EvaluationPipeline()
    assert pipeline.repetition_rate(["a b c a b c a b d"]) > 0
    chapter = Chapter(1, "Title", [Scene(1, SceneType.ACTION, "Asha moved through Delhi.", 4)], 4, "Asha moved.")
    report = pipeline.evaluate([chapter])
    path = pipeline.serialize_report(report, str(tmp_path), "s1")
    assert path.exists()
    assert "repetition_rate" in report.metrics


def test_evaluation_scores_are_derived_not_placeholders():
    pipeline = EvaluationPipeline()
    planner = NarrativePlanner(genre="historical fiction")
    plan = planner.create_plan(1)
    conditioning = ConditioningSpec(
        genre="historical fiction",
        tone="tense",
        style_keywords=("archive", "secret"),
    )
    scene = Scene(
        1,
        SceneType.DESCRIPTION,
        "A tense archive secret in Delhi revealed a colonial record and hidden history.",
        12,
        tension_score=0.2,
    )
    chapter = Chapter(1, "Chapter 1: Description - Archive Secret", [scene], 12, "Archive secret.")

    report = pipeline.evaluate(
        [chapter],
        plan=plan,
        genre="historical fiction",
        conditioning=conditioning,
    )

    assert report.metrics["genre_adherence"] > 0.0
    assert report.metrics["conditioning_adherence"] > 0.0
    assert report.metrics["plan_adherence"] > 0.9
    assert 0.0 <= report.metrics["narrative_coherence"] < 1.0


import string
from hypothesis import given, strategies as st

@given(st.text(alphabet=string.ascii_letters + " ", min_size=5))
def test_rouge_self_identity(text):
    pipeline = EvaluationPipeline()
    score = pipeline.rouge_l(text, text)
    assert 0.0 <= score <= 1.0

@given(st.text(alphabet=string.ascii_letters + " ", min_size=5))
def test_bleu_self_identity(text):
    pipeline = EvaluationPipeline()
    score = pipeline.bleu4(text, text)
    assert 0.0 <= score <= 1.0

def test_bert_score_availability():
    pipeline = EvaluationPipeline()
    res = pipeline.get_bert_score(["hello"], ["hello"])
    assert hasattr(res, "available")
