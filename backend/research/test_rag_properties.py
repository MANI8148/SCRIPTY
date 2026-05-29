import json

from backend.research.dataset_ingestion import load_sources
from backend.research.dataset_manifest import ManifestEntry, split_passages, validate_manifest_entry
from backend.research.rag_pipeline import RAGPipeline


def test_manifest_validation_rejects_missing_field():
    assert validate_manifest_entry({"source_id": "bad"}) is None


def test_passage_split_ids_are_stable():
    passages = split_passages("src", " ".join(f"w{i}" for i in range(1100)), window_tokens=500, stride_tokens=50)
    assert passages[0].passage_id == "src_p0000"
    assert passages[1].passage_id == "src_p0001"
    assert len(passages[0].text.split()) == 500


def test_rag_fixture_retrieves_with_provenance():
    pipeline = RAGPipeline(manifest_path="backend/data/test_manifest_fixture.jsonl", top_k=2)
    results = pipeline.retrieve("cities revolution historical pressure")
    assert results
    assert results[0].source_id
    assert results[0].passage_id
    assert results[0].score > 0
    assert "Grounding context:" in pipeline.get_grounding_context("cities revolution")


def test_catalog_sources_include_required_research_metadata():
    sources = load_sources(None, "backend/data/source_catalog.json")
    assert len(sources) == 60
    section_counts = {}
    for source in sources:
        section_counts[source["section"]] = section_counts.get(source["section"], 0) + 1
        assert source["license"] == "Public Domain"
        assert source["region"]
        assert source["period"]
        assert source["genre"]
        assert source["source_type"]
    assert set(section_counts.values()) == {15}


def test_manifest_entry_metadata_round_trip():
    raw = json.loads(
        '{"source_id":"s","title":"t","author":"a","license":"Public Domain","url":"https://example.test","region":"south_asia","period":"colonial","genre":"history","source_type":"memoir","passages":[{"passage_id":"s_p0000","text":"Delhi archive record"}]}'
    )
    entry = validate_manifest_entry(raw)
    assert isinstance(entry, ManifestEntry)
    assert entry.region == "south_asia"
    assert entry.period == "colonial"
    assert entry.genre == "history"
    assert entry.source_type == "memoir"


def test_rag_filters_preserve_provenance():
    pipeline = RAGPipeline(manifest_path="backend/data/test_manifest_fixture.jsonl", top_k=2)
    results = pipeline.retrieve("river trade danger", filters={"region": "north_america"})
    assert results
    assert results[0].source_id == "gutenberg_76"
    assert results[0].metadata["region"] == "north_america"
