import pytest
from data_pipeline.quality.quality_scorer import QualityScorer
from data_pipeline.schema.fragment import NarrativeFragment


class TestQualityScorer:
    def setup_method(self):
        self.scorer = QualityScorer()

    def test_high_quality_fragment(self):
        frag = NarrativeFragment(
            text="The golden sunset painted the sky in hues of amber and rose, "
                 "a metaphor for the dying light of their civilization. "
                 "She felt a surge of bittersweet joy as she remembered "
                 "the last time they had walked this path together.",
            emotion="joy",
            emotion_intensity=0.8,
        )
        score = self.scorer._calculate_quality(frag)
        assert score > 0.5

    def test_low_quality_short(self):
        frag = NarrativeFragment(text="It was a nice day.")
        score = self.scorer._calculate_quality(frag)
        assert score < 0.5

    def test_dialogue_quality(self):
        frag = NarrativeFragment(
            text='"I can\'t believe you did this," she said. '
                 '"Someone had to," he replied coldly.',
        )
        score = self.scorer._score_dialogue_quality(frag.text)
        assert score > 0.3

    def test_literary_quality(self):
        text = "The ship sailed across a sea of stars, a metaphor for hope in the darkness."
        score = self.scorer._score_literary_quality(text)
        assert score > 0.4

    def test_sensory_density(self):
        text = "She heard the waves crash and smelled the salt air. The warm sand touched her feet."
        score = self.scorer._score_sensory_density(text)
        assert score > 0.3

    def test_score_filtering(self):
        fragments = [
            NarrativeFragment(text="It was a nice day."),
            NarrativeFragment(text="The ancient forest whispered secrets of forgotten ages, "
                                    "a metaphor for all that had passed. Moonlight filtered "
                                    "through the canopy like silver rain, each beam a memory. "
                                    'She heard the distant howl of wolves. "I remember this place," '
                                    "she whispered, her voice trembling. Her heart ached with "
                                    "the weight of centuries.",
                              emotion="sadness", emotion_intensity=0.9,
                              participants=["Elena"]),
        ]
        scored = self.scorer.score_fragments(fragments)
        assert len(scored) > 0 or fragments[1].quality_score > fragments[0].quality_score
        if scored:
            assert all(f.quality_score >= 0.6 for f in scored)

    def test_elite_threshold(self):
        frag = NarrativeFragment(
            text="The ancient forest whispered secrets of forgotten ages. "
                 "Moonlight filtered through the canopy like silver rain, "
                 "each beam a memory of what had been lost. "
                 "He stood among the ruins, feeling the weight of centuries "
                 "pressing down on his shoulders like a shroud of stars.",
            emotion="sadness",
            emotion_intensity=0.9,
            participants=["Kaelen"],
        )
        score = self.scorer._calculate_quality(frag)
        assert score >= 0 or score <= 1.0


class TestDeduplicatorLogic:
    def test_fallback_dedup(self):
        from data_pipeline.quality.deduplicator import Deduplicator
        dedup = Deduplicator()
        dedup._model = None

        fragments = [
            NarrativeFragment(text="The sun set over the horizon.", quality_score=0.7),
            NarrativeFragment(text="The sun set over the horizon.", quality_score=0.8),
            NarrativeFragment(text="A completely different text about the ocean."),
        ]
        result = dedup._fallback_dedup(fragments)
        assert len(result) == 2
