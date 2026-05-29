from backend.research.rag_pipeline import RAGPipeline
from backend.research.research_responder import ResearchResponder


def test_research_responder_returns_ai_style_answer_with_citations():
    pipeline = RAGPipeline(manifest_path="backend/data/test_manifest_fixture.jsonl", top_k=2)
    responder = ResearchResponder(pipeline)
    response = responder.respond("cities revolution pressure", top_k=2)
    assert response.mode == "local_rag"
    assert response.retrieval_count > 0
    assert response.citations
    assert "Based on the local SCRIPTY corpus" in response.answer
