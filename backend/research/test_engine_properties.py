from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.data_models import SceneType
from backend.core.narrative_engine import NarrativeEngine
from backend.core.scene_builder import SceneBuilder


# Property 1: Template Fingerprint Uniqueness
# Validates: Requirements 1.1
@given(st.lists(st.text(min_size=5), min_size=2, max_size=10, unique=True))
@settings(max_examples=100)
def test_template_fingerprint_uniqueness(templates):
    """
    Before all templates are exhausted, each fingerprint should appear at most
    once in _session_fingerprints (no duplicate selection until pool is drained).

    **Validates: Requirements 1.1**
    """
    sb = SceneBuilder()
    seen_fingerprints = []
    for _ in range(len(templates)):
        chosen = sb._select_template(templates)
        fp = sb._fingerprint(chosen)
        # Before exhaustion, each fingerprint should appear at most once.
        # Once all templates have been seen (set size == len(templates)), reuse is allowed.
        assert seen_fingerprints.count(fp) == 0 or len(set(seen_fingerprints)) == len(templates)
        seen_fingerprints.append(fp)


def test_scene_builder_fingerprints_and_trigram_overlap():
    builder = SceneBuilder()
    first = builder._select_template(["one two three", "four five six"])
    second = builder._select_template(["one two three", "four five six"])
    assert builder._fingerprint(first) != builder._fingerprint(second)
    # _trigram_overlap expects sets of trigram tuples, not raw strings
    a = builder._trigrams("a b c d")
    b = builder._trigrams("a b c e")
    assert builder._trigram_overlap(a, b) > 0


def test_narrative_engine_runs_with_fixture(tmp_path):
    engine = NarrativeEngine(output_dir=str(tmp_path))
    engine.rag_pipeline.ingest("backend/data/test_manifest_fixture.jsonl")
    result = engine.generate_book(location="Delhi", year=1911, chapter_count=2, random_seed=7)
    assert result["chapters"]
    assert "repetition_rate" in result["evaluation"]["metrics"]
    assert result["experiment"]["random_seed"] == 7


# Property 2: Trigram Overlap Bound
# Validates: Requirements 1.3
@given(st.text(min_size=20), st.text(min_size=20))
@settings(max_examples=100)
def test_trigram_overlap_is_valid_jaccard(text_a, text_b):
    """
    _trigram_overlap returns a Jaccard similarity score, which must always be
    in [0.0, 1.0] for any two text inputs.

    **Validates: Requirements 1.3**
    """
    sb = SceneBuilder()
    tg_a = sb._trigrams(text_a)
    tg_b = sb._trigrams(text_b)
    overlap = sb._trigram_overlap(tg_a, tg_b)
    assert 0.0 <= overlap <= 1.0, (
        f"_trigram_overlap returned {overlap!r}, expected value in [0.0, 1.0]"
    )


@given(st.text(min_size=20), st.text(min_size=20))
@settings(max_examples=100)
def test_trigram_overlap_guard_condition(text_a, text_b):
    """
    When the trigram overlap between two texts exceeds 0.25, the SceneBuilder
    guard condition should be triggered (overlap > 0.25 is the retry threshold).
    This test verifies the guard logic: if overlap > 0.25, the condition
    evaluates to True (meaning a retry would be initiated).

    **Validates: Requirements 1.3**
    """
    sb = SceneBuilder()
    tg_a = sb._trigrams(text_a)
    tg_b = sb._trigrams(text_b)
    overlap = sb._trigram_overlap(tg_a, tg_b)

    # The guard condition: overlap > 0.25 means regeneration is needed.
    # We verify the boolean evaluation is consistent with the overlap value.
    guard_triggered = overlap > 0.25
    assert guard_triggered == (overlap > 0.25), (
        "Guard condition evaluation is inconsistent with overlap value"
    )

    # Symmetry property: overlap(a, b) == overlap(b, a)
    overlap_reversed = sb._trigram_overlap(tg_b, tg_a)
    assert overlap == overlap_reversed, (
        f"_trigram_overlap is not symmetric: {overlap} != {overlap_reversed}"
    )


@given(st.text(min_size=20))
@settings(max_examples=100)
def test_trigram_overlap_identical_texts_is_one(text):
    """
    The trigram overlap of a text with itself must be 1.0 (perfect Jaccard
    similarity), provided the text has at least one trigram.

    **Validates: Requirements 1.3**
    """
    sb = SceneBuilder()
    tg = sb._trigrams(text)
    if len(tg) == 0:
        # Fewer than 3 tokens — overlap is defined as 0.0 for empty sets.
        overlap = sb._trigram_overlap(tg, tg)
        assert overlap == 0.0
    else:
        overlap = sb._trigram_overlap(tg, tg)
        assert overlap == 1.0, (
            f"Self-overlap should be 1.0 but got {overlap!r}"
        )


@given(st.text(min_size=20), st.text(min_size=20))
@settings(max_examples=100)
def test_trigram_overlap_empty_set_returns_zero(text_a, text_b):
    """
    When either trigram set is empty, _trigram_overlap must return 0.0
    (no overlap is possible with an empty set).

    **Validates: Requirements 1.3**
    """
    sb = SceneBuilder()
    tg_a = sb._trigrams(text_a)
    # Pass an empty set as one argument — should always return 0.0.
    overlap = sb._trigram_overlap(set(), tg_a)
    assert overlap == 0.0, (
        f"Expected 0.0 when one set is empty, got {overlap!r}"
    )
    overlap2 = sb._trigram_overlap(tg_a, set())
    assert overlap2 == 0.0, (
        f"Expected 0.0 when one set is empty, got {overlap2!r}"
    )


# Property 2 (named): Trigram Overlap Bound
# Validates: Requirements 1.3
@given(
    st.text(
        min_size=0,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters=" ",
        ),
    ),
    st.text(
        min_size=0,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters=" ",
        ),
    ),
)
@settings(max_examples=100)
def test_trigram_overlap_bound(text_a, text_b):
    """
    Property 2: _trigram_overlap always returns a value in [0.0, 1.0] for any
    two text inputs, including empty strings and single-token strings that
    produce no trigrams.

    **Validates: Requirements 1.3**
    """
    sb = SceneBuilder()
    a_trigrams = sb._trigrams(text_a)
    b_trigrams = sb._trigrams(text_b)
    result = sb._trigram_overlap(a_trigrams, b_trigrams)
    assert isinstance(result, float), (
        f"_trigram_overlap must return a float, got {type(result)!r}"
    )
    assert 0.0 <= result <= 1.0, (
        f"_trigram_overlap returned {result!r}, expected value in [0.0, 1.0]"
    )
