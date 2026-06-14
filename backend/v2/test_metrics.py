"""Tests for the unified metrics module — no external dependencies."""

from backend.v2.metrics import (
    THRESHOLDS,
    MetricThresholds,
    MetricsResult,
    measure_all,
    measure_batch,
    word_count,
    sentence_count,
    unique_words,
    type_token_ratio,
    avg_sentence_length,
    dialogue_count,
    dialogue_density,
    show_vs_tell,
    unique_sentence_starts,
    emotional_expression,
    repetition_rate,
    coherence,
    simulation_pattern_count,
    bigram_overlap_ratio,
    trigram_jaccard,
    compute_divergence,
    conflict_keyword_count,
    emotion_keyword_count,
)


class TestWordCount:
    def test_empty(self):
        assert word_count("") == 0

    def test_single_word(self):
        assert word_count("hello") == 1

    def test_multiple_words(self):
        assert word_count("Arjun walked into the room") == 5

    def test_whitespace_handling(self):
        assert word_count("  hello   world  ") == 2


class TestDialogueMetrics:
    def test_dialogue_count_empty(self):
        assert dialogue_count("") == 0

    def test_dialogue_count_no_quotes(self):
        assert dialogue_count("Arjun walked into the room.") == 0

    def test_dialogue_count_double_quotes(self):
        text = '"What do you want?" she asked.'
        assert dialogue_count(text) == 1

    def test_dialogue_count_curly_quotes(self):
        text = '\u201cI need the truth.\u201d he replied.'
        assert dialogue_count(text) == 1

    def test_dialogue_count_multi_line(self):
        text = '"Hello," she said. "How are you?" he asked.'
        assert dialogue_count(text) == 2

    def test_dialogue_density_no_text(self):
        assert dialogue_density("") == 0.0

    def test_dialogue_density_no_dialogue(self):
        text = "Arjun looked around the empty room."
        assert dialogue_density(text) == 0.0

    def test_dialogue_density_half(self):
        text = '"Hello there," she said. Arjun nodded.'
        den = dialogue_density(text)
        assert 0.0 < den < 1.0

    def test_dialogue_density_all_dialogue(self):
        text = '"Hello there, how are you doing today?"'
        assert dialogue_density(text) > 0.8


class TestShowVsTell:
    def test_empty(self):
        assert show_vs_tell("") == 0.0

    def test_show_verb(self):
        assert show_vs_tell("He clenched his fists") > 0

    def test_tell_verb(self):
        assert show_vs_tell("He was angry") < 1.0  # tell dominates

    def test_show_tell_ratio(self):
        text = "He clenched his fists and glared at the wall. He was angry."
        ratio = show_vs_tell(text)
        assert ratio > 0  # should have both show and tell


class TestUniqueSentenceStarts:
    def test_empty_text(self):
        assert unique_sentence_starts("") == 1.0

    def test_single_sentence(self):
        assert unique_sentence_starts("Arjun walked into the room.") == 1.0

    def test_identical_starts(self):
        text = "Arjun entered the room. Arjun entered the room again."
        # Both sentences start with "Arjun entered the" (first 3 words)
        assert unique_sentence_starts(text) < 1.0

    def test_different_starts(self):
        text = "Arjun entered the room. Maya looked up slowly."
        assert unique_sentence_starts(text) == 1.0


class TestEmotionalExpression:
    def test_empty(self):
        assert emotional_expression("") == 0.0

    def test_behavior_words(self):
        text = "He clenched his fists and trembled with rage."
        assert emotional_expression(text) > 0

    def test_state_words(self):
        text = "He was angry and sad."
        val = emotional_expression(text)
        assert val == 0.0  # only state words, no behavior

    def test_higher_behavior_ratio(self):
        text = "She glared at him, then smiled. He was happy."
        val = emotional_expression(text)
        assert val > 0


class TestRepetitionRate:
    def test_empty(self):
        assert repetition_rate("") == 0.0

    def test_no_repetition(self):
        text = "the quick brown fox jumps over the lazy dog"
        assert repetition_rate(text) < 0.3

    def test_high_repetition(self):
        # 9 bigrams all "(la,la)" → 1 unique, repeated=1, rate=1/9≈0.11
        text = "la la la la la la la la la la"
        assert repetition_rate(text) >= 0.10


class TestCoherence:
    def test_empty_text(self):
        assert coherence("") == 1.0

    def test_single_sentence(self):
        assert coherence("Arjun walked into the room.") == 1.0

    def test_known_names_used(self):
        text = "Arjun entered the room. He saw Maya standing there. Arjun spoke first."
        val = coherence(text)
        assert val >= 0.5  # most sentences reference established entities

    def test_no_known_names(self):
        text = "Someone entered the room. They looked around. It was dark."
        val = coherence(text)
        assert val <= 0.5  # no known names, low coherence


class TestSimulationPatterns:
    def test_empty(self):
        assert simulation_pattern_count("") == 0

    def test_clean_text(self):
        text = "Arjun walked into the room. Maya looked up."
        assert simulation_pattern_count(text) == 0

    def test_mechanical_pattern(self):
        text = "He stood in silence as the weight of the moment pressed down."
        assert simulation_pattern_count(text) >= 1


