from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.research.rag_pipeline import RAGPipeline, RetrievalResult


@dataclass(frozen=True)
class ResearchResponse:
    answer: str
    citations: list[dict]
    retrieval_count: int
    mode: str = "local_rag"


class ResearchResponder:
    """Local retrieval-based response generator with citations."""

    def __init__(self, rag_pipeline: RAGPipeline | None = None) -> None:
        self.rag_pipeline = rag_pipeline or RAGPipeline()

    def respond(self, prompt: str, top_k: int = 5, filters: dict[str, str] | None = None) -> ResearchResponse:
        results = self.rag_pipeline.retrieve(prompt, top_k=top_k, filters=filters)
        if not results:
            return ResearchResponse(
                answer="I could not find enough local source material to answer that from the dataset. Add or ingest more sources, then try again.",
                citations=[],
                retrieval_count=0,
            )
        answer = self._compose_answer(prompt, results)
        citations = [
            {
                "source_id": result.source_id,
                "passage_id": result.passage_id,
                "score": result.score,
                "metadata": result.metadata,
            }
            for result in results
        ]
        return ResearchResponse(answer=answer, citations=citations, retrieval_count=len(results))

    def _compose_answer(self, prompt: str, results: list[RetrievalResult]) -> str:
        themes = []
        for result in results:
            text = " ".join(result.text.split()[:55])
            themes.append(f"{result.source_id}:{result.passage_id} suggests {text}")
        body = " ".join(themes)
        return (
            f"Based on the local SCRIPTY corpus, the strongest answer to '{prompt}' is grounded in {len(results)} retrieved passages. "
            f"{body} Use these citations as evidence, not as a final generated story."
        )


def response_to_dict(response: ResearchResponse) -> dict:
    return asdict(response)
