from backend.research.neural_reranker import NeuralReranker, train_from_manifest
from backend.research.rag_pipeline import RAGPipeline


def test_neural_reranker_training_and_loading(tmp_path):
    model_path = tmp_path / "neural_reranker.json"
    report = train_from_manifest(
        manifest_path="backend/data/test_manifest_fixture.jsonl",
        model_path=str(model_path),
        epochs=3,
        max_examples=12,
        random_seed=7,
    )
    assert model_path.exists()
    assert report.training_examples > 0
    assert 0.0 <= report.validation_accuracy <= 1.0
    model = NeuralReranker.load(model_path)
    pipeline = RAGPipeline(manifest_path="backend/data/test_manifest_fixture.jsonl", neural_model_path=str(model_path))
    results = pipeline.retrieve("cities revolution pressure", top_k=2)
    assert results
    assert model.score("cities revolution pressure", results[0]) >= 0.0