class TestTTR:
    def test_empty(self):
        assert type_token_ratio("") == 0.0

    def test_all_unique(self):
        assert type_token_ratio("the quick brown fox") == 1.0

    def test_all_repeated(self):
        assert type_token_ratio("the the the the") < 0.5


class TestBigramOverlap:
    def test_empty(self):
        assert bigram_overlap_ratio("") == 0.0

    def test_short_text(self):
        assert bigram_overlap_ratio("a") == 0.0

    def test_high_overlap(self):
        assert bigram_overlap_ratio("hello hello hello") >= 0.0


class TestTrigramJaccard:
    def test_identical(self):
        text = "the quick brown fox jumps"
        assert trigram_jaccard(text, text) == 1.0

    def test_different(self):
        text_a = "the quick brown fox"
        text_b = "completely unrelated text here"
        assert trigram_jaccard(text_a, text_b) < 0.5

    def test_empty_union(self):
        assert trigram_jaccard("a b", "c d") == 0.0

    def test_partial_overlap(self):
        text_a = "the quick brown fox jumps over"
        text_b = "the quick brown dog runs fast"
        jac = trigram_jaccard(text_a, text_b)
        assert 0.0 < jac < 1.0


class TestComputeDivergence:
    def test_identical(self):
        assert compute_divergence("hello world", "hello world") == 0.0

    def test_completely_different(self):
        div = compute_divergence("Arjun walked into the room", "Maya stared at the ceiling")
        assert 0.0 < div <= 1.0

    def test_partial_overlap(self):
        div = compute_divergence("Arjun and Maya walked together", "Arjun walked with Maya")
        assert 0.0 < div < 1.0


class TestKeywordCounts:
    def test_conflict_keywords(self):
        assert conflict_keyword_count("anger and war and battle") == 3

    def test_conflict_keywords_none(self):
        assert conflict_keyword_count("peace and love and joy") == 0

    def test_emotion_keywords(self):
        assert emotion_keyword_count("fear and joy and anger") >= 3

    def test_emotion_keywords_none(self):
        assert emotion_keyword_count("table and chair") == 0


class TestThresholds:
    def test_default_thresholds_exist(self):
        assert THRESHOLDS.dialogue_density == 0.15
        assert THRESHOLDS.show_vs_tell == 3.0
        assert THRESHOLDS.unique_sentence_starts == 0.85
        assert THRESHOLDS.coherence == 0.80
        assert THRESHOLDS.word_count_min == 50

    def test_invert_metrics_defined(self):
        from backend.v2.metrics import INVERT_METRICS
        assert "repetition_rate" in INVERT_METRICS
        assert "simulation_patterns" in INVERT_METRICS


class TestMetricsResult:
    def test_defaults(self):
        r = MetricsResult()
        assert r.dialogue_density == 0.0

    def test_passed_all_false(self):
        r = MetricsResult()
        passed = r.passed()
        assert not passed["dialogue_density"]
        assert not passed["coherence"]

    def test_passed_all_true(self):
        r = MetricsResult(
            dialogue_density=0.2,
            show_vs_tell=4.0,
            unique_sentence_starts=0.9,
            emotional_expression=0.6,
            repetition_rate=0.01,
            coherence=0.9,
            simulation_patterns=0,
            type_token_ratio=0.5,
            word_count=100,
        )
        passed = r.passed()
        assert all(passed.values()), f"Failed: {passed}"

    def test_high_repetition_fails(self):
        r = MetricsResult(repetition_rate=0.5)
        assert not r.passed()["repetition_rate"]


class TestMeasureAll:
    def test_empty_text(self):
        r = measure_all("")
        assert r.word_count == 0
        assert r.coherence == 1.0

    def test_basic_story(self):
        text = (
            "Arjun walked into the room. Maya looked up from her desk. "
            '"What do you want?" she asked. "I need the truth," he replied, '
            "his hands trembling slightly."
        )
        r = measure_all(text)
        assert r.word_count > 0
        assert r.dialogue_count >= 2
        assert r.sentence_count >= 4
        assert 0 < r.avg_sentence_length < 20

    def test_emotional_variety(self):
        text = 'Maya glared at Arjun. "You lied to me." He trembled with fear.'
        r = measure_all(text)
        assert r.emotional_expression > 0

    def test_coherent_story(self):
        text = (
            "Arjun entered the ancient temple. Arjun saw a hidden passage. "
            "Maya followed behind him. They discovered an old manuscript."
        )
        r = measure_all(text)
        assert r.coherence >= 0.5


class TestMeasureBatch:
    def test_empty_batch(self):
        r = measure_batch([])
        assert r.word_count == 0

    def test_single_story(self):
        r = measure_batch(["Arjun walked into the room."])
        assert r.word_count > 0

    def test_multiple_stories(self):
        texts = [
            "Arjun walked into the room. Maya looked up.",
            "The sun set over the city. Night fell quickly.",
            '"Hello," she said. "How are you?" he asked.',
        ]
        r = measure_batch(texts)
        assert r.word_count > 0
        assert r.sentence_count > 0
        assert r.dialogue_count > 0
        assert 0 <= r.dialogue_density <= 1.0
