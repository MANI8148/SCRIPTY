"""
SCRIPTY Narrative Corpus Extraction System v1.0

A production-grade platform for extracting, classifying, and storing
narrative fragments from literary works for future SCRIPTY generations.

Components:
  - parsers/       : TXT, EPUB, PDF document parsing
  - passes/        : 10-pass extraction pipeline
  - extractors/    : Specialized narrative element extractors
  - quality/       : Quality scoring and deduplication
  - analysis/      : Foreshadowing, scene patterns, character memory
  - rag/           : Embedding, FAISS index, corpus building
  - storage/       : JSONL and FAISS persistence
  - schema/        : Fragment and taxonomy definitions
  - reporting/     : Comprehensive statistics and reports
  - testing/       : Test suite and stress testing
"""

__version__ = "1.0.0"

def create_pipeline(config=None):
    from data_pipeline.orchestrator import PipelineOrchestrator
    return PipelineOrchestrator(config)

__all__ = ["create_pipeline"]
