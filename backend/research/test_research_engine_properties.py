from hypothesis import given, settings
from hypothesis import strategies as st

from backend.research.embedding_encoder import EmbeddingEncoder
from backend.research.hybrid_scene_selector import HybridSceneSelector, SceneConstraint
from backend.research.scene_dataset_generator import SceneDatasetGenerator, SceneFeatureExtractor
from backend.research.vector_store import VectorStore


@given(st.text(min_size=0, max_size=200))
@settings(max_examples=100)
def test_embedding_encoder_always_returns_normalized_dimension(text):
    vector = EmbeddingEncoder().encode(text)
    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


@given(
    st.lists(st.sampled_from(["action", "dialogue", "description", "introspection", "transition"]), min_size=0, max_size=8),
    st.sampled_from(["action", "dialogue", "description"]),
)
@settings(max_examples=100)
def test_hybrid_selector_respects_max_consecutive_constraint(previous, blocked_type):
    selector = HybridSceneSelector()
    selected = selector.select_next_scene(
        {blocked_type: 1.0},
        [SceneConstraint("max_consecutive", {"scene_type": blocked_type, "limit": 2})],
        previous_scene_types=[blocked_type, blocked_type] + previous[-1:],
    )
    if previous[-1:] == [blocked_type] or not previous:
        assert selected != blocked_type


@given(st.floats(min_value=0.0, max_value=1.0), st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_scene_features_keep_position_and_tension_in_bounds(tension, scene_count):
    extractor = SceneFeatureExtractor()
    features = extractor.extract({"tension": tension}, scene_index=scene_count - 1, scene_count=scene_count)
    assert 0.0 <= features["scene_position"] <= 1.0
    assert 0.0 <= features["tension"] <= 1.0


@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_synthetic_dataset_split_preserves_all_examples(book_count):
    generator = SceneDatasetGenerator()
    examples = generator.generate_synthetic_dataset(book_count=book_count)
    splits = generator.split_dataset(examples)
    assert sum(len(items) for items in splits.values()) == len(examples)


@given(st.lists(st.floats(min_value=-1.0, max_value=1.0), min_size=0, max_size=12))
@settings(max_examples=100)
def test_vector_store_search_never_returns_more_than_top_k(seed_values):
    query = (seed_values + [0.0] * 384)[:384]
    store = VectorStore()
    store.add([0.0] * 384, {"scene_id": "zero"})
    results = store.search(query, top_k=1)
    assert len(results) <= 1
